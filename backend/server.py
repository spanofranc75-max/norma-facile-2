"""
Norma Facile 2.0 - Server Entry Point
This file imports the app from main.py for supervisor compatibility.
"""
from main import app

# Re-export app for uvicorn
__all__ = ["app"]
