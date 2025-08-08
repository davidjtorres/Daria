from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import tool
from database import DatabaseClient
from utils import dollars_to_cents, validate_amount


class FinancialAgent:
    """LangChain agent for financial transaction management."""

    def __init__(self):
        """Initialize the financial agent."""
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.db = DatabaseClient()
        self.agent = self._create_agent()

    def _create_agent(self):
        """Create the LangChain agent with tools."""

        # Create tool functions that can access the agent instance
        @tool
        def insert_transaction_tool(
            amount: float, description: str, category: str, transaction_type: str
        ) -> str:
            """Insert a new transaction into the database."""
            try:
                # Validate and convert amount to cents
                validate_amount(amount)
                amount_cents = dollars_to_cents(amount)

                # Prepare transaction data
                transaction_data = {
                    "amount": amount_cents,
                    "description": description,
                    "category": category,
                    "type": transaction_type,
                }

                print(transaction_data)

                # Insert into database
                result = self.db.insert_transaction(transaction_data)

                return (
                    f"Successfully recorded {transaction_type} of ${amount:.2f} "
                    f"for {description} in category '{category}'. "
                    f"Transaction ID: {result['id']}"
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
                - Categories include: technology, food, shopping, transportation, entertainment, health, utilities
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

        @tool
        def extract_transaction_tool(text: str) -> str:
            """Extract transaction details from natural language text."""
            try:
                # Use the LLM to extract transaction details
                extraction_prompt = f"""
                Extract transaction details from the following text: "{text}"
                
                Return a JSON object with these fields:
                - amount: float (the transaction amount)
                - description: string (what the transaction was for)
                - category: string (category like food, shopping, transportation, etc.)
                - type: string (either "expense" or "income")
                
                If any information is missing, make reasonable assumptions.
                """

                response = self.llm.invoke(extraction_prompt)

                # Try to parse the response as JSON
                import json
                import re

                # Extract JSON from the response
                json_match = re.search(r"\{.*\}", str(response.content), re.DOTALL)
                if json_match:
                    transaction_data = json.loads(json_match.group())
                    return f"Extracted transaction: {json.dumps(transaction_data, indent=2)}"
                else:
                    return f"Could not extract transaction details from: {text}"

            except Exception as e:
                return f"Error extracting transaction: {str(e)}"

        # Define the tools
        tools = [
            insert_transaction_tool,
            query_transactions_tool,
            extract_transaction_tool,
        ]

        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a financial assistant that helps users manage their transactions.
            
            Your job is to understand user requests and determine the appropriate action:
            
            1. If the user is describing a transaction they want to record (e.g., "I spent $50 on groceries"), 
               use the insert_transaction_tool to store it.
            
            2. If the user is asking about their transactions (e.g., "How much did I spend on food?"), 
               use the query_transactions_tool to retrieve information. if query_transactions_tool returns a None, say that spendiing was 0.
            
            3. If the user is asking you to extract transaction details from text, 
               use the extract_transaction_tool.
            
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
