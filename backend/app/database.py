import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker

load_dotenv()


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required")
    return database_url


DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL)

# Supabase already owns the table schema, so startup opens request-scoped
# sessions but deliberately does not call create_all or run migrations.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

class Base(DeclarativeBase):
    pass


def get_db():
    # One session per request prevents transaction state leaking between users.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
