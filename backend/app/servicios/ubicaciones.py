"""Coordenadas aproximadas de las direcciones para los mapas de calor.

Las direcciones del sistema son texto (departamento, municipio y dirección). Para ubicarlas en el mapa:
1. Ciudad de Guatemala: si la dirección dice "Zona N", se usa el centro aproximado de esa zona.
2. Municipios del área metropolitana: tabla incluida.
3. Otros municipios: se consultan una vez a Nominatim (OpenStreetMap) y se guardan en la tabla `geocodigos`.
   Se puede apagar con GEOCODIFICAR=false.
4. Si nada de lo anterior responde, el centro del departamento (queda marcado como aproximado).
Para el mapa de calor basta con el nivel de zona o municipio; no se ubica la casa exacta.
"""
import hashlib
import logging
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.modelos.configuracion import Geocodigo

log = logging.getLogger("ubicaciones")

DEPARTAMENTOS = {
    "guatemala": (14.6349, -90.5069), "el progreso": (14.8530, -90.0690), "sacatepequez": (14.5586, -90.7295),
    "chimaltenango": (14.6610, -90.8193), "escuintla": (14.3050, -90.7850), "santa rosa": (14.2800, -90.3000),
    "solola": (14.7730, -91.1830), "totonicapan": (14.9110, -91.3610), "quetzaltenango": (14.8340, -91.5180),
    "suchitepequez": (14.5340, -91.5030), "retalhuleu": (14.5370, -91.6770), "san marcos": (14.9630, -91.7940),
    "huehuetenango": (15.3190, -91.4710), "quiche": (15.0310, -91.1490), "baja verapaz": (15.1030, -90.3170),
    "alta verapaz": (15.4700, -90.3740), "peten": (16.9270, -89.8920), "izabal": (15.7300, -88.5940),
    "zacapa": (14.9720, -89.5300), "chiquimula": (14.8000, -89.5450), "jalapa": (14.6340, -89.9890),
    "jutiapa": (14.2920, -89.8960),
}
MUNICIPIOS = {  # área metropolitana y cabeceras frecuentes
    ("guatemala", "guatemala"): (14.6349, -90.5069), ("guatemala", "mixco"): (14.6330, -90.6064),
    ("guatemala", "villa nueva"): (14.5251, -90.5875), ("guatemala", "san miguel petapa"): (14.5047, -90.5589),
    ("guatemala", "santa catarina pinula"): (14.5689, -90.4953), ("guatemala", "fraijanes"): (14.4650, -90.4410),
    ("guatemala", "san jose pinula"): (14.5460, -90.4110), ("guatemala", "chinautla"): (14.7020, -90.4990),
    ("guatemala", "amatitlan"): (14.4870, -90.6150), ("guatemala", "villa canales"): (14.4820, -90.5340),
    ("guatemala", "san juan sacatepequez"): (14.7190, -90.6440), ("guatemala", "san pedro sacatepequez"): (14.6850, -90.6430),
    ("guatemala", "palencia"): (14.6650, -90.3580), ("guatemala", "san jose del golfo"): (14.7600, -90.3780),
    ("guatemala", "san pedro ayampuc"): (14.7870, -90.4510), ("guatemala", "chuarrancho"): (14.8180, -90.5130),
    ("guatemala", "san raymundo"): (14.7650, -90.5950),
    ("sacatepequez", "antigua guatemala"): (14.5586, -90.7295), ("quetzaltenango", "quetzaltenango"): (14.8347, -91.5181),
    ("escuintla", "escuintla"): (14.3050, -90.7850), ("chimaltenango", "chimaltenango"): (14.6610, -90.8193),
}
ZONAS_CIUDAD = {  # centro aproximado de las zonas de la Ciudad de Guatemala
    1: (14.6420, -90.5130), 2: (14.6560, -90.5120), 3: (14.6310, -90.5250), 4: (14.6220, -90.5150),
    5: (14.6270, -90.4950), 6: (14.6560, -90.4930), 7: (14.6330, -90.5600), 8: (14.6180, -90.5270),
    9: (14.6060, -90.5190), 10: (14.5990, -90.5080), 11: (14.6130, -90.5530), 12: (14.5850, -90.5450),
    13: (14.5830, -90.5280), 14: (14.5830, -90.5020), 15: (14.5980, -90.4840), 16: (14.6100, -90.4650),
    17: (14.6600, -90.4350), 18: (14.6600, -90.4600), 19: (14.6450, -90.5750), 21: (14.5550, -90.5400),
    24: (14.6600, -90.4150), 25: (14.6800, -90.4000),
}
_ZONA = re.compile(r"\bzona\s*(\d{1,2})\b", re.I)


def _normal(texto: str | None) -> str:
    sin = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(sin.lower().split())


def desplazar(lat: float, lng: float, semilla: str, radio: float = 0.004) -> tuple[float, float]:
    """Pequeño desplazamiento fijo por caso (~400 m) para que los puntos de una misma zona no queden encimados."""
    h = hashlib.md5(semilla.encode()).digest()
    return lat + (h[0] / 255 - 0.5) * 2 * radio, lng + (h[1] / 255 - 0.5) * 2 * radio


class Ubicador:
    def __init__(self, sesion: Session, consultas_maximas: int = 5):
        self.sesion = sesion
        self.restantes = consultas_maximas  # consultas externas permitidas por petición
        self.activo = os.getenv("GEOCODIFICAR", "true").lower() not in ("false", "0", "no")
        self._cache: dict[str, tuple[float, float, str] | None] = {}

    def coordenadas(self, departamento: str | None, municipio: str | None,
                    direccion: str | None) -> tuple[float, float, str] | None:
        """(lat, lng, nivel) con nivel = zona | municipio | departamento."""
        d, m = _normal(departamento), _normal(municipio)
        if d == "guatemala" and m in ("guatemala", "ciudad de guatemala"):
            zona = _ZONA.search(direccion or "")
            if zona and int(zona.group(1)) in ZONAS_CIUDAD:
                return (*ZONAS_CIUDAD[int(zona.group(1))], "zona")
        if (d, m) in MUNICIPIOS:
            return (*MUNICIPIOS[(d, m)], "municipio")
        if m:
            encontrado = self._municipio(d, m, departamento, municipio)
            if encontrado:
                return encontrado
        if d in DEPARTAMENTOS:
            return (*DEPARTAMENTOS[d], "departamento")
        return None

    def _municipio(self, d: str, m: str, departamento: str | None, municipio: str | None):
        clave = f"{d}|{m}"
        if clave in self._cache:
            return self._cache[clave]
        fila = self.sesion.get(Geocodigo, clave)
        reciente = fila and fila.actualizado and fila.actualizado > datetime.now(timezone.utc) - timedelta(days=30)
        if fila and fila.encontrado:
            self._cache[clave] = (fila.lat, fila.lng, "municipio")
        elif fila and reciente:
            self._cache[clave] = None  # no se encontró hace poco: no se vuelve a consultar todavía
        elif self.activo and self.restantes > 0:
            self.restantes -= 1
            coords = self._consultar(f"{municipio}, {departamento}, Guatemala")
            fila = fila or Geocodigo(clave=clave)
            fila.encontrado, fila.actualizado = coords is not None, datetime.now(timezone.utc)
            if coords:
                fila.lat, fila.lng = coords
            self.sesion.merge(fila)
            self.sesion.commit()
            self._cache[clave] = (*coords, "municipio") if coords else None
        else:
            self._cache[clave] = None
        return self._cache[clave]

    @staticmethod
    def _consultar(texto: str) -> tuple[float, float] | None:
        try:
            import httpx
            r = httpx.get("https://nominatim.openstreetmap.org/search", timeout=4,
                          params={"q": texto, "format": "json", "limit": 1, "countrycodes": "gt"},
                          headers={"User-Agent": "DENTAL-TRACK/1.0 (sistema de laboratorio dental)"})
            datos = r.json() if r.status_code == 200 else []
            return (float(datos[0]["lat"]), float(datos[0]["lon"])) if datos else None
        except Exception as error:  # sin internet o servicio caído: se usa el departamento
            log.warning("No se pudo ubicar %s: %s", texto, error)
            return None
