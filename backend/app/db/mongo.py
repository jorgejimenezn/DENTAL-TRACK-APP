"""Conexión a MongoDB (base no relacional) para la bitácora de auditoría."""
from pymongo import MongoClient

from app.core.config import config

_cliente = None


def obtener_mongo():
    global _cliente
    if _cliente is None:
        if config.MONGO_URL.startswith("mongomock://"):
            # Solo para pruebas locales sin servidor Mongo
            import mongomock
            _cliente = mongomock.MongoClient()
        else:
            _cliente = MongoClient(config.MONGO_URL, serverSelectionTimeoutMS=5000)
    return _cliente[config.MONGO_DB]
