"""Acceso a datos de usuarios (PostgreSQL)."""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.modelos import ROL_CLIENTE, Usuario


class UsuarioRepositorio:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def por_id(self, usuario_id: int) -> Usuario | None:
        return self.sesion.get(Usuario, usuario_id)

    def por_email(self, email: str) -> Usuario | None:
        return self.sesion.scalar(select(Usuario).where(func.lower(Usuario.email) == email.lower()))

    def email_existe(self, email: str, excluir_id: int | None = None) -> bool:
        consulta = select(Usuario.id).where(func.lower(Usuario.email) == email.lower())
        if excluir_id:
            consulta = consulta.where(Usuario.id != excluir_id)
        return self.sesion.scalar(consulta) is not None

    def listar_empleados(self, texto: str | None = None, rol: str | None = None,
                         activo: bool | None = None) -> list[Usuario]:
        consulta = (select(Usuario).options(selectinload(Usuario.areas))
                    .where(Usuario.rol != ROL_CLIENTE).order_by(Usuario.nombre, Usuario.apellido))
        if texto:
            patron = f"%{texto.lower()}%"
            consulta = consulta.where(or_(func.lower(Usuario.nombre).like(patron),
                                          func.lower(Usuario.apellido).like(patron),
                                          func.lower(Usuario.email).like(patron)))
        if rol:
            consulta = consulta.where(Usuario.rol == rol)
        if activo is not None:
            consulta = consulta.where(Usuario.activo == activo)
        return list(self.sesion.scalars(consulta))

    def contar_admins_activos(self) -> int:
        return self.sesion.scalar(select(func.count(Usuario.id))
                                  .where(Usuario.rol == "admin", Usuario.activo.is_(True)))

    def agregar(self, usuario: Usuario) -> Usuario:
        self.sesion.add(usuario)
        self.sesion.flush()
        return usuario
