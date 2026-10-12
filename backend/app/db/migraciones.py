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
    if clientes and "cliente_odoo" not in clientes:
        pasos += ["ALTER TABLE clientes ADD COLUMN cliente_odoo VARCHAR(40)",
                  "ALTER TABLE clientes ADD COLUMN credito BOOLEAN NOT NULL DEFAULT FALSE"]
    if clientes and not clientes.get("telefono_celular", {}).get("nullable", True):
        pasos.append("ALTER TABLE clientes ALTER COLUMN telefono_celular DROP NOT NULL")

    # --- Fase 2A+: tope de trabajos por empleado ------------------------------
    if "max_trabajos" not in usuarios:
        pasos.append("ALTER TABLE usuarios ADD COLUMN max_trabajos INTEGER")

    # --- Fase 2A+: días con horario especial (medio día) ---------------------
    dias = _columnas(inspector, "dias_no_laborables")
    if dias and "hora_corte" not in dias:
        pasos += [
            "ALTER TABLE dias_no_laborables ADD COLUMN hora_corte VARCHAR(5)",
            "UPDATE dias_no_laborables SET hora_corte = '12:00' WHERE motivo ILIKE '%medio día%'",
        ]

    # --- Fase 3: número de factura en la solicitud ---------------------------
    solicitudes = _columnas(inspector, "solicitudes")
    if solicitudes and "factura_numero" not in solicitudes:
        pasos.append("ALTER TABLE solicitudes ADD COLUMN factura_numero VARCHAR(40)")
    if solicitudes and "colores_pieza" not in solicitudes:
        pasos.append("ALTER TABLE solicitudes ADD COLUMN colores_pieza JSON")
    # --- Caja física asignada por Ingresos -----------------------------------
    if solicitudes and "caja_numero" not in solicitudes:
        pasos += [
            "CREATE TABLE IF NOT EXISTS colores_caja (id SERIAL PRIMARY KEY, nombre VARCHAR(120) UNIQUE NOT NULL, "
            "activo BOOLEAN NOT NULL DEFAULT TRUE)",
            "ALTER TABLE solicitudes ADD COLUMN caja_color_id INTEGER REFERENCES colores_caja(id)",
            "ALTER TABLE solicitudes ADD COLUMN caja_color VARCHAR(120)",
            "ALTER TABLE solicitudes ADD COLUMN caja_numero VARCHAR(20)",
            "ALTER TABLE solicitudes ADD COLUMN ingresado_en TIMESTAMPTZ",
            "ALTER TABLE solicitudes ADD COLUMN ingresado_por_id INTEGER REFERENCES usuarios(id)",
        ]

    # --- Fase 3C: nombre de quien recibe la entrega ------------------------
    pasos_solicitud = _columnas(inspector, "solicitud_pasos")
    if pasos_solicitud and "receptor" not in pasos_solicitud:
        pasos.append("ALTER TABLE solicitud_pasos ADD COLUMN receptor VARCHAR(120)")

    # --- Operación por área: lote, simultáneos y meta de horas --------------
    areas = _columnas(inspector, "areas")
    if areas and "meta_horas" not in areas:
        pasos += [
            "ALTER TABLE areas ADD COLUMN lote BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE areas ADD COLUMN max_simultaneos INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE areas ADD COLUMN meta_horas DOUBLE PRECISION NOT NULL DEFAULT 4",
            "UPDATE areas SET lote = TRUE, max_simultaneos = 15 WHERE UPPER(nombre) LIKE 'YESO%' OR UPPER(nombre) LIKE 'CAM%'",
            "UPDATE areas SET meta_horas = 8 WHERE UPPER(nombre) LIKE 'CAM%'",
        ]
    # --- Cobros ------------------------------------------------------------
    if solicitudes and "pago_estado" not in solicitudes:
        pasos += [
            "ALTER TABLE solicitudes ADD COLUMN factura_fecha TIMESTAMPTZ",
            "ALTER TABLE solicitudes ADD COLUMN pago_estado VARCHAR(12)",
            "ALTER TABLE solicitudes ADD COLUMN pagado_en DATE",
            "ALTER TABLE solicitudes ADD COLUMN pago_referencia VARCHAR(80)",
            "ALTER TABLE solicitudes ADD COLUMN pago_por_id INTEGER REFERENCES usuarios(id)",
            "UPDATE solicitudes SET pago_estado = 'pendiente', factura_fecha = creado_en WHERE factura_numero IS NOT NULL",
        ]

    # --- Logística: recolecta/transporte, guía de salida y momento de recolecta ------
    if solicitudes and "entrega_metodo" not in solicitudes:
        pasos += [
            "ALTER TABLE solicitudes ADD COLUMN recolecta_metodo VARCHAR(12)",
            "ALTER TABLE solicitudes ADD COLUMN recolecta_guia VARCHAR(60)",
            "ALTER TABLE solicitudes ADD COLUMN entrega_metodo VARCHAR(12) NOT NULL DEFAULT 'mensajero'",
            "ALTER TABLE solicitudes ADD COLUMN entrega_transporte VARCHAR(80)",
            "ALTER TABLE solicitudes ADD COLUMN entrega_guia VARCHAR(60)",
            "UPDATE solicitudes SET recolecta_metodo = 'mensajero' WHERE modalidad = 'analogo'",
        ]
    if solicitudes and "manual" not in solicitudes:  # órdenes manuales: las capturadas por el personal
        pasos += [
            "ALTER TABLE solicitudes ADD COLUMN manual BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE solicitudes ADD COLUMN manual_motivo VARCHAR(200)",
            "UPDATE solicitudes s SET manual = TRUE FROM usuarios u WHERE u.id = s.creado_por_id AND u.rol <> 'doctor'",
        ]
    if solicitudes and "pausada" not in solicitudes:  # pausas
        pasos += [
            "ALTER TABLE solicitudes ADD COLUMN pausada BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE solicitudes ADD COLUMN pausa_motivo VARCHAR(250)",
            "ALTER TABLE solicitudes ADD COLUMN pausada_en TIMESTAMPTZ",
            "ALTER TABLE solicitudes ADD COLUMN pausada_por_id INTEGER REFERENCES usuarios(id)",
        ]
    if pasos_solicitud and "grupo" not in pasos_solicitud:  # pasos en paralelo, pausas y validación de diseño
        pasos += [
            "ALTER TABLE solicitud_pasos ADD COLUMN grupo INTEGER NOT NULL DEFAULT 0",
            "UPDATE solicitud_pasos SET grupo = orden",
            "ALTER TABLE solicitud_pasos ADD COLUMN pausa_espera DOUBLE PRECISION NOT NULL DEFAULT 0",
            "ALTER TABLE solicitud_pasos ADD COLUMN pausa_trabajo DOUBLE PRECISION NOT NULL DEFAULT 0",
            "ALTER TABLE solicitud_pasos ADD COLUMN enviado_en TIMESTAMPTZ",
        ]
    flujo_pasos = _columnas(inspector, "flujo_pasos")
    if flujo_pasos and "paralelo" not in flujo_pasos:
        pasos.append("ALTER TABLE flujo_pasos ADD COLUMN paralelo BOOLEAN NOT NULL DEFAULT FALSE")
    if pasos_solicitud and "recolectado_en" not in pasos_solicitud:
        pasos.append("ALTER TABLE solicitud_pasos ADD COLUMN recolectado_en TIMESTAMPTZ")

    if "estado" not in usuarios:  # estados del personal (conectado, refacción, almuerzo, capacitación, desconectado)
        pasos += [
            "ALTER TABLE usuarios ADD COLUMN estado VARCHAR(15) NOT NULL DEFAULT 'desconectado'",
            "ALTER TABLE usuarios ADD COLUMN estado_desde TIMESTAMPTZ",
            "ALTER TABLE usuarios ADD COLUMN estado_auto BOOLEAN NOT NULL DEFAULT TRUE",
            "ALTER TABLE usuarios ADD COLUMN capacitacion_solicitada_en TIMESTAMPTZ",
            "ALTER TABLE usuarios ADD COLUMN capacitacion_motivo VARCHAR(200)",
        ]
    if "cierre_navegador_en" not in usuarios:  # desconexión al cerrar el navegador sin cerrar sesión
        pasos.append("ALTER TABLE usuarios ADD COLUMN cierre_navegador_en TIMESTAMPTZ")

    if not pasos:
        return
    with engine.begin() as conexion:
        for sql in pasos:
            conexion.execute(text(sql))
    log.info("Migración aplicada: %s pasos", len(pasos))
