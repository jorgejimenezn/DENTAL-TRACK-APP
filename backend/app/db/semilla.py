"""Datos iniciales: áreas del laboratorio y primer administrador."""
from sqlalchemy import select

from app.core.config import config
from app.core.seguridad import cifrar_password
from app.db.migraciones import migrar
from app.db.postgres import Base, SesionLocal, engine
from app.db.semilla_configuracion import sembrar_configuracion
from app.modelos import Area, Usuario, valores_area

AREAS_INICIALES = [
    "Ingresos", "Logística", "Yesos", "Diseño", "CAD", "CAM_IMP",
    "CAM_FRES", "Finalización", "QA", "Facturación_Cobros", "Validación de diseño",
]


def inicializar_base():
    migrar()  # primero actualiza tablas de versiones anteriores
    Base.metadata.create_all(engine)
    with SesionLocal() as sesion:
        existentes = set(sesion.scalars(select(Area.nombre)))
        for nombre in AREAS_INICIALES:
            if nombre not in existentes:
                sesion.add(Area(nombre=nombre, **valores_area(nombre)))

        hay_admin = sesion.scalar(select(Usuario.id).where(Usuario.rol == "admin").limit(1))
        if not hay_admin:
            sesion.add(Usuario(
                nombre=config.ADMIN_NOMBRE, apellido="DENTAL TRACK",
                email=config.ADMIN_EMAIL.lower(), password_hash=cifrar_password(config.ADMIN_PASSWORD),
                rol="admin", activo=True,
            ))
        if config.DEMO_EMAIL and config.DEMO_PASSWORD and not sesion.scalar(
                select(Usuario.id).where(Usuario.email == config.DEMO_EMAIL.lower())):
            sesion.add(Usuario(nombre="Usuario", apellido="Demostración", email=config.DEMO_EMAIL.lower(),
                               password_hash=cifrar_password(config.DEMO_PASSWORD), rol="demo", activo=True))
        sesion.flush()
        sembrar_configuracion(sesion)
        sesion.flush()
        agregar_validacion_diseno(sesion)
        sesion.commit()


def preparar_recorridos():
    """Casos abiertos creados antes del motor de pasos: se les arma su recorrido."""
    from app.servicios.recorrido import Motor
    with SesionLocal() as sesion:
        if Motor(sesion).preparar_existentes():
            sesion.commit()


def agregar_validacion_diseno(sesion) -> None:
    """Una sola vez: inserta "Validación de diseño" en los flujos donde Diseño/CAD va seguido de impresión o fresado.
    Después el administrador puede quitarla o moverla; esta función no vuelve a tocar los flujos."""
    from app.modelos.configuracion import Flujo, FlujoPaso, Parametro
    from app.servicios.recorrido import _normal
    if sesion.get(Parametro, "flujos_validacion_diseno"):
        return
    validacion = next((a for a in sesion.scalars(select(Area)) if _normal(a.nombre).startswith("validacion de diseno")), None)
    if not validacion:
        return
    es_diseno = lambda a: _normal(a.nombre).startswith(("diseno", "cad"))  # noqa: E731
    es_cam = lambda a: _normal(a.nombre).startswith("cam")  # noqa: E731
    for flujo in sesion.scalars(select(Flujo)):
        pasos = sorted(flujo.pasos, key=lambda p: p.orden)
        if any(p.area_id == validacion.id for p in pasos):
            continue
        j = next((i for i, p in enumerate(pasos) if es_cam(p.area)), None)
        if not j or not es_diseno(pasos[j - 1].area):
            continue
        datos = [(p.area_id, p.paralelo) for p in pasos]
        datos.insert(j, (validacion.id, False))
        flujo.pasos.clear()
        sesion.flush()
        flujo.pasos.extend(FlujoPaso(orden=i + 1, area_id=a, paralelo=par) for i, (a, par) in enumerate(datos))
    sesion.add(Parametro(clave="flujos_validacion_diseno", valor="hecho"))
