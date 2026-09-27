"""Rutas internas de clientes."""
from fastapi import APIRouter, Depends, Query

from app.core.dependencias import Actor, obtener_actor
from app.esquemas.cliente import ClienteActualizar, ClienteCrear, ClienteOut, DireccionIn
from app.esquemas.comun import EstadoIn, PasswordIn
from app.rutas.proveedores import servicio_clientes
from app.servicios.cliente_servicio import ClienteServicio

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("", response_model=list[ClienteOut])
def listar(q: str | None = None, activo: bool | None = None, nivel: int | None = Query(None, ge=2, le=3),
           s: ClienteServicio = Depends(servicio_clientes)):
    return s.listar(q, activo, nivel)


@router.get("/{cliente_id}", response_model=ClienteOut)
def obtener(cliente_id: int, s: ClienteServicio = Depends(servicio_clientes)):
    return s.obtener(cliente_id)


@router.post("", response_model=ClienteOut, status_code=201)
def crear(datos: ClienteCrear, actor: Actor = Depends(obtener_actor),
          s: ClienteServicio = Depends(servicio_clientes)):
    return s.crear(datos, actor)


@router.put("/{cliente_id}", response_model=ClienteOut)
def actualizar(cliente_id: int, datos: ClienteActualizar, actor: Actor = Depends(obtener_actor),
               s: ClienteServicio = Depends(servicio_clientes)):
    return s.actualizar(cliente_id, datos, actor)


@router.patch("/{cliente_id}/estado", response_model=ClienteOut)
def cambiar_estado(cliente_id: int, datos: EstadoIn, actor: Actor = Depends(obtener_actor),
                   s: ClienteServicio = Depends(servicio_clientes)):
    return s.cambiar_estado(cliente_id, datos.activo, actor)


@router.post("/{cliente_id}/password", status_code=204)
def cambiar_password(cliente_id: int, datos: PasswordIn, actor: Actor = Depends(obtener_actor),
                     s: ClienteServicio = Depends(servicio_clientes)):
    s.cambiar_password(cliente_id, datos.password, actor)


@router.post("/{cliente_id}/direcciones", response_model=ClienteOut, status_code=201)
def agregar_direccion(cliente_id: int, datos: DireccionIn, actor: Actor = Depends(obtener_actor),
                      s: ClienteServicio = Depends(servicio_clientes)):
    return s.agregar_direccion(cliente_id, datos, actor)


@router.put("/{cliente_id}/direcciones/{direccion_id}", response_model=ClienteOut)
def actualizar_direccion(cliente_id: int, direccion_id: int, datos: DireccionIn,
                         actor: Actor = Depends(obtener_actor), s: ClienteServicio = Depends(servicio_clientes)):
    return s.actualizar_direccion(cliente_id, direccion_id, datos, actor)


@router.delete("/{cliente_id}/direcciones/{direccion_id}", response_model=ClienteOut)
def eliminar_direccion(cliente_id: int, direccion_id: int, actor: Actor = Depends(obtener_actor),
                       s: ClienteServicio = Depends(servicio_clientes)):
    return s.eliminar_direccion(cliente_id, direccion_id, actor)
