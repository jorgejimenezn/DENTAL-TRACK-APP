"""Feriados oficiales de Guatemala (Código de Trabajo, art. 127) para precargar el calendario."""
from datetime import date, timedelta


def domingo_de_pascua(anio: int) -> date:
    """Algoritmo anónimo gregoriano (Meeus/Jones/Butcher)."""
    a, b, c = anio % 19, anio // 100, anio % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(anio, mes, dia)


def feriados_guatemala(anio: int) -> list[tuple[date, str]]:
    pascua = domingo_de_pascua(anio)
    return sorted([
        (date(anio, 1, 1), "Año Nuevo"),
        (pascua - timedelta(days=3), "Jueves Santo"),
        (pascua - timedelta(days=2), "Viernes Santo"),
        (pascua - timedelta(days=1), "Sábado Santo"),
        (date(anio, 5, 1), "Día del Trabajo"),
        (date(anio, 6, 30), "Día del Ejército"),
        (date(anio, 8, 15), "Día de la Asunción (Ciudad de Guatemala)"),
        (date(anio, 9, 15), "Día de la Independencia"),
        (date(anio, 10, 20), "Día de la Revolución"),
        (date(anio, 11, 1), "Día de Todos los Santos"),
        (date(anio, 12, 24), "Nochebuena (medio día)"),
        (date(anio, 12, 25), "Navidad"),
        (date(anio, 12, 31), "Fin de año (medio día)"),
    ])
