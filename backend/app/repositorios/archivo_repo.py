"""Archivos de las solicitudes (STL, fotos, PDF) guardados en MongoDB con GridFS.

GridFS parte cada archivo en bloques de 255 KB, así se pueden guardar STL grandes
sin el límite de 16 MB por documento. PostgreSQL solo guarda la referencia (mongo_id).

Ciclo de vida:
  1. POST /archivos → se guarda como "pendiente" del usuario que lo sube.
  2. Al crear la solicitud se enlaza (pendiente = False, solicitud_id = N).
  3. Los pendientes con más de 24 h se borran solos (formularios abandonados).
"""
from datetime import datetime, timedelta, timezone

import gridfs
from bson import ObjectId
from bson.errors import InvalidId

from app.core.config import config

if config.MONGO_URL.startswith("mongomock://"):  # pruebas locales sin servidor Mongo
    import mongomock.gridfs
    mongomock.gridfs.enable_gridfs_integration()

COLECCION = "archivos"


def _oid(archivo_id: str) -> ObjectId | None:
    try:
        return ObjectId(archivo_id)
    except (InvalidId, TypeError):
        return None


class ArchivoRepositorio:
    def __init__(self, mongo):
        self.fs = gridfs.GridFS(mongo, COLECCION)
        self.meta = mongo[f"{COLECCION}.files"]

    def guardar(self, contenido: bytes, nombre: str, tipo_mime: str, tipo: str, usuario_id: int | None) -> dict:
        self.limpiar_abandonados()
        oid = self.fs.put(contenido, filename=nombre, contentType=tipo_mime, metadata={
            "usuario_id": usuario_id, "tipo": tipo, "pendiente": True, "solicitud_id": None,
            "subido_en": datetime.now(timezone.utc),
        })
        return {"id": str(oid), "nombre": nombre, "tipo": tipo, "tamano": len(contenido)}

    def pendientes(self, ids: list[str], usuario_id: int | None) -> list[dict]:
        """Archivos pendientes del usuario, en el mismo orden de ids. Omite los que no califican."""
        docs = {str(d["_id"]): d for d in self.meta.find({"_id": {"$in": [o for o in map(_oid, ids) if o]},
                                                          "metadata.pendiente": True,
                                                          "metadata.usuario_id": usuario_id})}
        return [{"id": i, "nombre": docs[i]["filename"], "tipo": docs[i]["metadata"]["tipo"],
                 "tamano": docs[i]["length"]} for i in ids if i in docs]

    def enlazar(self, ids: list[str], solicitud_id: int) -> None:
        self.meta.update_many({"_id": {"$in": [o for o in map(_oid, ids) if o]}},
                              {"$set": {"metadata.pendiente": False, "metadata.solicitud_id": solicitud_id}})

    def eliminar_pendiente(self, archivo_id: str, usuario_id: int | None) -> bool:
        oid = _oid(archivo_id)
        doc = oid and self.meta.find_one({"_id": oid, "metadata.pendiente": True, "metadata.usuario_id": usuario_id})
        if not doc:
            return False
        self.fs.delete(oid)
        return True

    def abrir(self, archivo_id: str):
        oid = _oid(archivo_id)
        if not oid or not self.fs.exists(oid):
            return None
        return self.fs.get(oid)

    def limpiar_abandonados(self) -> None:
        limite = datetime.now(timezone.utc) - timedelta(hours=24)
        for doc in self.meta.find({"metadata.pendiente": True, "metadata.subido_en": {"$lt": limite}}, {"_id": 1}):
            self.fs.delete(doc["_id"])
