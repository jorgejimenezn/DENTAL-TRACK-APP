"""Inicio de sesión: el backend valida credenciales y la API emite el token JWT."""
import jwt
from fastapi import APIRouter, Depends, Request, Response

from app.backend import llamar
from app.esquemas import LoginIn, RegistroIn, TokenOut, UsuarioOut
from app.config import config
from app.seguridad import crear_token, usuario_actual

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenOut, summary="Iniciar sesión")
async def login(datos: LoginIn):
    usuario = await llamar("POST", "/auth/verificar", json=datos.model_dump())
    token, expira = crear_token(usuario)
    return TokenOut(access_token=token, expira_en=expira.isoformat(), usuario=usuario)


@router.post("/registro", response_model=TokenOut, status_code=201, summary="Crear cuenta de cliente")
async def registro(datos: RegistroIn):
    """Registro público desde el login. Siempre crea un cliente con prioridad normal y deja la sesión iniciada."""
    usuario = await llamar("POST", "/auth/registro", json=datos.model_dump())
    token, expira = crear_token(usuario)
    return TokenOut(access_token=token, expira_en=expira.isoformat(), usuario=usuario)


@router.get("/yo", response_model=UsuarioOut, summary="Usuario de la sesión actual")
async def yo(usuario: dict = Depends(usuario_actual)):
    return usuario


@router.post("/salir", status_code=204, summary="Cerrar sesión (el empleado queda Desconectado)")
async def salir(usuario: dict = Depends(usuario_actual)):
    await llamar("POST", "/auth/salir", usuario)
    return Response(status_code=204)


@router.post("/cerrando", status_code=204, include_in_schema=False)
async def cerrando(request: Request):
    """Aviso de la página al cerrarse (navigator.sendBeacon). Lleva el token en el cuerpo porque sendBeacon no envía
    cabeceras. Si el empleado no vuelve a usar el sistema en 3 minutos, queda Desconectado."""
    token = (await request.body())[:4000].decode(errors="ignore").strip()
    try:
        datos = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
        await llamar("POST", "/auth/cerrando", {"id": int(datos["sub"]), "email": datos.get("email"), "rol": datos.get("rol")})
    except Exception:  # token vencido o inválido: no se hace nada
        pass
    return Response(status_code=204)
