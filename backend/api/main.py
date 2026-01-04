"""
FastAPI Main Application
This is the entry point for your REST API server
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

# Import database connection
from database import get_db, engine
# Import routers
from routes import signals, entries, dashboard, symbols, settings, live_prices

# Create FastAPI app instance

app = FastAPI(
    title="Trading Dashboard API",
    description="REST API for trading signals and entry tracking",
    version="1.0.0"
)

# CORS Configuration
# CORS = Cross-Origin Resource Sharing
# This allows your React app (running on port 5173) to talk to this API (running on port 8000)
# Without this, browsers will block the requests for security reasons
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://20.20.20.132:5173",  # Your React app
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Allow all headers
)
# Include routers
app.include_router(signals.router)
app.include_router(entries.router)
app.include_router(dashboard.router)
app.include_router(symbols.router)
app.include_router(settings.router)
app.include_router(live_prices.router)
# Root endpoint - just to test if API is running
# When you visit http://localhost:8000/ you'll see this message
@app.get("/")
async def root():
    """
    Root endpoint - health check
    """
    return {
        "message": "Trading Dashboard API is running!",
        "version": "1.0.0",
        "status": "healthy"
    }

# Health check endpoint
# This is useful for monitoring if your API is alive
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint with database verification
    """
    try:
        # Test database connection
        result = db.execute(text("SELECT 1")).fetchone()
        db_status = "connected" if result else "disconnected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status
    }

# API Info endpoint
# Returns information about available endpoints
@app.get("/api/info")
async def api_info():
    """
    API information
    """
    return {
        "name": "Trading Dashboard API",
        "version": "1.0.0",
        "endpoints": {
            "signals": "/api/signals",
            "entries": "/api/entries",
            "symbols": "/api/symbols",
            "dashboard": "/api/dashboard"
        }
    }