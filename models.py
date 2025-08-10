"""
SQLModel models for the financial application.
"""

from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class Transaction(SQLModel, table=True):
    """SQLModel model for financial transactions."""

    __tablename__ = "transactions"

    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)

    # Transaction details
    amount: int = Field(description="Amount stored in cents")
    description: str
    category: str
    type: str = Field(description="Transaction type: 'expense' or 'income'")

    # Timestamps
    date: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def __repr__(self) -> str:
        """String representation of Transaction."""
        return f"<Transaction(id={self.id}, type='{self.type}', amount={self.amount}, description='{self.description}')>"

    def to_dict(self) -> dict:
        """Convert Transaction to dictionary."""
        return {
            "id": self.id,
            "amount": self.amount,
            "description": self.description,
            "category": self.category,
            "type": self.type,
            "date": self.date.isoformat() if self.date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def amount_in_dollars(self) -> float:
        """Get amount in dollars (converted from cents)."""
        return self.amount / 100.0

    @classmethod
    def from_dollars(cls, amount_dollars: float, **kwargs) -> "Transaction":
        """Create Transaction with amount in dollars (converts to cents)."""
        amount_cents = int(amount_dollars * 100)
        return cls(amount=amount_cents, **kwargs)

    @classmethod
    def insert(
        cls,
        amount: int,
        description: str,
        category: str,
        type: str,
        date: Optional[datetime] = None,
        db_session=None,
    ) -> "Transaction":
        """
        Insert a new transaction into the database.

        Args:
            amount: Amount in cents
            description: Transaction description
            category: Transaction category
            type: Transaction type ('expense' or 'income')
            date: Transaction date (defaults to current time if not provided)
            db_session: Database session (if not provided, will create one)

        Returns:
            The created Transaction instance
        """
        from sqlalchemy_db import get_db_session

        # Use current time if date not provided
        if date is None:
            date = datetime.now()

        # Create transaction instance
        transaction = cls(
            amount=amount,
            description=description,
            category=category,
            type=type,
            date=date,
        )

        # Handle database session
        should_close_session = False
        if db_session is None:
            db_session = next(get_db_session())
            should_close_session = True

        try:
            db_session.add(transaction)
            db_session.commit()
            db_session.refresh(transaction)
            return transaction
        finally:
            if should_close_session:
                db_session.close()
