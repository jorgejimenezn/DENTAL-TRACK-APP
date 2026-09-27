"""Acceso a datos de clientes y direcciones (PostgreSQL)."""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.modelos import Cliente, Direccion, Usuario


class ClienteRepositorio:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def _base(self):
        return (select(Cliente).join(Cliente.usuario)
                .options(joinedload(Cliente.usuario), selectinload(Cliente.direcciones)))

    def por_id(self, cliente_id: int) -> Cliente | None:
        return self.sesion.scalar(self._base().where(Cliente.id == cliente_id))

    def listar(self, texto: str | None = None, activo: bool | None = None,
               nivel: int | None = None) -> list[Cliente]:
        consulta = self._base().order_by(Usuario.nombre, Usuario.apellido)
        if texto:
            patron = f"%{texto.lower()}%"
            consulta = consulta.where(or_(
                func.lower(Usuario.nombre).like(patron), func.lower(Usuario.apellido).like(patron),
                func.lower(Usuario.email).like(patron), func.lower(Cliente.clinica).like(patron),
                Cliente.numero_documento.like(f"%{texto.upper()}%"),
            ))
        if activo is not None:
            consulta = consulta.where(Usuario.activo == activo)
        if nivel:
            consulta = consulta.where(Cliente.nivel_prioridad == nivel)
        return list(self.sesion.scalars(consulta).unique())

    def documento_existe(self, numero: str, excluir_id: int | None = None) -> bool:
        consulta = select(Cliente.id).where(Cliente.numero_documento == numero)
        if excluir_id:
            consulta = consulta.where(Cliente.id != excluir_id)
        return self.sesion.scalar(consulta) is not None

    def agregar(self, cliente: Cliente) -> Cliente:
        self.sesion.add(cliente)
        self.sesion.flush()
        return cliente

    def direccion_por_id(self, cliente_id: int, direccion_id: int) -> Direccion | None:
        return self.sesion.scalar(select(Direccion).where(
            Direccion.id == direccion_id, Direccion.cliente_id == cliente_id))
