"""Motor del recorrido: arma los pasos de un caso a partir de su flujo y los asigna.

Idea central: el flujo de cada tipo de trabajo y modalidad ya describe todo el camino
(Logística → Ingresos → producción → QA → Facturación → Logística). Cada paso se copia
al caso y el estado visible del caso se deduce del paso en que va.

- Áreas de apoyo (Ingresos, QA, Facturación, Logística): el paso queda "en el área" y lo
  atiende cualquiera de sus integrantes.
- Áreas de producción: el paso se asigna a UN técnico que tenga el área y el tipo de trabajo,
  con menos carga y sin pasar su tope. Si todos están al tope queda en cola; si nadie cubre
  esa área y tipo, queda "sin técnico" para que el supervisor lo resuelva.
"""
import unicodedata
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.jornada import ZONA, Jornada
from app.modelos import ROL_CLIENTE, Area, Ausencia, Usuario, usuario_area
from app.modelos.configuracion import Flujo, usuario_area_tipo
from app.modelos.solicitud import (PASO_ASIGNADO, PASO_EN_AREA, PASO_EN_COLA, PASO_OMITIDO, PASO_PENDIENTE,
                                   PASO_SIN_TECNICO, PASO_TERMINADO, PASOS_ACTIVOS, PASOS_CARGA, Solicitud,
                                   SolicitudHistorial, SolicitudPaso, TiempoPaso)

ESTADO_POR_ETAPA = {
    "recolecta": "pendiente_recolecta", "ingresos": "recibida", "validacion_rp": "validacion_qa",
    "produccion": "en_produccion", "qa": "control_calidad", "facturacion": "facturacion", "entrega": "listo_entrega",
    "validacion_diseno": "validacion_diseno",
}
PLAZO_RECOLECTA_HORAS = 2  # horas laborales para recoger en la clínica (no aplica a transporte)


def estado_etapa(s: Solicitud, etapa: str) -> str:
    """Estado visible del caso cuando su paso actual está en `etapa` (esperando que lo atiendan)."""
    if etapa == "recolecta" and s.recolecta_metodo == "transporte":
        return "espera_transporte"
    return ESTADO_POR_ETAPA[etapa]


NOMBRE_ETAPA = {
    "recolecta": "Recolecta", "ingresos": "Ingresos", "validacion_rp": "Validación de RP", "produccion": "Producción",
    "qa": "Control de calidad", "facturacion": "Facturación", "entrega": "Entrega",
    "validacion_diseno": "Validación de diseño",
}


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def _normal(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_acentos.lower().strip()


def tipo_area(nombre: str) -> str:
    """Clasifica un área por su nombre: ingresos, logistica, qa, facturacion o produccion."""
    n = _normal(nombre)
    if n.startswith("ingreso"):
        return "ingresos"
    if n.startswith("logistic"):
        return "logistica"
    if n == "qa" or n.startswith("qa ") or n.startswith("qa_") or n.startswith("control de calidad"):
        return "qa"
    if n.startswith("factura"):
        return "facturacion"
    if n.startswith("validacion de diseno"):
        return "validacion_diseno"
    return "produccion"


class Motor:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    # ================= Plan de pasos =================
    def _area_de(self, tipo: str) -> Area | None:
        return next((a for a in self.sesion.scalars(select(Area).where(Area.activo.is_(True)).order_by(Area.id))
                     if tipo_area(a.nombre) == tipo), None)

    def flujo(self, s: Solicitud) -> Flujo | None:
        if not s.tipo_trabajo_id:
            return None
        return self.sesion.scalar(select(Flujo).where(Flujo.tipo_trabajo_id == s.tipo_trabajo_id,
                                                      Flujo.modalidad == s.modalidad, Flujo.activo.is_(True)))

    def plan(self, s: Solicitud) -> list[tuple[Area, str, bool]]:
        """Pasos (área, etapa, en paralelo con el anterior) del caso. Garantiza siempre una revisión de Ingresos.
        Solo se respeta el paralelo entre pasos de producción."""
        flujo = self.flujo(s)
        plan, vio_ingresos = [], False
        for p in (flujo.pasos if flujo else []):
            t = tipo_area(p.area.nombre)
            if t == "ingresos":
                etapa, vio_ingresos = "ingresos", True
            elif t == "logistica":
                etapa = "entrega" if vio_ingresos else "recolecta"
            else:
                etapa = t
            paralelo = bool(p.paralelo) and etapa == "produccion" and bool(plan) and plan[-1][1] == "produccion"
            plan.append((p.area, etapa, paralelo))
        if not vio_ingresos:
            ingresos = self._area_de("ingresos")
            inicio = [x for x in plan if x[1] == "recolecta"]
            if not inicio and s.modalidad == "analogo" and self._area_de("logistica"):
                inicio = [(self._area_de("logistica"), "recolecta", False)]
            resto = [x for x in plan if x[1] != "recolecta"]
            # Sin flujo (tipo fuera de catálogo) solo se llega hasta Ingresos; al aprobarlo se completa el recorrido
            plan = inicio + ([(ingresos, "ingresos", False)] if ingresos else []) + (resto if flujo else [])
        if s.tipo_caso == "RP":
            qa = self._area_de("qa")
            if qa:
                plan.insert(0, (qa, "validacion_rp", False))
        return plan

    def iniciar(self, s: Solicitud, usuario_id: int | None, nota: str) -> None:
        """Crea los pasos de un caso nuevo y activa el primero."""
        self._agregar(s, self.plan(s), 1, 1)
        self.sesion.flush()
        self.avanzar(s, usuario_id, nota)

    def completar_despues_de_ingresos(self, s: Solicitud, actual: SolicitudPaso) -> None:
        """Al aprobar Ingresos se rehace lo que sigue con el flujo vigente (por si se cambió el tipo)."""
        for p in s.pasos:
            if p.orden > actual.orden and p.estado == PASO_PENDIENTE:
                p.estado = PASO_OMITIDO
        plan = self.plan(s)
        indice = next((i for i, x in enumerate(plan) if x[1] == "ingresos"), -1)
        resto = plan[indice + 1:]
        if resto:
            resto[0] = (resto[0][0], resto[0][1], False)  # el primero después de Ingresos nunca es paralelo
        self._agregar(s, resto, max(p.orden for p in s.pasos) + 1, max(p.grupo or 0 for p in s.pasos) + 1,
                      actual.vuelta)
        self.sesion.flush()

    @staticmethod
    def _agregar(s: Solicitud, plan: list[tuple], orden: int, grupo: int, vuelta: int = 1) -> None:
        """Agrega pasos pendientes; los marcados en paralelo comparten el grupo del anterior."""
        grupo -= 1
        for i, (area, etapa, paralelo) in enumerate(plan):
            if not (paralelo and i):
                grupo += 1
            s.pasos.append(SolicitudPaso(orden=orden + i, area_id=area.id, area=area, etapa=etapa, grupo=grupo,
                                         estado=PASO_PENDIENTE, vuelta=vuelta))

    # ================= Movimiento =================
    @staticmethod
    def paso_actual(s: Solicitud) -> SolicitudPaso | None:
        return next((p for p in sorted(s.pasos, key=lambda x: x.orden) if p.estado in PASOS_ACTIVOS), None)

    @staticmethod
    def pasos_activos(s: Solicitud) -> list[SolicitudPaso]:
        """Todos los pasos en curso (más de uno cuando hay pasos en paralelo)."""
        return [p for p in sorted(s.pasos, key=lambda x: x.orden) if p.estado in PASOS_ACTIVOS]

    def terminar(self, paso: SolicitudPaso, usuario_id: int | None, nota: str | None = None) -> None:
        paso.estado = PASO_TERMINADO
        paso.terminado_en = ahora()
        paso.atendido_por_id = usuario_id
        paso.nota = (nota or "").strip()[:300] or paso.nota
        self.registrar_tiempo(paso, usuario_id)

    def registrar_tiempo(self, paso: SolicitudPaso, usuario_id: int | None) -> None:
        """Auditoría de tiempos en horas laborales, con la meta del área vigente en este momento."""
        if not hasattr(self, "_jornada"):
            self._jornada = Jornada(self.sesion)
        j, s = self._jornada, paso.solicitud
        produccion = paso.etapa == "produccion"
        # las horas en pausa no cuentan para la meta
        p_espera, p_trabajo = float(paso.pausa_espera or 0), float(paso.pausa_trabajo or 0)
        if produccion and paso.tecnico_id and paso.iniciado_en:
            # ni las horas en que el técnico no estuvo Conectado (refacción, almuerzo, capacitación, desconectado)
            from app.servicios.estados_personal import EstadosPersonal
            estados = EstadosPersonal(self.sesion)
            estados._jornada = j
            asignado = max(paso.asignado_en or paso.activado_en, paso.activado_en) if paso.activado_en else None
            p_espera += estados.horas_fuera(paso.tecnico_id, asignado, paso.iniciado_en)
            p_trabajo += estados.horas_fuera(paso.tecnico_id, paso.iniciado_en, paso.terminado_en)
        total = max(j.horas(paso.activado_en, paso.terminado_en) - p_espera - p_trabajo, 0.0)
        meta = float(paso.area.meta_horas or 4)
        if paso.etapa == "recolecta" and s.recolecta_metodo != "transporte":
            # lo que se mide es cuánto tardó en recogerse en la clínica: plazo fijo de 2 horas laborales
            total = max(j.horas(paso.activado_en, paso.recolectado_en or paso.terminado_en) - p_espera, 0.0)
            meta = float(PLAZO_RECOLECTA_HORAS)
        total = round(total, 2)
        self.sesion.add(TiempoPaso(
            paso_id=paso.id, solicitud_id=s.id, codigo=s.codigo, area_id=paso.area_id, area=paso.area.nombre,
            etapa=paso.etapa, tipo_trabajo=s.tipo_trabajo, responsable_id=paso.tecnico_id if produccion else usuario_id,
            vuelta=paso.vuelta, activado_en=paso.activado_en, iniciado_en=paso.iniciado_en,
            terminado_en=paso.terminado_en,
            espera_horas=round(max(j.horas(paso.activado_en, paso.iniciado_en) - p_espera, 0), 2)
            if produccion and paso.iniciado_en else None,
            trabajo_horas=round(max(j.horas(paso.iniciado_en, paso.terminado_en) - p_trabajo, 0), 2)
            if produccion and paso.iniciado_en else None,
            total_horas=total, meta_horas=meta, cumplio=total <= meta))

    def avanzar(self, s: Solicitud, usuario_id: int | None, nota: str | None = None) -> None:
        """Activa el siguiente grupo de pasos pendientes y actualiza el estado visible del caso.
        Si aún hay pasos en paralelo en curso, el caso espera a que terminen todos."""
        anterior = s.estado
        en_curso = self.pasos_activos(s)
        if en_curso:
            if nota:
                s.historial.append(SolicitudHistorial(estado=s.estado, nota=(
                    nota + " · espera a " + ", ".join(p.area.nombre for p in en_curso))[:300], usuario_id=usuario_id))
            return
        pendientes = [p for p in sorted(s.pasos, key=lambda x: x.orden) if p.estado == PASO_PENDIENTE]
        siguiente = pendientes[0] if pendientes else None
        if siguiente:
            grupo = [p for p in pendientes if p.grupo == siguiente.grupo] if siguiente.grupo else [siguiente]
            for p in grupo:
                self.activar(s, p)
            s.estado = estado_etapa(s, siguiente.etapa)
        else:
            s.estado = "entregada"
        if s.estado != anterior or nota:
            destino = " + ".join(p.area.nombre for p in self.pasos_activos(s)) if siguiente else ""
            texto = nota or (f"Pasa a {destino}" if siguiente else "Caso entregado y finalizado")
            s.historial.append(SolicitudHistorial(estado=s.estado, nota=texto[:300], usuario_id=usuario_id))

    def activar(self, s: Solicitud, paso: SolicitudPaso) -> None:
        paso.activado_en = ahora()
        if paso.etapa == "produccion":
            self.asignar(s, paso)
        else:
            paso.estado = PASO_EN_AREA

    def cancelar(self, s: Solicitud, usuario_id: int | None, motivo: str) -> None:
        for p in s.pasos:
            if p.estado in PASOS_ACTIVOS or p.estado == PASO_PENDIENTE:
                p.estado, p.tecnico_id = PASO_OMITIDO, None
        s.estado = "cancelada"
        s.historial.append(SolicitudHistorial(estado="cancelada", nota=motivo[:300], usuario_id=usuario_id))

    # ================= Asignación automática =================
    def candidatos(self, area_id: int, tipo_id: int | None) -> list[Usuario]:
        """Empleados activos con el área; si tienen tipos restringidos en esa área, debe incluir el tipo."""
        usuarios = list(self.sesion.scalars(
            select(Usuario).join(usuario_area, usuario_area.c.usuario_id == Usuario.id)
            .where(usuario_area.c.area_id == area_id, Usuario.activo.is_(True), Usuario.rol != ROL_CLIENTE)
            .order_by(Usuario.id)))
        restricciones: dict[int, set[int]] = {}
        for usuario_id, tipo in self.sesion.execute(select(usuario_area_tipo.c.usuario_id,
                                                           usuario_area_tipo.c.tipo_trabajo_id)
                                                    .where(usuario_area_tipo.c.area_id == area_id)):
            restricciones.setdefault(usuario_id, set()).add(tipo)
        ausentes = self.ausentes_hoy()
        return [u for u in usuarios if u.id not in ausentes
                and (u.id not in restricciones or tipo_id in restricciones[u.id])]

    def ausentes_hoy(self) -> set[int]:
        hoy = datetime.now(ZONA).date()
        return set(self.sesion.scalars(select(Ausencia.usuario_id).where(Ausencia.desde <= hoy, Ausencia.hasta >= hoy)))

    def liberar_ausentes(self) -> int:
        """Trabajos asignados (sin iniciar) a quien hoy no labora: vuelven a repartirse o a Logística."""
        ausentes = self.ausentes_hoy()
        if not ausentes:
            return 0
        pasos = list(self.sesion.scalars(select(SolicitudPaso).where(
            SolicitudPaso.tecnico_id.in_(ausentes), SolicitudPaso.estado == PASO_ASIGNADO)))
        for p in pasos:
            quien = f"{p.tecnico.nombre} {p.tecnico.apellido}".strip()
            p.tecnico_id, p.tecnico, p.asignado_en = None, None, None
            if p.etapa == "produccion":
                p.estado = PASO_EN_COLA
            else:  # recolecta o entrega de un mensajero ausente
                p.estado = PASO_EN_AREA
                p.solicitud.estado = estado_etapa(p.solicitud, p.etapa)
            p.solicitud.historial.append(SolicitudHistorial(
                estado=p.solicitud.estado, nota=f"{p.area.nombre}: se liberó porque {quien} no labora hoy"[:300]))
        self.sesion.flush()
        return len(pasos)

    def carga(self, usuario_id: int, etapas: tuple[str, ...] = ("produccion",)) -> int:
        """Trabajos que ocupan al empleado (los casos en pausa no cuentan para su tope)."""
        return self.sesion.scalar(select(func.count()).select_from(SolicitudPaso).join(Solicitud)
                                  .where(SolicitudPaso.tecnico_id == usuario_id, SolicitudPaso.etapa.in_(etapas),
                                         SolicitudPaso.estado.in_(PASOS_CARGA), Solicitud.pausada.is_(False))) or 0

    def asignar(self, s: Solicitud, paso: SolicitudPaso) -> None:
        self.sesion.flush()  # la sesión no hace autoflush: la carga debe ver lo recién asignado
        candidatos = self.candidatos(paso.area_id, s.tipo_trabajo_id)
        if not candidatos:
            paso.estado, paso.tecnico_id = PASO_SIN_TECNICO, None
            return
        # Solo recibe trabajo nuevo quien está Conectado (refacción, almuerzo, capacitación o desconectado esperan)
        from app.servicios.estados_personal import disponible
        presentes = [u for u in candidatos if disponible(u)]
        if not presentes:
            paso.estado, paso.tecnico_id = PASO_EN_COLA, None
            return
        con_espacio = [(self.carga(u.id), u.id, u) for u in presentes]
        con_espacio = [x for x in con_espacio if x[2].max_trabajos is None or x[0] < x[2].max_trabajos]
        if not con_espacio:
            paso.estado, paso.tecnico_id = PASO_EN_COLA, None
            return
        _, _, elegido = min(con_espacio, key=lambda x: (x[0], x[1]))  # menos carga; empate: el más antiguo
        paso.estado, paso.tecnico_id, paso.asignado_en = PASO_ASIGNADO, elegido.id, ahora()

    def repartir_colas(self) -> int:
        """Intenta asignar los pasos en cola o sin técnico, por prioridad y fecha de entrega."""
        from app.servicios.estados_personal import EstadosPersonal
        liberados = len(EstadosPersonal(self.sesion).normalizar())  # fin de jornada: desconecta a quien sigue
        liberados += self.liberar_ausentes()
        pendientes = list(self.sesion.execute(
            select(SolicitudPaso, Solicitud).join(Solicitud)
            .where(SolicitudPaso.estado.in_([PASO_EN_COLA, PASO_SIN_TECNICO]), Solicitud.pausada.is_(False))
            .order_by(Solicitud.prioridad, Solicitud.fecha_entrega, SolicitudPaso.activado_en)))
        asignados = 0
        for paso, s in pendientes:
            self.asignar(s, paso)
            self.sesion.flush()
            asignados += paso.estado == PASO_ASIGNADO
        return asignados + liberados

    # ================= Casos creados antes del motor =================
    def preparar_existentes(self) -> int:
        """Casos abiertos sin pasos (creados antes de esta versión): arrancan su recorrido."""
        casos = list(self.sesion.scalars(select(Solicitud).where(
            Solicitud.estado.not_in(["entregada", "cancelada"]), ~Solicitud.pasos.any())))
        for s in casos:
            self.iniciar(s, None, "Recorrido generado al actualizar el sistema")
        return len(casos)
