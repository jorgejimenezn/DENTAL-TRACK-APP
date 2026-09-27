"""Punto de entrada alternativo: permite que `uvicorn main:app` (comando automático de Railway)
levante el mismo servidor definido en server.py."""
from server import app  # noqa: F401
