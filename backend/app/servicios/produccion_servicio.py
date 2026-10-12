"""Bandeja de trabajo y acciones de cada área sobre el paso en que va el caso."""
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.dependencias import Actor
from app.core.errores import Conflicto, ErrorNegocio, NoEncontrado
from app.core.jornada import Jornada
from app.esquemas.bandeja import (CLASIFICACIONES, AreaBandeja, AsignarIn, Bandeja, Candidato, CambiosDisenoIn,
                                  EnvioIn, LoteArea, MetodoIn,
                                  ModificacionIn, PasoBandeja, PasoPrevio, Produccion, RechazoIn, ResumenArea,
                                  TerminarIn, ValidacionRpIn)
from app.modelos import ROL_CLIENTE, Area, Usuario
from app.modelos.configuracion import ColorCaja, DiaNoLaborable, MotivoRP
from app.modelos.solicitud import ESTADOS_CERRADOS
from app.modelos.solicitud import (PASO_ASIGNADO, PASO_EN_AREA, PASO_EN_COLA, PASO_EN_PROCESO, PASO_PENDIENTE,
                                   PASO_ENVIADO, PASO_RECOLECTADO, PASO_SIN_TECNICO, PASOS_ACTIVOS, PASOS_CARGA, Solicitud, SolicitudHistorial,
                                   SolicitudPaso, TiempoPaso)
from app.servicios.auditoria_servicio import AuditoriaServicio
from app.servicios.configuracion_servicio import ZONA
from app.servicios.recorrido import (NOMBRE_ETAPA, PLAZO_RECOLECTA_HORAS, Motor, ahora, estado_etapa,
                                     tipo_area)
from app.servicios.solicitud_servicio import SolicitudServicio, _fecha_texto

SUPERVISION = {"admin", "supervisor"}
DEMO = "demo"  # perfil de demostración: opera todos los pasos de la línea, no administra
ACCIONES_AREA = {
    "ingresos": ["aprobar", "modificar", "cancelar"],
    "validacion_rp": ["validar_rp"],
    "qa": ["aprobar_qa", "rechazar"],
    "facturacion": ["facturar"],
    "validacion_diseno": ["enviar_cliente", "aprobar_diseno", "cambios_diseno"],
}
RUTAS = ("recolecta", "entrega")
ESTADOS_RUTA = [PASO_EN_AREA, PASO_ASIGNADO, PASO_RECOLECTADO]


def acciones_ruta(p: SolicitudPaso, vista: str) -> list[str]:
    """Acciones de una recolecta o entrega según su método y estado.
    vista: "logistica" (el área), "mensajero" (quien la lleva) o "demo" (ambas)."""
    s = p.solicitud
    metodo = (s.recolecta_metodo if p.etapa == "recolecta" else s.entrega_metodo) or "mensajero"
    logistica: list[str] = []
    mensajero: list[str] = []
    if p.etapa == "recolecta":
        if metodo == "transporte":
            if p.estado == PASO_EN_AREA:
                logistica = ["recibido_transporte", "cambiar_metodo"]
        elif p.estado == PASO_EN_AREA:
            logistica = ["asignar_mensajero", "cambiar_metodo"]
        elif p.estado == PASO_ASIGNADO:
            logistica, mensajero = ["asignar_mensajero", "no_se_pudo"], ["recolectado", "no_se_pudo"]
        elif p.estado == PASO_RECOLECTADO:
            logistica, mensajero = ["entregado_lab"], ["entregado_lab"]
    else:
        final = "entregado_transporte" if metodo == "transporte" else "entregado"
        if p.estado == PASO_EN_AREA:
            logistica = (["entregado_transporte"] if metodo == "transporte" else []) + ["asignar_mensajero", "cambiar_metodo"]
        elif p.estado == PASO_ASIGNADO:
            logistica, mensajero = ["asignar_mensajero", "no_se_pudo"], [final, "no_se_pudo"]
    if vista == "mensajero":
        return mensajero
    if vista == "demo":
        return list(dict.fromkeys(mensajero + logistica))
    return logistica
ESTADOS_REASIGNABLES = {PASO_ASIGNADO, PASO_EN_COLA, PASO_SIN_TECNICO, PASO_EN_PROCESO}
NOTA_TERMINAR = {
    "recolecta": "Material recolectado", "qa": "Aprobado por control de calidad",
    "entrega": "Entregado al cliente", "facturacion": "Facturado y empacado",
    "validacion_diseno": "Diseño aprobado por el cliente",
}


def _nombre(u: Usuario | None) -> str | None:
    return f"{u.nombre} {u.apellido}".strip() if u else None


class ProduccionServicio:
    def __init__(self, sesion: Session, auditoria: AuditoriaServicio):
        self.sesion = sesion
        self.auditoria = auditoria
        self.motor = Motor(sesion)

    # ================= Utilidades =================
    def _paso(self, paso_id: int) -> SolicitudPaso:
        paso = self.sesion.get(SolicitudPaso, paso_id)
        if not paso:
            raise NoEncontrado("Paso no encontrado")
        return paso

    def _areas(self, actor: Actor) -> list[Area]:
        if actor.rol == DEMO:  # la demostración trabaja en todas las áreas
            return list(self.sesion.scalars(select(Area).where(Area.activo.is_(True)).order_by(Area.id)))
        usuario = self.sesion.get(Usuario, actor.id) if actor.id else None
        return [a for a in (usuario.areas if usuario else []) if a.activo]

    def _vigente(self, paso: SolicitudPaso, etapas: set[str] | None = None) -> Solicitud:
        """El paso debe ser el actual del caso (evita que dos personas lo atiendan a la vez)."""
        s = paso.solicitud
        if paso.estado not in PASOS_ACTIVOS or paso not in self.motor.pasos_activos(s):
            raise Conflicto(f"{s.codigo} ya no está en este paso. Actualiza tu bandeja")
        if s.pausada:
            raise Conflicto(f"{s.codigo} está en pausa: {s.pausa_motivo or 'sin motivo'}")
        if etapas and paso.etapa not in etapas:
            raise ErrorNegocio(f"Esta acción no corresponde a la etapa de {NOMBRE_ETAPA[paso.etapa]}")
        return s

    def _permiso_area(self, paso: SolicitudPaso, actor: Actor) -> None:
        if actor.rol in SUPERVISION or actor.rol == DEMO:
            return
        if paso.area_id not in {a.id for a in self._areas(actor)}:
            raise ErrorNegocio(f"No perteneces al área {paso.area.nombre}", 403)

    def _plazo(self, p: SolicitudPaso) -> tuple[datetime | None, bool]:
        """Recolecta con mensajero: límite de 2 horas laborales desde que se solicitó."""
        if p.etapa != "recolecta" or p.solicitud.recolecta_metodo == "transporte" or not p.activado_en:
            return None, False
        if not hasattr(self, "_jornada"):
            self._jornada = Jornada(self.sesion)
        # si el caso estuvo en pausa, el plazo se corre esas horas
        limite = self._jornada.sumar(p.activado_en, PLAZO_RECOLECTA_HORAS + float(p.pausa_espera or 0))
        return limite, (p.recolectado_en or ahora()) > limite

    def _salida(self, p: SolicitudPaso, acciones: list[str]) -> PasoBandeja:
        s = p.solicitud
        if s.pausada:
            acciones = []  # un caso en pausa no se trabaja hasta que el supervisor lo reanude
        limite, vencida = self._plazo(p)
        es_ruta = p.etapa in RUTAS
        previos = []
        if p.etapa in ("qa", "validacion_diseno"):  # opciones para devolver el caso
            ultimos: dict[int, SolicitudPaso] = {}
            primero: dict[int, int] = {}
            for x in sorted(s.pasos, key=lambda y: y.orden):
                if x.etapa == "produccion" and x.estado == "terminado" and x.orden < p.orden:
                    ultimos[x.area_id] = x
                    primero.setdefault(x.area_id, x.orden)
            previos = [PasoPrevio(id=x.id, orden=x.orden, area=x.area.nombre)
                       for x in sorted(ultimos.values(), key=lambda y: primero[y.area_id])]
        return PasoBandeja(
            paso_id=p.id, solicitud_id=s.id, codigo=s.codigo, tipo_caso=s.tipo_caso, cliente=s.cliente.razon_social,
            paciente=s.paciente, doctor_tratante=s.doctor_tratante,
            trabajo=" · ".join(x for x in (s.tipo_trabajo, s.material, s.unidad) if x),
            color=(f"{s.guia} · {s.color}" + (" · por pieza: " + ", ".join(f"{c['pieza']} {c['color']}" for c in s.colores_pieza)
                                               if s.colores_pieza else "")) if s.color else None, piezas=s.piezas or [], modalidad=s.modalidad,
            emergencia=s.emergencia, prioridad=s.prioridad, fecha_entrega=s.fecha_entrega,
            instrucciones=s.instrucciones, fuera_catalogo=s.fuera_catalogo, manual=bool(s.manual), area_id=p.area_id, area=p.area.nombre,
            etapa=p.etapa, etapa_texto=NOMBRE_ETAPA[p.etapa], estado=p.estado, tecnico=_nombre(p.tecnico),
            activado_en=p.activado_en, asignado_en=p.asignado_en, iniciado_en=p.iniciado_en, vuelta=p.vuelta,
            reapertura_tipo=s.reapertura_tipo, reapertura_motivo=s.reapertura_motivo,
            qa_clasificacion=CLASIFICACIONES.get(s.qa_clasificacion), factura_numero=s.factura_numero,
            direccion=("El cliente lo envía por transporte" if p.etapa == "recolecta" and s.recolecta_metodo == "transporte"
                       else f"{s.recolecta_direccion}, {s.recolecta_municipio}" if p.etapa == "recolecta"
                       and s.recolecta_direccion else f"{s.entrega_direccion}, {s.entrega_municipio}"),
            archivos=len(s.archivos), telefono=s.cliente.telefono_celular or s.cliente.telefono_fijo,
            cliente_odoo=s.cliente.cliente_odoo, credito=s.cliente.credito,
            devolucion=p.nota if p.vuelta > 1 and p.estado != "terminado" else None,
            receptor=p.receptor, caja=f"{s.caja_color} {s.caja_numero}" if s.caja_numero else None,
            metodo=((s.recolecta_metodo if p.etapa == "recolecta" else s.entrega_metodo) or "mensajero") if es_ruta else None,
            limite=limite, vencida=vencida, recolectado_en=p.recolectado_en,
            guia=(s.recolecta_guia if p.etapa == "recolecta" else s.entrega_guia) if es_ruta else None,
            transporte=s.entrega_transporte if p.etapa == "entrega" else None,
            pausada=bool(s.pausada), pausa_motivo=s.pausa_motivo, enviado_en=p.enviado_en,
            paralelo_con=[x.area.nombre for x in s.pasos if x is not p and x.grupo and x.grupo == p.grupo
                          and x.estado != "omitido"],
            acciones=acciones, pasos_previos=previos)

    @staticmethod
    def _orden_prioridad(p: SolicitudPaso):
        return (p.solicitud.prioridad, p.solicitud.fecha_entrega, p.asignado_en or p.activado_en or ahora())

    def _finalizar(self, s: Solicitud, paso: SolicitudPaso, actor: Actor, nota_historial: str, accion: str,
                   detalle: dict | None = None):
        self.motor.avanzar(s, actor.id, nota_historial)
        self.motor.repartir_colas()  # pudo liberarse espacio para alguien en cola
        self.sesion.commit()
        self.auditoria.registrar(accion, "solicitud", s.id, actor, {
            "codigo": s.codigo, "area": paso.area.nombre, "estado": s.estado, **(detalle or {})})

    # ================= Bandeja =================
    def bandeja(self, actor: Actor, area_id: int | None = None) -> Bandeja:
        if self.motor.repartir_colas():
            self.sesion.commit()
        opciones = (selectinload(SolicitudPaso.solicitud).selectinload(Solicitud.cliente),
                    selectinload(SolicitudPaso.solicitud).selectinload(Solicitud.pasos),
                    selectinload(SolicitudPaso.area), selectinload(SolicitudPaso.tecnico))
        areas = self._areas(actor)

        # --- Producción: lo asignado a mí, uno a la vez ---
        mios = sorted(self.sesion.scalars(select(SolicitudPaso).options(*opciones).where(
            SolicitudPaso.tecnico_id == actor.id, SolicitudPaso.etapa == "produccion",
            SolicitudPaso.estado.in_(PASOS_CARGA))), key=self._orden_prioridad)
        produccion = None
        demo = actor.rol == DEMO
        pausados = [p for p in mios if p.solicitud.pausada]
        mios = [p for p in mios if not p.solicitud.pausada]
        if not demo and (mios or pausados or any(tipo_area(a.nombre) == "produccion" for a in areas)):
            normales = [p for p in mios if not p.area.lote]
            actual = next((p for p in normales if p.estado == PASO_EN_PROCESO), None)
            en_espera = [p for p in normales if p.estado == PASO_ASIGNADO]
            siguiente = en_espera[0] if en_espera else None
            # Áreas por lote: todo lo asignado a la vista, varios en proceso hasta el máximo del área
            lotes = []
            for area in sorted({p.area for p in mios if p.area.lote} | {a for a in areas if a.lote},
                               key=lambda a: a.nombre):
                del_area = [p for p in mios if p.area_id == area.id]
                proceso = [p for p in del_area if p.estado == PASO_EN_PROCESO]
                espera = [p for p in del_area if p.estado == PASO_ASIGNADO]
                puede = len(proceso) < area.max_simultaneos
                lotes.append(LoteArea(area_id=area.id, area=area.nombre, max_simultaneos=area.max_simultaneos,
                                      en_proceso=[self._salida(p, ["terminar"]) for p in proceso],
                                      en_espera=[self._salida(p, ["iniciar"] if puede else []) for p in espera]))
            usuario = self.sesion.get(Usuario, actor.id)
            produccion = Produccion(
                actual=self._salida(actual, ["terminar"]) if actual else None,
                siguiente=self._salida(siguiente, [] if actual else ["iniciar"]) if siguiente else None,
                asignados=[], en_espera=max(len(en_espera) - 1, 0), lotes=lotes,
                pausados=[self._salida(p, []) for p in pausados], total=len(mios),
                max_trabajos=usuario.max_trabajos if usuario else None)

        # --- Mensajero: sus recolectas y entregas ---
        rutas = None
        if actor.rol == "mensajero":
            propias = sorted(self.sesion.scalars(select(SolicitudPaso).options(*opciones).where(
                SolicitudPaso.tecnico_id == actor.id, SolicitudPaso.etapa.in_(RUTAS),
                SolicitudPaso.estado.in_([PASO_ASIGNADO, PASO_RECOLECTADO]))), key=self._orden_prioridad)
            rutas = [self._salida(p, acciones_ruta(p, "mensajero")) for p in propias]

        # --- Áreas de apoyo: lo que está en el área, lo atiende cualquiera ---
        supervisa = actor.rol in SUPERVISION

        def acciones_de(p: SolicitudPaso) -> list[str]:
            if p.etapa in RUTAS:
                return acciones_ruta(p, "demo" if demo else "logistica")
            if demo and p.etapa == "produccion":  # la demo hace el trabajo de cualquier técnico
                return ["terminar"] if p.estado == PASO_EN_PROCESO else ["iniciar"]
            if p.etapa == "validacion_diseno":
                return (["enviar_cliente", "aprobar_diseno", "cambios_diseno"] if p.estado == PASO_EN_AREA
                        else ["aprobar_diseno", "cambios_diseno", "enviar_cliente"])
            if p.estado == PASO_EN_AREA:
                return ACCIONES_AREA.get(p.etapa, [])
            if supervisa and p.etapa == "produccion" and p.estado in ESTADOS_REASIGNABLES:
                return ["asignar", "prioridad"]
            return []

        def pasos_de(area: Area, todos: bool) -> list[PasoBandeja]:
            if todos or (demo and tipo_area(area.nombre) == "produccion"):
                estados = PASOS_ACTIVOS
            else:
                estados = ESTADOS_RUTA if tipo_area(area.nombre) == "logistica" else [PASO_EN_AREA]
            consulta = select(SolicitudPaso).options(*opciones).where(SolicitudPaso.area_id == area.id,
                                                                      SolicitudPaso.estado.in_(estados))
            return [self._salida(p, acciones_de(p)) for p in sorted(self.sesion.scalars(consulta),
                                                                   key=self._orden_prioridad)]

        salida_areas = [AreaBandeja(area_id=a.id, area=a.nombre, tipo=tipo_area(a.nombre), pasos=pasos_de(a, False))
                        for a in areas if demo or tipo_area(a.nombre) != "produccion"]
        if demo:  # primero las áreas con trabajo
            salida_areas.sort(key=lambda x: not x.pasos)

        # --- Supervisión: resumen de todas las áreas y detalle de una ---
        supervision = None
        if actor.rol in SUPERVISION or demo:
            conteos: dict[int, dict[str, int]] = {}
            for aid, estado, n in self.sesion.execute(
                    select(SolicitudPaso.area_id, SolicitudPaso.estado, func.count())
                    .where(SolicitudPaso.estado.in_(PASOS_ACTIVOS)).group_by(SolicitudPaso.area_id, SolicitudPaso.estado)):
                conteos.setdefault(aid, {})[estado] = n
            todas = list(self.sesion.scalars(select(Area).where(Area.activo.is_(True)).order_by(Area.id)))
            supervision = [ResumenArea(area_id=a.id, area=a.nombre, tipo=tipo_area(a.nombre),
                                       activos=sum(conteos.get(a.id, {}).values()),
                                       en_proceso=conteos.get(a.id, {}).get(PASO_EN_PROCESO, 0),
                                       en_cola=conteos.get(a.id, {}).get(PASO_EN_COLA, 0),
                                       sin_tecnico=conteos.get(a.id, {}).get(PASO_SIN_TECNICO, 0)) for a in todas]
            elegida = next((a for a in todas if a.id == area_id), None)
            if elegida and not demo:
                salida_areas = [x for x in salida_areas if x.area_id != elegida.id]
                salida_areas.insert(0, AreaBandeja(area_id=elegida.id, area=elegida.nombre,
                                                   tipo=tipo_area(elegida.nombre), pasos=pasos_de(elegida, True)))
        return Bandeja(produccion=produccion, rutas=rutas, areas=salida_areas, supervision=supervision)

    # ================= Producción =================
    def iniciar(self, paso_id: int, actor: Actor) -> None:
        paso = self._paso(paso_id)
        self._vigente(paso, {"produccion"})
        if actor.rol == DEMO:  # demostración: inicia cualquier trabajo, sin reglas de turno
            if paso.estado == PASO_EN_PROCESO:
                raise Conflicto("Este trabajo ya se inició")
            # el trabajo queda a nombre de la demo: no suma ni resta a las métricas de los técnicos
            paso.tecnico_id, paso.asignado_en = actor.id, paso.asignado_en or ahora()
            paso.estado, paso.iniciado_en = PASO_EN_PROCESO, ahora()
            self.sesion.flush()
            self.motor.repartir_colas()  # el técnico que lo tenía queda con espacio
            self.sesion.commit()
            self.auditoria.registrar("iniciar", "solicitud", paso.solicitud_id, actor,
                                     {"codigo": paso.solicitud.codigo, "area": paso.area.nombre, "demo": True})
            return
        if paso.tecnico_id != actor.id:
            raise ErrorNegocio("Este trabajo no está asignado a ti", 403)
        if paso.estado != PASO_ASIGNADO:
            raise Conflicto("Este trabajo ya se inició")
        mios = sorted((p for p in self.sesion.scalars(select(SolicitudPaso).where(
            SolicitudPaso.tecnico_id == actor.id, SolicitudPaso.etapa == "produccion",
            SolicitudPaso.estado.in_(PASOS_CARGA))) if not p.solicitud.pausada), key=self._orden_prioridad)
        if paso.area.lote:
            en_area = sum(1 for p in mios if p.estado == PASO_EN_PROCESO and p.area_id == paso.area_id)
            if en_area >= paso.area.max_simultaneos:
                raise Conflicto(f"Ya tienes {en_area} en proceso en {paso.area.nombre} "
                                f"(máximo {paso.area.max_simultaneos})")
        else:
            normales = [p for p in mios if not p.area.lote]
            if any(p.estado == PASO_EN_PROCESO for p in normales):
                raise Conflicto("Termina el trabajo que tienes en proceso antes de iniciar otro")
            primero = next(p for p in normales if p.estado == PASO_ASIGNADO)
            if primero.id != paso.id:
                raise Conflicto(f"El sistema te entrega primero {primero.solicitud.codigo} por prioridad")
        paso.estado, paso.iniciado_en = PASO_EN_PROCESO, ahora()
        self.sesion.commit()
        self.auditoria.registrar("iniciar", "solicitud", paso.solicitud_id, actor,
                                 {"codigo": paso.solicitud.codigo, "area": paso.area.nombre})

    # ================= Terminar (todas las áreas) =================
    def terminar(self, paso_id: int, datos: TerminarIn, actor: Actor) -> None:
        paso = self._paso(paso_id)
        s = self._vigente(paso)
        if paso.etapa == "validacion_rp":
            raise ErrorNegocio("Esta reapertura se valida con la clasificación de QA")
        if paso.etapa == "produccion":
            if paso.estado != PASO_EN_PROCESO:
                raise Conflicto("Inicia el trabajo antes de terminarlo")
            if paso.tecnico_id != actor.id and actor.rol not in SUPERVISION and actor.rol != DEMO:
                raise ErrorNegocio("Este trabajo no está asignado a ti", 403)
            self.motor.terminar(paso, actor.id, datos.nota)
            nota = f"{paso.area.nombre} terminado" + (f" · {datos.nota}" if datos.nota else "")
            return self._finalizar(s, paso, actor, nota, "terminar_paso")

        es_su_ruta = (paso.etapa in RUTAS and paso.estado in (PASO_ASIGNADO, PASO_RECOLECTADO)
                      and paso.tecnico_id == actor.id)
        if not es_su_ruta:
            self._permiso_area(paso, actor)
        detalle = {}
        if paso.etapa == "recolecta":
            if s.recolecta_metodo == "transporte":
                if paso.estado != PASO_EN_AREA:
                    raise Conflicto("Esta recolecta ya no está pendiente")
                s.recolecta_guia = datos.guia
                nota = "Material recibido por transporte" + (f" · guía {datos.guia}" if datos.guia else "")
            else:
                if paso.estado != PASO_RECOLECTADO:
                    raise ErrorNegocio("Primero marca la recolecta como Recolectado (el mensajero ya tiene el material)")
                nota = "Material entregado en el laboratorio"
        elif paso.etapa == "entrega":
            if s.entrega_metodo == "transporte":
                if not datos.guia:
                    raise ErrorNegocio("Ingresa el número de guía del transporte para finalizar el caso")
                s.entrega_guia, s.entrega_transporte = datos.guia, datos.transporte
                paso.receptor = f"Transporte {datos.transporte or ''}".strip() + f" · guía {datos.guia}"
                detalle.update(guia=datos.guia, transporte=datos.transporte)
                nota = (f"Entregado a transporte {datos.transporte or ''}".rstrip()
                        + f" · guía {datos.guia} · caso finalizado")
            else:
                if paso.estado != PASO_ASIGNADO:
                    raise ErrorNegocio("Asigna un mensajero antes de marcar la entrega")
                if not datos.receptor:
                    raise ErrorNegocio("Escribe el nombre de quien recibe")
                paso.receptor = datos.receptor
                detalle["recibio"] = datos.receptor
                nota = f"Entregado · recibió {datos.receptor}"
        if paso.etapa == "ingresos":
            if not s.tipo_trabajo_id:
                raise ErrorNegocio("El tipo de trabajo está fuera de catálogo: usa Modificar y elige uno del catálogo")
            if not self.motor.flujo(s):
                raise ErrorNegocio(f"{s.tipo_trabajo} no tiene flujo activo en modalidad "
                                   f"{'digital' if s.modalidad == 'digital' else 'analógica'}")
            self._asignar_caja(s, datos, actor)
            self.motor.completar_despues_de_ingresos(s, paso)
            nota = ("Aprobado por Ingresos" + (" · material recibido" if s.modalidad == "analogo" else "")
                    + f" · caja {s.caja_color} {s.caja_numero}")
            detalle["caja"] = f"{s.caja_color} {s.caja_numero}"
        elif paso.etapa == "facturacion":
            if not datos.factura_numero:
                raise ErrorNegocio("Ingresa el número de factura")
            s.factura_numero, s.factura_fecha = datos.factura_numero, ahora()
            sin_cobro = s.tipo_caso == "RP" and s.qa_clasificacion in ("garantia_total", "garantia_parcial_sin_cobro")
            s.pago_estado = "no_aplica" if sin_cobro else ("credito" if s.cliente.credito else "pendiente")
            detalle["factura"] = datos.factura_numero
            nota = f"Factura {datos.factura_numero} · empacado"
        elif paso.etapa in RUTAS:
            pass  # la nota ya se armó arriba
        else:
            nota = NOTA_TERMINAR.get(paso.etapa, f"{paso.area.nombre} terminado")
        if paso.etapa in RUTAS and paso.tecnico:
            nota += f" (mensajero {_nombre(paso.tecnico)})"
        if datos.nota:
            nota += f" · {datos.nota}"
        self.motor.terminar(paso, actor.id, datos.nota)
        self._finalizar(s, paso, actor, nota, "terminar_paso", detalle)

    def _asignar_caja(self, s: Solicitud, datos: TerminarIn, actor: Actor) -> None:
        """Color y número de la caja física. Una caja no puede estar en dos casos abiertos a la vez."""
        if not datos.caja_color_id or not datos.caja_numero:
            raise ErrorNegocio("Indica el color y el número de caja")
        color = self.sesion.get(ColorCaja, datos.caja_color_id)
        if not color or not color.activo:
            raise ErrorNegocio("Color de caja no válido")
        numero = datos.caja_numero.upper()
        if not all(ch.isalnum() or ch in "-_ " for ch in numero):
            raise ErrorNegocio("El número de caja solo puede tener letras, números y guiones")
        ocupada = self.sesion.scalar(select(Solicitud.codigo).where(
            Solicitud.id != s.id, Solicitud.caja_color_id == color.id,
            func.upper(Solicitud.caja_numero) == numero, Solicitud.estado.not_in(ESTADOS_CERRADOS)))
        if ocupada:
            raise Conflicto(f"La caja {color.nombre} {numero} está en uso por {ocupada}")
        s.caja_color_id, s.caja_color, s.caja_numero = color.id, color.nombre, numero
        s.ingresado_en, s.ingresado_por_id = ahora(), actor.id

    # ================= QA =================
    def validar_rp(self, paso_id: int, datos: ValidacionRpIn, actor: Actor) -> None:
        paso = self._paso(paso_id)
        s = self._vigente(paso, {"validacion_rp"})
        self._permiso_area(paso, actor)
        motivo = self.sesion.get(MotivoRP, datos.motivo_id)
        if not motivo or not motivo.activo:
            raise ErrorNegocio("Motivo no válido")
        observacion = " ".join((datos.observacion or "").split()) or None
        if motivo.nombre.lower().startswith("otro") and not observacion:
            raise ErrorNegocio("Con el motivo \"Otro\" describe la observación")
        s.qa_clasificacion, s.qa_motivo_id, s.qa_observacion = datos.clasificacion, motivo.id, observacion
        s.qa_usuario_id, s.qa_fecha = actor.id, ahora()
        texto = f"QA: {CLASIFICACIONES[datos.clasificacion]} · {motivo.nombre}"
        self.motor.terminar(paso, actor.id, texto)
        self._finalizar(s, paso, actor, texto + (f" · {observacion}" if observacion else ""), "validar_rp",
                        {"clasificacion": CLASIFICACIONES[datos.clasificacion], "motivo": motivo.nombre})

    def rechazar(self, paso_id: int, datos: RechazoIn, actor: Actor) -> None:
        """QA devuelve el caso a un paso de producción: se repite desde ahí hasta QA."""
        paso = self._paso(paso_id)
        s = self._vigente(paso, {"qa"})
        self._permiso_area(paso, actor)
        destino = next((p for p in s.pasos if p.id == datos.volver_a_paso_id), None)
        if not destino or destino.etapa != "produccion" or destino.orden > paso.orden or destino.estado != "terminado":
            raise ErrorNegocio("Elige un paso de producción ya realizado en este caso")
        if datos.modo == "solo":  # solo ese paso y de regreso a QA
            repetir = [destino, paso]
        else:  # desde ese paso: ese y los de producción que le siguen en el flujo (su última vuelta) y QA
            ultimos: dict[int, SolicitudPaso] = {}
            primero: dict[int, int] = {}
            for p in sorted(s.pasos, key=lambda x: x.orden):
                if p.orden < paso.orden and p.estado == "terminado" and p.etapa == "produccion":
                    ultimos[p.area_id] = p
                    primero.setdefault(p.area_id, p.orden)
            desde = primero[destino.area_id]
            repetir = sorted((p for aid, p in ultimos.items() if primero[aid] >= desde),
                             key=lambda x: primero[x.area_id]) + [paso]
        despues = [p for p in s.pasos if p.orden > paso.orden and p.estado == PASO_PENDIENTE]
        for p in despues:
            p.orden += len(repetir)
        self.sesion.flush()
        motivo = " ".join(datos.motivo.split())
        self._repetir(s, paso, repetir, f"Devuelto por QA: {motivo}")
        ids_devueltos = [p.id for p in repetir if p is not paso]
        for t in self.sesion.scalars(select(TiempoPaso).where(TiempoPaso.paso_id.in_(ids_devueltos))):
            t.devuelto = True
        self.motor.terminar(paso, actor.id, f"Devuelto a {destino.area.nombre}: {motivo}")
        self.sesion.flush()
        alcance = "solo ese paso" if datos.modo == "solo" else f"{len(repetir) - 1} paso(s) de producción"
        self._finalizar(s, paso, actor, f"QA devolvió el caso a {destino.area.nombre} ({alcance}): {motivo}",
                        "rechazar_qa", {"volver_a": destino.area.nombre, "modo": datos.modo, "motivo": motivo})

    def _repetir(self, s: Solicitud, despues_de: SolicitudPaso, repetir: list[SolicitudPaso], nota: str) -> None:
        """Agrega copias pendientes de `repetir` después de `despues_de`. Los que eran paralelos lo siguen siendo."""
        grupos: dict[int, int] = {}
        siguiente = max((x.grupo or 0) for x in s.pasos) + 1
        for i, p in enumerate(repetir, start=1):
            clave = p.grupo or -p.id
            if clave not in grupos or p.etapa != "produccion":
                grupos[clave] = siguiente
                siguiente += 1
            s.pasos.append(SolicitudPaso(orden=despues_de.orden + i, area_id=p.area_id, area=p.area, etapa=p.etapa,
                                         estado=PASO_PENDIENTE, vuelta=despues_de.vuelta + 1, grupo=grupos[clave],
                                         nota=nota[:300]))

    # ================= Validación de diseño con el cliente =================
    def enviar_cliente(self, paso_id: int, datos: EnvioIn, actor: Actor) -> None:
        """El supervisor envió el diseño al cliente (fuera de la plataforma) y espera su respuesta."""
        paso = self._paso(paso_id)
        s = self._vigente(paso, {"validacion_diseno"})
        self._permiso_area(paso, actor)
        reenvio = paso.estado == PASO_ENVIADO
        paso.estado, paso.enviado_en = PASO_ENVIADO, ahora()
        s.estado = "diseno_enviado"
        nota = (" · " + " ".join(datos.nota.split())) if datos.nota else ""
        s.historial.append(SolicitudHistorial(estado=s.estado, usuario_id=actor.id,
                                              nota=(("Diseño reenviado" if reenvio else "Diseño enviado al cliente")
                                                    + " para su aprobación" + nota)[:300]))
        self.sesion.commit()
        self.auditoria.registrar("enviar_diseno", "solicitud", s.id, actor, {"codigo": s.codigo, "reenvio": reenvio})

    def cambios_diseno(self, paso_id: int, datos: CambiosDisenoIn, actor: Actor) -> None:
        """El cliente pidió cambios: se repite el paso de diseño elegido y vuelve a validarse."""
        paso = self._paso(paso_id)
        s = self._vigente(paso, {"validacion_diseno"})
        self._permiso_area(paso, actor)
        previos = [p for p in sorted(s.pasos, key=lambda x: x.orden)
                   if p.etapa == "produccion" and p.estado == "terminado" and p.orden < paso.orden]
        if not previos:
            raise ErrorNegocio("No hay un paso de diseño previo al que regresar")
        destino = next((p for p in previos if p.id == datos.volver_a_paso_id), None) if datos.volver_a_paso_id \
            else previos[-1]
        if not destino:
            raise ErrorNegocio("Elige un paso de producción ya realizado en este caso")
        for p in s.pasos:
            if p.orden > paso.orden and p.estado == PASO_PENDIENTE:
                p.orden += 2
        self.sesion.flush()
        motivo = " ".join(datos.motivo.split())
        self._repetir(s, paso, [destino, paso], f"Cambios pedidos por el cliente: {motivo}")
        self.motor.terminar(paso, actor.id, f"El cliente pidió cambios: {motivo}")
        self.sesion.flush()
        self._finalizar(s, paso, actor, f"El cliente pidió cambios al diseño; regresa a {destino.area.nombre}: {motivo}",
                        "cambios_diseno", {"volver_a": destino.area.nombre, "motivo": motivo})

    def validaciones(self, actor: Actor) -> dict:
        """Tablero del supervisor: diseños por enviar y enviados sin respuesta, por antigüedad."""
        if actor.rol not in SUPERVISION | {DEMO}:
            raise ErrorNegocio("Solo supervisión valida diseños con el cliente", 403)
        opciones = (selectinload(SolicitudPaso.solicitud).selectinload(Solicitud.cliente),
                    selectinload(SolicitudPaso.solicitud).selectinload(Solicitud.pasos),
                    selectinload(SolicitudPaso.area), selectinload(SolicitudPaso.tecnico))
        pasos = sorted(self.sesion.scalars(select(SolicitudPaso).options(*opciones).where(
            SolicitudPaso.etapa == "validacion_diseno", SolicitudPaso.estado.in_([PASO_EN_AREA, PASO_ENVIADO]))),
            key=self._orden_prioridad)
        hoy = datetime.now(ZONA).date()
        por_enviar, enviados = [], []
        for p in pasos:
            salida = self._salida(p, ["enviar_cliente", "aprobar_diseno", "cambios_diseno"] if p.estado == PASO_EN_AREA
                                  else ["aprobar_diseno", "cambios_diseno", "enviar_cliente"]).model_dump()
            if p.estado == PASO_EN_AREA:
                por_enviar.append(salida)
            else:
                dias = (hoy - p.enviado_en.astimezone(ZONA).date()).days
                salida["dias"] = dias
                salida["rango"] = "hoy" if dias <= 0 else "1" if dias == 1 else "2-3" if dias <= 3 else "4+"
                enviados.append(salida)
        enviados.sort(key=lambda x: x["enviado_en"])
        return {"por_enviar": por_enviar, "enviados": enviados,
                "rangos": {r: sum(1 for e in enviados if e["rango"] == r) for r in ("hoy", "1", "2-3", "4+")}}

    # ================= Ingresos =================
    def modificar(self, paso_id: int, datos: ModificacionIn, actor: Actor) -> None:
        paso = self._paso(paso_id)
        s = self._vigente(paso, {"ingresos"})
        self._permiso_area(paso, actor)
        if (datos.guia_color is None) != (datos.color is None):
            raise ErrorNegocio("Indica la guía de color y el color")
        metodo_antes = s.entrega_metodo or "mensajero"
        apoyo = SolicitudServicio(self.sesion, self.auditoria, None)
        catalogo = apoyo._catalogo(datos)
        apoyo._validar_modalidad(catalogo["tipo_trabajo_id"], catalogo["tipo_trabajo"], s.modalidad)
        hoy = datetime.now(ZONA).date()
        if datos.fecha_entrega < hoy or datos.fecha_entrega > hoy + timedelta(days=180):
            raise ErrorNegocio("La fecha de entrega debe estar entre hoy y los próximos 180 días")
        if datos.fecha_entrega.weekday() >= 5:
            raise ErrorNegocio("Los sábados y domingos no hay entregas")
        bloqueo = self.sesion.scalar(select(DiaNoLaborable).where(DiaNoLaborable.fecha == datos.fecha_entrega,
                                                                  DiaNoLaborable.hora_corte.is_(None)))
        if bloqueo:
            raise ErrorNegocio(f"El {_fecha_texto(datos.fecha_entrega)} no se labora ({bloqueo.motivo})")
        antes = {"trabajo": " · ".join(x for x in (s.tipo_trabajo, s.material, s.unidad, s.guia, s.color) if x),
                 "piezas": ", ".join(map(str, s.piezas or [])), "fecha_entrega": str(s.fecha_entrega),
                 "entrega": metodo_antes}
        guia_anterior = s.guia_id
        for campo, valor in catalogo.items():
            setattr(s, campo, valor)
        s.piezas, s.fecha_entrega = datos.piezas, datos.fecha_entrega
        # colores por pieza: se conservan si sigue la misma guía (solo de las piezas que quedan)
        s.colores_pieza = ([c for c in (s.colores_pieza or []) if c["pieza"] in datos.piezas] or None
                           if s.guia_id and s.guia_id == guia_anterior else None)
        s.entrega_metodo = datos.entrega_metodo or metodo_antes
        despues = {"trabajo": " · ".join(x for x in (s.tipo_trabajo, s.material, s.unidad, s.guia, s.color) if x),
                   "piezas": ", ".join(map(str, s.piezas)), "fecha_entrega": str(s.fecha_entrega),
                   "entrega": s.entrega_metodo}
        cambios = {k: [antes[k], despues[k]] for k in antes if antes[k] != despues[k]}
        if not cambios:
            raise ErrorNegocio("No hay cambios que guardar")
        nota = " ".join(datos.nota.split())
        s.historial.append(SolicitudHistorial(estado=s.estado, nota=f"Modificado por Ingresos: {nota}"[:300],
                                              usuario_id=actor.id))
        self.sesion.commit()
        self.auditoria.registrar("modificar", "solicitud", s.id, actor, {"codigo": s.codigo, "cambios": cambios,
                                                                          "nota": nota})

    def cancelar(self, paso_id: int, motivo: str, actor: Actor) -> None:
        paso = self._paso(paso_id)
        s = self._vigente(paso, {"ingresos"})
        self._permiso_area(paso, actor)
        motivo = " ".join(motivo.split())
        self.motor.cancelar(s, actor.id, f"Cancelado por Ingresos: {motivo}")
        self.motor.repartir_colas()
        self.sesion.commit()
        self.auditoria.registrar("cancelar", "solicitud", s.id, actor, {"codigo": s.codigo, "motivo": motivo})

    # ================= Asignación manual (Logística → mensajero, supervisor → técnico) =================
    def _control_asignacion(self, paso: SolicitudPaso, actor: Actor) -> None:
        if paso.etapa in RUTAS:
            self._permiso_area(paso, actor)  # Logística o supervisión
            if paso.estado not in (PASO_EN_AREA, PASO_ASIGNADO):
                raise Conflicto("Este paso ya no se puede asignar")
        elif paso.etapa == "produccion":
            if actor.rol not in SUPERVISION:
                raise ErrorNegocio("Solo el supervisor o el administrador reasignan trabajos", 403)
            if paso.estado not in ESTADOS_REASIGNABLES:
                raise Conflicto("Este paso ya no se puede reasignar")
        else:
            raise ErrorNegocio(f"Los pasos de {NOMBRE_ETAPA[paso.etapa]} los atiende toda el área, no se asignan")

    def candidatos(self, paso_id: int, actor: Actor) -> list[Candidato]:
        paso = self._paso(paso_id)
        s = self._vigente(paso)
        self._control_asignacion(paso, actor)
        if paso.etapa in RUTAS:
            usuarios = self.sesion.scalars(select(Usuario).where(Usuario.rol == "mensajero", Usuario.activo.is_(True))
                                           .order_by(Usuario.nombre))
            lista = [Candidato(id=u.id, nombre=_nombre(u), rol=u.rol, carga=self.motor.carga(u.id, RUTAS),
                               max_trabajos=None, cubre=True) for u in usuarios]
        else:
            cubren = {u.id for u in self.motor.candidatos(paso.area_id, s.tipo_trabajo_id)}
            # técnicos de cualquier área (apoyo) y quien ya cubre el paso aunque tenga otro rol
            usuarios = self.sesion.scalars(select(Usuario).where(Usuario.activo.is_(True)).order_by(Usuario.nombre))
            lista = [Candidato(id=u.id, nombre=_nombre(u), rol=u.rol, carga=self.motor.carga(u.id),
                               max_trabajos=u.max_trabajos, cubre=u.id in cubren)
                     for u in usuarios if u.id in cubren or u.rol == "tecnico"]
        from app.servicios.estados_personal import ESTADOS_PERSONAL, ROLES_CON_ESTADO
        ausentes = self.motor.ausentes_hoy()
        personas = {u.id: u for u in self.sesion.scalars(select(Usuario).where(Usuario.id.in_([c.id for c in lista] or [0])))}
        for c in lista:
            u = personas.get(c.id)
            if u and u.rol in ROLES_CON_ESTADO:
                c.estado, c.estado_texto = u.estado, ESTADOS_PERSONAL.get(u.estado, u.estado)
            c.recibe_trabajo = bool(u) and (u.rol not in ROLES_CON_ESTADO or u.estado == "conectado") and c.id not in ausentes
        # primero quien cubre y está disponible; luego por carga
        return sorted(lista, key=lambda c: (not c.cubre, not c.recibe_trabajo, c.carga, c.nombre))

    def asignar(self, paso_id: int, datos: AsignarIn, actor: Actor) -> None:
        paso = self._paso(paso_id)
        s = self._vigente(paso)
        self._control_asignacion(paso, actor)
        persona = self.sesion.get(Usuario, datos.usuario_id)
        if not persona or not persona.activo or persona.rol == ROL_CLIENTE:
            raise NoEncontrado("Empleado no encontrado o inactivo")
        if paso.etapa in RUTAS and persona.rol != "mensajero":
            raise ErrorNegocio("Las recolectas y entregas se asignan a un mensajero")
        if paso.etapa == "recolecta" and s.recolecta_metodo == "transporte":
            raise ErrorNegocio("Este material llega por transporte: cambia el método a mensajero para asignarlo")
        if paso.etapa == "produccion" and persona.rol != "tecnico" and persona.id not in {
                u.id for u in self.motor.candidatos(paso.area_id, s.tipo_trabajo_id)}:
            raise ErrorNegocio("Los trabajos de producción se asignan a técnicos")
        if paso.tecnico_id == persona.id and paso.estado == PASO_ASIGNADO:
            raise ErrorNegocio(f"Ya está asignado a {_nombre(persona)}")
        anterior = _nombre(paso.tecnico)
        estaba = paso.estado
        paso.tecnico_id, paso.tecnico = persona.id, persona
        paso.estado, paso.asignado_en, paso.iniciado_en = PASO_ASIGNADO, ahora(), None
        nota = (datos.nota or "").strip()
        if paso.etapa == "recolecta":
            texto = f"Recolecta asignada a {_nombre(persona)}"
        elif paso.etapa == "entrega" and s.entrega_metodo == "transporte":
            texto, s.estado = f"{_nombre(persona)} lleva el trabajo a la empresa de transporte", "en_ruta"
        elif paso.etapa == "entrega":
            texto, s.estado = f"En ruta de entrega con {_nombre(persona)}", "en_ruta"
        else:
            origen = {PASO_EN_COLA: "desde la cola", PASO_SIN_TECNICO: "(no había técnico)"}.get(estaba, f"(antes {anterior})")
            texto = f"{paso.area.nombre}: asignado manualmente a {_nombre(persona)} {origen}"
        s.historial.append(SolicitudHistorial(estado=s.estado, nota=(texto + (f" · {nota}" if nota else ""))[:300],
                                              usuario_id=actor.id))
        self.motor.repartir_colas()  # quien soltó el trabajo pudo quedar con espacio
        self.sesion.commit()
        self.auditoria.registrar("asignar", "solicitud", s.id, actor, {
            "codigo": s.codigo, "area": paso.area.nombre, "a": _nombre(persona), "antes": anterior})

    def recolectado(self, paso_id: int, actor: Actor) -> None:
        """El mensajero ya tiene el material en sus manos: va en camino al laboratorio."""
        paso = self._paso(paso_id)
        s = self._vigente(paso, {"recolecta"})
        if s.recolecta_metodo == "transporte":
            raise ErrorNegocio("Este material llega por transporte: usa Recibido")
        if paso.estado != PASO_ASIGNADO:
            raise Conflicto("La recolecta debe estar asignada a un mensajero")
        if paso.tecnico_id != actor.id:
            self._permiso_area(paso, actor)
        paso.estado, paso.recolectado_en = PASO_RECOLECTADO, ahora()
        s.estado = "material_en_camino"
        limite, vencida = self._plazo(paso)
        plazo = " · fuera del plazo de 2 horas" if vencida else ""
        s.historial.append(SolicitudHistorial(
            estado=s.estado, nota=f"Material recolectado por {_nombre(paso.tecnico) or 'Logística'}{plazo}"[:300],
            usuario_id=actor.id))
        self.sesion.commit()
        self.auditoria.registrar("recolectado", "solicitud", s.id, actor,
                                 {"codigo": s.codigo, "mensajero": _nombre(paso.tecnico), "a_tiempo": not vencida})

    def cambiar_metodo(self, paso_id: int, datos: MetodoIn, actor: Actor) -> None:
        """Logística cambia entre mensajero y transporte mientras el paso está en el área."""
        paso = self._paso(paso_id)
        s = self._vigente(paso, set(RUTAS))
        self._permiso_area(paso, actor)
        if paso.estado != PASO_EN_AREA:
            raise Conflicto("Quita primero la asignación del mensajero (No se pudo) para cambiar el método")
        campo = "recolecta_metodo" if paso.etapa == "recolecta" else "entrega_metodo"
        if (getattr(s, campo) or "mensajero") == datos.metodo:
            raise ErrorNegocio("Ya tiene ese método")
        setattr(s, campo, datos.metodo)
        if paso.etapa == "recolecta" and datos.metodo == "mensajero" and not s.recolecta_direccion:
            s.recolecta_departamento, s.recolecta_municipio, s.recolecta_direccion = (
                s.entrega_departamento, s.entrega_municipio, s.entrega_direccion)
        s.estado = estado_etapa(s, paso.etapa)
        nombre = "mensajero" if datos.metodo == "mensajero" else "transporte"
        tipo = "Recolecta" if paso.etapa == "recolecta" else "Entrega"
        motivo = " ".join(datos.motivo.split())
        s.historial.append(SolicitudHistorial(estado=s.estado, nota=f"{tipo} cambiada a {nombre}: {motivo}"[:300],
                                              usuario_id=actor.id))
        self.sesion.commit()
        self.auditoria.registrar("cambiar_metodo", "solicitud", s.id, actor,
                                 {"codigo": s.codigo, "etapa": paso.etapa, "metodo": datos.metodo, "motivo": motivo})

    def no_se_pudo(self, paso_id: int, motivo: str, actor: Actor) -> None:
        """Visita fallida del mensajero: el paso regresa a Logística para reprogramarlo."""
        paso = self._paso(paso_id)
        s = self._vigente(paso, set(RUTAS))
        if paso.estado != PASO_ASIGNADO:
            raise Conflicto("Esta ruta no está asignada a un mensajero")
        if paso.tecnico_id != actor.id:
            self._permiso_area(paso, actor)
        motivo = " ".join(motivo.split())
        quien = _nombre(paso.tecnico)
        paso.estado, paso.tecnico_id, paso.tecnico, paso.asignado_en = PASO_EN_AREA, None, None, None
        s.estado = estado_etapa(s, paso.etapa)
        tipo = "Recolecta" if paso.etapa == "recolecta" else "Entrega"
        s.historial.append(SolicitudHistorial(estado=s.estado, nota=f"{tipo} no realizada ({quien}): {motivo}"[:300],
                                              usuario_id=actor.id))
        self.sesion.commit()
        self.auditoria.registrar("visita_fallida", "solicitud", s.id, actor,
                                 {"codigo": s.codigo, "mensajero": quien, "motivo": motivo})
