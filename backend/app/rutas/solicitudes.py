"""Rutas internas de solicitudes (CN / RP) y archivos adjuntos."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencias import Actor, obtener_actor
from app.db.mongo import obtener_mongo
from app.db.postgres import obtener_sesion
from app.esquemas.solicitud import (ArchivoOut, ClienteBreve, EstadoIn, PerfilSolicitud, ReaperturaIn, SolicitudIn,
                                    SolicitudOut, SolicitudResumen)
from app.repositorios.archivo_repo import ArchivoRepositorio
from app.rutas.proveedores import servicio_auditoria
from app.servicios.auditoria_servicio import AuditoriaServicio
from app.servicios.solicitud_servicio import SolicitudServicio

router = APIRouter(tags=["Solicitudes"])


def _servicio(sesion: Session = Depends(obtener_sesion),
              auditoria: AuditoriaServicio = Depends(servicio_auditoria)) -> SolicitudServicio:
    return SolicitudServicio(sesion, auditoria, ArchivoRepositorio(obtener_mongo()))


# ---------- Archivos ----------
@router.post("/archivos", response_model=ArchivoOut, status_code=201)
async def subir_archivo(archivo: UploadFile = File(...), actor: Actor = Depends(obtener_actor),
                        s: SolicitudServicio = Depends(_servicio)):
    contenido = await archivo.read()
    return s.subir_archivo(contenido, archivo.filename, archivo.content_type, actor)


@router.delete("/archivos/{archivo_id}", status_code=204)
def quitar_archivo(archivo_id: str, actor: Actor = Depends(obtener_actor), s: SolicitudServicio = Depends(_servicio)):
    s.quitar_archivo(archivo_id, actor)
    return Response(status_code=204)


# ---------- Datos para el formulario ----------
@router.get("/solicitudes/clientes", response_model=list[ClienteBreve])
def clientes(actor: Actor = Depends(obtener_actor), s: SolicitudServicio = Depends(_servicio)):
    return s.clientes(actor)


@router.get("/solicitudes/perfil", response_model=PerfilSolicitud)
def perfil(cliente_id: int | None = None, actor: Actor = Depends(obtener_actor),
           s: SolicitudServicio = Depends(_servicio)):
    return s.perfil(actor, cliente_id)


# ---------- Solicitudes ----------
@router.get("/solicitudes", response_model=list[SolicitudResumen])
def listar(vigentes: bool | None = None, estado: str | None = None, tipo_caso: str | None = None,
           q: str | None = None, cliente_id: int | None = None, limite: int = Query(200, ge=1, le=500),
           actor: Actor = Depends(obtener_actor), s: SolicitudServicio = Depends(_servicio)):
    return s.listar(actor, vigentes, estado, tipo_caso, q, cliente_id, limite)


@router.post("/solicitudes", response_model=SolicitudOut, status_code=201)
def crear(datos: SolicitudIn, actor: Actor = Depends(obtener_actor), s: SolicitudServicio = Depends(_servicio)):
    return s.crear(datos, actor)


@router.get("/solicitudes/{solicitud_id}", response_model=SolicitudOut)
def obtener(solicitud_id: int, actor: Actor = Depends(obtener_actor), s: SolicitudServicio = Depends(_servicio)):
    return s.obtener(solicitud_id, actor)


@router.post("/solicitudes/{solicitud_id}/reapertura", response_model=SolicitudOut, status_code=201)
def reabrir(solicitud_id: int, datos: ReaperturaIn, actor: Actor = Depends(obtener_actor),
            s: SolicitudServicio = Depends(_servicio)):
    return s.reabrir(solicitud_id, datos, actor)


@router.patch("/solicitudes/{solicitud_id}/estado", response_model=SolicitudOut)
def cambiar_estado(solicitud_id: int, datos: EstadoIn, actor: Actor = Depends(obtener_actor),
                   s: SolicitudServicio = Depends(_servicio)):
    return s.cambiar_estado(solicitud_id, datos.estado, datos.nota, actor)


@router.get("/solicitudes/{solicitud_id}/archivos/{archivo_id}")
def descargar(solicitud_id: int, archivo_id: str, actor: Actor = Depends(obtener_actor),
              s: SolicitudServicio = Depends(_servicio)):
    archivo = s.descargar(solicitud_id, archivo_id, actor)
    return StreamingResponse(
        iter(lambda: archivo.read(1024 * 1024), b""),
        media_type=archivo.content_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(archivo.filename)}",
                 "Content-Length": str(archivo.length)})
