"""Rutas internas de empleados."""
from fastapi import APIRouter, Depends

from app.core.dependencias import Actor, obtener_actor
from app.esquemas.comun import EstadoIn, PasswordIn
from app.esquemas.empleado import EmpleadoActualizar, EmpleadoCrear, EmpleadoOut
from app.rutas.proveedores import servicio_empleados
from app.servicios.empleado_servicio import EmpleadoServicio

router = APIRouter(prefix="/empleados", tags=["Empleados"])


@router.get("", response_model=list[EmpleadoOut])
def listar(q: str | None = None, rol: str | None = None, activo: bool | None = None,
           s: EmpleadoServicio = Depends(servicio_empleados)):
    return s.listar(q, rol, activo)


@router.get("/{empleado_id}", response_model=EmpleadoOut)
def obtener(empleado_id: int, s: EmpleadoServicio = Depends(servicio_empleados)):
    return s.obtener(empleado_id)


@router.post("", response_model=EmpleadoOut, status_code=201)
def crear(datos: EmpleadoCrear, actor: Actor = Depends(obtener_actor),
          s: EmpleadoServicio = Depends(servicio_empleados)):
    return s.crear(datos, actor)


@router.put("/{empleado_id}", response_model=EmpleadoOut)
def actualizar(empleado_id: int, datos: EmpleadoActualizar, actor: Actor = Depends(obtener_actor),
               s: EmpleadoServicio = Depends(servicio_empleados)):
    return s.actualizar(empleado_id, datos, actor)


@router.patch("/{empleado_id}/estado", response_model=EmpleadoOut)
def cambiar_estado(empleado_id: int, datos: EstadoIn, actor: Actor = Depends(obtener_actor),
                   s: EmpleadoServicio = Depends(servicio_empleados)):
    return s.cambiar_estado(empleado_id, datos.activo, actor)


@router.post("/{empleado_id}/password", status_code=204)
def cambiar_password(empleado_id: int, datos: PasswordIn, actor: Actor = Depends(obtener_actor),
                     s: EmpleadoServicio = Depends(servicio_empleados)):
    s.cambiar_password(empleado_id, datos.password, actor)
