"""Acceso a datos del catálogo de áreas (PostgreSQL)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos import Area


class AreaRepositorio:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def listar_activas(self) -> list[Area]:
        return list(self.sesion.scalars(select(Area).where(Area.activo.is_(True)).order_by(Area.id)))

    def por_ids(self, ids: list[int]) -> list[Area]:
        if not ids:
            return []
        return list(self.sesion.scalars(select(Area).where(Area.id.in_(ids), Area.activo.is_(True))))
