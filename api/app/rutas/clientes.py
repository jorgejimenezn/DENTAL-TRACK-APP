"""Gestión de clientes.

- Admin: todo (crear, editar, activar, contraseña).
- Supervisor, Ingresos y Facturación: consultar clientes, administrar sus direcciones de entrega
  y sus datos comerciales (cliente Odoo y crédito). El crédito solo lo quita el admin.
"""
from fastapi import APIRouter, Depends, Query, Response

from app.backend import llamar
from app.esquemas import ClienteActualizar, ClienteCrear, ComercialIn, DireccionIn, EstadoIn, PasswordIn
from app.seguridad import requiere_rol, solo_admin

gestion_clientes = requiere_rol("admin", "supervisor", "ingresos", "facturacion")

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("", summary="Listar clientes")
async def listar(q: str | None = None, activo: bool | None = None, nivel: int | None = Query(None, ge=2, le=3),
                 u: dict = Depends(gestion_clientes)):
    return await llamar("GET", "/clientes", u, params={"q": q, "activo": activo, "nivel": nivel})


@router.get("/{cliente_id}", summary="Detalle de un cliente")
async def obtener(cliente_id: int, u: dict = Depends(gestion_clientes)):
    return await llamar("GET", f"/clientes/{cliente_id}", u)


@router.post("", status_code=201, summary="Crear cliente con su usuario de acceso")
async def crear(datos: ClienteCrear, u: dict = Depends(solo_admin)):
    return await llamar("POST", "/clientes", u, json=datos.model_dump())


@router.put("/{cliente_id}", summary="Editar cliente")
async def actualizar(cliente_id: int, datos: ClienteActualizar, u: dict = Depends(solo_admin)):
    return await llamar("PUT", f"/clientes/{cliente_id}", u, json=datos.model_dump())


@router.patch("/{cliente_id}/estado", summary="Activar o desactivar cliente")
async def cambiar_estado(cliente_id: int, datos: EstadoIn, u: dict = Depends(solo_admin)):
    return await llamar("PATCH", f"/clientes/{cliente_id}/estado", u, json=datos.model_dump())


@router.post("/{cliente_id}/password", status_code=204, summary="Restablecer contraseña del cliente")
async def cambiar_password(cliente_id: int, datos: PasswordIn, u: dict = Depends(solo_admin)):
    await llamar("POST", f"/clientes/{cliente_id}/password", u, json=datos.model_dump())
    return Response(status_code=204)


@router.post("/{cliente_id}/direcciones", status_code=201, summary="Agregar dirección de entrega")
async def agregar_direccion(cliente_id: int, datos: DireccionIn, u: dict = Depends(gestion_clientes)):
    return await llamar("POST", f"/clientes/{cliente_id}/direcciones", u, json=datos.model_dump())


@router.put("/{cliente_id}/direcciones/{direccion_id}", summary="Editar dirección de entrega")
async def actualizar_direccion(cliente_id: int, direccion_id: int, datos: DireccionIn,
                               u: dict = Depends(gestion_clientes)):
    return await llamar("PUT", f"/clientes/{cliente_id}/direcciones/{direccion_id}", u, json=datos.model_dump())


@router.delete("/{cliente_id}/direcciones/{direccion_id}", summary="Eliminar dirección de entrega")
async def eliminar_direccion(cliente_id: int, direccion_id: int, u: dict = Depends(gestion_clientes)):
    return await llamar("DELETE", f"/clientes/{cliente_id}/direcciones/{direccion_id}", u)


@router.patch("/{cliente_id}/comercial", summary="Cliente Odoo y crédito (admin, supervisor, ingresos, facturación)")
async def comercial(cliente_id: int, datos: ComercialIn, u: dict = Depends(gestion_clientes)):
    return await llamar("PATCH", f"/clientes/{cliente_id}/comercial", u, json=datos.model_dump())
