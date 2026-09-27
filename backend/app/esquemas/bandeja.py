"""Contratos de la bandeja de trabajo por área (Ingresos, producción, QA, Facturación, Logística)."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.esquemas.solicitud import PIEZAS_FDI, Seleccion

CLASIFICACIONES = {
    "garantia_total": "Garantía total",
    "garantia_parcial_sin_cobro": "Garantía parcial sin cobro",
    "garantia_parcial_con_cobro": "Garantía parcial con cobro",
    "cobro": "Cobro",
}


class PasoPrevio(BaseModel):
    id: int
    orden: int
    area: str


class PasoBandeja(BaseModel):
    paso_id: int
    solicitud_id: int
    codigo: str
    tipo_caso: str
    cliente: str
    paciente: str
    doctor_tratante: str | None
    trabajo: str
    color: str | None
    piezas: list[int]
    modalidad: str
    emergencia: bool
    prioridad: int
    fecha_entrega: date
    instrucciones: str | None
    fuera_catalogo: bool
    area_id: int
    area: str
    etapa: str
    etapa_texto: str
    estado: str
    tecnico: str | None
    activado_en: datetime | None
    asignado_en: datetime | None
    iniciado_en: datetime | None
    vuelta: int
    reapertura_tipo: str | None
    reapertura_motivo: str | None
    qa_clasificacion: str | None
    factura_numero: str | None
    direccion: str
    archivos: int
    telefono: str | None = None
    receptor: str | None = None
    acciones: list[str]
    pasos_previos: list[PasoPrevio] = []


class Produccion(BaseModel):
    actual: PasoBandeja | None
    siguiente: PasoBandeja | None
    asignados: list[PasoBandeja]
    total: int
    max_trabajos: int | None


class AreaBandeja(BaseModel):
    area_id: int
    area: str
    tipo: str
    pasos: list[PasoBandeja]


class ResumenArea(BaseModel):
    area_id: int
    area: str
    tipo: str
    activos: int
    en_proceso: int
    en_cola: int
    sin_tecnico: int


class Bandeja(BaseModel):
    produccion: Produccion | None
    rutas: list[PasoBandeja] | None = None
    areas: list[AreaBandeja]
    supervision: list[ResumenArea] | None


# ---------------- Acciones ----------------
class TerminarIn(BaseModel):
    nota: str | None = Field(default=None, max_length=300)
    factura_numero: str | None = Field(default=None, max_length=40, description="Obligatorio en Facturación")
    receptor: str | None = Field(default=None, max_length=120, description="Obligatorio al entregar: quién recibe")

    @field_validator("nota", "factura_numero", "receptor")
    @classmethod
    def limpiar(cls, v: str | None) -> str | None:
        return " ".join((v or "").split()) or None


class RechazoIn(BaseModel):
    volver_a_paso_id: int = Field(description="Paso de producción al que regresa el caso")
    motivo: str = Field(min_length=3, max_length=250)


class ValidacionRpIn(BaseModel):
    clasificacion: Literal["garantia_total", "garantia_parcial_sin_cobro", "garantia_parcial_con_cobro", "cobro"]
    motivo_id: int
    observacion: str | None = Field(default=None, max_length=300)


class ModificacionIn(BaseModel):
    """Corrección de Ingresos antes de aprobar (ej. asignar un tipo del catálogo a un caso fuera de catálogo)."""
    tipo_trabajo: Seleccion
    material: Seleccion
    unidad: Seleccion
    guia_color: Seleccion | None = None
    color: Seleccion | None = None
    piezas: list[int] = Field(min_length=1)
    fecha_entrega: date
    nota: str = Field(min_length=3, max_length=250, description="Qué se corrigió y por qué")

    @field_validator("piezas")
    @classmethod
    def validar_piezas(cls, v: list[int]) -> list[int]:
        if any(p not in PIEZAS_FDI for p in v):
            raise ValueError("Piezas no válidas (FDI)")
        return sorted(set(v))


class CancelarIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=250)


class Candidato(BaseModel):
    id: int
    nombre: str
    rol: str
    carga: int
    max_trabajos: int | None
    cubre: bool  # tiene el área y el tipo de trabajo (producción) o es mensajero (rutas)


class AsignarIn(BaseModel):
    usuario_id: int
    nota: str | None = Field(default=None, max_length=200)


class PrioridadIn(BaseModel):
    prioridad: Literal[1, 2, 3] = Field(description="1 emergencia, 2 VIP, 3 normal")
    motivo: str = Field(min_length=3, max_length=200)
