"""PostgreSQL connection manager using psycopg3 + SQLAlchemy."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    """Return the DATABASE_URL from environment, defaulting to local arlo db."""
    return os.environ.get("DATABASE_URL", "postgresql://localhost/arlo")


def get_engine(url: str | None = None):
    """Create a SQLAlchemy engine for the given (or default) database URL."""
    return create_engine(url or get_database_url())


def get_session(engine=None):
    """Create a new SQLAlchemy session, optionally bound to a specific engine."""
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
