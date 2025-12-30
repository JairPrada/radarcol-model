"""
Entry point for deployment platforms.
Redirects to the main FastAPI application.
"""
from app.main import app

__all__ = ["app"]
