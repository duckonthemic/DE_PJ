"""
Database connector utilities
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings


def get_source_engine():
    """Get SQLAlchemy engine for source database"""
    settings = get_settings()
    return create_engine(settings.source_db_url, pool_pre_ping=True)


def get_dw_engine():
    """Get SQLAlchemy engine for data warehouse"""
    settings = get_settings()
    return create_engine(settings.dw_db_url, pool_pre_ping=True)


@contextmanager
def get_source_session() -> Generator[Session, None, None]:
    """Get database session for source database"""
    engine = get_source_engine()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_dw_session() -> Generator[Session, None, None]:
    """Get database session for data warehouse"""
    engine = get_dw_engine()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
