from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings

# SQLAlchemy 2.x Engine
engine = create_engine(
    settings.sqlalchemy_database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

# Session factory for DB interactions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Declarative Base for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for providing SQLAlchemy DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
