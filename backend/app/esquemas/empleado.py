"""Esquemas de empleados del laboratorio."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.esquemas.comun import AreaOut

RolInterno = Literal["admin", "ingresos", "tecnico", "qa", "facturacion", "logistica"]


class _EmpleadoBase(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    apellido: str = Field(min_length=2, max_length=80)
    email: EmailStr
    rol: RolInterno
    area_ids: list[int] = []


class EmpleadoCrear(_EmpleadoBase):
    password: str = Field(min_length=8, max_length=72)


class EmpleadoActualizar(_EmpleadoBase):
    pass


class EmpleadoOut(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str
    rol: str
    activo: bool
    areas: list[AreaOut]
    creado_en: datetime | None
    ultimo_acceso: datetime | None
