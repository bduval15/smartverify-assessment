import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

class Base(DeclarativeBase):
    pass

if __name__ == "__main__":
    try:
        with engine.connect() as connection:
            print("Connected to your PostgreSQL database via Supabase.")
    except Exception as e:
        print(f"Connection failed!\nError: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()