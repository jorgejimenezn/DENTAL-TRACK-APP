"""Respuesta limpia para errores de validación: campo + mensaje en español.

No se devuelve el cuerpo recibido (podría contener contraseñas).
"""
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _mensaje(error: dict) -> str:
    tipo, ctx = error.get("type", ""), error.get("ctx") or {}
    if tipo == "missing":
        return "Campo requerido"
    if tipo == "string_too_short":
        return f"Debe tener al menos {ctx.get('min_length')} caracteres"
    if tipo == "string_too_long":
        return f"Debe tener máximo {ctx.get('max_length')} caracteres"
    if tipo == "too_short":
        return "Debe incluir al menos un elemento"
    if tipo == "literal_error":
        return "Valor no permitido"
    if tipo in ("int_parsing", "int_type"):
        return "Debe ser un número"
    if tipo == "value_error" and "email" in error.get("msg", "").lower():
        return "Correo electrónico no válido"
    return error.get("msg", "Dato no válido").removeprefix("Value error, ")


async def manejar_validacion(_: Request, exc: RequestValidationError):
    detalle = []
    for error in exc.errors():
        ubicacion = [str(p) for p in error.get("loc", []) if p not in ("body", "query", "path")]
        detalle.append({"campo": ".".join(ubicacion) or None, "mensaje": _mensaje(error)})
    return JSONResponse(status_code=422, content={"detail": detalle})
