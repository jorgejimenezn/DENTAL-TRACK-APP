"""Validaciones de formato propias de Guatemala: NIT, DPI (CUI) y teléfonos."""
import re

DEPARTAMENTOS = [
    "Guatemala", "El Progreso", "Sacatepéquez", "Chimaltenango", "Escuintla", "Santa Rosa",
    "Sololá", "Totonicapán", "Quetzaltenango", "Suchitepéquez", "Retalhuleu", "San Marcos",
    "Huehuetenango", "Quiché", "Baja Verapaz", "Alta Verapaz", "Petén", "Izabal", "Zacapa",
    "Chiquimula", "Jalapa", "Jutiapa",
]


def limpiar_numero(valor: str) -> str:
    return re.sub(r"[\s\-]", "", valor or "").upper()


def nit_valido(nit: str) -> bool:
    """NIT: cuerpo numérico + dígito verificador (0-9 o K), algoritmo módulo 11."""
    nit = limpiar_numero(nit)
    if len(nit) < 2:
        return False
    cuerpo, verificador = nit[:-1], nit[-1]
    if not cuerpo.isdigit() or not (verificador.isdigit() or verificador == "K"):
        return False
    total = sum(int(d) * (i + 2) for i, d in enumerate(reversed(cuerpo)))
    calculado = (11 - total % 11) % 11
    esperado = "K" if calculado == 10 else str(calculado)
    return verificador == esperado


def dpi_valido(dpi: str) -> bool:
    """DPI (CUI): 13 dígitos = 8 correlativo + 1 verificador + 2 departamento + 2 municipio."""
    dpi = limpiar_numero(dpi)
    if not re.fullmatch(r"\d{13}", dpi):
        return False
    correlativo, verificador = dpi[:8], int(dpi[8])
    depto, muni = int(dpi[9:11]), int(dpi[11:13])
    if not 1 <= depto <= 22 or muni < 1:
        return False
    total = sum(int(d) * (i + 2) for i, d in enumerate(correlativo))
    return total % 11 == verificador


def telefono_valido(telefono: str) -> bool:
    """Teléfono de Guatemala: 8 dígitos."""
    return bool(re.fullmatch(r"\d{8}", limpiar_numero(telefono)))
