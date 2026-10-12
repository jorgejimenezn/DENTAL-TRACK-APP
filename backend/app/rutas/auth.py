"""Rutas internas de autenticación (las consume solo el servicio API)."""
from fastapi import APIRouter, Depends, Response

from app.core.dependencias import Actor, obtener_actor

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


@router.post("/salir", status_code=204, summary="Cierre de sesión (el empleado queda Desconectado)")
def salir(actor: Actor = Depends(obtener_actor), servicio: AuthServicio = Depends(servicio_auth)):
    servicio.salir(actor)
    return Response(status_code=204)


@router.post("/cerrando", status_code=204, summary="La página se cerró (posible cierre del navegador sin cerrar sesión)")
def cerrando(actor: Actor = Depends(obtener_actor), servicio: AuthServicio = Depends(servicio_auth)):
    servicio.navegador_cerrado(actor)
    return Response(status_code=204)
