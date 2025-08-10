"""
SQLModel database configuration and session management.
"""

import os
from sqlalchemy.orm import sessionmaker, Session
from sqlmodel import SQLModel, create_engine
from typing import Generator


class DatabaseEngine:
    """SQLModel database engine for managing connections and sessions."""

    _instance = None
    _initialized = False

    def __new__(cls):
        """Ensure only one instance is created."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the database engine only once."""
        if not self._initialized:
            self.database_url = self._get_database_url()
            self.engine = self._create_engine()
            self.session_local = self._create_session_local()
            DatabaseEngine._initialized = True

    def _get_database_url(self) -> str:
        """Get database URL from environment variables."""
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        return database_url

    def _create_engine(self):
        """Create the SQLAlchemy engine."""
        return create_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False,  # Set to True for SQL query logging
        )

    def _create_session_local(self):
        """Create SessionLocal class."""
        return sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_db_session(self) -> Generator[Session, None, None]:
        """
        Dependency function to get database session.

        Yields:
            Database session
        """
        db = self.session_local()
        try:
            yield db
        finally:
            db.close()

    def get_session(self) -> Session:
        """Get a single database session."""
        return self.session_local()

    def create_tables(self):
        """Create all tables in the database."""
        SQLModel.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """Drop all tables in the database."""
        SQLModel.metadata.drop_all(bind=self.engine)
