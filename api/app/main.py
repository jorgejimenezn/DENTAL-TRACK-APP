"""Servicio API de DENTAL TRACK (pública).

Puerta de entrada del frontend: autentica con JWT, controla permisos por rol y se
comunica con el servicio backend por la red privada de Railway. Swagger en /docs.
"""
from contextlib import asynccontextmanager

from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app import backend
from app.errores_validacion import manejar_validacion
from app.config import config
from app.rutas import auth, bandeja, catalogos, clientes, configuracion, empleados, gestion, personal, solicitudes


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    yield
    await backend.cerrar()


app = FastAPI(
    title="DENTAL TRACK · API",
    description="API pública del sistema de gestión de laboratorio dental. "
                "Inicia sesión en **POST /auth/login**, copia el `access_token` y usa el botón **Authorize**.",
    version="1.0.0",
    lifespan=ciclo_de_vida,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_exception_handler(RequestValidationError, manejar_validacion)


@app.get("/", include_in_schema=False)
async def raiz():
    return RedirectResponse("/docs")


@app.get("/salud", tags=["Salud"], summary="Estado de la API y del backend")
async def salud():
    try:
        estado_backend = await backend.llamar("GET", "/salud")
    except Exception as error:
        estado_backend = f"sin conexión: {getattr(error, 'detail', error)}"
    return {"servicio": "api", "backend_url": config.BACKEND_URL, "backend": estado_backend}


for modulo in (auth, clientes, empleados, catalogos, configuracion, solicitudes, bandeja, gestion, personal):
    app.include_router(modulo.router)
