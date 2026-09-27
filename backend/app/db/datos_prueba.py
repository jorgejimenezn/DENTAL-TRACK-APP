"""Carga los datos simulados (datos_prueba.json) si CARGAR_DATOS_PRUEBA=true.

Es idempotente: omite correos o NIT que ya existan, así que puede quedar activa
sin duplicar nada en cada reinicio del servicio.
"""
import json
import logging
import os
from pathlib import Path

from sqlalchemy import func, select

from app.db.mongo import obtener_mongo
from app.db.postgres import SesionLocal
from app.modelos import ROL_CLIENTE, Area, Cliente, Direccion, Usuario
from app.repositorios.auditoria_repo import AuditoriaRepositorio

ARCHIVO = Path(__file__).with_name("datos_prueba.json")
log = logging.getLogger("datos_prueba")


def cargar_datos_prueba() -> None:
    if os.getenv("CARGAR_DATOS_PRUEBA", "").lower() not in ("1", "true", "si", "sí"):
        return
    if not ARCHIVO.exists():
        log.warning("No existe %s", ARCHIVO.name)
        return
    datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
    nuevos_empleados = nuevos_clientes = 0

    with SesionLocal() as sesion:
        correos = set(sesion.scalars(select(func.lower(Usuario.email))))
        documentos = set(sesion.scalars(select(Cliente.numero_documento)))
        areas = {a.nombre: a for a in sesion.scalars(select(Area))}

        for e in datos.get("empleados", []):
            if e["email"] in correos:
                continue
            sesion.add(Usuario(
                nombre=e["nombre"], apellido=e["apellido"], email=e["email"], telefono=e.get("telefono"),
                direccion=e.get("direccion"), password_hash=e["password_hash"], rol=e["rol"], activo=True,
                areas=[areas[n] for n in e.get("areas", []) if n in areas],
            ))
            correos.add(e["email"])
            nuevos_empleados += 1

        for c in datos.get("clientes", []):
            if c["email"] in correos or c["numero_documento"] in documentos:
                continue
            usuario = Usuario(nombre=c["razon_social"], apellido="", email=c["email"],
                              telefono=c.get("telefono_celular") or c.get("telefono_fijo"),
                              password_hash=c["password_hash"], rol=ROL_CLIENTE, activo=True)
            sesion.add(usuario)
            sesion.flush()
            sesion.add(Cliente(
                usuario_id=usuario.id, razon_social=c["razon_social"], nombre_facturacion=c["nombre_facturacion"],
                telefono_celular=c.get("telefono_celular"), telefono_fijo=c.get("telefono_fijo"),
                tipo_documento=c["tipo_documento"], numero_documento=c["numero_documento"],
                nivel_prioridad=c["nivel_prioridad"],
                direcciones=[Direccion(**c["direccion"], principal=True)],
            ))
            correos.add(c["email"])
            documentos.add(c["numero_documento"])
            nuevos_clientes += 1

        sesion.commit()

    if nuevos_empleados or nuevos_clientes:
        log.info("Datos de prueba: %s empleados y %s clientes nuevos", nuevos_empleados, nuevos_clientes)
        try:
            AuditoriaRepositorio(obtener_mongo()).registrar({
                "accion": "carga_datos_prueba", "entidad": "sistema", "entidad_id": None,
                "actor_id": None, "actor_email": "sistema",
                "detalle": {"empleados": nuevos_empleados, "clientes": nuevos_clientes},
            })
        except Exception as error:
            log.warning("No se pudo registrar la carga en la bitácora: %s", error)
