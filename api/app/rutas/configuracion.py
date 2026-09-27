"""Configuración administrable: catálogos, flujos, asignaciones, calendario y parámetros.

Lectura del árbol de catálogos, parámetros, calendario y fecha mínima: cualquier usuario con sesión
(los usarán los formularios de solicitud). Todo lo demás: solo administradores.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response

from app.backend import llamar
from app.esquemas import (AsignacionIn, CatalogoSimple, DiaIn, FlujoIn, IdsIn, ItemActualizar, Modalidad, NombreIn,
                          ParametrosIn, RelacionesMaterialIn)
from app.seguridad import solo_admin, usuario_actual

router = APIRouter(prefix="/config", tags=["Configuración"])


# ---------- Catálogos ----------
@router.get("/catalogos", summary="Todos los catálogos con sus relaciones (incluye inactivos)")
async def catalogos(u: dict = Depends(solo_admin)):
    return await llamar("GET", "/config/catalogos", u)


@router.get("/arbol", summary="Catálogo activo y anidado para formularios")
async def arbol(u: dict = Depends(usuario_actual)):
    return await llamar("GET", "/config/arbol", u)


@router.post("/catalogos/{catalogo}", status_code=201, summary="Agregar elemento a un catálogo")
async def crear(catalogo: CatalogoSimple, datos: NombreIn, u: dict = Depends(solo_admin)):
    return await llamar("POST", f"/config/catalogos/{catalogo}", u, json=datos.model_dump())


@router.put("/catalogos/{catalogo}/{item_id}", summary="Renombrar o activar/desactivar")
async def actualizar(catalogo: CatalogoSimple, item_id: int, datos: ItemActualizar, u: dict = Depends(solo_admin)):
    return await llamar("PUT", f"/config/catalogos/{catalogo}/{item_id}", u, json=datos.model_dump())


@router.put("/tipos/{tipo_id}/materiales", summary="Materiales permitidos para un tipo de trabajo")
async def materiales_de_tipo(tipo_id: int, datos: IdsIn, u: dict = Depends(solo_admin)):
    return await llamar("PUT", f"/config/tipos/{tipo_id}/materiales", u, json=datos.model_dump())


@router.put("/materiales/{material_id}/relaciones", summary="Unidades y guías de color de un material")
async def relaciones_material(material_id: int, datos: RelacionesMaterialIn, u: dict = Depends(solo_admin)):
    return await llamar("PUT", f"/config/materiales/{material_id}/relaciones", u, json=datos.model_dump())


@router.post("/guias/{guia_id}/colores", status_code=201, summary="Agregar color a una guía")
async def crear_color(guia_id: int, datos: NombreIn, u: dict = Depends(solo_admin)):
    return await llamar("POST", f"/config/guias/{guia_id}/colores", u, json=datos.model_dump())


@router.put("/colores/{color_id}", summary="Renombrar o activar/desactivar un color")
async def actualizar_color(color_id: int, datos: ItemActualizar, u: dict = Depends(solo_admin)):
    return await llamar("PUT", f"/config/colores/{color_id}", u, json=datos.model_dump())


# ---------- Flujos ----------
@router.get("/flujos", summary="Flujos de pasos con cobertura de técnicos")
async def flujos(u: dict = Depends(solo_admin)):
    return await llamar("GET", "/config/flujos", u)


@router.put("/flujos", summary="Crear o reemplazar el flujo de un tipo de trabajo y modalidad")
async def guardar_flujo(datos: FlujoIn, u: dict = Depends(solo_admin)):
    return await llamar("PUT", "/config/flujos", u, json=datos.model_dump())


# ---------- Asignaciones ----------
@router.get("/asignaciones", summary="Áreas y tipos de trabajo que atiende cada empleado")
async def asignaciones(u: dict = Depends(solo_admin)):
    return await llamar("GET", "/config/asignaciones", u)


@router.put("/asignaciones/{usuario_id}", summary="Restringir tipos de trabajo por área de un empleado")
async def guardar_asignacion(usuario_id: int, datos: AsignacionIn, u: dict = Depends(solo_admin)):
    return await llamar("PUT", f"/config/asignaciones/{usuario_id}", u, json=datos.model_dump())


# ---------- Calendario y parámetros ----------
@router.get("/calendario", summary="Días no laborables")
async def calendario(anio: int | None = Query(None, ge=2000, le=2100), u: dict = Depends(usuario_actual)):
    return await llamar("GET", "/config/calendario", u, params={"anio": anio})


@router.post("/calendario", status_code=201, summary="Bloquear un día")
async def bloquear_dia(datos: DiaIn, u: dict = Depends(solo_admin)):
    return await llamar("POST", "/config/calendario", u, json=datos.model_dump(mode="json"))


@router.delete("/calendario/{dia_id}", status_code=204, summary="Desbloquear un día")
async def desbloquear_dia(dia_id: int, u: dict = Depends(solo_admin)):
    await llamar("DELETE", f"/config/calendario/{dia_id}", u)
    return Response(status_code=204)


@router.post("/calendario/feriados/{anio}", summary="Cargar feriados oficiales de Guatemala de un año")
async def cargar_feriados(anio: int, u: dict = Depends(solo_admin)):
    return await llamar("POST", f"/config/calendario/feriados/{anio}", u)


@router.get("/parametros", summary="Horas de corte y días mínimos de entrega")
async def parametros(u: dict = Depends(usuario_actual)):
    return await llamar("GET", "/config/parametros", u)


@router.put("/parametros", summary="Actualizar horas de corte y días mínimos")
async def guardar_parametros(datos: ParametrosIn, u: dict = Depends(solo_admin)):
    return await llamar("PUT", "/config/parametros", u, json=datos.model_dump())


@router.get("/fecha-minima", summary="Primera fecha de entrega posible según las reglas")
async def fecha_minima(modalidad: Modalidad, emergencia: bool = False, ahora: datetime | None = None,
                       u: dict = Depends(usuario_actual)):
    params = {"modalidad": modalidad, "emergencia": str(emergencia).lower(),
              "ahora": ahora.isoformat() if ahora else None}
    return await llamar("GET", "/config/fecha-minima", u, params=params)
