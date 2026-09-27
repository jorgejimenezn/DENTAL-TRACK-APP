"""Ejecuta un archivo SQL contra la base de datos de Railway desde tu computadora.

Uso (desde la raíz del repositorio, en la terminal de VS Code):
    pip install "psycopg[binary]"
    python herramientas/ejecutar_sql.py "<DATABASE_PUBLIC_URL>" herramientas/datos_prueba.sql

La URL está en Railway → Postgres → Variables → DATABASE_PUBLIC_URL.
"""
import sys
from pathlib import Path

import psycopg


def main():
    if len(sys.argv) != 3:
        raise SystemExit('Uso: python herramientas/ejecutar_sql.py "<DATABASE_PUBLIC_URL>" <archivo.sql>')
    url, archivo = sys.argv[1], Path(sys.argv[2])
    sql = archivo.read_text(encoding="utf-8")

    with psycopg.connect(url, autocommit=True) as conexion:
        conexion.execute(sql)
        print(f"✔ {archivo.name} ejecutado\n")

        print("Usuarios por rol:")
        for rol, total in conexion.execute("SELECT rol, COUNT(*) FROM usuarios GROUP BY rol ORDER BY rol"):
            print(f"  {rol:<12} {total}")

        print("\nClientes por prioridad:")
        nombres = {2: "VIP", 3: "Normal"}
        for nivel, total in conexion.execute(
                "SELECT nivel_prioridad, COUNT(*) FROM clientes GROUP BY nivel_prioridad ORDER BY nivel_prioridad"):
            print(f"  {nivel} · {nombres.get(nivel, '?'):<7} {total}")


if __name__ == "__main__":
    main()
