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
                # Parse the query into structured parameters
                query_params = self._parse_query(query)

                # Execute the query
                results = self.db.query_transactions(query_params)

                # Format the response
                if isinstance(results, dict) and any(
                    key in results
                    for key in ["total_amount", "count", "average_amount"]
                ):
                    # Aggregation results
                    response_parts = []
                    if "total_amount_dollars" in results:
                        response_parts.append(
                            f"Total: ${results['total_amount_dollars']:.2f}"
                        )
                    if "count" in results:
                        response_parts.append(f"Count: {results['count']} transactions")
                    if "average_amount_dollars" in results:
                        response_parts.append(
                            f"Average: ${results['average_amount_dollars']:.2f}"
                        )

                    return f"Query results: {' | '.join(response_parts)}"
                else:
                    # List of transactions
                    if not results:
                        return "No transactions found matching your query."

                    response_parts = [f"Found {len(results)} transactions:"]
                    # Show first 5 transactions
                    first_five = results[:5] if isinstance(results, list) else []
                    for i, transaction in enumerate(first_five, 1):
                        amount = transaction.get(
                            "amount_dollars", transaction.get("amount", 0) / 100
                        )
                        response_parts.append(
                            f"{i}. ${amount:.2f} - {transaction['description']} "
                            f"({transaction['category']})"
                        )

                    if len(results) > 5:
                        response_parts.append(
                            f"... and {len(results) - 5} more transactions"
                        )

                    return "\n".join(response_parts)

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
               use the query_transactions_tool to retrieve information.
            
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

    def _parse_query(self, query: str) -> Dict[str, Any]:
        """
        Parse natural language query into structured parameters.
        """
        # Simple keyword-based parsing (can be enhanced with LLM)
        query_lower = query.lower()

        # Extract category
        category_mapping = {
            "technology": ["tech", "computer", "laptop", "software", "technology"],
            "food": [
                "food",
                "restaurant",
                "coffee",
                "lunch",
                "dinner",
                "breakfast",
                "groceries",
            ],
            "shopping": ["shopping", "clothes", "amazon", "store", "purchase"],
            "transportation": ["uber", "lyft", "gas", "fuel", "transportation", "car"],
            "entertainment": ["movie", "netflix", "spotify", "entertainment"],
            "health": ["medical", "doctor", "pharmacy", "health"],
            "utilities": ["electricity", "water", "internet", "phone", "utilities"],
        }

        detected_category = None
        for category, keywords in category_mapping.items():
            if any(keyword in query_lower for keyword in keywords):
                detected_category = category
                break

        # Detect query type
        query_type = None
        if any(
            word in query_lower for word in ["spent", "spending", "expense", "cost"]
        ):
            query_type = "expense"
        elif any(
            word in query_lower for word in ["earned", "income", "salary", "revenue"]
        ):
            query_type = "income"

        # Detect aggregation
        aggregations = []
        if any(word in query_lower for word in ["total", "sum", "how much"]):
            aggregations.append("sum")
        elif any(word in query_lower for word in ["average", "avg"]):
            aggregations.append("average")
        elif any(word in query_lower for word in ["count", "how many"]):
            aggregations.append("count")

        # Detect time range
        date_range = None
        if any(
            word in query_lower for word in ["this month", "month", "current month"]
        ):
            date_range = "this_month"

        return {
            "filters": {
                "category": detected_category,
                "type": query_type,
                "date_range": date_range,
            },
            "aggregations": aggregations,
            "sort_by": "date",
            "sort_order": "desc",
        }

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
