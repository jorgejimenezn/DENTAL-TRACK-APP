"""Orden de trabajo en PDF (CN y RP) con reportlab.

Se imprime después de que Ingresos aprueba el caso (ya tiene caja asignada) y acompaña
al trabajo físico dentro del laboratorio: por eso lleva código de barras, la caja en grande,
el odontograma y una tabla del recorrido con espacio para firma en cada paso.
"""
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

from reportlab.graphics.barcode import code128
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ZONA = ZoneInfo("America/Guatemala")
LOGO = Path(__file__).resolve().parent.parent / "recursos" / "logo.png"

NEGRO, GRIS, GRIS_CLARO, LINEA = colors.HexColor("#111111"), colors.HexColor("#6b6b6b"), colors.HexColor("#f1f1f1"), colors.HexColor("#d4d4d4")
AZUL, ROJO, VERDE = colors.HexColor("#1f6feb"), colors.HexColor("#cf222e"), colors.HexColor("#1a7f37")
COLORES_CAJA = {"azul": "#1f6feb", "celeste": "#5bc0eb", "verde": "#1a7f37", "naranja": "#f28c28",
                "roja": "#cf222e", "rojo": "#cf222e", "amarilla": "#e3b505", "amarillo": "#e3b505",
                "morada": "#7e57c2", "morado": "#7e57c2", "negra": "#111111", "negro": "#111111",
                "blanca": "#ffffff", "blanco": "#ffffff", "gris": "#8a8a8a", "rosada": "#e75480"}
CLASIFICACIONES = {"garantia_total": "Garantía total", "garantia_parcial_sin_cobro": "Garantía parcial sin cobro",
                   "garantia_parcial_con_cobro": "Garantía parcial con cobro", "cobro": "Cobro"}
ETAPAS = {"recolecta": "Recolecta", "ingresos": "Ingresos", "validacion_rp": "Validación RP", "produccion": "Producción",
          "qa": "Control de calidad", "facturacion": "Facturación", "entrega": "Entrega"}

E = {
    "marca": ParagraphStyle("marca", fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=NEGRO),
    "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=8.5, leading=11, textColor=GRIS),
    "codigo": ParagraphStyle("codigo", fontName="Courier-Bold", fontSize=20, leading=22, alignment=TA_RIGHT),
    "der": ParagraphStyle("der", fontName="Helvetica", fontSize=8, leading=10, alignment=TA_RIGHT, textColor=GRIS),
    "seccion": ParagraphStyle("seccion", fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=GRIS,
                              spaceBefore=8, spaceAfter=4),
    "etq": ParagraphStyle("etq", fontName="Helvetica", fontSize=7, leading=9, textColor=GRIS),
    "val": ParagraphStyle("val", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=NEGRO),
    "texto": ParagraphStyle("texto", fontName="Helvetica", fontSize=9, leading=12, textColor=NEGRO),
    "chico": ParagraphStyle("chico", fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=NEGRO),
    "grande": ParagraphStyle("grande", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=NEGRO),
}


def _esc(texto) -> str:
    return (str(texto if texto is not None else "—").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _dato(etiqueta: str, valor, fdc: bool = False) -> list:
    extra = ' <font color="#1f6feb" size="7">(fuera de catálogo)</font>' if fdc else ""
    return [Paragraph(etiqueta.upper(), E["etq"]), Paragraph(_esc(valor) + extra, E["val"])]


def _fecha(d) -> str:
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    return f"{dias[d.weekday()]} {d.day} {meses[d.month - 1]} {d.year}"


def _fecha_hora(dt) -> str:
    return dt.astimezone(ZONA).strftime("%d/%m/%Y %H:%M") if dt else ""


def _nombre(u) -> str:
    return f"{u.nombre} {u.apellido}".strip() if u else ""


def _rejilla(filas: list[list], anchos: list[float]) -> Table:
    """Tabla de datos etiqueta/valor sin bordes, en columnas."""
    t = Table(filas, colWidths=anchos)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


def _celda(etiqueta: str, valor) -> list:
    return [Paragraph(etiqueta.upper(), E["etq"]), Paragraph(_esc(valor), E["val"])]


def _odontograma(piezas: list[int], ancho: float) -> Table:
    sup = [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28]
    inf = [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38]
    t = Table([[str(n) for n in sup], [str(n) for n in inf]], colWidths=[ancho / 16] * 16, rowHeights=[7 * mm] * 2)
    estilo = [("FONT", (0, 0), (-1, -1), "Helvetica-Bold", 8), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
              ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.5, LINEA),
              ("TEXTCOLOR", (0, 0), (-1, -1), GRIS), ("LINEAFTER", (7, 0), (7, 1), 1.6, NEGRO),
              ("LINEBELOW", (0, 0), (-1, 0), 1.2, NEGRO)]
    for fila, lista in enumerate((sup, inf)):
        for col, n in enumerate(lista):
            if n in piezas:
                estilo += [("BACKGROUND", (col, fila), (col, fila), NEGRO), ("TEXTCOLOR", (col, fila), (col, fila), colors.white)]
    t.setStyle(TableStyle(estilo))
    return t


def generar_orden(s, generado_por: str) -> bytes:
    """Devuelve el PDF de la orden de la solicitud `s` (modelo Solicitud con relaciones cargadas)."""
    buffer = BytesIO()
    ahora = datetime.now(ZONA)
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm,
                            bottomMargin=16 * mm, title=f"Orden {s.codigo}", author="DENTAL TRACK")
    ancho = letter[0] - 28 * mm
    h = []

    # ---------- Encabezado: logo + marca | código ----------
    logo = Image(str(LOGO), width=15 * mm, height=21.4 * mm) if LOGO.exists() else Spacer(15 * mm, 21 * mm)
    tipo = "REAPERTURA (RP)" if s.tipo_caso == "RP" else "CASO NUEVO (CN)"
    barras = code128.Code128(s.codigo, barHeight=9 * mm, barWidth=0.9)
    derecha = Table([[Paragraph(f'<font color="{"#1f6feb" if s.tipo_caso == "RP" else "#111111"}"><b>{tipo}</b></font>', E["der"])],
                     [Paragraph(_esc(s.codigo), E["codigo"])], [barras]], colWidths=[62 * mm])
    derecha.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "RIGHT"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    marca = [Paragraph("DENTAL TRACK", E["marca"]), Paragraph("Orden de trabajo · Laboratorio dental", E["sub"]),
             Paragraph(f"Registrada {_fecha_hora(s.creado_en)}" + (f" · Ingresada {_fecha_hora(s.ingresado_en)}"
                                                                     if s.ingresado_en else ""), E["sub"])]
    cab = Table([[logo, marca, derecha]], colWidths=[19 * mm, ancho - 19 * mm - 62 * mm, 62 * mm])
    cab.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("LINEBELOW", (0, 0), (-1, 0), 1.5, NEGRO), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    h += [cab, Spacer(0, 4 * mm)]

    # ---------- Franja: caja, entrega, prioridad, modalidad ----------
    color_caja = colors.HexColor(COLORES_CAJA.get((s.caja_color or "").lower(), "#8a8a8a"))
    muestra = Table([[""]], colWidths=[9 * mm], rowHeights=[9 * mm])
    muestra.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), color_caja), ("BOX", (0, 0), (0, 0), 0.8, NEGRO)]))
    caja = Table([[muestra, [Paragraph("CAJA", E["etq"]),
                             Paragraph(f"{_esc(s.caja_color)} {_esc(s.caja_numero)}", E["grande"])]]],
                 colWidths=[11 * mm, None])
    caja.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    prioridad = {1: "1 · EMERGENCIA", 2: "2 · VIP", 3: "3 · Normal"}.get(s.prioridad, str(s.prioridad))
    franja = Table([[caja, _celda("Fecha de entrega", _fecha(s.fecha_entrega)),
                     [Paragraph("PRIORIDAD", E["etq"]),
                      Paragraph(f'<font color="{"#cf222e" if s.prioridad == 1 else "#111111"}">{prioridad}</font>', E["val"])],
                     _celda("Modalidad", "Digital (STL)" if s.modalidad == "digital" else "Analógico")]],
                   colWidths=[ancho * 0.30, ancho * 0.28, ancho * 0.21, ancho * 0.21])
    franja.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GRIS_CLARO), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 7),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                                ("LINEBEFORE", (0, 0), (0, 0), 4, ROJO if s.emergencia else color_caja)]))
    h.append(franja)

    # ---------- Reapertura ----------
    if s.tipo_caso == "RP":
        origen = s.caso_origen.codigo if s.caso_origen else "—"
        qa = CLASIFICACIONES.get(s.qa_clasificacion, "Pendiente")
        motivo_qa = s.qa_motivo.nombre if getattr(s, "qa_motivo", None) else ""
        h += [Paragraph("REAPERTURA", E["seccion"]),
              _rejilla([[_dato("Caso original", origen),
                         _dato("Solicitada como", "Garantía" if s.reapertura_tipo == "garantia" else "Modificación"),
                         _dato("Clasificación de QA", qa),
                         _dato("Motivo QA", motivo_qa or "—")]], [ancho / 4] * 4),
              Paragraph(f"<b>Motivo del doctor:</b> {_esc(s.reapertura_motivo)}"
                        + (f"<br/><b>Observación QA:</b> {_esc(s.qa_observacion)}" if s.qa_observacion else ""),
                        E["texto"])]

    # ---------- Cliente y paciente ----------
    cli = s.cliente
    telefono = cli.telefono_celular or cli.telefono_fijo
    h += [Paragraph("CLIENTE Y PACIENTE", E["seccion"]),
          _rejilla([[_dato("Cliente", cli.razon_social), _dato("Clínica", cli.clinica or "—"),
                     _dato("Teléfono", telefono or "—")],
                    [_dato("Paciente", s.paciente), _dato("Doctor tratante", s.doctor_tratante or "Titular de la cuenta"),
                     _dato("Referencia de la clínica", s.referencia_clinica or "—")]], [ancho / 3] * 3)]

    # ---------- Trabajo ----------
    color_txt = f"{s.guia} · {s.color}" if s.color else "No aplica"
    color_fdc = bool(s.color) and (s.guia_id is None or s.color_id is None)
    h += [Paragraph("TRABAJO", E["seccion"]),
          _rejilla([[_dato("Tipo de trabajo", s.tipo_trabajo, s.tipo_trabajo_id is None),
                     _dato("Material", s.material, s.material_id is None),
                     _dato("Unidades", s.unidad, s.unidad_id is None),
                     _dato("Guía y color", color_txt, color_fdc)]], [ancho / 4] * 4),
          Spacer(0, 1 * mm),
          Paragraph(f"PIEZAS (FDI) · {len(s.piezas or [])} seleccionada(s): {', '.join(map(str, s.piezas or []))}", E["etq"]),
          Spacer(0, 1.5 * mm), _odontograma(s.piezas or [], ancho)]
    if s.instrucciones:
        caja_inst = Table([[Paragraph(_esc(s.instrucciones).replace("\n", "<br/>"), E["texto"])]], colWidths=[ancho])
        caja_inst.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, LINEA), ("LEFTPADDING", (0, 0), (-1, -1), 6),
                                       ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        h += [Paragraph("INSTRUCCIONES", E["seccion"]), caja_inst]

    # ---------- Direcciones ----------
    entrega = f"{s.entrega_direccion}, {s.entrega_municipio}, {s.entrega_departamento}"
    fila = [_dato("Dirección de entrega", entrega)]
    if s.recolecta_direccion:
        fila.append(_dato("Dirección de recolecta",
                          f"{s.recolecta_direccion}, {s.recolecta_municipio}, {s.recolecta_departamento}"))
    h += [Paragraph("ENTREGA", E["seccion"]), _rejilla([fila], [ancho / len(fila)] * len(fila))]

    # ---------- Recorrido con firma ----------
    filas = [["#", "Área", "Etapa", "Responsable", "Fecha", "Firma / Vo. Bo."]]
    pasos = [p for p in sorted(s.pasos, key=lambda x: x.orden) if p.estado != "omitido"]
    for i, p in enumerate(pasos, start=1):
        responsable = _nombre(p.atendido_por) or _nombre(p.tecnico)
        etapa = ETAPAS.get(p.etapa, p.etapa) + (" (retrabajo)" if p.vuelta > 1 else "")
        filas.append([str(i), Paragraph(_esc(p.area.nombre), E["chico"]), Paragraph(etapa, E["chico"]),
                      Paragraph(_esc(responsable) if responsable else "", E["chico"]),
                      _fecha_hora(p.terminado_en) if p.estado == "terminado" else "", ""])
    rec = Table(filas, colWidths=[8 * mm, 34 * mm, 32 * mm, ancho - 8 * mm - 34 * mm - 32 * mm - 28 * mm - 36 * mm,
                                  28 * mm, 36 * mm], repeatRows=1)
    rec.setStyle(TableStyle([("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.5), ("FONT", (0, 1), (-1, -1), "Helvetica", 7.5),
                             ("BACKGROUND", (0, 0), (-1, 0), NEGRO), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                             ("GRID", (0, 0), (-1, -1), 0.4, LINEA), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                             ("TOPPADDING", (0, 1), (-1, -1), 5), ("BOTTOMPADDING", (0, 1), (-1, -1), 5)]))
    h += [KeepTogether([Paragraph("RECORRIDO", E["seccion"]), rec])]

    # ---------- Archivos ----------
    if s.archivos:
        h += [Paragraph("ARCHIVOS ADJUNTOS (en el sistema)", E["seccion"]),
              Paragraph(" · ".join(_esc(a.nombre) for a in s.archivos), E["chico"])]

    def pie(canvas, documento):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GRIS)
        canvas.drawString(14 * mm, 9 * mm, f"DENTAL TRACK · {s.codigo} · Generado {ahora.strftime('%d/%m/%Y %H:%M')} por {generado_por}")
        canvas.drawRightString(letter[0] - 14 * mm, 9 * mm, f"Página {documento.page}")
        canvas.restoreState()

    doc.build(h, onFirstPage=pie, onLaterPages=pie)
    return buffer.getvalue()
