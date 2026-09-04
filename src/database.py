"""Database engine and session management."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import DATABASE_URL
from src.models import Base

logger = logging.getLogger(__name__)


def make_engine(database_url: str = DATABASE_URL):
    """Create a SQLAlchemy engine, ensuring the parent directory exists
    for file-based SQLite URLs.

    Args:
        database_url: A SQLAlchemy connection URL.

    Returns:
        A configured ``Engine``.
    """
    if database_url.startswith("sqlite:///") and database_url != "sqlite:///:memory:":
        db_path = database_url.replace("sqlite:///", "", 1)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(database_url, connect_args={"check_same_thread": False} if "sqlite" in database_url else {})


def init_db(database_url: str = DATABASE_URL) -> None:
    """Create all tables if they don't already exist.

    Args:
        database_url: A SQLAlchemy connection URL.
    """
    engine = make_engine(database_url)
    Base.metadata.create_all(engine)
    logger.info("Database initialized at '%s'", database_url)


def get_session_factory(database_url: str = DATABASE_URL) -> sessionmaker[Session]:
    """Build a session factory bound to a fresh engine for the given URL.

    Args:
        database_url: A SQLAlchemy connection URL.

    Returns:
        A ``sessionmaker`` — call it to get a new ``Session``.
    """
    engine = make_engine(database_url)
    return sessionmaker(bind=engine)
