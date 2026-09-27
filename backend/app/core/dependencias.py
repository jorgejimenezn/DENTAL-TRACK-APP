"""Dependencias comunes: protección por clave interna y datos del usuario que actúa."""
from dataclasses import dataclass

from fastapi import Header, HTTPException

from app.core.config import config


def verificar_clave_interna(x_internal_key: str = Header(default="")):
    """Solo el servicio API conoce esta clave: nadie más puede llamar al backend."""
    if x_internal_key != config.INTERNAL_KEY:
        raise HTTPException(status_code=403, detail="Acceso solo desde el servicio API")


@dataclass
class Actor:
    id: int | None
    email: str | None


def obtener_actor(x_usuario_id: str | None = Header(default=None),
                  x_usuario_email: str | None = Header(default=None)) -> Actor:
    """La API envía quién hizo la petición para registrarlo en la bitácora."""
    return Actor(id=int(x_usuario_id) if x_usuario_id and x_usuario_id.isdigit() else None,
                 email=x_usuario_email)
