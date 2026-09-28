"""Acceso a la bitácora de auditoría (MongoDB)."""
from datetime import datetime, timezone

from pymongo import DESCENDING


class AuditoriaRepositorio:
    def __init__(self, mongo):
        self.coleccion = mongo["auditoria"]

    def registrar(self, evento: dict) -> None:
        evento = {**evento, "fecha": datetime.now(timezone.utc)}
        self.coleccion.insert_one(evento)

    def listar(self, limite: int = 100, entidad: str | None = None, accion: str | None = None,
               solo_de: tuple[int | None, str | None] | None = None) -> list[dict]:
        filtro = {}
        if solo_de:  # solo los eventos de una persona (por id o por correo, p. ej. inicios fallidos)
            usuario_id, email = solo_de
            filtro["$or"] = [{"actor_id": usuario_id}, {"actor_email": (email or "").lower()}]
        if entidad:
            filtro["entidad"] = entidad
        if accion:
            filtro["accion"] = accion
        cursor = self.coleccion.find(filtro).sort("fecha", DESCENDING).limit(limite)
        eventos = []
        for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            fecha = doc.get("fecha")
            if isinstance(fecha, datetime) and fecha.tzinfo is None:
                doc["fecha"] = fecha.replace(tzinfo=timezone.utc)  # Mongo guarda en UTC
            eventos.append(doc)
        return eventos
