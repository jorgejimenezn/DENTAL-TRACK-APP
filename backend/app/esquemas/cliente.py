"""Esquemas (contratos de entrada/salida) de clientes y direcciones."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.validaciones import DEPARTAMENTOS, dpi_valido, limpiar_numero, nit_valido, telefono_valido


class DireccionIn(BaseModel):
    departamento: str
    municipio: str = Field(min_length=2, max_length=80)
    direccion: str = Field(min_length=5, max_length=250)
    principal: bool = False

    @field_validator("departamento")
    @classmethod
    def validar_departamento(cls, v: str) -> str:
        if v not in DEPARTAMENTOS:
            raise ValueError("Departamento no válido")
        return v


class DireccionOut(BaseModel):
    id: int
    departamento: str
    municipio: str
    direccion: str
    principal: bool
    activo: bool


class _ClienteBase(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    apellido: str = Field(min_length=2, max_length=80)
    email: EmailStr
    clinica: str | None = Field(default=None, max_length=120)
    es_red: bool = False
    telefono_celular: str
    telefono_fijo: str | None = None
    tipo_documento: Literal["NIT", "DPI"]
    numero_documento: str
    nivel_prioridad: Literal[1, 2] = 2

    @field_validator("telefono_celular")
    @classmethod
    def validar_celular(cls, v: str) -> str:
        if not telefono_valido(v):
            raise ValueError("El celular debe tener 8 dígitos")
        return limpiar_numero(v)

    @field_validator("telefono_fijo")
    @classmethod
    def validar_fijo(cls, v: str | None) -> str | None:
        if not v:
            return None
        if not telefono_valido(v):
            raise ValueError("El teléfono fijo debe tener 8 dígitos")
        return limpiar_numero(v)

    @model_validator(mode="after")
    def validar_documento(self):
        numero = limpiar_numero(self.numero_documento)
        if self.tipo_documento == "NIT" and not nit_valido(numero):
            raise ValueError("NIT no válido: revisa el número y su dígito verificador")
        if self.tipo_documento == "DPI" and not dpi_valido(numero):
            raise ValueError("DPI no válido: deben ser 13 dígitos con verificador correcto")
        self.numero_documento = numero
        return self


class ClienteCrear(_ClienteBase):
    password: str = Field(min_length=8, max_length=72)
    direcciones: list[DireccionIn] = Field(min_length=1)


class ClienteActualizar(_ClienteBase):
    pass


class ClienteOut(BaseModel):
    id: int
    usuario_id: int
    nombre: str
    apellido: str
    email: str
    clinica: str | None
    es_red: bool
    telefono_celular: str
    telefono_fijo: str | None
    tipo_documento: str
    numero_documento: str
    nivel_prioridad: int
    activo: bool
    creado_en: datetime | None
    direcciones: list[DireccionOut]
