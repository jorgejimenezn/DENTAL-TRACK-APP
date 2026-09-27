"""Solicitudes de trabajo: casos nuevos (CN) y reaperturas (RP).

Los datos del catálogo se guardan dos veces a propósito: el id (para reportes y flujos)
y el nombre como "foto" del momento, así un caso viejo no cambia si luego se renombra
un material. Si el id es nulo y el nombre no, el valor fue "fuera de catálogo".
"""
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base

# Estado → (texto visible, columna del tablero Kanban del doctor)
ESTADOS = {
    "pendiente_recolecta": ("Pendiente de recolecta", "Ingreso"),
    "validacion_qa": ("Validación de QA", "Ingreso"),
    "recibida": ("Recibida", "Ingreso"),
    "en_produccion": ("En producción", "Producción"),
    "control_calidad": ("Control de calidad", "Producción"),
    "facturacion": ("Facturación y empaque", "Despacho"),
    "en_ruta": ("En ruta de entrega", "Despacho"),
    "entregada": ("Entregada", "Entregado"),
    "cancelada": ("Cancelada", "Cancelado"),
}
ESTADOS_CERRADOS = {"entregada", "cancelada"}


class Correlativo(Base):
    """Último número usado por prefijo (CN, RP). Se bloquea la fila al generar un código."""
    __tablename__ = "correlativos"
    prefijo: Mapped[str] = mapped_column(String(4), primary_key=True)
    ultimo: Mapped[int] = mapped_column(Integer, default=0)


class Solicitud(Base):
    __tablename__ = "solicitudes"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    tipo_caso: Mapped[str] = mapped_column(String(2))  # CN | RP
    estado: Mapped[str] = mapped_column(String(30), index=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    creado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # --- Reapertura (solo RP) ---
    caso_origen_id: Mapped[int | None] = mapped_column(ForeignKey("solicitudes.id"), nullable=True, index=True)
    reapertura_tipo: Mapped[str | None] = mapped_column(String(15), nullable=True)  # garantia | modificacion
    reapertura_motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Validación de QA (se llena en la siguiente fase)
    qa_clasificacion: Mapped[str | None] = mapped_column(String(30), nullable=True)
    qa_motivo_id: Mapped[int | None] = mapped_column(ForeignKey("motivos_rp.id"), nullable=True)
    qa_observacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    qa_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    qa_fecha: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Datos del caso ---
    modalidad: Mapped[str] = mapped_column(String(10))  # digital | analogo
    requiere_recolecta: Mapped[bool] = mapped_column(Boolean, default=False)
    paciente: Mapped[str] = mapped_column(String(120))
    referencia_clinica: Mapped[str | None] = mapped_column(String(60), nullable=True)
    doctor_tratante: Mapped[str | None] = mapped_column(String(120), nullable=True)

    tipo_trabajo_id: Mapped[int | None] = mapped_column(ForeignKey("tipos_trabajo.id"), nullable=True)
    tipo_trabajo: Mapped[str] = mapped_column(String(120))
    material_id: Mapped[int | None] = mapped_column(ForeignKey("materiales.id"), nullable=True)
    material: Mapped[str] = mapped_column(String(120))
    unidad_id: Mapped[int | None] = mapped_column(ForeignKey("unidades.id"), nullable=True)
    unidad: Mapped[str] = mapped_column(String(120))
    guia_id: Mapped[int | None] = mapped_column(ForeignKey("guias_color.id"), nullable=True)
    guia: Mapped[str | None] = mapped_column(String(120), nullable=True)  # nulo = no aplica
    color_id: Mapped[int | None] = mapped_column(ForeignKey("colores.id"), nullable=True)
    color: Mapped[str | None] = mapped_column(String(120), nullable=True)
    fuera_catalogo: Mapped[bool] = mapped_column(Boolean, default=False)
    piezas: Mapped[list] = mapped_column(JSON, default=list)

    # --- Prioridad y fechas ---
    emergencia: Mapped[bool] = mapped_column(Boolean, default=False)
    prioridad: Mapped[int] = mapped_column(Integer, index=True)  # 1 emergencia, 2 VIP, 3 normal
    fecha_minima: Mapped[date] = mapped_column(Date)
    fecha_entrega: Mapped[date] = mapped_column(Date, index=True)

    # --- Direcciones (copia de la dirección usada) ---
    entrega_departamento: Mapped[str] = mapped_column(String(40))
    entrega_municipio: Mapped[str] = mapped_column(String(80))
    entrega_direccion: Mapped[str] = mapped_column(String(250))
    recolecta_departamento: Mapped[str | None] = mapped_column(String(40), nullable=True)
    recolecta_municipio: Mapped[str | None] = mapped_column(String(80), nullable=True)
    recolecta_direccion: Mapped[str | None] = mapped_column(String(250), nullable=True)

    instrucciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    cliente: Mapped["Cliente"] = relationship()  # noqa: F821
    creado_por: Mapped["Usuario | None"] = relationship(foreign_keys=[creado_por_id])  # noqa: F821
    caso_origen: Mapped["Solicitud | None"] = relationship(remote_side=[id], foreign_keys=[caso_origen_id])
    archivos: Mapped[list["SolicitudArchivo"]] = relationship(back_populates="solicitud", order_by="SolicitudArchivo.id",
                                                             cascade="all, delete-orphan")
    historial: Mapped[list["SolicitudHistorial"]] = relationship(order_by="SolicitudHistorial.id",
                                                                 cascade="all, delete-orphan")


class SolicitudArchivo(Base):
    """Referencia relacional al archivo guardado en MongoDB (GridFS)."""
    __tablename__ = "solicitud_archivos"
    id: Mapped[int] = mapped_column(primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id", ondelete="CASCADE"), index=True)
    mongo_id: Mapped[str] = mapped_column(String(24), unique=True)
    nombre: Mapped[str] = mapped_column(String(200))
    tipo: Mapped[str] = mapped_column(String(10))  # stl | imagen | pdf
    tamano: Mapped[int] = mapped_column(Integer)
    subido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    solicitud: Mapped[Solicitud] = relationship(back_populates="archivos")


class SolicitudHistorial(Base):
    """Cada cambio de estado del caso (línea de tiempo del detalle)."""
    __tablename__ = "solicitud_historial"
    id: Mapped[int] = mapped_column(primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id", ondelete="CASCADE"), index=True)
    estado: Mapped[str] = mapped_column(String(30))
    nota: Mapped[str | None] = mapped_column(String(300), nullable=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    usuario: Mapped["Usuario | None"] = relationship()  # noqa: F821
