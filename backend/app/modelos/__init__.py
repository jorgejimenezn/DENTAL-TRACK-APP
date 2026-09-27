"""Modelos de la base relacional (PostgreSQL)."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base

ROLES_INTERNOS = ["admin", "ingresos", "tecnico", "qa", "facturacion", "logistica"]
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
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
