"""Catálogos de consulta y bitácora de auditoría."""
from fastapi import APIRouter, Depends, Query

from app.backend import llamar
from app.seguridad import solo_admin, usuario_actual

router = APIRouter(tags=["Catálogos y bitácora"])


@router.get("/areas", summary="Áreas del laboratorio")
async def areas(u: dict = Depends(usuario_actual)):
    return await llamar("GET", "/areas", u)


@router.get("/departamentos", summary="Departamentos de Guatemala")
async def departamentos(u: dict = Depends(usuario_actual)):
    return await llamar("GET", "/departamentos", u)


@router.get("/auditoria", summary="Bitácora de eventos (MongoDB)")
async def auditoria(limite: int = Query(100, ge=1, le=500), entidad: str | None = None,
                    accion: str | None = None, u: dict = Depends(solo_admin)):
    return await llamar("GET", "/auditoria", u, params={"limite": limite, "entidad": entidad, "accion": accion})
