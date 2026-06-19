# backend/app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Connect directly to your local Postgres
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# This dependency gives our routes a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()