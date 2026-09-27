"""Rutas internas de autenticación (las consume solo el servicio API)."""
from fastapi import APIRouter, Depends

from app.esquemas.cliente import RegistroCliente
from app.esquemas.comun import CredencialesIn, UsuarioSesion
from app.rutas.proveedores import servicio_auth, servicio_clientes
from app.servicios.auth_servicio import AuthServicio
from app.servicios.cliente_servicio import ClienteServicio

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/verificar", response_model=UsuarioSesion, summary="Validar credenciales")
def verificar(datos: CredencialesIn, servicio: AuthServicio = Depends(servicio_auth)):
    return servicio.verificar(datos.email, datos.password)


@router.get("/usuarios/{usuario_id}", response_model=UsuarioSesion, summary="Usuario activo de una sesión")
def usuario_activo(usuario_id: int, servicio: AuthServicio = Depends(servicio_auth)):
    return servicio.usuario_activo(usuario_id)


@router.post("/registro", response_model=UsuarioSesion, status_code=201, summary="Auto-registro de cliente")
def registro(datos: RegistroCliente, clientes: ClienteServicio = Depends(servicio_clientes),
             auth: AuthServicio = Depends(servicio_auth)):
    cliente = clientes.registrar(datos)
    return auth.usuario_activo(cliente.usuario_id)
