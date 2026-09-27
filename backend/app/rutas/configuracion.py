"""Rutas internas de configuración administrable."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.dependencias import Actor, obtener_actor
from app.db.postgres import obtener_sesion
from app.esquemas.configuracion import (Arbol, AsignacionEmpleado, AsignacionIn, CatalogoCompleto, CatalogoSimple,
                                        DiaIn, DiaOut, FechaMinimaOut, FlujoIn, FlujoOut, GuiaOut, IdsIn,
                                        ItemActualizar, ItemOut, MaterialOut, Modalidad, NombreIn, Parametros,
                                        RelacionesMaterialIn, TipoOut)
from app.rutas.proveedores import servicio_auditoria
from app.servicios.auditoria_servicio import AuditoriaServicio
from app.servicios.configuracion_servicio import (AsignacionServicio, CalendarioServicio, CatalogoServicio,
                                                  FlujoServicio)

router = APIRouter(prefix="/config", tags=["Configuración"])


def _cat(s: Session = Depends(obtener_sesion), a: AuditoriaServicio = Depends(servicio_auditoria)):
    return CatalogoServicio(s, a)


def _flujos(s: Session = Depends(obtener_sesion), a: AuditoriaServicio = Depends(servicio_auditoria)):
    return FlujoServicio(s, a)


def _asig(s: Session = Depends(obtener_sesion), a: AuditoriaServicio = Depends(servicio_auditoria)):
    return AsignacionServicio(s, a)


def _cal(s: Session = Depends(obtener_sesion), a: AuditoriaServicio = Depends(servicio_auditoria)):
    return CalendarioServicio(s, a)


# ---------- Catálogos ----------
@router.get("/catalogos", response_model=CatalogoCompleto)
def catalogos(s: CatalogoServicio = Depends(_cat)):
    return s.completo()


@router.get("/arbol", response_model=Arbol)
def arbol(s: CatalogoServicio = Depends(_cat)):
    return s.arbol()


@router.post("/catalogos/{catalogo}", response_model=ItemOut, status_code=201)
def crear(catalogo: CatalogoSimple, datos: NombreIn, actor: Actor = Depends(obtener_actor),
          s: CatalogoServicio = Depends(_cat)):
    return s.crear(catalogo, datos.nombre, actor)


@router.put("/catalogos/{catalogo}/{item_id}", response_model=ItemOut)
def actualizar(catalogo: CatalogoSimple, item_id: int, datos: ItemActualizar, actor: Actor = Depends(obtener_actor),
               s: CatalogoServicio = Depends(_cat)):
    return s.actualizar(catalogo, item_id, datos.nombre, datos.activo, actor)


@router.put("/tipos/{tipo_id}/materiales", response_model=TipoOut)
def materiales_de_tipo(tipo_id: int, datos: IdsIn, actor: Actor = Depends(obtener_actor),
                       s: CatalogoServicio = Depends(_cat)):
    return s.materiales_de_tipo(tipo_id, datos.ids, actor)


@router.put("/materiales/{material_id}/relaciones", response_model=MaterialOut)
def relaciones_material(material_id: int, datos: RelacionesMaterialIn, actor: Actor = Depends(obtener_actor),
                        s: CatalogoServicio = Depends(_cat)):
    return s.relaciones_material(material_id, datos.unidad_ids, datos.guia_ids, actor)


@router.post("/guias/{guia_id}/colores", response_model=GuiaOut, status_code=201)
def crear_color(guia_id: int, datos: NombreIn, actor: Actor = Depends(obtener_actor),
                s: CatalogoServicio = Depends(_cat)):
    return s.crear_color(guia_id, datos.nombre, actor)


@router.put("/colores/{color_id}", response_model=GuiaOut)
def actualizar_color(color_id: int, datos: ItemActualizar, actor: Actor = Depends(obtener_actor),
                     s: CatalogoServicio = Depends(_cat)):
    return s.actualizar_color(color_id, datos.nombre, datos.activo, actor)


# ---------- Flujos ----------
@router.get("/flujos", response_model=list[FlujoOut])
def flujos(s: FlujoServicio = Depends(_flujos)):
    return s.listar()


@router.put("/flujos", response_model=FlujoOut)
def guardar_flujo(datos: FlujoIn, actor: Actor = Depends(obtener_actor), s: FlujoServicio = Depends(_flujos)):
    return s.guardar(datos, actor)


# ---------- Asignaciones ----------
@router.get("/asignaciones", response_model=list[AsignacionEmpleado])
def asignaciones(s: AsignacionServicio = Depends(_asig)):
    return s.listar()


@router.put("/asignaciones/{usuario_id}", response_model=AsignacionEmpleado)
def guardar_asignacion(usuario_id: int, datos: AsignacionIn, actor: Actor = Depends(obtener_actor),
                       s: AsignacionServicio = Depends(_asig)):
    return s.guardar(usuario_id, datos, actor)


# ---------- Calendario y parámetros ----------
@router.get("/calendario", response_model=list[DiaOut])
def calendario(anio: int | None = Query(None, ge=2000, le=2100), s: CalendarioServicio = Depends(_cal)):
    return s.listar(anio)


@router.post("/calendario", response_model=DiaOut, status_code=201)
def bloquear_dia(datos: DiaIn, actor: Actor = Depends(obtener_actor), s: CalendarioServicio = Depends(_cal)):
    return s.agregar(datos, actor)


@router.delete("/calendario/{dia_id}", status_code=204)
def desbloquear_dia(dia_id: int, actor: Actor = Depends(obtener_actor), s: CalendarioServicio = Depends(_cal)):
    s.eliminar(dia_id, actor)
    return Response(status_code=204)


@router.post("/calendario/feriados/{anio}", response_model=list[DiaOut])
def cargar_feriados(anio: int, actor: Actor = Depends(obtener_actor), s: CalendarioServicio = Depends(_cal)):
    return s.cargar_feriados(anio, actor)


@router.get("/parametros", response_model=Parametros)
def parametros(s: CalendarioServicio = Depends(_cal)):
    return s.parametros()


@router.put("/parametros", response_model=Parametros)
def guardar_parametros(datos: Parametros, actor: Actor = Depends(obtener_actor), s: CalendarioServicio = Depends(_cal)):
    return s.guardar_parametros(datos, actor)


@router.get("/fecha-minima", response_model=FechaMinimaOut)
def fecha_minima(modalidad: Modalidad, emergencia: bool = False, ahora: datetime | None = None,
                 s: CalendarioServicio = Depends(_cal)):
    return s.fecha_minima(modalidad, emergencia, ahora)
