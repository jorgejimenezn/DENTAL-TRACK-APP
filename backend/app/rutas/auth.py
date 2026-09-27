"""Rutas internas de autenticación (las consume solo el servicio API)."""
from fastapi import APIRouter, Depends

from app.esquemas.comun import CredencialesIn, UsuarioSesion
from app.rutas.proveedores import servicio_auth
from app.servicios.auth_servicio import AuthServicio

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/verificar", response_model=UsuarioSesion, summary="Validar credenciales")
def verificar(datos: CredencialesIn, servicio: AuthServicio = Depends(servicio_auth)):
    return servicio.verificar(datos.email, datos.password)


@router.get("/usuarios/{usuario_id}", response_model=UsuarioSesion, summary="Usuario activo de una sesión")
def usuario_activo(usuario_id: int, servicio: AuthServicio = Depends(servicio_auth)):
    return servicio.usuario_activo(usuario_id)
