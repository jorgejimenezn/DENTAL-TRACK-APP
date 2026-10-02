"""Gestión de la operación: áreas y metas, ausencias, cobros y métricas.

- Áreas y metas: solo admin (lote, simultáneos por técnico, meta en horas laborales).
- Ausencias: admin y supervisor (el reparto no asigna a quien no labora y reparte lo que tenía sin iniciar).
- Cobros: facturación, admin y supervisor (operaciones solo consulta).
- Métricas de operación: admin, supervisor y operaciones. Métricas personales: cada empleado las suyas.
"""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Response

from app.backend import llamar
from app.esquemas import AreaOperacionIn, AusenciaIn, PagoIn
from app.seguridad import requiere_rol, solo_admin, usuario_actual

router = APIRouter(tags=["Gestión"])
supervision = requiere_rol("admin", "supervisor")
metricas = requiere_rol("admin", "supervisor", "operaciones", "demo")
cobranza = requiere_rol("admin", "supervisor", "facturacion", "operaciones", "demo")


@router.get("/config/areas-operacion", summary="Áreas con su modo lote, simultáneos y meta de horas")
async def areas(u: dict = Depends(usuario_actual)):
    return await llamar("GET", "/config/areas-operacion", u)


@router.put("/config/areas-operacion/{area_id}", summary="Editar lote, simultáneos y meta de un área")
async def guardar_area(area_id: int, datos: AreaOperacionIn, u: dict = Depends(solo_admin)):
    return await llamar("PUT", f"/config/areas-operacion/{area_id}", u, json=datos.model_dump())


@router.get("/ausencias", summary="Ausencias registradas (últimos 30 días y futuras)")
async def ausencias(todas: bool = False, u: dict = Depends(requiere_rol("admin", "supervisor", "operaciones", "demo"))):
    return await llamar("GET", "/ausencias", u, params={"todas": str(todas).lower()})


@router.post("/ausencias", status_code=201, summary="Registrar que un empleado no labora")
async def registrar_ausencia(datos: AusenciaIn, u: dict = Depends(supervision)):
    return await llamar("POST", "/ausencias", u, json=datos.model_dump(mode="json"))


@router.delete("/ausencias/{ausencia_id}", status_code=204, summary="Quitar una ausencia")
async def quitar_ausencia(ausencia_id: int, u: dict = Depends(supervision)):
    await llamar("DELETE", f"/ausencias/{ausencia_id}", u)
    return Response(status_code=204)


@router.get("/cobros", summary="Pendientes de pago por antigüedad (Hoy, 1-5, 6-10, 11-15, +15 días)")
async def cobros(u: dict = Depends(cobranza)):
    return await llamar("GET", "/cobros", u)


@router.post("/cobros/{solicitud_id}/pagar", status_code=204, summary="Marcar factura como pagada")
async def pagar(solicitud_id: int, datos: PagoIn, u: dict = Depends(requiere_rol("admin", "supervisor", "facturacion"))):
    await llamar("POST", f"/cobros/{solicitud_id}/pagar", u, json=datos.model_dump(mode="json"))
    return Response(status_code=204)


@router.get("/metricas/operacion", summary="Dashboard de operación: en vivo y desempeño del periodo")
async def operacion(desde: date | None = None, hasta: date | None = None, u: dict = Depends(metricas)):
    return await llamar("GET", "/metricas/operacion", u,
                        params={"desde": desde.isoformat() if desde else None, "hasta": hasta.isoformat() if hasta else None})


@router.get("/metricas/mias", summary="Mis métricas personales (solo mis datos)")
async def mias(u: dict = Depends(usuario_actual)):
    return await llamar("GET", "/metricas/mias", u)


@router.get("/agenda-entregas", summary="Agenda de entregas: atrasados, hoy, siguiente día hábil, próximos y listos para salir")
async def agenda(u: dict = Depends(requiere_rol("admin", "supervisor", "operaciones", "demo", "logistica"))):
    return await llamar("GET", "/agenda-entregas", u)


@router.get("/metricas/mapa", summary="Mapa de calor de entregas o recolectas (puntos por zona o municipio)")
async def mapa(capa: Literal["entregas", "recolectas"], desde: date | None = None, hasta: date | None = None,
               tipo_trabajo_id: int | None = None, material_id: int | None = None, u: dict = Depends(metricas)):
    return await llamar("GET", "/metricas/mapa", u, params={
        "capa": capa, "desde": desde and str(desde), "hasta": hasta and str(hasta),
        "tipo_trabajo_id": tipo_trabajo_id, "material_id": material_id})
