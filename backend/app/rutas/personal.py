"""Rutas internas: estado del personal (conectado, refacción, almuerzo, capacitación, desconectado)."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencias import Actor, obtener_actor
from app.db.postgres import obtener_sesion
from app.rutas.proveedores import servicio_auditoria
from app.servicios.auditoria_servicio import AuditoriaServicio
from app.servicios.estados_personal import EstadosPersonal

router = APIRouter(tags=["Personal"])


class EstadoIn(BaseModel):
    estado: Literal["conectado", "refaccion", "almuerzo", "desconectado"]


class SolicitudCapacitacionIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=200)


class ResolverCapacitacionIn(BaseModel):
    autorizar: bool = True
    con_reparto: bool = False
    motivo: str | None = Field(default=None, max_length=200)


def _servicio(sesion: Session = Depends(obtener_sesion),
              auditoria: AuditoriaServicio = Depends(servicio_auditoria)) -> EstadosPersonal:
    return EstadosPersonal(sesion, auditoria)


@router.get("/mi-estado")
def mi_estado(actor: Actor = Depends(obtener_actor), s: EstadosPersonal = Depends(_servicio)):
    return s.mi_estado(actor)


@router.put("/mi-estado")
def cambiar_mi_estado(datos: EstadoIn, actor: Actor = Depends(obtener_actor), s: EstadosPersonal = Depends(_servicio)):
    return s.cambiar_mio(datos.estado, actor)


@router.post("/mi-estado/capacitacion")
def solicitar_capacitacion(datos: SolicitudCapacitacionIn, actor: Actor = Depends(obtener_actor),
                           s: EstadosPersonal = Depends(_servicio)):
    return s.solicitar_capacitacion(datos.motivo, actor)


@router.delete("/mi-estado/capacitacion")
def cancelar_capacitacion(actor: Actor = Depends(obtener_actor), s: EstadosPersonal = Depends(_servicio)):
    return s.cancelar_solicitud(actor)


@router.get("/personal/estados")
def tablero(actor: Actor = Depends(obtener_actor), s: EstadosPersonal = Depends(_servicio)):
    return s.tablero(actor)


@router.get("/personal/estados/historial")
def historial(desde: date | None = None, hasta: date | None = None, usuario_id: int | None = None,
              actor: Actor = Depends(obtener_actor), s: EstadosPersonal = Depends(_servicio)):
    return s.historial(actor, desde, hasta, usuario_id)


@router.post("/personal/{usuario_id}/capacitacion")
def resolver_capacitacion(usuario_id: int, datos: ResolverCapacitacionIn, actor: Actor = Depends(obtener_actor),
                          s: EstadosPersonal = Depends(_servicio)):
    return s.resolver_capacitacion(usuario_id, datos.autorizar, datos.con_reparto, datos.motivo, actor)


@router.put("/personal/{usuario_id}/estado")
def asignar_estado(usuario_id: int, datos: EstadoIn, actor: Actor = Depends(obtener_actor),
                   s: EstadosPersonal = Depends(_servicio)):
    return s.asignar_estado(usuario_id, datos.estado, actor)
