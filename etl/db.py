"""Database connection helpers."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from etl.models import Base

DB_PATH = os.environ.get("DB_PATH", "energy_grid.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    """Create all tables if they don't already exist."""
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
