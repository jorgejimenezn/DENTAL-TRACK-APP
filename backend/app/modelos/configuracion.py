"""Modelos de configuración administrable: catálogos, flujos, asignaciones, calendario y parámetros."""
from datetime import date

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base

# ---------------- Relaciones entre catálogos ----------------
# Tipo de trabajo → materiales permitidos
tipo_material = Table(
    "tipo_material", Base.metadata,
    Column("tipo_trabajo_id", ForeignKey("tipos_trabajo.id", ondelete="CASCADE"), primary_key=True),
    Column("material_id", ForeignKey("materiales.id", ondelete="CASCADE"), primary_key=True),
)
# Material → unidades permitidas
material_unidad = Table(
    "material_unidad", Base.metadata,
    Column("material_id", ForeignKey("materiales.id", ondelete="CASCADE"), primary_key=True),
    Column("unidad_id", ForeignKey("unidades.id", ondelete="CASCADE"), primary_key=True),
)
# Material → guías de color permitidas
material_guia = Table(
    "material_guia", Base.metadata,
    Column("material_id", ForeignKey("materiales.id", ondelete="CASCADE"), primary_key=True),
    Column("guia_id", ForeignKey("guias_color.id", ondelete="CASCADE"), primary_key=True),
)


class TipoTrabajo(Base):
    __tablename__ = "tipos_trabajo"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    materiales: Mapped[list["Material"]] = relationship(secondary=tipo_material, order_by="Material.nombre")


class Material(Base):
    __tablename__ = "materiales"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    unidades: Mapped[list["Unidad"]] = relationship(secondary=material_unidad, order_by="Unidad.id")
    guias: Mapped[list["GuiaColor"]] = relationship(secondary=material_guia, order_by="GuiaColor.nombre")


class Unidad(Base):
    __tablename__ = "unidades"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class GuiaColor(Base):
    __tablename__ = "guias_color"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    colores: Mapped[list["Color"]] = relationship(back_populates="guia", order_by="Color.id",
                                                  cascade="all, delete-orphan")


class Color(Base):
    __tablename__ = "colores"
    __table_args__ = (UniqueConstraint("guia_id", "nombre"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    guia_id: Mapped[int] = mapped_column(ForeignKey("guias_color.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(20))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    guia: Mapped[GuiaColor] = relationship(back_populates="colores")


class MotivoRP(Base):
    """Motivos que QA registra al validar un reproceso (garantía o cobro)."""
    __tablename__ = "motivos_rp"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


# ---------------- Flujos de pasos ----------------
class Flujo(Base):
    """Secuencia de áreas que recorre una orden según su tipo de trabajo y modalidad."""
    __tablename__ = "flujos"
    __table_args__ = (UniqueConstraint("tipo_trabajo_id", "modalidad"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tipo_trabajo_id: Mapped[int] = mapped_column(ForeignKey("tipos_trabajo.id", ondelete="CASCADE"))
    modalidad: Mapped[str] = mapped_column(String(10))  # digital | analogo
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    tipo_trabajo: Mapped[TipoTrabajo] = relationship()
    pasos: Mapped[list["FlujoPaso"]] = relationship(back_populates="flujo", order_by="FlujoPaso.orden",
                                                    cascade="all, delete-orphan")


class FlujoPaso(Base):
    __tablename__ = "flujo_pasos"
    __table_args__ = (UniqueConstraint("flujo_id", "orden"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    flujo_id: Mapped[int] = mapped_column(ForeignKey("flujos.id", ondelete="CASCADE"), index=True)
    orden: Mapped[int] = mapped_column(Integer)
    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id"))
    flujo: Mapped[Flujo] = relationship(back_populates="pasos")
    area: Mapped["Area"] = relationship()  # noqa: F821 (definida en modelos/__init__)


# ---------------- Asignación de técnicos ----------------
# Si un empleado tiene un área SIN filas aquí, puede trabajar todos los tipos en esa área.
# Si tiene filas, solo los tipos listados.
usuario_area_tipo = Table(
    "usuario_area_tipo", Base.metadata,
    Column("usuario_id", ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
    Column("area_id", ForeignKey("areas.id", ondelete="CASCADE"), primary_key=True),
    Column("tipo_trabajo_id", ForeignKey("tipos_trabajo.id", ondelete="CASCADE"), primary_key=True),
)


# ---------------- Calendario y parámetros ----------------
class DiaNoLaborable(Base):
    __tablename__ = "dias_no_laborables"
    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, unique=True, index=True)
    motivo: Mapped[str] = mapped_column(String(120))


class Parametro(Base):
    __tablename__ = "parametros"
    clave: Mapped[str] = mapped_column(String(40), primary_key=True)
    valor: Mapped[str] = mapped_column(String(40))
