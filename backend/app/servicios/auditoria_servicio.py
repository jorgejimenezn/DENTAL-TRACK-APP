"""Registro de eventos en la bitácora (MongoDB). Nunca debe romper la operación principal."""
import logging

from app.core.dependencias import Actor
from app.repositorios.auditoria_repo import AuditoriaRepositorio

log = logging.getLogger("auditoria")


class AuditoriaServicio:
    def __init__(self, repo: AuditoriaRepositorio):
        self.repo = repo

    def registrar(self, accion: str, entidad: str, entidad_id=None, actor: Actor | None = None,
                  detalle: dict | None = None) -> None:
        try:
            self.repo.registrar({
                "accion": accion,
                "entidad": entidad,
                "entidad_id": entidad_id,
                "actor_id": actor.id if actor else None,
                "actor_email": actor.email if actor else None,
                "detalle": detalle or {},
            })
        except Exception as error:  # la bitácora no debe tumbar el registro de un cliente
            log.warning("No se pudo registrar en la bitácora: %s", error)

    def listar(self, limite: int, entidad: str | None, accion: str | None, actor: Actor | None = None) -> list[dict]:
        # El perfil de demostración solo ve sus propios movimientos
        solo_de = (actor.id, actor.email) if actor and actor.rol == "demo" else None
        return self.repo.listar(limite, entidad, accion, solo_de)
