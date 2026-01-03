from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Get DB connection string from environment variables.
# Defaults to the payment-database service defined in docker-compose.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@payment-database:5432/payment_database")

# Create the SQLAlchemy engine.
engine = create_engine(DATABASE_URL)

# Create a configured "Session" class for database interactions.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative ORM models.
Base = declarative_base()

def get_db():
    """Dependency to get a DB session for a single request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        # Ensure the session is always closed after the request is finished.
        db.close()