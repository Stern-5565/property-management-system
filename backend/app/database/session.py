"""SQLAlchemy engine and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.sqlalchemy_database_uri, pool_pre_ping=True, echo=settings.app_debug)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class every SQLAlchemy model inherits from."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a database session, always closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
