"""Lógica de inicio de sesión: valida credenciales. El token lo emite el servicio API."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.dependencias import Actor
from app.core.errores import NoAutorizado
from app.core.seguridad import verificar_password
from app.esquemas.comun import UsuarioSesion
from app.repositorios.usuario_repo import UsuarioRepositorio
from app.servicios.auditoria_servicio import AuditoriaServicio


class AuthServicio:
    def __init__(self, sesion: Session, auditoria: AuditoriaServicio):
        self.sesion = sesion
        self.usuarios = UsuarioRepositorio(sesion)
        self.auditoria = auditoria

    def verificar(self, email: str, password: str) -> UsuarioSesion:
        usuario = self.usuarios.por_email(email)
        if not usuario or not verificar_password(password, usuario.password_hash):
            self.auditoria.registrar("login_fallido", "sesion", actor=Actor(None, email.lower()),
                                     detalle={"motivo": "credenciales"})
            raise NoAutorizado("Correo o contraseña incorrectos")
        if not usuario.activo:
            self.auditoria.registrar("login_fallido", "sesion", usuario.id, Actor(usuario.id, usuario.email),
                                     {"motivo": "usuario inactivo"})
            raise NoAutorizado("Tu usuario está desactivado. Contacta al administrador.")

        usuario.ultimo_acceso = datetime.now(timezone.utc)
        from app.servicios.estados_personal import EstadosPersonal
        EstadosPersonal(self.sesion, self.auditoria).al_iniciar_sesion(usuario)  # queda Conectado
        self.sesion.commit()
        self.auditoria.registrar("login_exitoso", "sesion", usuario.id, Actor(usuario.id, usuario.email),
                                 {"rol": usuario.rol})
        return self.a_sesion(usuario)

    def usuario_activo(self, usuario_id: int) -> UsuarioSesion:
        usuario = self.usuarios.por_id(usuario_id)
        if not usuario or not usuario.activo:
            raise NoAutorizado("Sesión no válida")
        from app.servicios.estados_personal import EstadosPersonal
        if EstadosPersonal(self.sesion, self.auditoria).con_actividad(usuario):
            self.sesion.commit()
        return self.a_sesion(usuario)

    def salir(self, actor: Actor) -> None:
        """Cierre de sesión: el empleado queda Desconectado (sus emergencias asignadas sin iniciar se reparten)."""
        usuario = self.usuarios.por_id(actor.id) if actor.id else None
        if not usuario:
            return
        from app.servicios.estados_personal import EstadosPersonal
        EstadosPersonal(self.sesion, self.auditoria).al_cerrar_sesion(usuario)
        self.sesion.commit()
        self.auditoria.registrar("logout", "sesion", usuario.id, actor, {"rol": usuario.rol})

    @staticmethod
    def a_sesion(usuario) -> UsuarioSesion:
        return UsuarioSesion(id=usuario.id, nombre=usuario.nombre, apellido=usuario.apellido,
                             email=usuario.email, rol=usuario.rol)
