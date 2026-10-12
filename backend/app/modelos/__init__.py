"""Modelos de la base relacional (PostgreSQL)."""
from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base

ROLES_INTERNOS = ["admin", "supervisor", "operaciones", "ingresos", "tecnico", "qa", "facturacion", "logistica",
                  "mensajero", "demo"]  # demo: ve todo sin editar y opera todos los pasos de la línea
ROL_CLIENTE = "doctor"
NIVELES_CLIENTE = {2: "VIP", 3: "Normal"}  # la prioridad 1 es exclusiva de emergencias

# Relación N:M empleado <-> área del laboratorio
usuario_area = Table(
    "usuario_area",
    Base.metadata,
    Column("usuario_id", ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
    Column("area_id", ForeignKey("areas.id", ondelete="CASCADE"), primary_key=True),
)


class Area(Base):
    __tablename__ = "areas"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    # Operación del área (editable por el admin en "Áreas y metas")
    lote: Mapped[bool] = mapped_column(Boolean, default=False)            # el técnico trabaja varios a la vez
    max_simultaneos: Mapped[int] = mapped_column(Integer, default=1)      # tope de trabajos en proceso por técnico
    meta_horas: Mapped[float] = mapped_column(Float, default=4.0)         # meta de horas laborales en el área


def valores_area(nombre: str) -> dict:
    """Valores iniciales: Yesos, CAM_IMP y CAM_FRES trabajan por lote (15); CAM tiene meta de 8 h, el resto 4 h."""
    n = nombre.upper()
    lote = n.startswith("YESO") or n.startswith("CAM")
    meta = 8.0 if n.startswith("CAM") or n.startswith("VALIDACI") else 4.0
    return {"lote": lote, "max_simultaneos": 15 if lote else 1, "meta_horas": meta}


class Usuario(Base):
    """Toda persona que inicia sesión: empleados del laboratorio y doctores (clientes)."""
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    apellido: Mapped[str] = mapped_column(String(80), default="")
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    telefono: Mapped[str | None] = mapped_column(String(8), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(250), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    rol: Mapped[str] = mapped_column(String(20))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    # Tope de órdenes asignadas o en proceso al mismo tiempo. None = sin límite.
    max_trabajos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Estado del personal (conectado, refaccion, almuerzo, capacitacion, desconectado): solo se asigna a "conectado"
    estado: Mapped[str] = mapped_column(String(15), default="desconectado", server_default="desconectado")
    estado_desde: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # True si el estado lo puso el sistema (inicio o fin de jornada): con actividad en horario se vuelve a conectar solo
    estado_auto: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    capacitacion_solicitada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    capacitacion_motivo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Cuándo cerró el navegador sin cerrar sesión: si no vuelve a haber actividad en 3 minutos, queda Desconectado
    cierre_navegador_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    areas: Mapped[list[Area]] = relationship(secondary=usuario_area, order_by=Area.nombre)
    cliente: Mapped["Cliente | None"] = relationship(back_populates="usuario", uselist=False)


class Cliente(Base):
    """Datos comerciales del doctor/clínica. Su acceso al sistema vive en Usuario (rol doctor)."""
    __tablename__ = "clientes"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True)
    razon_social: Mapped[str] = mapped_column(String(150))
    nombre_facturacion: Mapped[str] = mapped_column(String(150))
    clinica: Mapped[str | None] = mapped_column(String(120), nullable=True)
    es_red: Mapped[bool] = mapped_column(Boolean, default=False)
    telefono_celular: Mapped[str | None] = mapped_column(String(8), nullable=True)
    telefono_fijo: Mapped[str | None] = mapped_column(String(8), nullable=True)
    tipo_documento: Mapped[str] = mapped_column(String(3))  # NIT o DPI
    numero_documento: Mapped[str] = mapped_column(String(20), unique=True)
    # Prioridad: 1 = emergencia (se marca en la solicitud), 2 = cliente VIP, 3 = cliente normal
    nivel_prioridad: Mapped[int] = mapped_column(Integer, default=3)
    # Datos comerciales: referencia del cliente en Odoo y si tiene crédito (no pasa por Cobros)
    cliente_odoo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    credito: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    usuario: Mapped[Usuario] = relationship(back_populates="cliente")
    direcciones: Mapped[list["Direccion"]] = relationship(
        back_populates="cliente", order_by="Direccion.id", cascade="all, delete-orphan"
    )


class Direccion(Base):
    __tablename__ = "direcciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id", ondelete="CASCADE"), index=True)
    departamento: Mapped[str] = mapped_column(String(40))
    municipio: Mapped[str] = mapped_column(String(80))
    direccion: Mapped[str] = mapped_column(String(250))
    principal: Mapped[bool] = mapped_column(Boolean, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    cliente: Mapped[Cliente] = relationship(back_populates="direcciones")


class Ausencia(Base):
    """Días en que un empleado no labora: el reparto automático no le asigna trabajo."""
    __tablename__ = "ausencias"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    desde: Mapped["date"] = mapped_column(Date)  # noqa: F821
    hasta: Mapped["date"] = mapped_column(Date)  # noqa: F821
    motivo: Mapped[str] = mapped_column(String(150))
    creado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    usuario: Mapped[Usuario] = relationship(foreign_keys=[usuario_id])


class EstadoPersonal(Base):
    """Auditoría de estados del personal: un registro por periodo (hasta = NULL mientras sigue en ese estado)."""
    __tablename__ = "estados_personal"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    estado: Mapped[str] = mapped_column(String(15))
    desde: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # usuario | supervisor | inicio_sesion | cierre_sesion | actividad | automatico
    origen: Mapped[str] = mapped_column(String(20))
    nota: Mapped[str | None] = mapped_column(String(200), nullable=True)   # motivo de la capacitación
    con_reparto: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # capacitación: se repartió lo asignado
    registrado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    usuario: Mapped[Usuario] = relationship(foreign_keys=[usuario_id])
    registrado_por: Mapped["Usuario | None"] = relationship(foreign_keys=[registrado_por_id])


# Modelos de configuración (catálogos, flujos, calendario...). Se importan aquí para registrarlos.
from app.modelos.configuracion import (  # noqa: E402,F401
    Color, ColorCaja, DiaNoLaborable, Flujo, FlujoPaso, GuiaColor, Material, MotivoRP, Parametro, TipoTrabajo, Unidad,
    material_guia, material_unidad, tipo_material, usuario_area_tipo,
)
from app.modelos.solicitud import (  # noqa: E402,F401
    ESTADOS, ESTADOS_CERRADOS, Correlativo, Solicitud, SolicitudArchivo, SolicitudHistorial, SolicitudPaso, TiempoPaso,
)
