"""Servicio FRONTEND de DENTAL TRACK: sirve las pantallas HTML/CSS/JS.

La URL de la API se inyecta desde la variable de entorno API_URL en /js/config.js,
así el mismo código funciona en local y en Railway.
"""
import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

API_URL = os.getenv("API_URL", "http://localhost:8002").rstrip("/")
if API_URL and not API_URL.startswith("http"):
    API_URL = "https://" + API_URL  # permite usar ${{api.RAILWAY_PUBLIC_DOMAIN}} directamente

CARPETA = Path(__file__).parent / "static"

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/js/config.js", include_in_schema=False)
def configuracion():
    contenido = f"window.API_URL = {json.dumps(API_URL)};\n"
    return Response(contenido, media_type="application/javascript", headers={"Cache-Control": "no-store"})


@app.get("/", include_in_schema=False)
def inicio():
    return RedirectResponse("/login.html")


@app.get("/salud", include_in_schema=False)
def salud():
    return {"servicio": "frontend", "api": API_URL}


app.mount("/", StaticFiles(directory=CARPETA, html=True), name="static")
