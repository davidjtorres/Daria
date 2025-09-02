from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import tool
from database import DatabaseClient
from utils import dollars_to_cents, validate_amount
from constants import TransactionCategory
from datetime import datetime
from repositories import TransactionRepository


class FinancialAgent:
    """LangChain agent for financial transaction management."""

    def __init__(self):
        """Initialize the financial agent."""
        self.llm = ChatOpenAI(model="gpt-4o-mini")
        self.db = DatabaseClient()
        self.transaction_repository = TransactionRepository()
        self.agent = self._create_agent()

    def _create_agent(self):
        """Create the LangChain agent with tools."""

        # Create tool functions that can access the agent instance
        @tool
        def insert_transaction_tool(
            amount: float,
            description: str,
            category: str,
            transaction_type: str,
            date: str,
        ) -> str:
            """Insert a new transaction into the database."""
            try:
                # convert date to iso format
                transaction_date = datetime.strptime(date, "%Y-%m-%d")

                # Validate and convert amount to cents
                validate_amount(amount)
                amount_cents = dollars_to_cents(amount)

                # Create and insert transaction using TransactionRepository
                transaction = self.transaction_repository.insert_transaction(
                    amount=amount_cents,
                    description=description,
                    category=category,
                    type=transaction_type,
                    date=transaction_date,
                )

                return (
                    f"Successfully recorded {transaction_type} of ${amount:.2f} "
                    f"for {description} in category '{category}'. "
                    f"Transaction ID: {transaction.id}"
                )

            except Exception as e:
                return f"Error inserting transaction: {str(e)}"

        @tool
        def query_transactions_tool(query: str) -> str:
            """Query transactions using natural language."""
            try:
                # Use LLM to translate natural language to SQL
                sql_prompt = f"""
                Translate this natural language query to SQL: "{query}"
                
                The transactions table has these columns:
                - id (SERIAL PRIMARY KEY)
                - amount (INTEGER, stored in cents)
                - description (TEXT)
                - category (TEXT)
                - type (TEXT, either 'expense' or 'income')
                - date (TIMESTAMP WITH TIME ZONE)
                - created_at (TIMESTAMP WITH TIME ZONE)
                - updated_at (TIMESTAMP WITH TIME ZONE)
                
                Important notes:
                - Amount is stored in cents, so $10.50 is stored as 1050
                - Use amount/100.0 to convert cents to dollars for display
                - Types are: expense, income
                
                Return ONLY the raw SQL query as a plain string. Do not use markdown 
                formatting, code blocks, or any other formatting. Just the SQL query itself.
                """

                response = self.llm.invoke(sql_prompt)
                sql_query = str(response.content).strip()

                print(f"Generated SQL: {sql_query}")

                # Execute the SQL query
                results = self.db.execute_sql(sql_query)

                return str(results)

            except Exception as e:
                return f"Error querying transactions: {str(e)}"

        # Define the tools
        tools = [
            insert_transaction_tool,
            query_transactions_tool,
        ]

        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    f"""You are a financial assistant that helps users manage their transactions.

            Your job is to understand user requests and determine the appropriate action:

            1. If the user is describing a transaction they want to record 
               (e.g., "I spent $50 on groceries"), use the insert_transaction_tool to store it. 
               The category should be one of the following: {[category.value for category in TransactionCategory]}
               - Consider that the current date is {datetime.now().isoformat()} and the date should be in the format YYYY-MM-DD
               - User might provide the time of transaction with words like "yesterday", "today", 
                 "last week", "last month", "last year", etc.
               - If the user provides the time of transaction with words, convert it to the format YYYY-MM-DD
               - If the user provides the time of transaction with a date, use it as is.

            2. If the user is asking about their transactions (e.g., "How much did I spend on food?"), 
               use the query_transactions_tool to retrieve information. if query_transactions_tool returns a None, 
               say that spending was 0.

            Always be helpful and provide clear responses about what you're doing.
            """,
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        # Create the agent
        agent = create_openai_functions_agent(llm=self.llm, tools=tools, prompt=prompt)

        return AgentExecutor(
            agent=agent, tools=tools, verbose=True, handle_parsing_errors=True
        )

    def chat(
        self, message: str, chat_history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Process a chat message and return a response.

        Args:
            message: User's message
            chat_history: Previous chat messages

        Returns:
            Agent's response
        """
        if chat_history is None:
            chat_history = []

        try:
            result = self.agent.invoke({"input": message, "chat_history": chat_history})

            return result["output"]

        except Exception as e:
            return f"Error processing your request: {str(e)}"
