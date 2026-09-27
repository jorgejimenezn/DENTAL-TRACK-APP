"""Bandeja de trabajo y acciones de cada área sobre el paso en que va el caso."""
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.dependencias import Actor
from app.core.errores import Conflicto, ErrorNegocio, NoEncontrado
from app.esquemas.bandeja import (CLASIFICACIONES, AreaBandeja, AsignarIn, Bandeja, Candidato, ModificacionIn,
                                  PasoBandeja, PasoPrevio, Produccion, RechazoIn, ResumenArea, TerminarIn,
                                  ValidacionRpIn)
from app.modelos import ROL_CLIENTE, Area, Usuario
from app.modelos.configuracion import ColorCaja, DiaNoLaborable, MotivoRP
from app.modelos.solicitud import ESTADOS_CERRADOS
from app.modelos.solicitud import (PASO_ASIGNADO, PASO_EN_AREA, PASO_EN_COLA, PASO_EN_PROCESO, PASO_PENDIENTE,
                                   PASO_SIN_TECNICO, PASOS_ACTIVOS, PASOS_CARGA, Solicitud, SolicitudHistorial,
                                   SolicitudPaso)
from app.servicios.auditoria_servicio import AuditoriaServicio
from app.servicios.configuracion_servicio import ZONA
from app.servicios.recorrido import ESTADO_POR_ETAPA, NOMBRE_ETAPA, Motor, ahora, tipo_area
from app.servicios.solicitud_servicio import SolicitudServicio, _fecha_texto

SUPERVISION = {"admin", "supervisor"}
ACCIONES_AREA = {
    "ingresos": ["aprobar", "modificar", "cancelar"],
    "validacion_rp": ["validar_rp"],
    "qa": ["aprobar_qa", "rechazar"],
    "facturacion": ["facturar"],
    "recolecta": ["asignar_mensajero", "recolectado"],
    "entrega": ["asignar_mensajero", "entregado"],
}
RUTAS = ("recolecta", "entrega")
ESTADOS_REASIGNABLES = {PASO_ASIGNADO, PASO_EN_COLA, PASO_SIN_TECNICO, PASO_EN_PROCESO}
NOTA_TERMINAR = {
    "recolecta": "Material recolectado", "qa": "Aprobado por control de calidad",
    "entrega": "Entregado al cliente", "facturacion": "Facturado y empacado",
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
        usuario = self.sesion.get(Usuario, actor.id) if actor.id else None
        return [a for a in (usuario.areas if usuario else []) if a.activo]

    def _vigente(self, paso: SolicitudPaso, etapas: set[str] | None = None) -> Solicitud:
        """El paso debe ser el actual del caso (evita que dos personas lo atiendan a la vez)."""
        s = paso.solicitud
        if self.motor.paso_actual(s) is not paso or paso.estado not in PASOS_ACTIVOS:
            raise Conflicto(f"{s.codigo} ya no está en este paso. Actualiza tu bandeja")
        if etapas and paso.etapa not in etapas:
            raise ErrorNegocio(f"Esta acción no corresponde a la etapa de {NOMBRE_ETAPA[paso.etapa]}")
        return s

    def _permiso_area(self, paso: SolicitudPaso, actor: Actor) -> None:
        if actor.rol in SUPERVISION:
            return
        if paso.area_id not in {a.id for a in self._areas(actor)}:
            raise ErrorNegocio(f"No perteneces al área {paso.area.nombre}", 403)

    def _salida(self, p: SolicitudPaso, acciones: list[str]) -> PasoBandeja:
        s = p.solicitud
        previos = []
        if p.etapa == "qa":  # opciones para devolver el caso
            previos = [PasoPrevio(id=x.id, orden=x.orden, area=x.area.nombre) for x in s.pasos
                       if x.etapa == "produccion" and x.estado == "terminado" and x.orden < p.orden]
        return PasoBandeja(
            paso_id=p.id, solicitud_id=s.id, codigo=s.codigo, tipo_caso=s.tipo_caso, cliente=s.cliente.razon_social,
            paciente=s.paciente, doctor_tratante=s.doctor_tratante,
            trabajo=" · ".join(x for x in (s.tipo_trabajo, s.material, s.unidad) if x),
            color=f"{s.guia} · {s.color}" if s.color else None, piezas=s.piezas or [], modalidad=s.modalidad,
            emergencia=s.emergencia, prioridad=s.prioridad, fecha_entrega=s.fecha_entrega,
            instrucciones=s.instrucciones, fuera_catalogo=s.fuera_catalogo, area_id=p.area_id, area=p.area.nombre,
            etapa=p.etapa, etapa_texto=NOMBRE_ETAPA[p.etapa], estado=p.estado, tecnico=_nombre(p.tecnico),
            activado_en=p.activado_en, asignado_en=p.asignado_en, iniciado_en=p.iniciado_en, vuelta=p.vuelta,
            reapertura_tipo=s.reapertura_tipo, reapertura_motivo=s.reapertura_motivo,
            qa_clasificacion=CLASIFICACIONES.get(s.qa_clasificacion), factura_numero=s.factura_numero,
            direccion=(f"{s.recolecta_direccion}, {s.recolecta_municipio}" if p.etapa == "recolecta"
                       and s.recolecta_direccion else f"{s.entrega_direccion}, {s.entrega_municipio}"),
            archivos=len(s.archivos), telefono=s.cliente.telefono_celular or s.cliente.telefono_fijo,
            receptor=p.receptor, caja=f"{s.caja_color} {s.caja_numero}" if s.caja_numero else None,
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
        if mios or any(tipo_area(a.nombre) == "produccion" for a in areas):
            actual = next((p for p in mios if p.estado == PASO_EN_PROCESO), None)
            en_espera = [p for p in mios if p.estado == PASO_ASIGNADO]
            siguiente = en_espera[0] if en_espera else None
            usuario = self.sesion.get(Usuario, actor.id)
            produccion = Produccion(
                actual=self._salida(actual, ["terminar"]) if actual else None,
                siguiente=self._salida(siguiente, [] if actual else ["iniciar"]) if siguiente else None,
                asignados=[self._salida(p, []) for p in en_espera[1:]], total=len(mios),
                max_trabajos=usuario.max_trabajos if usuario else None)

        # --- Mensajero: sus recolectas y entregas ---
        rutas = None
        if actor.rol == "mensajero":
            propias = sorted(self.sesion.scalars(select(SolicitudPaso).options(*opciones).where(
                SolicitudPaso.tecnico_id == actor.id, SolicitudPaso.etapa.in_(RUTAS),
                SolicitudPaso.estado == PASO_ASIGNADO)), key=self._orden_prioridad)
            rutas = [self._salida(p, ["hecho", "no_se_pudo"]) for p in propias]

        # --- Áreas de apoyo: lo que está en el área, lo atiende cualquiera ---
        supervisa = actor.rol in SUPERVISION

        def acciones_de(p: SolicitudPaso) -> list[str]:
            if p.estado == PASO_EN_AREA:
                return ACCIONES_AREA.get(p.etapa, [])
            if p.etapa in RUTAS and p.estado == PASO_ASIGNADO:
                return ["asignar_mensajero", "no_se_pudo"]  # reasignar o regresar al área
            if supervisa and p.etapa == "produccion" and p.estado in ESTADOS_REASIGNABLES:
                return ["asignar", "prioridad"]
            return []

        def pasos_de(area: Area, todos: bool) -> list[PasoBandeja]:
            estados = PASOS_ACTIVOS if todos else (
                [PASO_EN_AREA, PASO_ASIGNADO] if tipo_area(area.nombre) == "logistica" else [PASO_EN_AREA])
            consulta = select(SolicitudPaso).options(*opciones).where(SolicitudPaso.area_id == area.id,
                                                                      SolicitudPaso.estado.in_(estados))
            return [self._salida(p, acciones_de(p)) for p in sorted(self.sesion.scalars(consulta),
                                                                   key=self._orden_prioridad)]

        salida_areas = [AreaBandeja(area_id=a.id, area=a.nombre, tipo=tipo_area(a.nombre), pasos=pasos_de(a, False))
                        for a in areas if tipo_area(a.nombre) != "produccion"]

        # --- Supervisión: resumen de todas las áreas y detalle de una ---
        supervision = None
        if actor.rol in SUPERVISION:
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
            if elegida:
                salida_areas = [x for x in salida_areas if x.area_id != elegida.id]
                salida_areas.insert(0, AreaBandeja(area_id=elegida.id, area=elegida.nombre,
                                                   tipo=tipo_area(elegida.nombre), pasos=pasos_de(elegida, True)))
        return Bandeja(produccion=produccion, rutas=rutas, areas=salida_areas, supervision=supervision)

    # ================= Producción =================
    def iniciar(self, paso_id: int, actor: Actor) -> None:
        paso = self._paso(paso_id)
        self._vigente(paso, {"produccion"})
        if paso.tecnico_id != actor.id:
            raise ErrorNegocio("Este trabajo no está asignado a ti", 403)
        if paso.estado != PASO_ASIGNADO:
            raise Conflicto("Este trabajo ya se inició")
        mios = sorted(self.sesion.scalars(select(SolicitudPaso).where(
            SolicitudPaso.tecnico_id == actor.id, SolicitudPaso.etapa == "produccion",
            SolicitudPaso.estado.in_(PASOS_CARGA))), key=self._orden_prioridad)
        if any(p.estado == PASO_EN_PROCESO for p in mios):
            raise Conflicto("Termina el trabajo que tienes en proceso antes de iniciar otro")
        primero = next(p for p in mios if p.estado == PASO_ASIGNADO)
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
            if paso.tecnico_id != actor.id and actor.rol not in SUPERVISION:
                raise ErrorNegocio("Este trabajo no está asignado a ti", 403)
            self.motor.terminar(paso, actor.id, datos.nota)
            nota = f"{paso.area.nombre} terminado" + (f" · {datos.nota}" if datos.nota else "")
            return self._finalizar(s, paso, actor, nota, "terminar_paso")

        es_su_ruta = paso.etapa in RUTAS and paso.estado == PASO_ASIGNADO and paso.tecnico_id == actor.id
        if not es_su_ruta:
            self._permiso_area(paso, actor)
        detalle = {}
        if paso.etapa == "entrega":
            if not datos.receptor:
                raise ErrorNegocio("Escribe el nombre de quien recibe")
            paso.receptor = datos.receptor
            detalle["recibio"] = datos.receptor
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
            s.factura_numero = datos.factura_numero
            detalle["factura"] = datos.factura_numero
            nota = f"Factura {datos.factura_numero} · empacado"
        elif paso.etapa == "entrega":
            nota = f"Entregado · recibió {datos.receptor}"
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
        repetir = [p for p in sorted(s.pasos, key=lambda x: x.orden)
                   if destino.orden <= p.orden <= paso.orden and (p.estado == "terminado" or p is paso)
                   and p.etapa in ("produccion", "qa")]
        despues = [p for p in s.pasos if p.orden > paso.orden and p.estado == PASO_PENDIENTE]
        for p in despues:
            p.orden += len(repetir)
        self.sesion.flush()
        for i, p in enumerate(repetir, start=1):
            s.pasos.append(SolicitudPaso(orden=paso.orden + i, area_id=p.area_id, area=p.area, etapa=p.etapa,
                                         estado=PASO_PENDIENTE, vuelta=paso.vuelta + 1))
        motivo = " ".join(datos.motivo.split())
        self.motor.terminar(paso, actor.id, f"Devuelto a {destino.area.nombre}: {motivo}")
        self.sesion.flush()
        self._finalizar(s, paso, actor, f"QA devolvió el caso a {destino.area.nombre}: {motivo}", "rechazar_qa",
                        {"volver_a": destino.area.nombre, "motivo": motivo})

    # ================= Ingresos =================
    def modificar(self, paso_id: int, datos: ModificacionIn, actor: Actor) -> None:
        paso = self._paso(paso_id)
        s = self._vigente(paso, {"ingresos"})
        self._permiso_area(paso, actor)
        if (datos.guia_color is None) != (datos.color is None):
            raise ErrorNegocio("Indica la guía de color y el color")
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
                 "piezas": ", ".join(map(str, s.piezas or [])), "fecha_entrega": str(s.fecha_entrega)}
        for campo, valor in catalogo.items():
            setattr(s, campo, valor)
        s.piezas, s.fecha_entrega = datos.piezas, datos.fecha_entrega
        despues = {"trabajo": " · ".join(x for x in (s.tipo_trabajo, s.material, s.unidad, s.guia, s.color) if x),
                   "piezas": ", ".join(map(str, s.piezas)), "fecha_entrega": str(s.fecha_entrega)}
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
        return sorted(lista, key=lambda c: (not c.cubre, c.carga, c.nombre))

    def asignar(self, paso_id: int, datos: AsignarIn, actor: Actor) -> None:
        paso = self._paso(paso_id)
        s = self._vigente(paso)
        self._control_asignacion(paso, actor)
        persona = self.sesion.get(Usuario, datos.usuario_id)
        if not persona or not persona.activo or persona.rol == ROL_CLIENTE:
            raise NoEncontrado("Empleado no encontrado o inactivo")
        if paso.etapa in RUTAS and persona.rol != "mensajero":
            raise ErrorNegocio("Las recolectas y entregas se asignan a un mensajero")
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
        s.estado = ESTADO_POR_ETAPA[paso.etapa]
        tipo = "Recolecta" if paso.etapa == "recolecta" else "Entrega"
        s.historial.append(SolicitudHistorial(estado=s.estado, nota=f"{tipo} no realizada ({quien}): {motivo}"[:300],
                                              usuario_id=actor.id))
        self.sesion.commit()
        self.auditoria.registrar("visita_fallida", "solicitud", s.id, actor,
                                 {"codigo": s.codigo, "mensajero": quien, "motivo": motivo})
