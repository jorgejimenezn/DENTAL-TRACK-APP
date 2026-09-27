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


class _DatosCliente(BaseModel):
    """Datos que el propio cliente puede capturar (sin prioridad)."""
    razon_social: str = Field(min_length=2, max_length=150, description="Cliente o razón social (nombre visible)")
    nombre_facturacion: str = Field(min_length=2, max_length=150, description="Nombre que aparece en la factura")
    email: EmailStr
    clinica: str | None = Field(default=None, max_length=120)
    es_red: bool = False
    telefono_celular: str | None = None
    telefono_fijo: str | None = None
    tipo_documento: Literal["NIT", "DPI"]
    numero_documento: str

    @field_validator("telefono_celular", "telefono_fijo")
    @classmethod
    def validar_telefono(cls, v: str | None) -> str | None:
        if not v:
            return None
        if not telefono_valido(v):
            raise ValueError("El teléfono debe tener 8 dígitos")
        return limpiar_numero(v)

    @model_validator(mode="after")
    def validar_documento_y_telefono(self):
        if not self.telefono_celular and not self.telefono_fijo:
            raise ValueError("Ingresa al menos un teléfono (celular o fijo)")
        numero = limpiar_numero(self.numero_documento)
        if self.tipo_documento == "NIT" and not nit_valido(numero):
            raise ValueError("NIT no válido: revisa el número y su dígito verificador")
        if self.tipo_documento == "DPI" and not dpi_valido(numero):
            raise ValueError("DPI no válido: deben ser 13 dígitos con verificador correcto")
        self.numero_documento = numero
        return self


class _ClienteBase(_DatosCliente):
    # 2 = VIP, 3 = normal. La prioridad 1 es solo para solicitudes de emergencia.
    nivel_prioridad: Literal[2, 3] = 3


class RegistroCliente(_DatosCliente):
    """Auto-registro público: siempre crea un cliente (rol doctor) con prioridad normal."""
    password: str = Field(min_length=8, max_length=72)
    direccion: DireccionIn


class ClienteCrear(_ClienteBase):
    password: str = Field(min_length=8, max_length=72)
    direcciones: list[DireccionIn] = Field(min_length=1)


class ClienteActualizar(_ClienteBase):
    pass


class ClienteOut(BaseModel):
    id: int
    usuario_id: int
    razon_social: str
    nombre_facturacion: str
    email: str
    clinica: str | None
    es_red: bool
    telefono_celular: str | None
    telefono_fijo: str | None
    tipo_documento: str
    numero_documento: str
    nivel_prioridad: int
    activo: bool
    creado_en: datetime | None
    direcciones: list[DireccionOut]
