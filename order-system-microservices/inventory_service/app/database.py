from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Get DB connection string from environment variables.
DATABASE_URL = os.getenv("DATABASE_URL")

# Create the SQLAlchemy engine.
engine = create_engine(DATABASE_URL)

# Create a configured "Session" class.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models.
Base = declarative_base()

def get_db():
    """Dependency to get a DB session for a request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        # Ensure the session is closed after use.
        db.close()
