"""
SQLModel database configuration and session management.
"""

import os
from sqlalchemy.orm import sessionmaker, Session
from sqlmodel import SQLModel, create_engine
from typing import Generator


# Create the SQLAlchemy engine
def get_database_url() -> str:
    """Get database URL from environment variables."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    return database_url


# Create engine
engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,  # Set to True for SQL query logging
)

# Create SessionLocal class
session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.

    Yields:
        Database session
    """
    db = session_local()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables in the database."""
    SQLModel.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all tables in the database."""
    SQLModel.metadata.drop_all(bind=engine)
