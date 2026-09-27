"""Fábricas de servicios para inyección de dependencias (principio D de SOLID)."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.mongo import obtener_mongo
from app.db.postgres import obtener_sesion
from app.repositorios.auditoria_repo import AuditoriaRepositorio
from app.servicios.auditoria_servicio import AuditoriaServicio
from app.servicios.auth_servicio import AuthServicio
from app.servicios.cliente_servicio import ClienteServicio
from app.servicios.empleado_servicio import EmpleadoServicio


def servicio_auditoria() -> AuditoriaServicio:
    return AuditoriaServicio(AuditoriaRepositorio(obtener_mongo()))


def servicio_auth(sesion: Session = Depends(obtener_sesion),
                  auditoria: AuditoriaServicio = Depends(servicio_auditoria)) -> AuthServicio:
    return AuthServicio(sesion, auditoria)


def servicio_clientes(sesion: Session = Depends(obtener_sesion),
                      auditoria: AuditoriaServicio = Depends(servicio_auditoria)) -> ClienteServicio:
    return ClienteServicio(sesion, auditoria)


def servicio_empleados(sesion: Session = Depends(obtener_sesion),
                       auditoria: AuditoriaServicio = Depends(servicio_auditoria)) -> EmpleadoServicio:
    return EmpleadoServicio(sesion, auditoria)
