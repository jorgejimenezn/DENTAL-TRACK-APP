"""Configuración del servicio backend (se lee de variables de entorno de Railway)."""
import os


class Config:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/dentaltrack")
    MONGO_URL: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    MONGO_DB: str = os.getenv("MONGO_DB") or "dentaltrack"  # vacío también usa el valor por defecto
    # Clave compartida solo entre API y backend (red privada de Railway)
    INTERNAL_KEY: str = os.getenv("INTERNAL_KEY", "cambia-esta-clave-interna")
    # Primer administrador (se crea solo si no existe ningún admin)
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@dentaltrack.com")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "Admin123!")
    ADMIN_NOMBRE: str = os.getenv("ADMIN_NOMBRE", "Administrador")


config = Config()
