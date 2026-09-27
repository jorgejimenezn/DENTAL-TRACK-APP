"""Horas laborales entre dos momentos, según el calendario del laboratorio.

Jornada: de "inicio_jornada" a la hora de corte (lunes a viernes: corte_semana; sábado: corte_sabado).
Domingos y días sin labores no cuentan; los días con horario especial cierran a su hora_corte.
Así un trabajo que llega a las 5:00 pm no "incumple" la meta durante la noche.
"""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos.configuracion import DiaNoLaborable, Parametro

ZONA = ZoneInfo("America/Guatemala")


def _hora(texto: str) -> time:
    h, m = texto.split(":")
    return time(int(h), int(m))


class Jornada:
    def __init__(self, sesion: Session):
        valores = {p.clave: p.valor for p in sesion.scalars(select(Parametro))}
        self.inicio = _hora(valores.get("inicio_jornada", "08:00"))
        self.corte_semana = _hora(valores.get("corte_semana", "18:00"))
        self.corte_sabado = _hora(valores.get("corte_sabado", "12:00"))
        self.sesion = sesion
        self._especiales: dict[date, time | None] | None = None

    def _dias(self) -> dict[date, time | None]:
        if self._especiales is None:
            self._especiales = {d.fecha: (_hora(d.hora_corte) if d.hora_corte else None)
                                for d in self.sesion.scalars(select(DiaNoLaborable))}
        return self._especiales

    def ventana(self, dia: date) -> tuple[datetime, datetime] | None:
        """Horario laborable de un día, o None si no se trabaja."""
        especiales = self._dias()
        if dia.weekday() == 6 or (dia in especiales and especiales[dia] is None):
            return None
        cierre = self.corte_sabado if dia.weekday() == 5 else self.corte_semana
        if dia in especiales:
            cierre = min(cierre, especiales[dia])
        abre, cierra = datetime.combine(dia, self.inicio, ZONA), datetime.combine(dia, cierre, ZONA)
        return (abre, cierra) if cierra > abre else None

    def horas(self, desde: datetime | None, hasta: datetime | None) -> float:
        if not desde or not hasta or hasta <= desde:
            return 0.0
        desde, hasta = desde.astimezone(ZONA), hasta.astimezone(ZONA)
        total, dia = 0.0, desde.date()
        while dia <= hasta.date():
            v = self.ventana(dia)
            if v:
                inicio, fin = max(desde, v[0]), min(hasta, v[1])
                if fin > inicio:
                    total += (fin - inicio).total_seconds()
            dia += timedelta(days=1)
        return round(total / 3600, 2)
