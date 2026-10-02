"""Rutas internas de gestión: áreas y metas, ausencias, cobros y métricas."""
from datetime import date

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.dependencias import Actor, obtener_actor
from app.db.postgres import obtener_sesion
from app.esquemas.gestion import AreaOperacionIn, AusenciaIn, PagoIn
from app.rutas.proveedores import servicio_auditoria
from app.servicios.auditoria_servicio import AuditoriaServicio
from app.servicios.gestion_servicio import GestionServicio, TableroServicio

router = APIRouter(tags=["Gestión"])


def _servicio(sesion: Session = Depends(obtener_sesion),
              auditoria: AuditoriaServicio = Depends(servicio_auditoria)) -> GestionServicio:
    return GestionServicio(sesion, auditoria)


@router.get("/config/areas-operacion")
def areas(s: GestionServicio = Depends(_servicio)):
    return s.areas()


@router.put("/config/areas-operacion/{area_id}")
def guardar_area(area_id: int, datos: AreaOperacionIn, actor: Actor = Depends(obtener_actor),
                 s: GestionServicio = Depends(_servicio)):
    return s.guardar_area(area_id, datos.lote, datos.max_simultaneos, datos.meta_horas, actor)


@router.get("/ausencias")
def ausencias(todas: bool = False, actor: Actor = Depends(obtener_actor), s: GestionServicio = Depends(_servicio)):
    return s.ausencias(actor, todas)


@router.post("/ausencias", status_code=201)
def registrar_ausencia(datos: AusenciaIn, actor: Actor = Depends(obtener_actor),
                       s: GestionServicio = Depends(_servicio)):
    return s.registrar_ausencia(datos.usuario_id, datos.desde, datos.hasta, datos.motivo, actor)


@router.delete("/ausencias/{ausencia_id}", status_code=204)
def quitar_ausencia(ausencia_id: int, actor: Actor = Depends(obtener_actor), s: GestionServicio = Depends(_servicio)):
    s.quitar_ausencia(ausencia_id, actor)
    return Response(status_code=204)


@router.get("/cobros")
def cobros(actor: Actor = Depends(obtener_actor), s: GestionServicio = Depends(_servicio)):
    return s.cobros(actor)


@router.post("/cobros/{solicitud_id}/pagar", status_code=204)
def pagar(solicitud_id: int, datos: PagoIn, actor: Actor = Depends(obtener_actor),
          s: GestionServicio = Depends(_servicio)):
    s.pagar(solicitud_id, datos.fecha, datos.referencia, actor)
    return Response(status_code=204)


@router.get("/metricas/operacion")
def operacion(desde: date | None = None, hasta: date | None = None, actor: Actor = Depends(obtener_actor),
              s: GestionServicio = Depends(_servicio)):
    return s.operacion(actor, desde, hasta)


@router.get("/metricas/mias")
def mias(actor: Actor = Depends(obtener_actor), s: GestionServicio = Depends(_servicio)):
    return s.mias(actor)


@router.get("/agenda-entregas")
def agenda(actor: Actor = Depends(obtener_actor), sesion: Session = Depends(obtener_sesion)):
    return TableroServicio(sesion).agenda(actor)


@router.get("/metricas/mapa")
def mapa(capa: str, desde: date | None = None, hasta: date | None = None, tipo_trabajo_id: int | None = None,
         material_id: int | None = None, actor: Actor = Depends(obtener_actor), sesion: Session = Depends(obtener_sesion)):
    return TableroServicio(sesion).mapa(actor, capa, desde, hasta, tipo_trabajo_id, material_id)
