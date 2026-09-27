"""Contratos de solicitudes (CN y RP), archivos y perfil del cliente para el formulario."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.validaciones import DEPARTAMENTOS

Modalidad = Literal["digital", "analogo"]
PIEZAS_FDI = {c * 10 + n for c in (1, 2, 3, 4) for n in range(1, 9)}


def _texto(v: str | None) -> str | None:
    if v is None:
        return None
    v = " ".join(v.split())
    return v or None


# ---------------- Entrada ----------------
class Seleccion(BaseModel):
    """Elemento del catálogo (id) o texto libre "fuera de catálogo". Solo uno de los dos."""
    id: int | None = None
    fuera_catalogo: str | None = Field(default=None, max_length=120)

    @field_validator("fuera_catalogo")
    @classmethod
    def limpiar(cls, v: str | None) -> str | None:
        return _texto(v)

    @model_validator(mode="after")
    def uno_solo(self):
        if (self.id is None) == (self.fuera_catalogo is None):
            raise ValueError("Elige una opción del catálogo o describe el valor fuera de catálogo")
        return self


class DireccionSel(BaseModel):
    tipo: Literal["existente", "nueva", "misma_que_entrega"]
    direccion_id: int | None = None
    departamento: str | None = None
    municipio: str | None = Field(default=None, max_length=80)
    direccion: str | None = Field(default=None, max_length=250)
    guardar: bool = False

    @model_validator(mode="after")
    def validar(self):
        if self.tipo == "existente" and not self.direccion_id:
            raise ValueError("Selecciona una dirección")
        if self.tipo == "nueva":
            self.municipio, self.direccion = _texto(self.municipio), _texto(self.direccion)
            if self.departamento not in DEPARTAMENTOS:
                raise ValueError("Departamento no válido")
            if not self.municipio or len(self.municipio) < 2:
                raise ValueError("Indica el municipio")
            if not self.direccion or len(self.direccion) < 5:
                raise ValueError("La dirección debe tener al menos 5 caracteres")
        return self


class _EntregaIn(BaseModel):
    modalidad: Modalidad
    piezas: list[int] = Field(min_length=1)
    fecha_entrega: date
    emergencia: bool = False
    direccion_entrega: DireccionSel
    direccion_recolecta: DireccionSel | None = None
    instrucciones: str | None = Field(default=None, max_length=2000)
    archivo_ids: list[str] = Field(default=[], max_length=12, description="IDs devueltos por POST /archivos")

    @field_validator("piezas")
    @classmethod
    def validar_piezas(cls, v: list[int]) -> list[int]:
        invalidas = [p for p in v if p not in PIEZAS_FDI]
        if invalidas:
            raise ValueError(f"Piezas no válidas (FDI): {', '.join(map(str, invalidas))}")
        return sorted(set(v))

    @field_validator("instrucciones")
    @classmethod
    def limpiar_instrucciones(cls, v: str | None) -> str | None:
        return (v or "").strip() or None

    @model_validator(mode="after")
    def validar_direcciones(self):
        if self.direccion_entrega.tipo == "misma_que_entrega":
            raise ValueError("La dirección de entrega debe ser existente o nueva")
        if self.modalidad == "digital":
            self.direccion_recolecta = None
        elif self.direccion_recolecta is None:
            self.direccion_recolecta = DireccionSel(tipo="misma_que_entrega")
        return self


class SolicitudIn(_EntregaIn):
    """Caso nuevo (CN)."""
    cliente_id: int | None = Field(default=None, description="Solo personal del laboratorio. El doctor usa su cuenta")
    paciente: str = Field(min_length=2, max_length=120)
    referencia_clinica: str | None = Field(default=None, max_length=60)
    doctor_tratante: str | None = Field(default=None, max_length=120)
    tipo_trabajo: Seleccion
    material: Seleccion
    unidad: Seleccion
    guia_color: Seleccion | None = Field(default=None, description="Nulo cuando el material no usa color")
    color: Seleccion | None = None

    @field_validator("paciente", "referencia_clinica", "doctor_tratante")
    @classmethod
    def limpiar_textos(cls, v: str | None) -> str | None:
        return _texto(v)

    @model_validator(mode="after")
    def guia_y_color(self):
        if (self.guia_color is None) != (self.color is None):
            raise ValueError("Indica la guía de color y el color")
        return self


class ReaperturaIn(_EntregaIn):
    """Reapertura (RP) de un caso entregado: mismo trabajo, nuevo motivo."""
    tipo_reapertura: Literal["garantia", "modificacion"]
    motivo: str = Field(min_length=5, max_length=1000)

    @field_validator("motivo")
    @classmethod
    def limpiar_motivo(cls, v: str) -> str:
        return " ".join(v.split())


class MotivoIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=250)


# ---------------- Salida ----------------
class ArchivoOut(BaseModel):
    id: str
    nombre: str
    tipo: str
    tamano: int
    subido_en: datetime | None = None


class ValorOut(BaseModel):
    id: int | None
    nombre: str
    fuera_catalogo: bool


class DireccionTexto(BaseModel):
    departamento: str
    municipio: str
    direccion: str


class HistorialOut(BaseModel):
    estado: str
    estado_texto: str
    nota: str | None
    usuario: str | None
    fecha: datetime


class CasoRef(BaseModel):
    id: int
    codigo: str
    estado: str
    estado_texto: str
    creado_en: datetime


class RecorridoPaso(BaseModel):
    id: int
    orden: int
    area: str
    etapa: str
    etapa_texto: str
    estado: str
    tecnico: str | None
    atendido_por: str | None
    activado_en: datetime | None
    terminado_en: datetime | None
    nota: str | None
    receptor: str | None = None
    vuelta: int


class SolicitudResumen(BaseModel):
    id: int
    codigo: str
    tipo_caso: str
    estado: str
    estado_texto: str
    columna: str
    cliente_id: int
    cliente: str
    paciente: str
    doctor_tratante: str | None
    trabajo: str
    piezas: list[int]
    modalidad: str
    emergencia: bool
    prioridad: int | None
    fecha_entrega: date
    creado_en: datetime
    caso_origen: str | None
    fuera_catalogo: bool
    area_actual: str | None = None
    caja: str | None = None
    pasos_total: int = 0
    pasos_hechos: int = 0
    entregado_en: datetime | None = None


class SolicitudOut(SolicitudResumen):
    clinica: str | None
    creado_por: str | None
    caso_origen_id: int | None
    reapertura_tipo: str | None
    reapertura_motivo: str | None
    qa_clasificacion: str | None
    qa_motivo: str | None
    qa_observacion: str | None
    referencia_clinica: str | None
    requiere_recolecta: bool
    tipo_trabajo: ValorOut
    material: ValorOut
    unidad: ValorOut
    guia_color: ValorOut | None
    color: ValorOut | None
    fecha_minima: date
    entrega: DireccionTexto
    recolecta: DireccionTexto | None
    instrucciones: str | None
    archivos: list[ArchivoOut]
    historial: list[HistorialOut]
    reaperturas: list[CasoRef]
    puede_reabrir: bool
    motivo_no_reabrir: str | None
    factura_numero: str | None
    recorrido: list[RecorridoPaso]


class DireccionPerfil(BaseModel):
    id: int
    departamento: str
    municipio: str
    direccion: str
    principal: bool


class PerfilSolicitud(BaseModel):
    """Lo que el formulario necesita del cliente (sin su nivel de prioridad)."""
    cliente_id: int
    razon_social: str
    clinica: str | None
    es_red: bool
    titular: str
    direcciones: list[DireccionPerfil]
    doctores: list[str]


class ClienteBreve(BaseModel):
    id: int
    razon_social: str
    clinica: str | None
    es_red: bool


class ColumnaTablero(BaseModel):
    nombre: str
    casos: list[SolicitudResumen]


class Tablero(BaseModel):
    columnas: list[ColumnaTablero]
    dias_entregados: int
