"""
Transaction repository for database operations.
"""

from datetime import datetime
from typing import Optional
from models import Transaction
from sqlalchemy_db import DatabaseEngine


class TransactionRepository:
    """Repository class for transaction database operations."""

    def __init__(self):
        """Initialize the transaction repository."""
        self.db_engine = DatabaseEngine()

    def insert_transaction(
        self,
        amount: int,
        description: str,
        category: str,
        type: str,
        date: Optional[datetime] = None,
    ) -> Transaction:
        """
        Insert a new transaction into the database.

        Args:
            amount: Amount in cents
            description: Transaction description
            category: Transaction category
            type: Transaction type ('expense' or 'income')
            date: Transaction date (defaults to current time if not provided)

        Returns:
            The created Transaction instance
        """
        # Use current time if date not provided
        if date is None:
            date = datetime.now()

        # Create transaction instance
        transaction = Transaction(
            amount=amount,
            description=description,
            category=category,
            type=type,
            date=date,
        )

        # Insert into database
        with next(self.db_engine.get_db_session()) as session:
            session.add(transaction)
            session.commit()
            session.refresh(transaction)
            return transaction
