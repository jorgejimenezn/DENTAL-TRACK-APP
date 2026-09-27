"""Conexión a PostgreSQL (base relacional) con SQLAlchemy."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import config

# Railway entrega postgres:// o postgresql://; usamos siempre el driver psycopg (v3)
_url = config.DATABASE_URL
for prefijo in ("postgres://", "postgresql://"):
    if _url.startswith(prefijo):
        _url = "postgresql+psycopg://" + _url[len(prefijo):]
        break

engine = create_engine(_url, pool_pre_ping=True)
SesionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def obtener_sesion():
    sesion = SesionLocal()
    try:
        yield sesion
    finally:
        sesion.close()
