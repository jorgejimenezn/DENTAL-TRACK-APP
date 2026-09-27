"""Contratos de la configuración administrable."""
import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

CatalogoSimple = Literal["tipos", "materiales", "unidades", "guias", "motivos-rp", "areas"]
Modalidad = Literal["digital", "analogo"]


class NombreIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)

    @field_validator("nombre")
    @classmethod
    def limpiar(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("El nombre no puede estar vacío")
        return v


class ItemActualizar(NombreIn):
    activo: bool = True


class ItemOut(BaseModel):
    id: int
    nombre: str
    activo: bool


class TipoOut(ItemOut):
    material_ids: list[int]


class MaterialOut(ItemOut):
    unidad_ids: list[int]
    guia_ids: list[int]


class GuiaOut(ItemOut):
    colores: list[ItemOut]


class CatalogoCompleto(BaseModel):
    tipos: list[TipoOut]
    materiales: list[MaterialOut]
    unidades: list[ItemOut]
    guias: list[GuiaOut]
    motivos: list[ItemOut]
    areas: list[ItemOut]


class IdsIn(BaseModel):
    ids: list[int] = []


class RelacionesMaterialIn(BaseModel):
    unidad_ids: list[int] = []
    guia_ids: list[int] = []


# --- Árbol para formularios (solo elementos activos) ---
class NodoGuia(BaseModel):
    id: int
    nombre: str
    colores: list[ItemOut]


class NodoMaterial(BaseModel):
    id: int
    nombre: str
    unidades: list[ItemOut]
    guias: list[NodoGuia]


class NodoTipo(BaseModel):
    id: int
    nombre: str
    materiales: list[NodoMaterial]
    modalidades: list[Modalidad]


class Arbol(BaseModel):
    tipos: list[NodoTipo]
    motivos_rp: list[ItemOut]


# --- Flujos ---
class PasoOut(BaseModel):
    orden: int
    area_id: int
    area: str
    tecnicos: int = Field(description="Empleados que pueden realizar este paso para este tipo de trabajo")


class FlujoOut(BaseModel):
    id: int
    tipo_trabajo_id: int
    tipo_trabajo: str
    modalidad: Modalidad
    activo: bool
    pasos: list[PasoOut]


class FlujoIn(BaseModel):
    tipo_trabajo_id: int
    modalidad: Modalidad
    activo: bool = True
    area_ids: list[int] = Field(min_length=1, description="Áreas en el orden en que se recorren")


# --- Asignaciones ---
class AsignacionArea(BaseModel):
    area_id: int
    area: str | None = None
    tipo_ids: list[int] = Field(default=[], description="Vacío = todos los tipos de trabajo")


class AsignacionEmpleado(BaseModel):
    usuario_id: int
    nombre: str
    rol: str
    max_trabajos: int | None = None
    areas: list[AsignacionArea]


class AsignacionIn(BaseModel):
    areas: list[AsignacionArea]


# --- Calendario y parámetros ---
_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class DiaIn(BaseModel):
    fecha: date
    motivo: str = Field(min_length=2, max_length=120)
    hora_corte: str | None = Field(default=None, description="Vacío = no se labora; HH:MM = horario especial",
                                   examples=["12:00"])

    @field_validator("hora_corte")
    @classmethod
    def validar_hora(cls, v: str | None) -> str | None:
        if not v:
            return None
        if not _HORA.match(v):
            raise ValueError("Formato de hora HH:MM (00:00 a 23:59)")
        return v


class DiaOut(DiaIn):
    id: int


class Parametros(BaseModel):
    corte_semana: str = Field(description="Hora de corte lunes a viernes (HH:MM)", examples=["18:00"])
    corte_sabado: str = Field(description="Hora de corte sábado (HH:MM)", examples=["12:00"])
    min_digital: int = Field(ge=0, le=30)
    min_analogo: int = Field(ge=0, le=30)
    min_emergencia: int = Field(ge=0, le=30)

    @field_validator("corte_semana", "corte_sabado")
    @classmethod
    def validar_hora(cls, v: str) -> str:
        if not _HORA.match(v):
            raise ValueError("Formato de hora HH:MM (00:00 a 23:59)")
        return v


class FechaMinimaOut(BaseModel):
    registro: str = Field(description="Fecha y hora de registro considerada (Guatemala)")
    cuenta_desde: date
    dias_minimos: int
    primera_fecha: date
    nota: str
