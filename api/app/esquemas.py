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


class _DatosCliente(BaseModel):
    razon_social: str = Field(examples=["Clínica Dental Sonrisa Perfecta S.A."])
    nombre_facturacion: str = Field(examples=["Sonrisa Perfecta, S.A."])
    email: EmailStr
    clinica: str | None = None
    es_red: bool = False
    telefono_celular: str | None = Field(default=None, examples=["55551234"])
    telefono_fijo: str | None = Field(default=None, examples=["22359012"])
    tipo_documento: Literal["NIT", "DPI"]
    numero_documento: str = Field(examples=["576937-K"])


class _ClienteBase(_DatosCliente):
    nivel_prioridad: Literal[2, 3] = Field(default=3, description="2 = VIP, 3 = normal (1 se reserva para emergencias)")


class RegistroIn(_DatosCliente):
    """Auto-registro: el servidor fija rol doctor y prioridad 3 (normal)."""
    password: str = Field(min_length=8, max_length=72)
    direccion: DireccionIn


class ClienteCrear(_ClienteBase):
    password: str = Field(min_length=8, max_length=72)
    direcciones: list[DireccionIn] = Field(min_length=1)


class ClienteActualizar(_ClienteBase):
    pass


RolInterno = Literal["admin", "supervisor", "ingresos", "tecnico", "qa", "facturacion", "logistica", "mensajero"]


class _EmpleadoBase(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    telefono: str | None = None
    direccion: str | None = None
    rol: RolInterno
    area_ids: list[int] = []
    max_trabajos: int | None = Field(default=None, ge=1, le=200,
                                     description="Máximo de trabajos activos al mismo tiempo. Vacío = sin límite")


class EmpleadoCrear(_EmpleadoBase):
    password: str = Field(min_length=8, max_length=72)


class EmpleadoActualizar(_EmpleadoBase):
    pass


# ---------------- Configuración ----------------
from datetime import date  # noqa: E402

CatalogoSimple = Literal["tipos", "materiales", "unidades", "guias", "motivos-rp", "areas"]
Modalidad = Literal["digital", "analogo"]


class NombreIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120, examples=["Corona"])


class ItemActualizar(NombreIn):
    activo: bool = True


class IdsIn(BaseModel):
    ids: list[int] = Field(default=[], description="IDs relacionados (reemplaza la lista completa)")


class RelacionesMaterialIn(BaseModel):
    unidad_ids: list[int] = []
    guia_ids: list[int] = []


class FlujoIn(BaseModel):
    tipo_trabajo_id: int
    modalidad: Modalidad
    activo: bool = True
    area_ids: list[int] = Field(min_length=1, description="Áreas en el orden en que se recorren")


class AsignacionAreaIn(BaseModel):
    area_id: int
    tipo_ids: list[int] = Field(default=[], description="Vacío = todos los tipos de trabajo")


class AsignacionIn(BaseModel):
    areas: list[AsignacionAreaIn]


class DiaIn(BaseModel):
    fecha: date
    motivo: str = Field(min_length=2, max_length=120, examples=["Asueto del laboratorio"])
    hora_corte: str | None = Field(default=None, description="Vacío = no se labora; HH:MM = horario especial",
                                   examples=["12:00"])


class ParametrosIn(BaseModel):
    corte_semana: str = Field(examples=["18:00"])
    corte_sabado: str = Field(examples=["12:00"])
    min_digital: int = Field(ge=0, le=30, examples=[2])
    min_analogo: int = Field(ge=0, le=30, examples=[3])
    min_emergencia: int = Field(ge=0, le=30, examples=[1])
