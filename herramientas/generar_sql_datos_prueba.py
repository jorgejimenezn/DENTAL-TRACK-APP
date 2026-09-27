"""Genera un script SQL con los datos de prueba para ejecutarlo en la consola de Postgres.

Uso (desde la raíz del repositorio):
    python herramientas/generar_sql_datos_prueba.py

Lee backend/app/db/datos_prueba.json y escribe herramientas/datos_prueba.sql.
El script es idempotente: se puede ejecutar varias veces sin duplicar registros.
Requiere las tablas de la versión 2 (el backend las crea o migra al arrancar).
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "backend" / "app" / "db" / "datos_prueba.json"
SALIDA = RAIZ / "herramientas" / "datos_prueba.sql"


def q(valor) -> str:
    """Literal SQL seguro."""
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "TRUE" if valor else "FALSE"
    if isinstance(valor, (int, float)):
        return str(valor)
    return "'" + str(valor).replace("'", "''") + "'"


def filas(tuplas) -> str:
    return ",\n  ".join("(" + ", ".join(q(v) for v in t) + ")" for t in tuplas)


def main():
    datos = json.loads(ENTRADA.read_text(encoding="utf-8"))
    empleados, clientes = datos["empleados"], datos["clientes"]

    usuarios_emp = [(e["nombre"], e["apellido"], e["email"], e.get("telefono"), e.get("direccion"),
                     e["password_hash"], e["rol"]) for e in empleados]
    areas = [(e["email"], a) for e in empleados for a in e.get("areas", [])]
    usuarios_cli = [(c["razon_social"], "", c["email"], c.get("telefono_celular") or c.get("telefono_fijo"), None,
                     c["password_hash"], "doctor") for c in clientes]
    datos_cli = [(c["email"], c["razon_social"], c["nombre_facturacion"], c.get("telefono_celular"),
                  c.get("telefono_fijo"), c["tipo_documento"], c["numero_documento"], c["nivel_prioridad"])
                 for c in clientes]
    direcciones = [(c["email"], c["direccion"]["departamento"], c["direccion"]["municipio"],
                    c["direccion"]["direccion"]) for c in clientes]

    sql = f"""-- DENTAL TRACK · Datos de prueba ({len(empleados)} empleados, {len(clientes)} clientes)
-- Idempotente: omite correos, NIT y relaciones que ya existan.
-- Las contraseñas iniciales están en credenciales_prueba.xlsx (aquí solo van cifradas).

BEGIN;

-- 1. Usuarios: empleados y cuentas de acceso de los clientes
INSERT INTO usuarios (nombre, apellido, email, telefono, direccion, password_hash, rol, activo)
SELECT v.nombre, v.apellido, v.email, v.telefono, v.direccion, v.hash, v.rol, TRUE
FROM (VALUES
  {filas(usuarios_emp + usuarios_cli)}
) AS v(nombre, apellido, email, telefono, direccion, hash, rol)
ON CONFLICT (email) DO NOTHING;

-- 2. Áreas de cada empleado
INSERT INTO usuario_area (usuario_id, area_id)
SELECT u.id, a.id
FROM (VALUES
  {filas(areas)}
) AS v(email, area)
JOIN usuarios u ON u.email = v.email
JOIN areas a ON a.nombre = v.area
ON CONFLICT DO NOTHING;

-- 3. Datos comerciales de los clientes (solo sobre usuarios con rol doctor)
INSERT INTO clientes (usuario_id, razon_social, nombre_facturacion, clinica, es_red, telefono_celular,
                      telefono_fijo, tipo_documento, numero_documento, nivel_prioridad)
SELECT u.id, v.razon, v.facturacion, NULL, FALSE, v.celular, v.fijo, v.tipo, v.documento, v.nivel
FROM (VALUES
  {filas(datos_cli)}
) AS v(email, razon, facturacion, celular, fijo, tipo, documento, nivel)
JOIN usuarios u ON u.email = v.email AND u.rol = 'doctor'
WHERE NOT EXISTS (SELECT 1 FROM clientes c WHERE c.usuario_id = u.id OR c.numero_documento = v.documento);

-- 4. Dirección principal de entrega de cada cliente
INSERT INTO direcciones (cliente_id, departamento, municipio, direccion, principal, activo)
SELECT c.id, v.departamento, v.municipio, v.direccion, TRUE, TRUE
FROM (VALUES
  {filas(direcciones)}
) AS v(email, departamento, municipio, direccion)
JOIN usuarios u ON u.email = v.email
JOIN clientes c ON c.usuario_id = u.id
WHERE NOT EXISTS (SELECT 1 FROM direcciones d WHERE d.cliente_id = c.id);

COMMIT;

-- Verificación
SELECT rol, COUNT(*) AS usuarios FROM usuarios GROUP BY rol ORDER BY rol;
SELECT nivel_prioridad, COUNT(*) AS clientes FROM clientes GROUP BY nivel_prioridad ORDER BY nivel_prioridad;
"""
    SALIDA.write_text(sql, encoding="utf-8")
    print(f"Script generado: {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
