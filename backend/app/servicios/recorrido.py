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

from app.modelos import ROL_CLIENTE, Area, Usuario, usuario_area
from app.modelos.configuracion import Flujo, usuario_area_tipo
from app.modelos.solicitud import (PASO_ASIGNADO, PASO_EN_AREA, PASO_EN_COLA, PASO_OMITIDO, PASO_PENDIENTE,
                                   PASO_SIN_TECNICO, PASO_TERMINADO, PASOS_ACTIVOS, PASOS_CARGA, Solicitud,
                                   SolicitudHistorial, SolicitudPaso)

ESTADO_POR_ETAPA = {
    "recolecta": "pendiente_recolecta", "ingresos": "recibida", "validacion_rp": "validacion_qa",
    "produccion": "en_produccion", "qa": "control_calidad", "facturacion": "facturacion", "entrega": "en_ruta",
}
NOMBRE_ETAPA = {
    "recolecta": "Recolecta", "ingresos": "Ingresos", "validacion_rp": "Validación de RP", "produccion": "Producción",
    "qa": "Control de calidad", "facturacion": "Facturación", "entrega": "Entrega",
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

    def plan(self, s: Solicitud) -> list[tuple[Area, str]]:
        """Pasos (área, etapa) del caso. Garantiza siempre una revisión de Ingresos."""
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
            plan.append((p.area, etapa))
        if not vio_ingresos:
            ingresos = self._area_de("ingresos")
            inicio = [x for x in plan if x[1] == "recolecta"]
            if not inicio and s.modalidad == "analogo" and self._area_de("logistica"):
                inicio = [(self._area_de("logistica"), "recolecta")]
            resto = [x for x in plan if x[1] != "recolecta"]
            # Sin flujo (tipo fuera de catálogo) solo se llega hasta Ingresos; al aprobarlo se completa el recorrido
            plan = inicio + ([(ingresos, "ingresos")] if ingresos else []) + (resto if flujo else [])
        if s.tipo_caso == "RP":
            qa = self._area_de("qa")
            if qa:
                plan.insert(0, (qa, "validacion_rp"))
        return plan

    def iniciar(self, s: Solicitud, usuario_id: int | None, nota: str) -> None:
        """Crea los pasos de un caso nuevo y activa el primero."""
        for i, (area, etapa) in enumerate(self.plan(s), start=1):
            s.pasos.append(SolicitudPaso(orden=i, area_id=area.id, area=area, etapa=etapa, estado=PASO_PENDIENTE))
        self.sesion.flush()
        self.avanzar(s, usuario_id, nota)

    def completar_despues_de_ingresos(self, s: Solicitud, actual: SolicitudPaso) -> None:
        """Al aprobar Ingresos se rehace lo que sigue con el flujo vigente (por si se cambió el tipo)."""
        for p in s.pasos:
            if p.orden > actual.orden and p.estado == PASO_PENDIENTE:
                p.estado = PASO_OMITIDO
        plan = self.plan(s)
        indice = next((i for i, x in enumerate(plan) if x[1] == "ingresos"), -1)
        siguiente = max(p.orden for p in s.pasos) + 1
        for area, etapa in plan[indice + 1:]:
            s.pasos.append(SolicitudPaso(orden=siguiente, area_id=area.id, area=area, etapa=etapa,
                                         estado=PASO_PENDIENTE, vuelta=actual.vuelta))
            siguiente += 1
        self.sesion.flush()

    # ================= Movimiento =================
    @staticmethod
    def paso_actual(s: Solicitud) -> SolicitudPaso | None:
        return next((p for p in sorted(s.pasos, key=lambda x: x.orden) if p.estado in PASOS_ACTIVOS), None)

    def terminar(self, paso: SolicitudPaso, usuario_id: int | None, nota: str | None = None) -> None:
        paso.estado = PASO_TERMINADO
        paso.terminado_en = ahora()
        paso.atendido_por_id = usuario_id
        paso.nota = (nota or "").strip()[:300] or paso.nota

    def avanzar(self, s: Solicitud, usuario_id: int | None, nota: str | None = None) -> None:
        """Activa el siguiente paso pendiente y actualiza el estado visible del caso."""
        anterior = s.estado
        siguiente = next((p for p in sorted(s.pasos, key=lambda x: x.orden) if p.estado == PASO_PENDIENTE), None)
        if siguiente:
            self.activar(s, siguiente)
            s.estado = ESTADO_POR_ETAPA[siguiente.etapa]
        else:
            s.estado = "entregada"
        if s.estado != anterior or nota:
            texto = nota or (f"Pasa a {siguiente.area.nombre}" if siguiente else "Caso entregado y finalizado")
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
        return [u for u in usuarios if u.id not in restricciones or (tipo_id in restricciones[u.id])]

    def carga(self, usuario_id: int) -> int:
        return self.sesion.scalar(select(func.count()).select_from(SolicitudPaso)
                                  .where(SolicitudPaso.tecnico_id == usuario_id,
                                         SolicitudPaso.estado.in_(PASOS_CARGA))) or 0

    def asignar(self, s: Solicitud, paso: SolicitudPaso) -> None:
        self.sesion.flush()  # la sesión no hace autoflush: la carga debe ver lo recién asignado
        candidatos = self.candidatos(paso.area_id, s.tipo_trabajo_id)
        if not candidatos:
            paso.estado, paso.tecnico_id = PASO_SIN_TECNICO, None
            return
        con_espacio = [(self.carga(u.id), u.id, u) for u in candidatos]
        con_espacio = [x for x in con_espacio if x[2].max_trabajos is None or x[0] < x[2].max_trabajos]
        if not con_espacio:
            paso.estado, paso.tecnico_id = PASO_EN_COLA, None
            return
        _, _, elegido = min(con_espacio, key=lambda x: (x[0], x[1]))  # menos carga; empate: el más antiguo
        paso.estado, paso.tecnico_id, paso.asignado_en = PASO_ASIGNADO, elegido.id, ahora()

    def repartir_colas(self) -> int:
        """Intenta asignar los pasos en cola o sin técnico, por prioridad y fecha de entrega."""
        pendientes = list(self.sesion.execute(
            select(SolicitudPaso, Solicitud).join(Solicitud)
            .where(SolicitudPaso.estado.in_([PASO_EN_COLA, PASO_SIN_TECNICO]))
            .order_by(Solicitud.prioridad, Solicitud.fecha_entrega, SolicitudPaso.activado_en)))
        asignados = 0
        for paso, s in pendientes:
            self.asignar(s, paso)
            self.sesion.flush()
            asignados += paso.estado == PASO_ASIGNADO
        return asignados

    # ================= Casos creados antes del motor =================
    def preparar_existentes(self) -> int:
        """Casos abiertos sin pasos (creados antes de esta versión): arrancan su recorrido."""
        casos = list(self.sesion.scalars(select(Solicitud).where(
            Solicitud.estado.not_in(["entregada", "cancelada"]), ~Solicitud.pasos.any())))
        for s in casos:
            self.iniciar(s, None, "Recorrido generado al actualizar el sistema")
        return len(casos)
