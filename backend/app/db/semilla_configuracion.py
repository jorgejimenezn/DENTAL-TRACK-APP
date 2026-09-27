"""Datos iniciales de configuración. Cada bloque solo se carga si su tabla está vacía,
así el administrador puede modificarlos después sin que se sobrescriban."""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.feriados import feriados_guatemala
from app.modelos import Area
from app.modelos.configuracion import (Color, ColorCaja, DiaNoLaborable, Flujo, FlujoPaso, GuiaColor, Material, MotivoRP,
                                       Parametro, TipoTrabajo, Unidad)

PARAMETROS_INICIALES = {
    "corte_semana": "18:00",   # después de esta hora (lun-vie) cuenta desde el siguiente día hábil
    "corte_sabado": "12:00",   # después de esta hora (sábado) cuenta desde el siguiente día hábil
    "min_digital": "2",        # días hábiles mínimos para trabajos digitales
    "min_analogo": "3",        # días hábiles mínimos para trabajos analógicos
    "min_emergencia": "1",     # días hábiles mínimos para emergencias
}

VITA_CLASSIC = ["A1", "A2", "A3", "A3.5", "A4", "B1", "B2", "B3", "B4", "C1", "C2", "C3", "C4", "D2", "D3", "D4"]
VITA_3D = ["0M1", "0M2", "0M3", "1M1", "1M2", "2L1.5", "2L2.5", "2M1", "2M2", "2M3", "2R1.5", "2R2.5",
           "3L1.5", "3L2.5", "3M1", "3M2", "3M3", "3R1.5", "3R2.5", "4L1.5", "4L2.5", "4M1", "4M2", "4M3",
           "4R1.5", "4R2.5", "5M1", "5M2", "5M3"]

# tipo: materiales permitidos
TIPOS = {
    "Corona": ["Zirconio", "Disilicato de litio", "Metal-porcelana"],
    "Puente": ["Zirconio", "Metal-porcelana"],
    "Carilla": ["Disilicato de litio", "Resina"],
    "Incrustación": ["Disilicato de litio", "Resina"],
    "Prótesis total": ["Acrílico"],
    "Modelo completo": ["Resina de impresión"],
}
# material: (unidades, guías)
MATERIALES = {
    "Zirconio": (["Pieza individual", "Pieza en puente"], ["VITA Classic", "VITA 3D-Master"]),
    "Disilicato de litio": (["Pieza individual"], ["VITA Classic", "VITA 3D-Master"]),
    "Metal-porcelana": (["Pieza individual", "Pieza en puente"], ["VITA Classic", "VITA 3D-Master"]),
    "Resina": (["Pieza individual"], ["VITA Classic"]),
    "Acrílico": (["Arcada superior", "Arcada inferior", "Ambas arcadas"], ["VITA Classic"]),
    "Resina de impresión": (["Arcada superior", "Arcada inferior", "Ambas arcadas"], []),
}
UNIDADES = ["Pieza individual", "Pieza en puente", "Arcada superior", "Arcada inferior", "Ambas arcadas"]
COLORES_CAJA = ["Azul", "Celeste", "Verde", "Naranja", "Roja"]
MOTIVOS_RP = ["Fractura", "Desadaptación marginal", "Ajuste oclusal", "Contacto proximal",
              "Color no coincide", "Error de diseño del laboratorio", "Cambio solicitado por el doctor",
              "Nueva impresión o escaneo del doctor"]

# Flujos de ejemplo por modalidad (el administrador los ajusta)
_FIJA_DIGITAL = ["Ingresos", "CAD", "CAM_FRES", "Finalización", "QA", "Facturación_Cobros", "Logística"]
_FIJA_ANALOGO = ["Logística", "Ingresos", "Yesos", "CAD", "CAM_FRES", "Finalización", "QA",
                 "Facturación_Cobros", "Logística"]
FLUJOS = {
    "Corona": (_FIJA_DIGITAL, _FIJA_ANALOGO),
    "Puente": (_FIJA_DIGITAL, _FIJA_ANALOGO),
    "Carilla": (_FIJA_DIGITAL, _FIJA_ANALOGO),
    "Incrustación": (_FIJA_DIGITAL, _FIJA_ANALOGO),
    "Prótesis total": (["Ingresos", "Diseño", "CAD", "CAM_IMP", "Finalización", "QA", "Facturación_Cobros", "Logística"],
                       ["Logística", "Ingresos", "Yesos", "Diseño", "Finalización", "QA", "Facturación_Cobros",
                        "Logística"]),
    "Modelo completo": (["Ingresos", "CAD", "CAM_IMP", "QA", "Facturación_Cobros", "Logística"],
                        ["Logística", "Ingresos", "Yesos", "QA", "Facturación_Cobros", "Logística"]),
}


def _vacia(sesion: Session, modelo) -> bool:
    return not sesion.scalar(select(func.count()).select_from(modelo))


def sembrar_configuracion(sesion: Session) -> None:
    if _vacia(sesion, Parametro):
        sesion.add_all(Parametro(clave=k, valor=v) for k, v in PARAMETROS_INICIALES.items())

    if _vacia(sesion, TipoTrabajo) and _vacia(sesion, Material):
        unidades = {n: Unidad(nombre=n) for n in UNIDADES}
        guias = {"VITA Classic": GuiaColor(nombre="VITA Classic", colores=[Color(nombre=c) for c in VITA_CLASSIC]),
                 "VITA 3D-Master": GuiaColor(nombre="VITA 3D-Master", colores=[Color(nombre=c) for c in VITA_3D])}
        materiales = {n: Material(nombre=n, unidades=[unidades[u] for u in us], guias=[guias[g] for g in gs])
                      for n, (us, gs) in MATERIALES.items()}
        tipos = {n: TipoTrabajo(nombre=n, materiales=[materiales[m] for m in ms]) for n, ms in TIPOS.items()}
        sesion.add_all([*unidades.values(), *guias.values(), *materiales.values(), *tipos.values()])
        sesion.flush()

        areas = {a.nombre: a for a in sesion.scalars(select(Area))}
        for tipo, (digital, analogo) in FLUJOS.items():
            for modalidad, pasos in (("digital", digital), ("analogo", analogo)):
                sesion.add(Flujo(tipo_trabajo=tipos[tipo], modalidad=modalidad, pasos=[
                    FlujoPaso(orden=i + 1, area_id=areas[a].id) for i, a in enumerate(pasos) if a in areas]))

    if _vacia(sesion, ColorCaja):
        sesion.add_all(ColorCaja(nombre=n) for n in COLORES_CAJA)

    if _vacia(sesion, MotivoRP):
        sesion.add_all(MotivoRP(nombre=m) for m in MOTIVOS_RP)

    if _vacia(sesion, DiaNoLaborable):
        anio = date.today().year
        for a in (anio, anio + 1):
            sesion.add_all(DiaNoLaborable(fecha=f, motivo=m, hora_corte=h) for f, m, h in feriados_guatemala(a))
