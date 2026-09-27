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


RolInterno = Literal["admin", "supervisor", "operaciones", "ingresos", "tecnico", "qa", "facturacion", "logistica", "mensajero"]


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

CatalogoSimple = Literal["tipos", "materiales", "unidades", "guias", "motivos-rp", "areas", "colores-caja"]
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
    inicio_jornada: str = Field(default="08:00", examples=["08:00"], description="Inicio de la jornada (horas laborales)")
    min_digital: int = Field(ge=0, le=30, examples=[2])
    min_analogo: int = Field(ge=0, le=30, examples=[3])
    min_emergencia: int = Field(ge=0, le=30, examples=[1])


# ---------------- Solicitudes (CN / RP) ----------------
class SeleccionIn(BaseModel):
    """Elemento del catálogo (id) o texto libre fuera de catálogo. Solo uno de los dos."""
    id: int | None = Field(default=None, examples=[1])
    fuera_catalogo: str | None = Field(default=None, max_length=120, examples=[None])


class DireccionSelIn(BaseModel):
    tipo: Literal["existente", "nueva", "misma_que_entrega"] = Field(examples=["existente"])
    direccion_id: int | None = Field(default=None, examples=[1])
    departamento: str | None = None
    municipio: str | None = None
    direccion: str | None = None
    guardar: bool = Field(default=False, description="Nueva dirección: guardarla en las direcciones del cliente")


class _EntregaIn(BaseModel):
    modalidad: Modalidad
    piezas: list[int] = Field(min_length=1, description="Numeración FDI", examples=[[11, 21]])
    fecha_entrega: date
    emergencia: bool = Field(default=False, description="Prioridad 1: permite la fecha mínima de emergencia")
    direccion_entrega: DireccionSelIn
    direccion_recolecta: DireccionSelIn | None = Field(default=None, description="Solo analógico. Vacío = misma de entrega")
    instrucciones: str | None = Field(default=None, max_length=2000)
    archivo_ids: list[str] = Field(default=[], description="IDs devueltos por POST /archivos (STL obligatorio en digital)")


class SolicitudIn(_EntregaIn):
    cliente_id: int | None = Field(default=None, description="Solo personal del laboratorio (admin, supervisor, ingresos)")
    paciente: str = Field(min_length=2, max_length=120, examples=["Carlos Pérez"])
    referencia_clinica: str | None = Field(default=None, max_length=60)
    doctor_tratante: str | None = Field(default=None, max_length=120)
    tipo_trabajo: SeleccionIn
    material: SeleccionIn
    unidad: SeleccionIn
    guia_color: SeleccionIn | None = None
    color: SeleccionIn | None = None


class ReaperturaIn(_EntregaIn):
    tipo_reapertura: Literal["garantia", "modificacion"]
    motivo: str = Field(min_length=5, max_length=1000, examples=["La corona quedó alta en oclusión"])


class MotivoIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=250, examples=["Cliente solicitó cancelar"])


# ---------------- Bandeja y acciones por paso ----------------
class TerminarIn(BaseModel):
    nota: str | None = Field(default=None, max_length=300)
    factura_numero: str | None = Field(default=None, max_length=40, description="Obligatorio en Facturación")
    receptor: str | None = Field(default=None, max_length=120, description="Obligatorio al entregar: quién recibe")
    caja_color_id: int | None = Field(default=None, description="Ingresos: color de caja (GET /config/arbol → colores_caja)")
    caja_numero: str | None = Field(default=None, max_length=20, description="Ingresos: número de caja")


class RechazoIn(BaseModel):
    volver_a_paso_id: int = Field(description="Paso de producción al que regresa (ver pasos_previos en la bandeja)")
    motivo: str = Field(min_length=3, max_length=250)


class ValidacionRpIn(BaseModel):
    clasificacion: Literal["garantia_total", "garantia_parcial_sin_cobro", "garantia_parcial_con_cobro", "cobro"]
    motivo_id: int = Field(description="ID de GET /config/arbol → motivos_rp")
    observacion: str | None = Field(default=None, max_length=300)


class ModificacionIn(BaseModel):
    tipo_trabajo: SeleccionIn
    material: SeleccionIn
    unidad: SeleccionIn
    guia_color: SeleccionIn | None = None
    color: SeleccionIn | None = None
    piezas: list[int] = Field(min_length=1)
    fecha_entrega: date
    nota: str = Field(min_length=3, max_length=250, description="Qué se corrigió y por qué")


class CancelarPasoIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=250)


class AsignarIn(BaseModel):
    usuario_id: int = Field(description="Mensajero (recolecta/entrega) o empleado (producción). Ver /pasos/{id}/candidatos")
    nota: str | None = Field(default=None, max_length=200)


class PrioridadIn(BaseModel):
    prioridad: Literal[1, 2, 3] = Field(description="1 emergencia, 2 VIP, 3 normal")
    motivo: str = Field(min_length=3, max_length=200)


# ---------------- Gestión ----------------
class AreaOperacionIn(BaseModel):
    lote: bool = Field(default=False, description="El técnico trabaja varios a la vez (Yesos, CAM)")
    max_simultaneos: int = Field(default=1, ge=1, le=50, description="Máximo en proceso por técnico si es por lote")
    meta_horas: float = Field(ge=0.5, le=200, description="Meta en horas laborales para terminar el paso")


class AusenciaIn(BaseModel):
    usuario_id: int
    desde: date
    hasta: date
    motivo: str = Field(min_length=3, max_length=150, examples=["Vacaciones"])


class PagoIn(BaseModel):
    fecha: date
    referencia: str | None = Field(default=None, max_length=80, examples=["Depósito 55821"])
