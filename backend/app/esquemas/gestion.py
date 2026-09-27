"""Contratos de gestión: áreas y metas, ausencias y cobros."""
from datetime import date

from pydantic import BaseModel, Field


class AreaOperacionIn(BaseModel):
    lote: bool = False
    max_simultaneos: int = Field(default=1, ge=1, le=50)
    meta_horas: float = Field(ge=0.5, le=200)


class AusenciaIn(BaseModel):
    usuario_id: int
    desde: date
    hasta: date
    motivo: str = Field(min_length=3, max_length=150)


class PagoIn(BaseModel):
    fecha: date
    referencia: str | None = Field(default=None, max_length=80)
