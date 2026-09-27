"""Rutas internas de la bandeja de trabajo y las acciones sobre cada paso del recorrido."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.dependencias import Actor, obtener_actor
from app.db.postgres import obtener_sesion
from app.esquemas.bandeja import (AsignarIn, Bandeja, CancelarIn, Candidato, ModificacionIn, RechazoIn, TerminarIn,
                                  ValidacionRpIn)
from app.rutas.proveedores import servicio_auditoria
from app.servicios.auditoria_servicio import AuditoriaServicio
from app.servicios.produccion_servicio import ProduccionServicio

router = APIRouter(tags=["Bandeja"])


def _servicio(sesion: Session = Depends(obtener_sesion),
              auditoria: AuditoriaServicio = Depends(servicio_auditoria)) -> ProduccionServicio:
    return ProduccionServicio(sesion, auditoria)


@router.get("/bandeja", response_model=Bandeja)
def bandeja(area_id: int | None = None, actor: Actor = Depends(obtener_actor),
            s: ProduccionServicio = Depends(_servicio)):
    return s.bandeja(actor, area_id)


@router.post("/pasos/{paso_id}/iniciar", status_code=204)
def iniciar(paso_id: int, actor: Actor = Depends(obtener_actor), s: ProduccionServicio = Depends(_servicio)):
    s.iniciar(paso_id, actor)
    return Response(status_code=204)


@router.post("/pasos/{paso_id}/terminar", status_code=204)
def terminar(paso_id: int, datos: TerminarIn, actor: Actor = Depends(obtener_actor),
             s: ProduccionServicio = Depends(_servicio)):
    s.terminar(paso_id, datos, actor)
    return Response(status_code=204)


@router.post("/pasos/{paso_id}/validar-rp", status_code=204)
def validar_rp(paso_id: int, datos: ValidacionRpIn, actor: Actor = Depends(obtener_actor),
               s: ProduccionServicio = Depends(_servicio)):
    s.validar_rp(paso_id, datos, actor)
    return Response(status_code=204)


@router.post("/pasos/{paso_id}/rechazar", status_code=204)
def rechazar(paso_id: int, datos: RechazoIn, actor: Actor = Depends(obtener_actor),
             s: ProduccionServicio = Depends(_servicio)):
    s.rechazar(paso_id, datos, actor)
    return Response(status_code=204)


@router.put("/pasos/{paso_id}/modificar", status_code=204)
def modificar(paso_id: int, datos: ModificacionIn, actor: Actor = Depends(obtener_actor),
              s: ProduccionServicio = Depends(_servicio)):
    s.modificar(paso_id, datos, actor)
    return Response(status_code=204)


@router.post("/pasos/{paso_id}/cancelar", status_code=204)
def cancelar(paso_id: int, datos: CancelarIn, actor: Actor = Depends(obtener_actor),
             s: ProduccionServicio = Depends(_servicio)):
    s.cancelar(paso_id, datos.motivo, actor)
    return Response(status_code=204)


@router.get("/pasos/{paso_id}/candidatos", response_model=list[Candidato])
def candidatos(paso_id: int, actor: Actor = Depends(obtener_actor), s: ProduccionServicio = Depends(_servicio)):
    return s.candidatos(paso_id, actor)


@router.post("/pasos/{paso_id}/asignar", status_code=204)
def asignar(paso_id: int, datos: AsignarIn, actor: Actor = Depends(obtener_actor),
            s: ProduccionServicio = Depends(_servicio)):
    s.asignar(paso_id, datos, actor)
    return Response(status_code=204)


@router.post("/pasos/{paso_id}/no-se-pudo", status_code=204)
def no_se_pudo(paso_id: int, datos: CancelarIn, actor: Actor = Depends(obtener_actor),
               s: ProduccionServicio = Depends(_servicio)):
    s.no_se_pudo(paso_id, datos.motivo, actor)
    return Response(status_code=204)
