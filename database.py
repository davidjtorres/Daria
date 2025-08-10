"""
PostgreSQL database client for financial transactions.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any


class DatabaseClient:
    """PostgreSQL client for financial transaction management."""

    def __init__(self):
        """Initialize database connection."""
        self.connection_string = os.environ.get("AGENT_DATABASE_URL")
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

    def execute_sql(self, sql: str) -> List[Dict[str, Any]]:
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
                    cur.execute(sql)
                    results = cur.fetchall()
                    return [dict(row) for row in results]

        except Exception as e:
            raise Exception(f"Error executing SQL: {str(e)}")
