"""Esquemas de empleados del laboratorio."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.validaciones import limpiar_numero, telefono_valido

from app.esquemas.comun import AreaOut

RolInterno = Literal["admin", "ingresos", "tecnico", "qa", "facturacion", "logistica"]


class _EmpleadoBase(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    apellido: str = Field(min_length=2, max_length=80)
    email: EmailStr
    telefono: str | None = None
    direccion: str | None = Field(default=None, max_length=250)
    rol: RolInterno
    area_ids: list[int] = []

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: str | None) -> str | None:
        if not v:
            return None
        if not telefono_valido(v):
            raise ValueError("El teléfono debe tener 8 dígitos")
        return limpiar_numero(v)


class EmpleadoCrear(_EmpleadoBase):
    password: str = Field(min_length=8, max_length=72)


class EmpleadoActualizar(_EmpleadoBase):
    pass


class EmpleadoOut(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str
    telefono: str | None
    direccion: str | None
    rol: str
    activo: bool
    areas: list[AreaOut]
    creado_en: datetime | None
    ultimo_acceso: datetime | None
