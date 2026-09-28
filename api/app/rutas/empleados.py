"""Administración de empleados (solo administradores)."""
from fastapi import APIRouter, Depends, Response

from app.backend import llamar
from app.esquemas import EmpleadoActualizar, EmpleadoCrear, EstadoIn, PasswordIn
from app.seguridad import lectura_admin, requiere_rol, solo_admin

router = APIRouter(prefix="/empleados", tags=["Empleados"])
PRIVADOS = ("email", "telefono", "direccion")  # el perfil demo no ve datos de contacto del personal


def _para(u: dict, empleado: dict) -> dict:
    return {**empleado, **{k: None for k in PRIVADOS if k in empleado}} if u["rol"] == "demo" else empleado


@router.get("", summary="Listar empleados")
async def listar(q: str | None = None, rol: str | None = None, activo: bool | None = None,
                 u: dict = Depends(requiere_rol("admin", "supervisor", "demo"))):
    lista = await llamar("GET", "/empleados", u, params={"q": q, "rol": rol, "activo": activo})
    return [_para(u, e) for e in lista]


@router.get("/{empleado_id}", summary="Detalle de un empleado")
async def obtener(empleado_id: int, u: dict = Depends(lectura_admin)):
    return _para(u, await llamar("GET", f"/empleados/{empleado_id}", u))


@router.post("", status_code=201, summary="Crear empleado")
async def crear(datos: EmpleadoCrear, u: dict = Depends(solo_admin)):
    return await llamar("POST", "/empleados", u, json=datos.model_dump())


@router.put("/{empleado_id}", summary="Editar empleado, rol y áreas")
async def actualizar(empleado_id: int, datos: EmpleadoActualizar, u: dict = Depends(solo_admin)):
    return await llamar("PUT", f"/empleados/{empleado_id}", u, json=datos.model_dump())


@router.patch("/{empleado_id}/estado", summary="Activar o desactivar empleado")
async def cambiar_estado(empleado_id: int, datos: EstadoIn, u: dict = Depends(solo_admin)):
    return await llamar("PATCH", f"/empleados/{empleado_id}/estado", u, json=datos.model_dump())


@router.post("/{empleado_id}/password", status_code=204, summary="Restablecer contraseña")
async def cambiar_password(empleado_id: int, datos: PasswordIn, u: dict = Depends(solo_admin)):
    await llamar("POST", f"/empleados/{empleado_id}/password", u, json=datos.model_dump())
    return Response(status_code=204)
