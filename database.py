"""
PostgreSQL database client for financial transactions.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Union
import datetime
from utils import dollars_to_cents, cents_to_dollars, validate_amount


class DatabaseClient:
    """PostgreSQL client for financial transaction management."""

    def __init__(self):
        """Initialize database connection."""
        self.connection_string = os.environ.get("DATABASE_URL")
        if not self.connection_string:
            raise ValueError("DATABASE_URL environment variable is required")

        self._create_tables()

    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self.connection_string)

    def _create_tables(self):
        """Create database tables if they don't exist."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            amount INTEGER NOT NULL, -- Store in cents
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('expense', 'income')),
            date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
        CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
        CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
        CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);
        """

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_table_sql)
                conn.commit()

    def insert_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert a new transaction into the database.

        Args:
            transaction_data: Dictionary containing transaction details
                - amount: int
                - description: str
                - category: str
                - date: str (ISO format)
                - type: str (expense/income)

        Returns:
            Dict containing the inserted transaction with amount in cents
        """
        try:
            # Ensure required fields
            required_fields = ["amount", "description", "category", "type"]
            for field in required_fields:
                if field not in transaction_data:
                    raise ValueError(f"Missing required field: {field}")

            # Set default date if not provided
            if "date" not in transaction_data:
                transaction_data["date"] = datetime.datetime.now().isoformat()

            # Insert into database
            insert_sql = """
            INSERT INTO transactions (amount, description, category, type, date, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, amount, description, category, type, date, created_at, updated_at;
            """

            current_time = datetime.datetime.now()

            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        insert_sql,
                        (
                            transaction_data["amount"],
                            transaction_data["description"],
                            transaction_data["category"],
                            transaction_data["type"],
                            transaction_data["date"],
                            current_time,
                            current_time,
                        ),
                    )

                    result = cur.fetchone()
                    conn.commit()

                    if result:
                        # Convert back to dict and format amount
                        transaction_dict = dict(result)
                        transaction_dict["amount_dollars"] = cents_to_dollars(
                            transaction_dict["amount"]
                        )
                        return transaction_dict
                    else:
                        raise Exception("Failed to insert transaction")

        except Exception as e:
            raise Exception(f"Error inserting transaction: {str(e)}")

    def query_transactions(
        self, query_params: Dict[str, Any]
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Query transactions using structured parameters.

        Args:
            query_params: Dictionary containing query parameters
                - filters: Dict with category, type, date_range, amount_range
                - aggregations: List of aggregation types
                - sort_by: String for sorting field
                - sort_order: String 'asc' or 'desc'
                - limit: Number for limiting results

        Returns:
            List of transactions or aggregated results
        """
        try:
            # Build WHERE clause
            where_conditions = []
            params = []
            param_count = 0

            filters = query_params.get("filters", {})

            if filters.get("category"):
                param_count += 1
                where_conditions.append("category = %s")
                params.append(filters["category"])

            if filters.get("type"):
                param_count += 1
                where_conditions.append("type = %s")
                params.append(filters["type"])

            if filters.get("date_range") == "this_month":
                where_conditions.append("date >= DATE_TRUNC('month', CURRENT_DATE)")
                where_conditions.append(
                    "date < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'"
                )

            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # Build ORDER BY clause
            sort_by = query_params.get("sort_by", "date")
            sort_order = query_params.get("sort_order", "desc")
            order_clause = f"ORDER BY {sort_by} {sort_order.upper()}"

            # Build LIMIT clause
            limit = query_params.get("limit")
            limit_clause = f"LIMIT {limit}" if limit else ""

            # Check if we need aggregations
            aggregations = query_params.get("aggregations", [])

            if aggregations:
                # Build aggregation query
                agg_functions = []
                for agg in aggregations:
                    if agg == "sum":
                        agg_functions.append("SUM(amount) as total_amount")
                    elif agg == "count":
                        agg_functions.append("COUNT(*) as count")
                    elif agg == "average":
                        agg_functions.append("AVG(amount) as average_amount")

                select_clause = ", ".join(agg_functions)
                sql = f"SELECT {select_clause} FROM transactions WHERE {where_clause}"

                with self._get_connection() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute(sql, params)
                        result = cur.fetchone()

                        if result:
                            # Convert amounts from cents to dollars
                            result_dict = dict(result)
                            if (
                                "total_amount" in result_dict
                                and result_dict["total_amount"]
                            ):
                                result_dict["total_amount_dollars"] = cents_to_dollars(
                                    result_dict["total_amount"]
                                )
                            if (
                                "average_amount" in result_dict
                                and result_dict["average_amount"]
                            ):
                                result_dict["average_amount_dollars"] = (
                                    cents_to_dollars(int(result_dict["average_amount"]))
                                )

                            return result_dict
                        else:
                            return {agg: 0 for agg in aggregations}
            else:
                # Regular query
                sql = f"SELECT * FROM transactions WHERE {where_clause} {order_clause} {limit_clause}".strip()

                with self._get_connection() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute(sql, params)
                        results = cur.fetchall()

                        # Convert amounts from cents to dollars
                        transactions = []
                        for row in results:
                            transaction_dict = dict(row)
                            transaction_dict["amount_dollars"] = cents_to_dollars(
                                transaction_dict["amount"]
                            )
                            transactions.append(transaction_dict)

                        return transactions

        except Exception as e:
            raise Exception(f"Error querying transactions: {str(e)}")

    def execute_sql(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute raw SQL query.

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            List of results as dictionaries
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, params)
                    results = cur.fetchall()
                    return [dict(row) for row in results]

        except Exception as e:
            raise Exception(f"Error executing SQL: {str(e)}")
