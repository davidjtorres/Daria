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

    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self.connection_string)

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
