"""Inicio de sesión: el backend valida credenciales y la API emite el token JWT."""
from fastapi import APIRouter, Depends

from app.backend import llamar
from app.esquemas import LoginIn, TokenOut, UsuarioOut
from app.seguridad import crear_token, usuario_actual

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenOut, summary="Iniciar sesión")
async def login(datos: LoginIn):
    usuario = await llamar("POST", "/auth/verificar", json=datos.model_dump())
    token, expira = crear_token(usuario)
    return TokenOut(access_token=token, expira_en=expira.isoformat(), usuario=usuario)


@router.get("/yo", response_model=UsuarioOut, summary="Usuario de la sesión actual")
async def yo(usuario: dict = Depends(usuario_actual)):
    return usuario
