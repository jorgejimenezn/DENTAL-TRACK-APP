"""Migraciones ligeras: actualizan tablas creadas por versiones anteriores sin borrar datos.

`create_all` solo crea tablas nuevas; no agrega columnas a las existentes. Cada paso
revisa primero si hace falta, así que es seguro ejecutarlo en cada arranque.
"""
import logging

from sqlalchemy import inspect, text

from app.db.postgres import engine

log = logging.getLogger("migraciones")


def _columnas(inspector, tabla: str) -> dict:
    if not inspector.has_table(tabla):
        return {}
    return {c["name"]: c for c in inspector.get_columns(tabla)}


def migrar() -> None:
    inspector = inspect(engine)
    usuarios = _columnas(inspector, "usuarios")
    clientes = _columnas(inspector, "clientes")
    if not usuarios:
        return  # base nueva: create_all se encarga de todo

    pasos: list[str] = []

    # --- v1 → v2: usuarios -------------------------------------------------
    if "telefono" not in usuarios:
        pasos.append("ALTER TABLE usuarios ADD COLUMN telefono VARCHAR(8)")
    if "direccion" not in usuarios:
        pasos.append("ALTER TABLE usuarios ADD COLUMN direccion VARCHAR(250)")
    if getattr(usuarios["nombre"]["type"], "length", 150) < 150:
        pasos.append("ALTER TABLE usuarios ALTER COLUMN nombre TYPE VARCHAR(150)")

    # --- v1 → v2: clientes -------------------------------------------------
    if clientes and "razon_social" not in clientes:
        pasos += [
            "ALTER TABLE clientes ADD COLUMN razon_social VARCHAR(150)",
            "ALTER TABLE clientes ADD COLUMN nombre_facturacion VARCHAR(150)",
            # La razón social toma el nombre del doctor registrado en la v1
            """UPDATE clientes c
               SET razon_social = TRIM(u.nombre || ' ' || u.apellido),
                   nombre_facturacion = TRIM(u.nombre || ' ' || u.apellido)
               FROM usuarios u WHERE u.id = c.usuario_id""",
            "UPDATE usuarios u SET nombre = c.razon_social, apellido = '' FROM clientes c WHERE c.usuario_id = u.id",
            "ALTER TABLE clientes ALTER COLUMN razon_social SET NOT NULL",
            "ALTER TABLE clientes ALTER COLUMN nombre_facturacion SET NOT NULL",
            # v1: 1 = alta, 2 = normal  →  v2: 2 = VIP, 3 = normal (el orden importa)
            "UPDATE clientes SET nivel_prioridad = 3 WHERE nivel_prioridad = 2",
            "UPDATE clientes SET nivel_prioridad = 2 WHERE nivel_prioridad = 1",
        ]
    if clientes and not clientes.get("telefono_celular", {}).get("nullable", True):
        pasos.append("ALTER TABLE clientes ALTER COLUMN telefono_celular DROP NOT NULL")

    if not pasos:
        return
    with engine.begin() as conexion:
        for sql in pasos:
            conexion.execute(text(sql))
    log.info("Migración aplicada: %s pasos", len(pasos))
