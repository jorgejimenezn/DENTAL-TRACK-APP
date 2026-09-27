"""Datos iniciales: áreas del laboratorio y primer administrador."""
from sqlalchemy import select

from app.core.config import config
from app.core.seguridad import cifrar_password
from app.db.migraciones import migrar
from app.db.postgres import Base, SesionLocal, engine
from app.db.semilla_configuracion import sembrar_configuracion
from app.modelos import Area, Usuario

AREAS_INICIALES = [
    "Ingresos", "Logística", "Yesos", "Diseño", "CAD", "CAM_IMP",
    "CAM_FRES", "Finalización", "QA", "Facturación_Cobros",
]


def inicializar_base():
    migrar()  # primero actualiza tablas de versiones anteriores
    Base.metadata.create_all(engine)
    with SesionLocal() as sesion:
        existentes = set(sesion.scalars(select(Area.nombre)))
        for nombre in AREAS_INICIALES:
            if nombre not in existentes:
                sesion.add(Area(nombre=nombre))

        hay_admin = sesion.scalar(select(Usuario.id).where(Usuario.rol == "admin").limit(1))
        if not hay_admin:
            sesion.add(Usuario(
                nombre=config.ADMIN_NOMBRE, apellido="DENTAL TRACK",
                email=config.ADMIN_EMAIL.lower(), password_hash=cifrar_password(config.ADMIN_PASSWORD),
                rol="admin", activo=True,
            ))
        sesion.flush()
        sembrar_configuracion(sesion)
        sesion.commit()
