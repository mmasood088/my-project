"""
Database Connection Module
Handles PostgreSQL connections using SQLAlchemy
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# ============================================
# DATABASE CONFIGURATION
# ============================================

DB_USER = "postgres"
DB_PASSWORD = "trading123"
DB_HOST = "127.0.0.1"  # Use IP for TCP/IP connection
DB_PORT = "5432"
DB_NAME = "trading_db"

# Connection string
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ============================================
# SQLALCHEMY SETUP
# ============================================

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_size=10,           # Connection pool size
    max_overflow=20,        # Extra connections if needed
    pool_pre_ping=True,     # Test connection before using
    echo=False              # Set True to see SQL queries in console
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_db():
    """
    Get database session
    Usage:
        db = get_db()
        try:
            # Your database operations
            db.execute(...)
            db.commit()
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e

def test_connection():
    """
    Test database connection
    Returns: True if connected, False otherwise
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✓ Database connection successful!")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def get_table_count():
    """
    Get count of all tables in database
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT COUNT(*) as table_count 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            count = result.fetchone()[0]
            print(f"✓ Found {count} tables in database")
            return count
    except Exception as e:
        print(f"✗ Error getting table count: {e}")
        return 0

def get_table_names():
    """
    Get list of all table names
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            print(f"✓ Tables: {', '.join(tables)}")
            return tables
    except Exception as e:
        print(f"✗ Error getting table names: {e}")
        return []

# ============================================
# MAIN TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE CONNECTION TEST")
    print("=" * 60)
    print()
    
    # Test 1: Basic connection
    print("Test 1: Testing connection...")
    test_connection()
    print()
    
    # Test 2: Count tables
    print("Test 2: Counting tables...")
    get_table_count()
    print()
    
    # Test 3: List tables
    print("Test 3: Listing table names...")
    get_table_names()
    print()
    
    # Test 4: Query settings
    print("Test 4: Reading settings table...")
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT * FROM settings LIMIT 5"))
            print("Settings:")
            for row in result:
                print(f"  - {row[1]}: {row[2][:50]}...")  # key: value (truncated)
        print("✓ Settings query successful!")
    except Exception as e:
        print(f"✗ Settings query failed: {e}")
    
    print()
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)