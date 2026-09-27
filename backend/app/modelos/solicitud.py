"""Solicitudes de trabajo: casos nuevos (CN) y reaperturas (RP).

Los datos del catálogo se guardan dos veces a propósito: el id (para reportes y flujos)
y el nombre como "foto" del momento, así un caso viejo no cambia si luego se renombra
un material. Si el id es nulo y el nombre no, el valor fue "fuera de catálogo".
"""
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base

# Estado → (texto visible, columna del tablero Kanban del doctor)
ESTADOS = {
    "pendiente_recolecta": ("Pendiente de recolecta", "Recibido"),
    "validacion_qa": ("Validación de QA", "Recibido"),
    "recibida": ("En revisión de Ingresos", "Recibido"),
    "en_produccion": ("En producción", "En producción"),
    "control_calidad": ("Control de calidad", "Control de calidad"),
    "facturacion": ("Facturación y empaque", "Listo para entrega"),
    "listo_entrega": ("Listo para entrega", "Listo para entrega"),
    "en_ruta": ("En ruta de entrega", "Listo para entrega"),
    "entregada": ("Entregada", "Entregado"),
    "cancelada": ("Cancelada", "Cancelado"),
}
ESTADOS_CERRADOS = {"entregada", "cancelada"}
COLUMNAS_TABLERO = ["Recibido", "En producción", "Control de calidad", "Listo para entrega", "Entregado"]


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
    factura_numero: Mapped[str | None] = mapped_column(String(40), nullable=True)
    factura_fecha: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pago_estado: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)  # pendiente|pagado|no_aplica
    pagado_en: Mapped[date | None] = mapped_column(Date, nullable=True)
    pago_referencia: Mapped[str | None] = mapped_column(String(80), nullable=True)
    pago_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    # Caja física que asigna Ingresos al aprobar
    caja_color_id: Mapped[int | None] = mapped_column(ForeignKey("colores_caja.id"), nullable=True)
    caja_color: Mapped[str | None] = mapped_column(String(120), nullable=True)
    caja_numero: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ingresado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingresado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)

    cliente: Mapped["Cliente"] = relationship()  # noqa: F821
    creado_por: Mapped["Usuario | None"] = relationship(foreign_keys=[creado_por_id])  # noqa: F821
    ingresado_por: Mapped["Usuario | None"] = relationship(foreign_keys=[ingresado_por_id])  # noqa: F821
    qa_motivo: Mapped["MotivoRP | None"] = relationship()  # noqa: F821
    caso_origen: Mapped["Solicitud | None"] = relationship(remote_side=[id], foreign_keys=[caso_origen_id])
    archivos: Mapped[list["SolicitudArchivo"]] = relationship(back_populates="solicitud", order_by="SolicitudArchivo.id",
                                                             cascade="all, delete-orphan")
    historial: Mapped[list["SolicitudHistorial"]] = relationship(order_by="SolicitudHistorial.id",
                                                                 cascade="all, delete-orphan")
    pasos: Mapped[list["SolicitudPaso"]] = relationship(back_populates="solicitud", order_by="SolicitudPaso.orden",
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


# Estados de un paso del recorrido
PASO_PENDIENTE = "pendiente"      # todavía no le toca
PASO_EN_AREA = "en_area"          # áreas de apoyo: lo atiende cualquiera del área (Ingresos, QA, Facturación, Logística)
PASO_EN_COLA = "en_cola"          # producción: todos los que pueden hacerlo están al tope
PASO_SIN_TECNICO = "sin_tecnico"  # producción: nadie tiene asignada esa área y tipo de trabajo
PASO_ASIGNADO = "asignado"        # producción: en la bandeja de un técnico, esperando turno
PASO_EN_PROCESO = "en_proceso"    # producción: el técnico lo está trabajando (uno a la vez)
PASO_TERMINADO = "terminado"
PASO_OMITIDO = "omitido"          # cancelado o reemplazado al rehacer el recorrido
PASOS_ACTIVOS = {PASO_EN_AREA, PASO_EN_COLA, PASO_SIN_TECNICO, PASO_ASIGNADO, PASO_EN_PROCESO}
PASOS_CARGA = {PASO_ASIGNADO, PASO_EN_PROCESO}  # cuentan para el tope de trabajos del técnico


class SolicitudPaso(Base):
    """Un paso del recorrido del caso (copiado del flujo de su tipo de trabajo y modalidad)."""
    __tablename__ = "solicitud_pasos"
    id: Mapped[int] = mapped_column(primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id", ondelete="CASCADE"), index=True)
    orden: Mapped[int] = mapped_column(Integer)
    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id"))
    etapa: Mapped[str] = mapped_column(String(20))  # recolecta, ingresos, produccion, validacion_rp, qa, facturacion, entrega
    estado: Mapped[str] = mapped_column(String(15), default=PASO_PENDIENTE, index=True)
    tecnico_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True, index=True)
    atendido_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    activado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    asignado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    iniciado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    terminado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nota: Mapped[str | None] = mapped_column(String(300), nullable=True)
    receptor: Mapped[str | None] = mapped_column(String(120), nullable=True)  # quien recibió la entrega
    vuelta: Mapped[int] = mapped_column(Integer, default=1)  # sube cuando QA devuelve el caso

    solicitud: Mapped[Solicitud] = relationship(back_populates="pasos")
    area: Mapped["Area"] = relationship()  # noqa: F821
    tecnico: Mapped["Usuario | None"] = relationship(foreign_keys=[tecnico_id])  # noqa: F821
    atendido_por: Mapped["Usuario | None"] = relationship(foreign_keys=[atendido_por_id])  # noqa: F821


class TiempoPaso(Base):
    """Auditoría de tiempos: una fila por paso terminado, con horas laborales y la meta vigente en ese momento."""
    __tablename__ = "tiempos_paso"
    id: Mapped[int] = mapped_column(primary_key=True)
    paso_id: Mapped[int] = mapped_column(ForeignKey("solicitud_pasos.id", ondelete="CASCADE"), unique=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id", ondelete="CASCADE"), index=True)
    codigo: Mapped[str] = mapped_column(String(20))
    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id"), index=True)
    area: Mapped[str] = mapped_column(String(60))
    etapa: Mapped[str] = mapped_column(String(20))
    tipo_trabajo: Mapped[str] = mapped_column(String(120))
    responsable_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True, index=True)
    vuelta: Mapped[int] = mapped_column(Integer, default=1)
    activado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    iniciado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    terminado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    espera_horas: Mapped[float | None] = mapped_column(Float, nullable=True)   # llegada → inicio (producción)
    trabajo_horas: Mapped[float | None] = mapped_column(Float, nullable=True)  # inicio → fin (producción)
    total_horas: Mapped[float] = mapped_column(Float)                          # llegada → fin
    meta_horas: Mapped[float] = mapped_column(Float)
    cumplio: Mapped[bool] = mapped_column(Boolean)
    devuelto: Mapped[bool] = mapped_column(Boolean, default=False)  # QA devolvió el caso a este paso o antes
