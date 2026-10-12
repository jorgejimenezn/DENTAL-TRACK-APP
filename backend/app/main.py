"""Servicio BACKEND de DENTAL TRACK.

Capa de lógica de negocio y acceso a datos. Es privado: solo lo llama el servicio API
por la red interna de Railway, identificado con la cabecera X-Internal-Key.
"""
import logging
from contextlib import asynccontextmanager

from fastapi.exceptions import RequestValidationError
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.errores_validacion import manejar_validacion
from app.core.dependencias import verificar_clave_interna
from app.core.errores import ErrorNegocio
from app.db.mongo import obtener_mongo
from app.db.datos_prueba import cargar_datos_prueba
from app.db.semilla import inicializar_base, preparar_recorridos
from app.rutas import auth, bandeja, catalogos, clientes, configuracion, empleados, gestion, personal, solicitudes

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    inicializar_base()
    cargar_datos_prueba()
    preparar_recorridos()
    try:
        obtener_mongo()["auditoria"].create_index("fecha")
    except Exception as error:
        logging.warning("MongoDB no disponible al iniciar: %s", error)
    yield


app = FastAPI(
    title="DENTAL TRACK · Backend (interno)",
    description="Lógica de negocio y acceso a PostgreSQL y MongoDB. Requiere cabecera X-Internal-Key.",
    version="1.0.0",
    lifespan=ciclo_de_vida,
)


app.add_exception_handler(RequestValidationError, manejar_validacion)


@app.exception_handler(ErrorNegocio)
async def manejar_error_negocio(_: Request, error: ErrorNegocio):
    return JSONResponse(status_code=error.status, content={"detail": error.detalle})


@app.get("/salud", tags=["Salud"])
def salud():
    estado = {"servicio": "backend", "postgres": "ok", "mongo": "ok"}
    try:
        obtener_mongo().command("ping")
    except Exception:
        estado["mongo"] = "sin conexión"
    return estado


protegido = [Depends(verificar_clave_interna)]
for modulo in (auth, clientes, empleados, catalogos, configuracion, solicitudes, bandeja, gestion, personal):
    app.include_router(modulo.router, dependencies=protegido)
