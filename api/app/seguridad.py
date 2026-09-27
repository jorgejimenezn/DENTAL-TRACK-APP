"""Tokens JWT y control de acceso por rol."""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.backend import llamar
from app.config import config

esquema_bearer = HTTPBearer(auto_error=False, description="Token obtenido en POST /auth/login")


def crear_token(usuario: dict) -> tuple[str, datetime]:
    expira = datetime.now(timezone.utc) + timedelta(hours=config.JWT_HORAS)
    datos = {"sub": str(usuario["id"]), "rol": usuario["rol"], "email": usuario["email"], "exp": expira}
    return jwt.encode(datos, config.JWT_SECRET, algorithm="HS256"), expira


async def usuario_actual(credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer)) -> dict:
    if not credenciales:
        raise HTTPException(status_code=401, detail="Debes iniciar sesión")
    try:
        datos = jwt.decode(credenciales.credentials, config.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Tu sesión expiró, vuelve a iniciar sesión")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Sesión no válida")
    # Se consulta al backend para que un usuario desactivado pierda el acceso de inmediato
    return await llamar("GET", f"/auth/usuarios/{datos['sub']}")


def requiere_rol(*roles: str):
    async def verificar(usuario: dict = Depends(usuario_actual)) -> dict:
        if usuario["rol"] not in roles:
            raise HTTPException(status_code=403, detail="No tienes permiso para esta acción")
        return usuario
    return verificar


solo_admin = requiere_rol("admin")
