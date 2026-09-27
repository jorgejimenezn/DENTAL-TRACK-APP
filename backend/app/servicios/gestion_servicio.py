"""Gestión de la operación: áreas y metas, ausencias, cobros y métricas (dashboards)."""
from datetime import date, datetime, time, timedelta
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.dependencias import Actor
from app.core.errores import ErrorNegocio, NoEncontrado
from app.core.jornada import ZONA
from app.modelos import ROL_CLIENTE, Area, Ausencia, Usuario
from app.modelos.configuracion import MotivoRP
from app.modelos.solicitud import (ESTADOS_CERRADOS, PASO_EN_COLA, PASO_EN_PROCESO, PASO_SIN_TECNICO, PASOS_ACTIVOS,
                                   PASOS_CARGA, Solicitud, SolicitudHistorial, SolicitudPaso, TiempoPaso)
from app.servicios.auditoria_servicio import AuditoriaServicio
from app.servicios.recorrido import Motor, tipo_area

SUPERVISION = {"admin", "supervisor"}
LECTURA_METRICAS = {"admin", "supervisor", "operaciones"}
COBROS = {"admin", "supervisor", "facturacion", "operaciones"}
RANGOS = [("hoy", "Hoy", 0, 0), ("1-5", "1 a 5 días", 1, 5), ("6-10", "6 a 10 días", 6, 10),
          ("11-15", "11 a 15 días", 11, 15), ("15+", "Más de 15 días", 16, 10_000)]
CLASIFICACIONES = {"garantia_total": "Garantía total", "garantia_parcial_sin_cobro": "Garantía parcial sin cobro",
                   "garantia_parcial_con_cobro": "Garantía parcial con cobro", "cobro": "Cobro", None: "Pendiente de QA"}


def _nombre(u) -> str:
    return f"{u.nombre} {u.apellido}".strip() if u else ""


def _hoy() -> date:
    return datetime.now(ZONA).date()


def _inicio(d: date) -> datetime:
    return datetime.combine(d, time.min, ZONA)


class GestionServicio:
    def __init__(self, sesion: Session, auditoria: AuditoriaServicio):
        self.sesion = sesion
        self.auditoria = auditoria

    def _exigir(self, actor: Actor, roles: set[str]) -> None:
        if actor.rol not in roles:
            raise ErrorNegocio("No tienes permiso para esta acción", 403)

    # ================= Áreas y metas =================
    def areas(self) -> list[dict]:
        return [{"id": a.id, "nombre": a.nombre, "activo": a.activo, "tipo": tipo_area(a.nombre), "lote": a.lote,
                 "max_simultaneos": a.max_simultaneos, "meta_horas": a.meta_horas}
                for a in self.sesion.scalars(select(Area).order_by(Area.id))]

    def guardar_area(self, area_id: int, lote: bool, max_simultaneos: int, meta_horas: float, actor: Actor) -> dict:
        self._exigir(actor, {"admin"})
        area = self.sesion.get(Area, area_id)
        if not area:
            raise NoEncontrado("Área no encontrada")
        if lote and tipo_area(area.nombre) != "produccion":
            raise ErrorNegocio("Solo las áreas de producción trabajan por lote")
        antes = {"lote": area.lote, "max_simultaneos": area.max_simultaneos, "meta_horas": area.meta_horas}
        area.lote, area.max_simultaneos, area.meta_horas = lote, (max_simultaneos if lote else 1), meta_horas
        self.sesion.commit()
        despues = {"lote": area.lote, "max_simultaneos": area.max_simultaneos, "meta_horas": area.meta_horas}
        cambios = {k: [antes[k], v] for k, v in despues.items() if antes[k] != v}
        if cambios:
            self.auditoria.registrar("area_operacion", "configuracion", area.id, actor,
                                     {"area": area.nombre, "cambios": cambios})
        return next(a for a in self.areas() if a["id"] == area_id)

    # ================= Ausencias =================
    def _salida_ausencia(self, a: Ausencia) -> dict:
        hoy = _hoy()
        return {"id": a.id, "usuario_id": a.usuario_id, "empleado": _nombre(a.usuario), "rol": a.usuario.rol,
                "desde": a.desde, "hasta": a.hasta, "motivo": a.motivo,
                "vigente": a.desde <= hoy <= a.hasta, "pasada": a.hasta < hoy}

    def ausencias(self, actor: Actor, incluir_pasadas: bool = False) -> list[dict]:
        self._exigir(actor, SUPERVISION | {"operaciones"})
        consulta = select(Ausencia).options(selectinload(Ausencia.usuario)).order_by(Ausencia.desde.desc())
        if not incluir_pasadas:
            consulta = consulta.where(Ausencia.hasta >= _hoy() - timedelta(days=30))
        return [self._salida_ausencia(a) for a in self.sesion.scalars(consulta.limit(300))]

    def registrar_ausencia(self, usuario_id: int, desde: date, hasta: date, motivo: str, actor: Actor) -> dict:
        self._exigir(actor, SUPERVISION)
        usuario = self.sesion.get(Usuario, usuario_id)
        if not usuario or usuario.rol == ROL_CLIENTE:
            raise NoEncontrado("Empleado no encontrado")
        if hasta < desde:
            raise ErrorNegocio("La fecha final no puede ser anterior a la inicial")
        if hasta < _hoy():
            raise ErrorNegocio("La ausencia ya terminó; solo se registran ausencias de hoy en adelante")
        choque = self.sesion.scalar(select(Ausencia.id).where(Ausencia.usuario_id == usuario_id,
                                                              Ausencia.desde <= hasta, Ausencia.hasta >= desde))
        if choque:
            raise ErrorNegocio("Ya hay una ausencia registrada que cruza esas fechas")
        ausencia = Ausencia(usuario_id=usuario_id, desde=desde, hasta=hasta, motivo=" ".join(motivo.split()),
                            creado_por_id=actor.id)
        self.sesion.add(ausencia)
        self.sesion.flush()
        liberados = Motor(self.sesion).repartir_colas()  # si empieza hoy, sus trabajos sin iniciar se reparten
        self.sesion.commit()
        self.auditoria.registrar("ausencia", "empleado", usuario_id, actor, {
            "empleado": _nombre(usuario), "desde": str(desde), "hasta": str(hasta), "motivo": ausencia.motivo})
        return {**self._salida_ausencia(ausencia), "reasignados": liberados}

    def quitar_ausencia(self, ausencia_id: int, actor: Actor) -> None:
        self._exigir(actor, SUPERVISION)
        ausencia = self.sesion.get(Ausencia, ausencia_id)
        if not ausencia:
            raise NoEncontrado("Ausencia no encontrada")
        datos = {"empleado": _nombre(ausencia.usuario), "desde": str(ausencia.desde), "hasta": str(ausencia.hasta)}
        self.sesion.delete(ausencia)
        Motor(self.sesion).repartir_colas()
        self.sesion.commit()
        self.auditoria.registrar("quitar_ausencia", "empleado", ausencia.usuario_id, actor, datos)

    # ================= Cobros =================
    def cobros(self, actor: Actor) -> dict:
        self._exigir(actor, COBROS)
        hoy = _hoy()
        filas = self.sesion.scalars(select(Solicitud).options(selectinload(Solicitud.cliente))
                                    .where(Solicitud.pago_estado == "pendiente")
                                    .order_by(Solicitud.factura_fecha))
        rangos = {clave: [] for clave, *_ in RANGOS}
        for s in filas:
            fecha = (s.factura_fecha or s.creado_en).astimezone(ZONA).date()
            dias = (hoy - fecha).days
            clave = next(c for c, _, a, b in RANGOS if a <= dias <= b)
            rangos[clave].append({
                "id": s.id, "codigo": s.codigo, "tipo_caso": s.tipo_caso, "cliente": s.cliente.razon_social,
                "telefono": s.cliente.telefono_celular or s.cliente.telefono_fijo, "paciente": s.paciente,
                "factura": s.factura_numero, "facturado": fecha, "dias": dias, "estado": s.estado,
                "qa_clasificacion": CLASIFICACIONES.get(s.qa_clasificacion) if s.tipo_caso == "RP" else None})
        pagados = self.sesion.scalars(select(Solicitud).options(selectinload(Solicitud.cliente))
                                      .where(Solicitud.pago_estado == "pagado", Solicitud.pagado_en >= hoy - timedelta(days=30))
                                      .order_by(Solicitud.pagado_en.desc()).limit(200))
        return {"rangos": [{"clave": c, "titulo": t, "casos": rangos[c]} for c, t, *_ in RANGOS],
                "pagados": [{"id": s.id, "codigo": s.codigo, "cliente": s.cliente.razon_social,
                             "factura": s.factura_numero, "pagado_en": s.pagado_en, "referencia": s.pago_referencia}
                            for s in pagados]}

    def pagar(self, solicitud_id: int, fecha: date, referencia: str | None, actor: Actor) -> None:
        self._exigir(actor, {"admin", "supervisor", "facturacion"})
        s = self.sesion.get(Solicitud, solicitud_id)
        if not s or s.pago_estado != "pendiente":
            raise ErrorNegocio("Este caso no tiene un cobro pendiente")
        if fecha > _hoy():
            raise ErrorNegocio("La fecha de pago no puede ser futura")
        s.pago_estado, s.pagado_en, s.pago_referencia, s.pago_por_id = "pagado", fecha, referencia, actor.id
        s.historial.append(SolicitudHistorial(estado=s.estado, usuario_id=actor.id,
                                              nota=f"Factura {s.factura_numero} pagada" + (f" · ref. {referencia}" if referencia else "")))
        self.sesion.commit()
        self.auditoria.registrar("pago", "solicitud", s.id, actor, {"codigo": s.codigo, "factura": s.factura_numero,
                                                                     "fecha": str(fecha), "referencia": referencia})

    # ================= Métricas: operación =================
    def _tiempos(self, desde: date, hasta: date, **filtros) -> list[TiempoPaso]:
        consulta = select(TiempoPaso).where(TiempoPaso.terminado_en >= _inicio(desde),
                                            TiempoPaso.terminado_en < _inicio(hasta + timedelta(days=1)))
        for campo, valor in filtros.items():
            consulta = consulta.where(getattr(TiempoPaso, campo) == valor)
        return list(self.sesion.scalars(consulta))

    @staticmethod
    def _resumen_tiempos(filas: list[TiempoPaso]) -> dict:
        totales = [t.total_horas for t in filas]
        trabajo = [t.trabajo_horas for t in filas if t.trabajo_horas is not None]
        return {"terminados": len(filas),
                "promedio_horas": round(sum(totales) / len(totales), 2) if totales else None,
                "mediana_horas": round(median(totales), 2) if totales else None,
                "promedio_trabajo": round(sum(trabajo) / len(trabajo), 2) if trabajo else None,
                "cumplimiento": round(100 * sum(t.cumplio for t in filas) / len(filas), 1) if filas else None,
                "retrabajos": sum(1 for t in filas if t.vuelta > 1),
                "devueltos": sum(1 for t in filas if t.devuelto)}

    def operacion(self, actor: Actor, desde: date | None, hasta: date | None) -> dict:
        self._exigir(actor, LECTURA_METRICAS)
        hoy = _hoy()
        hasta = hasta or hoy
        desde = desde or hasta - timedelta(days=29)
        motor = Motor(self.sesion)
        if motor.repartir_colas():
            self.sesion.commit()

        # ---------- En vivo ----------
        vigentes = list(self.sesion.scalars(select(Solicitud).where(Solicitud.estado.not_in(ESTADOS_CERRADOS))))
        conteos: dict[int, dict[str, int]] = {}
        for aid, estado, n in self.sesion.execute(
                select(SolicitudPaso.area_id, SolicitudPaso.estado, func.count())
                .where(SolicitudPaso.estado.in_(PASOS_ACTIVOS)).group_by(SolicitudPaso.area_id, SolicitudPaso.estado)):
            conteos.setdefault(aid, {})[estado] = n
        areas = list(self.sesion.scalars(select(Area).where(Area.activo.is_(True)).order_by(Area.id)))
        ausentes_ids = motor.ausentes_hoy()
        ausentes = [self.sesion.get(Usuario, i) for i in ausentes_ids]
        en_proceso_ausentes = [
            {"codigo": p.solicitud.codigo, "solicitud_id": p.solicitud_id, "area": p.area.nombre, "tecnico": _nombre(p.tecnico)}
            for p in self.sesion.scalars(select(SolicitudPaso).where(SolicitudPaso.estado == PASO_EN_PROCESO,
                                                                     SolicitudPaso.tecnico_id.in_(ausentes_ids or [0])))]
        devoluciones_hoy = self.sesion.scalar(select(func.count()).select_from(SolicitudHistorial).where(
            SolicitudHistorial.fecha >= _inicio(hoy), SolicitudHistorial.nota.like("QA devolvió%"))) or 0
        vivo = {
            "vigentes": len(vigentes),
            "vencidos": sum(1 for s in vigentes if s.fecha_entrega < hoy),
            "vencen_hoy": sum(1 for s in vigentes if s.fecha_entrega == hoy),
            "vencen_manana": sum(1 for s in vigentes if s.fecha_entrega == hoy + timedelta(days=1)),
            "emergencias": sum(1 for s in vigentes if s.prioridad == 1),
            "en_cola": sum(c.get(PASO_EN_COLA, 0) for c in conteos.values()),
            "sin_tecnico": sum(c.get(PASO_SIN_TECNICO, 0) for c in conteos.values()),
            "devoluciones_hoy": devoluciones_hoy,
            "areas": [{"area_id": a.id, "area": a.nombre, "tipo": tipo_area(a.nombre),
                       "activos": sum(conteos.get(a.id, {}).values()),
                       "en_proceso": conteos.get(a.id, {}).get(PASO_EN_PROCESO, 0),
                       "en_cola": conteos.get(a.id, {}).get(PASO_EN_COLA, 0),
                       "sin_tecnico": conteos.get(a.id, {}).get(PASO_SIN_TECNICO, 0)} for a in areas],
            "vencidos_lista": [{"id": s.id, "codigo": s.codigo, "paciente": s.paciente, "fecha_entrega": s.fecha_entrega,
                                "estado": s.estado, "prioridad": s.prioridad}
                               for s in sorted(vigentes, key=lambda s: (s.fecha_entrega, s.prioridad))
                               if s.fecha_entrega <= hoy][:30],
            "ausentes": [{"id": u.id, "nombre": _nombre(u), "rol": u.rol} for u in ausentes if u],
            "en_proceso_ausentes": en_proceso_ausentes,
        }

        # ---------- Desempeño del periodo ----------
        tiempos = self._tiempos(desde, hasta)
        por_area = []
        for a in areas:
            filas = [t for t in tiempos if t.area_id == a.id]
            por_area.append({"area_id": a.id, "area": a.nombre, "tipo": tipo_area(a.nombre), "meta_horas": a.meta_horas,
                             **self._resumen_tiempos(filas)})
        rango = (_inicio(desde), _inicio(hasta + timedelta(days=1)))
        entregados = list(self.sesion.execute(
            select(Solicitud, func.max(SolicitudHistorial.fecha)).join(SolicitudHistorial)
            .where(SolicitudHistorial.estado == "entregada", SolicitudHistorial.fecha >= rango[0],
                   SolicitudHistorial.fecha < rango[1]).group_by(Solicitud.id)))
        a_tiempo = sum(1 for s, f in entregados if f.astimezone(ZONA).date() <= s.fecha_entrega)
        creados = list(self.sesion.scalars(select(Solicitud).where(Solicitud.creado_en >= rango[0],
                                                                   Solicitud.creado_en < rango[1])))
        por_tipo: dict[str, int] = {}
        for s in creados:
            por_tipo[s.tipo_trabajo] = por_tipo.get(s.tipo_trabajo, 0) + 1
        rps = [s for s in creados if s.tipo_caso == "RP"]
        por_clasificacion: dict[str, int] = {}
        por_motivo: dict[str, int] = {}
        for s in rps:
            c = CLASIFICACIONES.get(s.qa_clasificacion, s.qa_clasificacion)
            por_clasificacion[c] = por_clasificacion.get(c, 0) + 1
            if s.qa_motivo_id:
                m = self.sesion.get(MotivoRP, s.qa_motivo_id).nombre
                por_motivo[m] = por_motivo.get(m, 0) + 1
        fallidas = self.sesion.scalar(select(func.count()).select_from(SolicitudHistorial).where(
            SolicitudHistorial.fecha >= rango[0], SolicitudHistorial.fecha < rango[1],
            SolicitudHistorial.nota.like("% no realizada%"))) or 0
        pagados = list(self.sesion.scalars(select(Solicitud).where(Solicitud.pago_estado == "pagado",
                                                                   Solicitud.pagado_en >= desde, Solicitud.pagado_en <= hasta)))
        dias_cobro = [(s.pagado_en - s.factura_fecha.astimezone(ZONA).date()).days for s in pagados if s.factura_fecha]
        pendientes_cobro = self.sesion.scalar(select(func.count()).select_from(Solicitud)
                                              .where(Solicitud.pago_estado == "pendiente")) or 0
        # por técnico (solo producción)
        tecnicos: dict[int, list[TiempoPaso]] = {}
        for t in tiempos:
            if t.etapa == "produccion" and t.responsable_id:
                tecnicos.setdefault(t.responsable_id, []).append(t)
        por_tecnico = sorted(({"id": uid, "nombre": _nombre(self.sesion.get(Usuario, uid)),
                               "areas": sorted({t.area for t in filas}), **self._resumen_tiempos(filas)}
                              for uid, filas in tecnicos.items()), key=lambda x: -x["terminados"])
        periodo = {
            "desde": desde, "hasta": hasta,
            "por_area": por_area,
            "cumplimiento_general": self._resumen_tiempos([t for t in tiempos if t.etapa == "produccion"])["cumplimiento"],
            "entregados": len(entregados), "a_tiempo": a_tiempo,
            "puntualidad": round(100 * a_tiempo / len(entregados), 1) if entregados else None,
            "creados": len(creados), "cn": len(creados) - len(rps), "rp": len(rps),
            "digital": sum(1 for s in creados if s.modalidad == "digital"),
            "analogo": sum(1 for s in creados if s.modalidad == "analogo"),
            "emergencias": sum(1 for s in creados if s.emergencia),
            "por_tipo": sorted(({"nombre": k, "total": v} for k, v in por_tipo.items()), key=lambda x: -x["total"]),
            "rp_clasificacion": sorted(({"nombre": k, "total": v} for k, v in por_clasificacion.items()), key=lambda x: -x["total"]),
            "rp_motivos": sorted(({"nombre": k, "total": v} for k, v in por_motivo.items()), key=lambda x: -x["total"]),
            "visitas_fallidas": fallidas,
            "cobro_dias_promedio": round(sum(dias_cobro) / len(dias_cobro), 1) if dias_cobro else None,
            "cobros_pendientes": pendientes_cobro,
            "por_tecnico": por_tecnico,
        }
        return {"vivo": vivo, "periodo": periodo}

    # ================= Métricas: personales =================
    def mias(self, actor: Actor) -> dict:
        """Solo los datos propios del empleado, sin comparar con compañeros."""
        if actor.rol == ROL_CLIENTE:
            raise ErrorNegocio("No disponible para clientes", 403)
        hoy = _hoy()
        mes = self._tiempos(hoy - timedelta(days=29), hoy, responsable_id=actor.id)
        semana_inicio = hoy - timedelta(days=hoy.weekday())
        por_area: dict[str, list[TiempoPaso]] = {}
        for t in mes:
            por_area.setdefault(t.area, []).append(t)
        metas = {a.nombre: a.meta_horas for a in self.sesion.scalars(select(Area))}
        serie = []
        for i in range(13, -1, -1):
            d = hoy - timedelta(days=i)
            serie.append({"fecha": d, "terminados": sum(1 for t in mes if t.terminado_en.astimezone(ZONA).date() == d)})
        pendientes = sorted(self.sesion.scalars(select(SolicitudPaso).options(selectinload(SolicitudPaso.solicitud))
                                                .where(SolicitudPaso.tecnico_id == actor.id,
                                                       SolicitudPaso.estado.in_(PASOS_CARGA))),
                            key=lambda p: (p.solicitud.fecha_entrega, p.solicitud.prioridad))
        return {
            "hoy": sum(1 for t in mes if t.terminado_en.astimezone(ZONA).date() == hoy),
            "semana": sum(1 for t in mes if t.terminado_en.astimezone(ZONA).date() >= semana_inicio),
            "mes": len(mes),
            "resumen": self._resumen_tiempos(mes),
            "por_area": [{"area": k, "meta_horas": metas.get(k), **self._resumen_tiempos(v)} for k, v in sorted(por_area.items())],
            "serie": serie,
            "proximos": [{"solicitud_id": p.solicitud_id, "codigo": p.solicitud.codigo, "area": p.area.nombre,
                          "estado": p.estado, "fecha_entrega": p.solicitud.fecha_entrega,
                          "vencido": p.solicitud.fecha_entrega < hoy, "emergencia": p.solicitud.emergencia}
                         for p in pendientes[:15]],
        }
