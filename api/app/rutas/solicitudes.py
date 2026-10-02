"""Solicitudes de trabajo: casos nuevos (CN), reaperturas (RP) y archivos adjuntos.

- El doctor solo ve y crea solicitudes de su propia cuenta (el backend lo garantiza).
- Admin, supervisor e ingresos pueden capturar solicitudes a nombre de un cliente.
- El resto del personal puede consultarlas.
- Los archivos se suben primero (POST /archivos) y luego se envían sus IDs en la solicitud.
"""
from datetime import date

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile

from app.backend import descargar, llamar
from app.esquemas import MotivoIn, PrioridadIn, ReanudarIn, ReaperturaIn, SolicitudIn
from app.seguridad import requiere_rol, usuario_actual

router = APIRouter(tags=["Solicitudes"])
admin_o_supervisor = requiere_rol("admin", "supervisor")


# ---------- Archivos ----------
@router.post("/archivos", status_code=201, summary="Subir un archivo (STL máx. 80 MB; JPG, PNG o PDF máx. 15 MB)")
async def subir_archivo(archivo: UploadFile = File(...), u: dict = Depends(usuario_actual)):
    contenido = await archivo.read()
    return await llamar("POST", "/archivos", u, files={"archivo": (archivo.filename, contenido, archivo.content_type)},
                        timeout=180)


@router.delete("/archivos/{archivo_id}", status_code=204, summary="Quitar un archivo que aún no se envió")
async def quitar_archivo(archivo_id: str, u: dict = Depends(usuario_actual)):
    await llamar("DELETE", f"/archivos/{archivo_id}", u)
    return Response(status_code=204)


# ---------- Datos para el formulario ----------
@router.get("/solicitudes/clientes", summary="Clientes activos (para capturar a nombre de un cliente)")
async def clientes(u: dict = Depends(usuario_actual)):
    return await llamar("GET", "/solicitudes/clientes", u)


@router.get("/solicitudes/perfil", summary="Direcciones y doctores del cliente para el formulario")
async def perfil(cliente_id: int | None = None, u: dict = Depends(usuario_actual)):
    return await llamar("GET", "/solicitudes/perfil", u, params={"cliente_id": cliente_id})


# ---------- Solicitudes ----------
@router.get("/solicitudes/tablero", summary="Tablero Kanban: vigentes por columna y entregados recientes")
async def tablero(dias: int = Query(15, ge=1, le=90), q: str | None = None, cliente_id: int | None = None,
                  u: dict = Depends(usuario_actual)):
    return await llamar("GET", "/solicitudes/tablero", u, params={"dias": dias, "q": q, "cliente_id": cliente_id})


@router.get("/solicitudes", summary="Listar solicitudes (vigentes=true para el tablero, false para el historial)")
async def listar(vigentes: bool | None = None, estado: str | None = None, tipo_caso: str | None = None,
                 q: str | None = None, cliente_id: int | None = None, limite: int = Query(200, ge=1, le=500),
                 manual: bool | None = Query(None, description="true: solo órdenes manuales (capturadas por el laboratorio)"),
                 u: dict = Depends(usuario_actual)):
    params = {"vigentes": None if vigentes is None else str(vigentes).lower(), "estado": estado,
              "tipo_caso": tipo_caso, "q": q, "cliente_id": cliente_id, "limite": limite,
              "manual": None if manual is None else str(manual).lower()}
    return await llamar("GET", "/solicitudes", u, params=params)


@router.post("/solicitudes", status_code=201, summary="Crear caso nuevo (CN)")
async def crear(datos: SolicitudIn, u: dict = Depends(usuario_actual)):
    return await llamar("POST", "/solicitudes", u, json=datos.model_dump(mode="json"))


@router.get("/solicitudes/{solicitud_id}", summary="Detalle de una solicitud")
async def obtener(solicitud_id: int, u: dict = Depends(usuario_actual)):
    return await llamar("GET", f"/solicitudes/{solicitud_id}", u)


@router.post("/solicitudes/{solicitud_id}/reapertura", status_code=201,
             summary="Reabrir un caso entregado (RP): garantía o modificación, pasa primero por QA")
async def reabrir(solicitud_id: int, datos: ReaperturaIn, u: dict = Depends(usuario_actual)):
    return await llamar("POST", f"/solicitudes/{solicitud_id}/reapertura", u, json=datos.model_dump(mode="json"))


@router.post("/solicitudes/{solicitud_id}/cancelar", summary="Cancelar un caso en cualquier etapa (admin, supervisor)")
async def cancelar(solicitud_id: int, datos: MotivoIn, u: dict = Depends(admin_o_supervisor)):
    return await llamar("POST", f"/solicitudes/{solicitud_id}/cancelar", u, json=datos.model_dump())


@router.get("/solicitudes/{solicitud_id}/orden.pdf", summary="Orden de trabajo en PDF (personal, después del Ok de Ingresos)")
async def orden_pdf(solicitud_id: int, u: dict = Depends(usuario_actual)):
    return await descargar(f"/solicitudes/{solicitud_id}/orden.pdf", u)


@router.get("/solicitudes/{solicitud_id}/archivos/{archivo_id}", summary="Descargar un archivo de la solicitud")
async def descargar_archivo(solicitud_id: int, archivo_id: str, u: dict = Depends(usuario_actual)):
    return await descargar(f"/solicitudes/{solicitud_id}/archivos/{archivo_id}", u)


@router.post("/solicitudes/{solicitud_id}/prioridad", summary="Cambiar la prioridad de un caso (admin, supervisor)")
async def prioridad(solicitud_id: int, datos: PrioridadIn, u: dict = Depends(admin_o_supervisor)):
    return await llamar("POST", f"/solicitudes/{solicitud_id}/prioridad", u, json=datos.model_dump())


@router.post("/solicitudes/{solicitud_id}/pausar", summary="Pausar un caso con motivo (admin, supervisor). Detiene su tiempo")
async def pausar(solicitud_id: int, datos: MotivoIn, u: dict = Depends(admin_o_supervisor)):
    return await llamar("POST", f"/solicitudes/{solicitud_id}/pausar", u, json=datos.model_dump())


@router.post("/solicitudes/{solicitud_id}/reanudar", summary="Reanudar un caso en pausa (admin, supervisor)")
async def reanudar(solicitud_id: int, datos: ReanudarIn, u: dict = Depends(admin_o_supervisor)):
    return await llamar("POST", f"/solicitudes/{solicitud_id}/reanudar", u, json=datos.model_dump(mode="json"))


@router.get("/pausas", summary="Auditoría de pausas (quién, por qué, cuánto duró)")
async def pausas(desde: date | None = None, hasta: date | None = None, abiertas: bool = False,
                 u: dict = Depends(requiere_rol("admin", "supervisor", "operaciones", "demo"))):
    return await llamar("GET", "/pausas", u, params={"desde": desde and str(desde), "hasta": hasta and str(hasta),
                                                     "abiertas": str(abiertas).lower()})
