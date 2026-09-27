"""Cliente HTTP hacia el servicio backend por la red privada de Railway."""
import httpx
from fastapi import HTTPException

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


async def llamar(metodo: str, ruta: str, usuario: dict | None = None, json=None, params: dict | None = None):
    """Reenvía la petición al backend con la clave interna y quién la hace (para la bitácora)."""
    cabeceras = {"X-Internal-Key": config.INTERNAL_KEY}
    if usuario:
        cabeceras["X-Usuario-Id"] = str(usuario["id"])
        cabeceras["X-Usuario-Email"] = usuario["email"]
    if params:
        params = {k: v for k, v in params.items() if v is not None}
    try:
        respuesta = await http().request(metodo, ruta, headers=cabeceras, json=json, params=params)
    except httpx.HTTPError as error:
        raise HTTPException(status_code=503, detail=f"El servicio backend no está disponible ({type(error).__name__}: {error})")

    if respuesta.status_code == 204:
        return None
    try:
        cuerpo = respuesta.json()
    except ValueError:
        cuerpo = {"detail": respuesta.text or "Error en el backend"}
    if respuesta.status_code >= 400:
        raise HTTPException(status_code=respuesta.status_code, detail=cuerpo.get("detail", cuerpo))
    return cuerpo
