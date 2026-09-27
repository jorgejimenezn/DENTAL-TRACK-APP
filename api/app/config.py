"""Configuración del servicio API (pública)."""
import os


class Config:
    # URL privada del backend dentro de Railway, ej. http://backend.railway.internal:8000
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8001").rstrip("/")
    INTERNAL_KEY: str = os.getenv("INTERNAL_KEY", "cambia-esta-clave-interna")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "cambia-este-secreto-jwt")
    JWT_HORAS: int = int(os.getenv("JWT_HORAS", "10"))
    # Orígenes permitidos (URL pública del frontend). Separar varios con coma.
    CORS_ORIGINS: list[str] = [o.strip().rstrip("/") for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]


config = Config()
