"""# Import routers
import importlib, sys
_routers = [
    ("routes.auth", "auth_router"),
    ("routes.documents", "documents_router"),
    ("routes.chat", "chat_router"),
]
for _mod, _alias in _routers:
    try:
        _m = importlib.import_module(_mod)
        globals()[_alias] = _m.router
    except Exception as e:
        print(f"IMPORT ERROR {_mod}: {e}", file=sys.stderr)
        raise
Norma Facile 2.0 - Server Entry Point
This file imports the app from main.py for supervisor compatibility.
"""
from main import app

# Re-export app for uvicorn
__all__ = ["app"]
