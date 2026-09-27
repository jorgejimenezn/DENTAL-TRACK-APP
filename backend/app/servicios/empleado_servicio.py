"""Lógica de negocio de empleados del laboratorio."""
from sqlalchemy.orm import Session

from app.core.dependencias import Actor
from app.core.errores import Conflicto, ErrorNegocio, NoEncontrado
from app.core.seguridad import cifrar_password
from app.esquemas.comun import AreaOut
from app.esquemas.empleado import EmpleadoActualizar, EmpleadoCrear, EmpleadoOut
from app.modelos import ROL_CLIENTE, Usuario
from app.repositorios.area_repo import AreaRepositorio
from app.repositorios.usuario_repo import UsuarioRepositorio
from app.servicios.auditoria_servicio import AuditoriaServicio


class EmpleadoServicio:
    def __init__(self, sesion: Session, auditoria: AuditoriaServicio):
        self.sesion = sesion
        self.usuarios = UsuarioRepositorio(sesion)
        self.areas = AreaRepositorio(sesion)
        self.auditoria = auditoria

    @staticmethod
    def a_salida(u: Usuario) -> EmpleadoOut:
        return EmpleadoOut(id=u.id, nombre=u.nombre, apellido=u.apellido, email=u.email,
                           telefono=u.telefono, direccion=u.direccion, rol=u.rol,
                           activo=u.activo, areas=[AreaOut(id=a.id, nombre=a.nombre) for a in u.areas],
                           creado_en=u.creado_en, ultimo_acceso=u.ultimo_acceso)

    def _obtener(self, empleado_id: int) -> Usuario:
        u = self.usuarios.por_id(empleado_id)
        if not u or u.rol == ROL_CLIENTE:
            raise NoEncontrado("Empleado no encontrado")
        return u

    def _areas(self, ids: list[int]):
        ids = list(dict.fromkeys(ids))
        areas = self.areas.por_ids(ids)
        if len(areas) != len(ids):
            raise ErrorNegocio("Una o más áreas no existen o están inactivas")
        return areas

    def _es_ultimo_admin(self, u: Usuario) -> bool:
        return u.rol == "admin" and u.activo and self.usuarios.contar_admins_activos() <= 1

    def listar(self, texto=None, rol=None, activo=None) -> list[EmpleadoOut]:
        return [self.a_salida(u) for u in self.usuarios.listar_empleados(texto, rol, activo)]

    def obtener(self, empleado_id: int) -> EmpleadoOut:
        return self.a_salida(self._obtener(empleado_id))

    def crear(self, datos: EmpleadoCrear, actor: Actor) -> EmpleadoOut:
        if self.usuarios.email_existe(datos.email):
            raise Conflicto("Ya existe un usuario con ese correo")
        u = Usuario(nombre=datos.nombre, apellido=datos.apellido, email=datos.email.lower(),
                    telefono=datos.telefono, direccion=datos.direccion,
                    password_hash=cifrar_password(datos.password), rol=datos.rol, activo=True)
        u.areas = self._areas(datos.area_ids)
        self.usuarios.agregar(u)
        self.sesion.commit()
        self.auditoria.registrar("crear", "empleado", u.id, actor, {
            "nombre": f"{u.nombre} {u.apellido}", "rol": u.rol, "areas": [a.nombre for a in u.areas]})
        return self.obtener(u.id)

    def actualizar(self, empleado_id: int, datos: EmpleadoActualizar, actor: Actor) -> EmpleadoOut:
        u = self._obtener(empleado_id)
        if self.usuarios.email_existe(datos.email, u.id):
            raise Conflicto("Ya existe un usuario con ese correo")
        if datos.rol != "admin" and self._es_ultimo_admin(u):
            raise ErrorNegocio("No puedes quitar el rol al único administrador activo")
        campos = ("nombre", "apellido", "email", "telefono", "direccion", "rol")
        antes = {c: getattr(u, c) for c in campos} | {"areas": [a.nombre for a in u.areas]}
        u.nombre, u.apellido, u.email, u.rol = datos.nombre, datos.apellido, datos.email.lower(), datos.rol
        u.telefono, u.direccion = datos.telefono, datos.direccion
        u.areas = self._areas(datos.area_ids)
        despues = {c: getattr(u, c) for c in campos} | {"areas": [a.nombre for a in u.areas]}
        self.sesion.commit()
        cambios = {k: [antes[k], despues[k]] for k in antes if antes[k] != despues[k]}
        if cambios:
            self.auditoria.registrar("editar", "empleado", u.id, actor, {"cambios": cambios})
        return self.obtener(u.id)

    def cambiar_estado(self, empleado_id: int, activo: bool, actor: Actor) -> EmpleadoOut:
        u = self._obtener(empleado_id)
        if not activo and actor.id == u.id:
            raise ErrorNegocio("No puedes desactivar tu propio usuario")
        if not activo and self._es_ultimo_admin(u):
            raise ErrorNegocio("No puedes desactivar al único administrador activo")
        u.activo = activo
        self.sesion.commit()
        self.auditoria.registrar("activar" if activo else "desactivar", "empleado", u.id, actor)
        return self.obtener(u.id)

    def cambiar_password(self, empleado_id: int, password: str, actor: Actor) -> None:
        u = self._obtener(empleado_id)
        u.password_hash = cifrar_password(password)
        self.sesion.commit()
        self.auditoria.registrar("cambiar_password", "empleado", u.id, actor)
