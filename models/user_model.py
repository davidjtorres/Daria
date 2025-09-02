"""
SQLModel models for user management with AWS Cognito integration.
"""

from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class User(SQLModel, table=True):
    """SQLModel model for users with AWS Cognito integration."""

    __tablename__ = "users"

    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)

    # AWS Cognito reference - stores the 'sub' field from Cognito
    cognito_user_id: str = Field(unique=True, description="AWS Cognito user identifier (sub)")

    # User details
    email: str = Field(unique=True)
    username: str = Field(unique=True)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def __repr__(self) -> str:
        """String representation of User."""
        return (
            f"<User(id={self.id}, username='{self.username}', "
            f"email='{self.email}', cognito_user_id='{self.cognito_user_id}')>"
        )

    def to_dict(self) -> dict:
        """Convert User to dictionary."""
        return {
            "id": self.id,
            "cognito_user_id": self.cognito_user_id,
            "email": self.email,
            "username": self.username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_cognito_user(cls, cognito_user_info: dict, **kwargs) -> "User":
        """Create User from Cognito UserInfo data.

        Args:
            cognito_user_info: Dictionary containing Cognito user data with 'sub', 'username', 'email'
            **kwargs: Additional fields to set

        Returns:
            User instance
        """
        return cls(
            cognito_user_id=cognito_user_info['sub'],
            username=cognito_user_info['username'],
            email=cognito_user_info['email'],
            **kwargs
        )
