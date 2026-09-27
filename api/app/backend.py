"""Cliente HTTP hacia el servicio backend por la red privada de Railway."""
import httpx
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from app.config import config

_http: httpx.AsyncClient | None = None


def http() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient(base_url=config.BACKEND_URL, timeout=20.0)
    return _http


async def cerrar():
    if _http is not None:
        await _http.aclose()


def _cabeceras(usuario: dict | None) -> dict:
    cabeceras = {"X-Internal-Key": config.INTERNAL_KEY}
    if usuario:
        cabeceras["X-Usuario-Id"] = str(usuario["id"])
        cabeceras["X-Usuario-Email"] = usuario["email"]
        cabeceras["X-Usuario-Rol"] = usuario["rol"]
    return cabeceras


def _no_disponible(error: Exception) -> HTTPException:
    return HTTPException(status_code=503,
                         detail=f"El servicio backend no está disponible ({type(error).__name__}: {error})")


async def llamar(metodo: str, ruta: str, usuario: dict | None = None, json=None, params: dict | None = None,
                 files=None, timeout: float | None = None):
    """Reenvía la petición al backend con la clave interna y quién la hace (bitácora y permisos)."""
    if params:
        params = {k: v for k, v in params.items() if v is not None}
    extra = {"timeout": timeout} if timeout else {}
    try:
        respuesta = await http().request(metodo, ruta, headers=_cabeceras(usuario), json=json, params=params,
                                         files=files, **extra)
    except httpx.HTTPError as error:
        raise _no_disponible(error)
    return _procesar(respuesta)


async def descargar(ruta: str, usuario: dict) -> StreamingResponse:
    """Descarga en flujo (sin cargar el archivo completo en memoria)."""
    try:
        respuesta = await http().send(http().build_request("GET", ruta, headers=_cabeceras(usuario)), stream=True)
    except httpx.HTTPError as error:
        raise _no_disponible(error)
    if respuesta.status_code >= 400:
        await respuesta.aread()
        await respuesta.aclose()
        _procesar(respuesta)
    cabeceras = {k: v for k, v in respuesta.headers.items() if k.lower() in ("content-disposition", "content-length")}
    return StreamingResponse(respuesta.aiter_raw(), media_type=respuesta.headers.get("content-type"),
                             headers=cabeceras, background=BackgroundTask(respuesta.aclose))


def _procesar(respuesta: httpx.Response):
    if respuesta.status_code == 204:
        return None
    try:
        cuerpo = respuesta.json()
    except ValueError:
        cuerpo = {"detail": respuesta.text or "Error en el backend"}
    if respuesta.status_code >= 400:
        raise HTTPException(status_code=respuesta.status_code, detail=cuerpo.get("detail", cuerpo))
    return cuerpo
