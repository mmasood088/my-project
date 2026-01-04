"""
Database Connection
Reuses the same database connection from your automation scripts
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Database connection string
# This connects to the same PostgreSQL database you've been using
DATABASE_URL = "postgresql://postgres:trading123@localhost:5432/trading_db"

# Create engine
# Think of this as creating a "phone line" to your database
engine = create_engine(
    DATABASE_URL,
    pool_size=10,  # Keep 10 connections ready
    max_overflow=20,  # Can create 20 more if needed
    pool_pre_ping=True,  # Check if connection is alive before using
    echo=False  # Set to True to see SQL queries in console (useful for debugging)
)

# Create session maker
# A session is like a "conversation" with the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency function
# This will be used in API endpoints to get a database connection
def get_db():
    """
    Get database session
    
    Usage in API endpoint:
        @app.get("/something")
        async def endpoint(db: Session = Depends(get_db)):
            # Use db here
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()