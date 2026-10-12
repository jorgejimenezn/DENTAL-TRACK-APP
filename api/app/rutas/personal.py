"""Estado del personal: conectado, refacción, almuerzo, capacitación y desconectado.

- Cada empleado (técnico, mensajero, Ingresos, QA, Facturación, Logística) cambia su propio estado y solicita capacitación.
- El reparto automático solo asigna trabajo nuevo a quien está Conectado.
- Administración y supervisión ven a todo el personal, autorizan capacitaciones (con o sin reparto) y corrigen estados.
- Operaciones y el perfil demo solo consultan.
"""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.backend import llamar
from app.seguridad import requiere_rol, usuario_actual

router = APIRouter(tags=["Personal"])
consulta = requiere_rol("admin", "supervisor", "operaciones", "demo")
supervision = requiere_rol("admin", "supervisor")


class EstadoIn(BaseModel):
    estado: Literal["conectado", "refaccion", "almuerzo", "desconectado"] = Field(
        description="La capacitación no se elige aquí: se solicita y la autoriza el supervisor")


class SolicitudCapacitacionIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=200, examples=["Capacitación en el nuevo escáner"])


class ResolverCapacitacionIn(BaseModel):
    autorizar: bool = Field(default=True, description="false = rechazar la solicitud")
    con_reparto: bool = Field(default=False, description="true = lo asignado sin iniciar pasa a otros")
    motivo: str | None = Field(default=None, max_length=200, description="Obligatorio si no hay solicitud previa")


@router.get("/mi-estado", summary="Mi estado actual y si recibo trabajo")
async def mi_estado(u: dict = Depends(usuario_actual)):
    return await llamar("GET", "/mi-estado", u)


@router.put("/mi-estado", summary="Cambiar mi estado (conectado, refacción, almuerzo o desconectado)")
async def cambiar_mi_estado(datos: EstadoIn, u: dict = Depends(usuario_actual)):
    return await llamar("PUT", "/mi-estado", u, json=datos.model_dump())


@router.post("/mi-estado/capacitacion", summary="Solicitar capacitación (queda pendiente de autorización)")
async def solicitar_capacitacion(datos: SolicitudCapacitacionIn, u: dict = Depends(usuario_actual)):
    return await llamar("POST", "/mi-estado/capacitacion", u, json=datos.model_dump())


@router.delete("/mi-estado/capacitacion", summary="Cancelar mi solicitud de capacitación")
async def cancelar_capacitacion(u: dict = Depends(usuario_actual)):
    return await llamar("DELETE", "/mi-estado/capacitacion", u)


@router.get("/personal/estados", summary="Estado del personal en este momento (supervisión)")
async def tablero(u: dict = Depends(consulta)):
    return await llamar("GET", "/personal/estados", u)


@router.get("/personal/estados/historial", summary="Auditoría de estados: periodos y minutos por persona")
async def historial(desde: date | None = None, hasta: date | None = None, usuario_id: int | None = None,
                    u: dict = Depends(consulta)):
    return await llamar("GET", "/personal/estados/historial", u,
                        params={"desde": desde, "hasta": hasta, "usuario_id": usuario_id})


@router.post("/personal/{usuario_id}/capacitacion", summary="Autorizar (con o sin reparto) o rechazar una capacitación")
async def resolver_capacitacion(usuario_id: int, datos: ResolverCapacitacionIn, u: dict = Depends(supervision)):
    return await llamar("POST", f"/personal/{usuario_id}/capacitacion", u, json=datos.model_dump())


@router.put("/personal/{usuario_id}/estado", summary="Cambiar el estado de un empleado (terminar capacitación, corregir)")
async def asignar_estado(usuario_id: int, datos: EstadoIn, u: dict = Depends(supervision)):
    return await llamar("PUT", f"/personal/{usuario_id}/estado", u, json=datos.model_dump())
