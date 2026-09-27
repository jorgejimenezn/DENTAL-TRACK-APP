"""Contratos públicos de la API (lo que se ve en Swagger).

Las validaciones de negocio (NIT, DPI, duplicados) se hacen en el backend y sus
errores se devuelven tal cual al frontend.
"""
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LoginIn(BaseModel):
    email: EmailStr = Field(examples=["admin@dentaltrack.com"])
    password: str = Field(examples=["Admin123!"])


class UsuarioOut(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str
    rol: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expira_en: str
    usuario: UsuarioOut


class EstadoIn(BaseModel):
    activo: bool


class PasswordIn(BaseModel):
    password: str = Field(min_length=8, max_length=72)


class DireccionIn(BaseModel):
    departamento: str = Field(examples=["Guatemala"])
    municipio: str = Field(examples=["Mixco"])
    direccion: str = Field(examples=["Blvd. San Cristóbal 8-20, Consultorio 3"])
    principal: bool = False


class _ClienteBase(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    clinica: str | None = None
    es_red: bool = False
    telefono_celular: str = Field(examples=["55551234"])
    telefono_fijo: str | None = None
    tipo_documento: Literal["NIT", "DPI"]
    numero_documento: str = Field(examples=["576937-K"])
    nivel_prioridad: Literal[1, 2] = 2


class ClienteCrear(_ClienteBase):
    password: str = Field(min_length=8, max_length=72)
    direcciones: list[DireccionIn] = Field(min_length=1)


class ClienteActualizar(_ClienteBase):
    pass


RolInterno = Literal["admin", "ingresos", "tecnico", "qa", "facturacion", "logistica"]


class _EmpleadoBase(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    rol: RolInterno
    area_ids: list[int] = []


class EmpleadoCrear(_EmpleadoBase):
    password: str = Field(min_length=8, max_length=72)


class EmpleadoActualizar(_EmpleadoBase):
    pass
