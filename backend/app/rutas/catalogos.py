"""Rutas internas de catálogos y bitácora."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.validaciones import DEPARTAMENTOS
from app.db.postgres import obtener_sesion
from app.esquemas.comun import AreaOut
from app.repositorios.area_repo import AreaRepositorio
from app.core.dependencias import Actor, obtener_actor
from app.rutas.proveedores import servicio_auditoria
from app.servicios.auditoria_servicio import AuditoriaServicio

router = APIRouter(tags=["Catálogos y bitácora"])


@router.get("/areas", response_model=list[AreaOut])
def listar_areas(sesion: Session = Depends(obtener_sesion)):
    return [AreaOut(id=a.id, nombre=a.nombre) for a in AreaRepositorio(sesion).listar_activas()]


@router.get("/departamentos", response_model=list[str])
def listar_departamentos():
    return sorted(DEPARTAMENTOS)


@router.get("/auditoria")
def listar_auditoria(limite: int = Query(100, ge=1, le=500), entidad: str | None = None,
                     accion: str | None = None, s: AuditoriaServicio = Depends(servicio_auditoria),
                     actor: Actor = Depends(obtener_actor)):
    return s.listar(limite, entidad, accion, actor)
