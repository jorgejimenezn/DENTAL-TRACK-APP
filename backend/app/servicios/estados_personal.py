"""Estados del personal: conectado, refacción, almuerzo, capacitación y desconectado.

Reglas acordadas con el laboratorio:
- El reparto automático solo asigna trabajo nuevo a quien está **Conectado**.
- Lo que está en proceso siempre sigue siendo de la persona.
- Lo asignado sin iniciar:
    · Refacción y almuerzo: se le queda (son pausas cortas).
    · Capacitación: el supervisor decide al autorizarla, con reparto (pasa a otros) o sin reparto.
    · Desconectado: se le queda para el siguiente turno, excepto las emergencias (prioridad 1), que se reparten.
- La capacitación la solicita el empleado y la autoriza el supervisor (o el supervisor la asigna directamente).
- Al iniciar sesión queda Conectado; al cerrar sesión, Desconectado. Al terminar la jornada el sistema lo desconecta
  y, si vuelve a usar el sistema dentro del horario, lo conecta de nuevo.
- Las horas fuera de "Conectado" no cuentan para la meta de sus trabajos (ver Motor.registrar_tiempo).
- Cada cambio queda en la tabla de auditoría `estados_personal`.
"""
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.dependencias import Actor
from app.core.errores import Conflicto, ErrorNegocio, NoEncontrado
from app.core.jornada import ZONA, Jornada
from app.modelos import EstadoPersonal, Usuario
from app.modelos.configuracion import Parametro
from app.modelos.solicitud import PASO_ASIGNADO, PASO_EN_AREA, PASO_EN_COLA, PASO_EN_PROCESO, PASO_RECOLECTADO, \
    Solicitud, SolicitudHistorial, SolicitudPaso

ESTADOS_PERSONAL = {"conectado": "Conectado", "refaccion": "Refacción", "almuerzo": "Almuerzo",
                    "capacitacion": "En capacitación", "desconectado": "Desconectado"}
DISPONIBLE = "conectado"
# Roles que manejan estado. Técnicos y mensajeros son los que reciben trabajo individual;
# en Ingresos, QA, Facturación y Logística el estado es informativo (trabajan con la cola del área).
ROLES_CON_ESTADO = {"tecnico", "mensajero", "ingresos", "qa", "facturacion", "logistica"}
# El empleado elige entre estos; la capacitación se solicita y "Desconectado" ocurre al cerrar sesión
ELEGIBLES_EMPLEADO = {"conectado", "refaccion", "almuerzo"}
ELEGIBLES_SUPERVISOR = {"conectado", "refaccion", "almuerzo", "desconectado"}
LECTURA_PERSONAL = {"admin", "supervisor", "operaciones", "demo"}
GESTION_PERSONAL = {"admin", "supervisor"}
RUTAS = ("recolecta", "entrega")
# Tras cerrar el navegador sin cerrar sesión, minutos sin actividad para considerarlo Desconectado
# (cambiar de pantalla no cuenta: la siguiente pantalla registra actividad en segundos)
MINUTOS_CIERRE_NAVEGADOR = 3


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def disponible(usuario: Usuario) -> bool:
    """¿Puede recibir trabajo nuevo del reparto automático?"""
    return usuario.rol not in ROLES_CON_ESTADO or usuario.estado == DISPONIBLE


def _nombre(u: Usuario | None) -> str | None:
    return f"{u.nombre} {u.apellido}".strip() if u else None


class EstadosPersonal:
    def __init__(self, sesion: Session, auditoria=None):
        self.sesion = sesion
        self.auditoria = auditoria
        self._jornada: Jornada | None = None

    @property
    def jornada(self) -> Jornada:
        if self._jornada is None:
            self._jornada = Jornada(self.sesion)
        return self._jornada

    # ================= Núcleo =================
    def cambiar(self, u: Usuario, estado: str, origen: str, momento: datetime | None = None, actor_id: int | None = None,
                nota: str | None = None, con_reparto: bool | None = None, automatico: bool = False) -> list[SolicitudPaso]:
        """Cambia el estado, deja la auditoría y aplica sus efectos. Devuelve los pasos liberados (sin repartir)."""
        momento = momento or ahora()
        if u.estado == estado and u.estado_desde:
            u.estado_auto = automatico and u.estado_auto
            return []
        self.sesion.flush()  # la sesión no hace autoflush: debe ver los cambios de estado de esta misma operación
        abierta = self.sesion.scalar(select(EstadoPersonal).where(
            EstadoPersonal.usuario_id == u.id, EstadoPersonal.hasta.is_(None)).order_by(EstadoPersonal.id.desc()))
        if abierta:
            abierta.hasta = max(momento, abierta.desde)
        self.sesion.add(EstadoPersonal(usuario_id=u.id, estado=estado, desde=momento, origen=origen, nota=nota,
                                       con_reparto=con_reparto, registrado_por_id=actor_id))
        u.estado, u.estado_desde, u.estado_auto = estado, momento, automatico
        self.sesion.flush()
        if estado == "capacitacion":
            u.capacitacion_solicitada_en, u.capacitacion_motivo = None, None
        if estado == "desconectado":
            return self._liberar(u, solo_emergencias=True, motivo=f"{_nombre(u)} se desconectó")
        if estado == "capacitacion" and con_reparto:
            return self._liberar(u, solo_emergencias=False, motivo=f"{_nombre(u)} está en capacitación")
        return []

    def _liberar(self, u: Usuario, solo_emergencias: bool, motivo: str) -> list[SolicitudPaso]:
        """Trabajos asignados sin iniciar que pasan a otros (producción) o regresan a Logística (rutas)."""
        consulta = select(SolicitudPaso).join(Solicitud).where(
            SolicitudPaso.tecnico_id == u.id, SolicitudPaso.estado == PASO_ASIGNADO)
        if solo_emergencias:
            consulta = consulta.where(Solicitud.prioridad == 1)
        pasos = list(self.sesion.scalars(consulta))
        from app.servicios.recorrido import estado_etapa
        for p in pasos:
            p.tecnico_id, p.tecnico, p.asignado_en = None, None, None
            if p.etapa == "produccion":
                p.estado = PASO_EN_COLA
            else:
                p.estado = PASO_EN_AREA
                p.solicitud.estado = estado_etapa(p.solicitud, p.etapa)
            p.solicitud.historial.append(SolicitudHistorial(
                estado=p.solicitud.estado, nota=f"{p.area.nombre}: se liberó porque {motivo}"[:300]))
        self.sesion.flush()
        return pasos

    def _limite(self, desde: datetime) -> datetime:
        """Momento en que el sistema desconecta a quien sigue en un estado: el cierre de la jornada de ese día;
        si el estado empezó después del cierre (o en día sin labores), a la medianoche."""
        local = desde.astimezone(ZONA)
        v = self.jornada.ventana(local.date())
        if v and local < v[1]:
            return v[1]
        return datetime.combine(local.date() + timedelta(days=1), time(0, 0), ZONA)

    def en_horario(self, momento: datetime | None = None) -> bool:
        local = (momento or ahora()).astimezone(ZONA)
        v = self.jornada.ventana(local.date())
        return bool(v and v[0] <= local < v[1])

    def normalizar_usuario(self, u: Usuario, momento: datetime | None = None) -> list[SolicitudPaso]:
        momento = momento or ahora()
        if u.rol not in ROLES_CON_ESTADO or u.estado == "desconectado" or not u.estado_desde:
            u.cierre_navegador_en = None
            return []
        if u.cierre_navegador_en and momento - u.cierre_navegador_en >= timedelta(minutes=MINUTOS_CIERRE_NAVEGADOR):
            # cerró el navegador y no volvió: Desconectado desde la hora en que lo cerró
            cerro = max(u.cierre_navegador_en, u.estado_desde)
            u.cierre_navegador_en = None
            return self.cambiar(u, "desconectado", "cierre_navegador", min(cerro, self._limite(u.estado_desde)),
                                automatico=True)
        limite = self._limite(u.estado_desde)
        if momento >= limite:
            return self.cambiar(u, "desconectado", "automatico", limite, automatico=True)
        return []

    def normalizar(self) -> list[SolicitudPaso]:
        """Fin de jornada: quien quedó en cualquier estado pasa a Desconectado a la hora de cierre."""
        liberados: list[SolicitudPaso] = []
        for u in self.sesion.scalars(select(Usuario).where(
                Usuario.activo.is_(True), Usuario.rol.in_(ROLES_CON_ESTADO), Usuario.estado != "desconectado")):
            liberados += self.normalizar_usuario(u)
        return liberados

    def _repartir(self) -> None:
        from app.servicios.recorrido import Motor
        Motor(self.sesion).repartir_colas()

    # ================= Eventos de sesión =================
    def al_iniciar_sesion(self, u: Usuario) -> None:
        if u.rol not in ROLES_CON_ESTADO:
            return
        self.normalizar_usuario(u)
        if u.estado == "desconectado":
            self.cambiar(u, "conectado", "inicio_sesion", actor_id=u.id)
            self._repartir()

    def navegador_cerrado(self, u: Usuario) -> None:
        """La página avisó que se cerró. Si no hay actividad en unos minutos, normalizar() lo desconecta."""
        if u.rol in ROLES_CON_ESTADO and u.estado != "desconectado":
            u.cierre_navegador_en = ahora()

    def al_cerrar_sesion(self, u: Usuario) -> None:
        if u.rol not in ROLES_CON_ESTADO:
            return
        self.cambiar(u, "desconectado", "cierre_sesion", actor_id=u.id)
        self._repartir()

    def con_actividad(self, u: Usuario) -> bool:
        """En cada petición: desconecta al cerrar la jornada y vuelve a conectar a quien el sistema desconectó
        (no a quien eligió Desconectado) si usa el sistema dentro del horario. Devuelve True si hubo cambios."""
        if u.rol not in ROLES_CON_ESTADO:
            return False
        cambio = bool(self.normalizar_usuario(u)) or (u.estado == "desconectado" and not u.estado_desde)
        if u.cierre_navegador_en:  # volvió a usar el sistema (otra ventana o cambió de pantalla): no cerró
            u.cierre_navegador_en = None
            cambio = True
        if u.estado == "desconectado" and u.estado_auto and self.en_horario():
            self.cambiar(u, "conectado", "actividad", automatico=True)
            self._repartir()
            return True
        return cambio

    # ================= Empleado =================
    def _yo(self, actor: Actor) -> Usuario:
        u = self.sesion.get(Usuario, actor.id)
        if not u or not u.activo:
            raise NoEncontrado("Usuario no encontrado")
        return u

    def mi_estado(self, actor: Actor) -> dict:
        u = self._yo(actor)
        if u.rol not in ROLES_CON_ESTADO:
            return {"aplica": False}
        if self.normalizar_usuario(u):
            self._repartir()
        self.sesion.commit()
        return self._salida_propia(u)

    def _salida_propia(self, u: Usuario) -> dict:
        return {"aplica": True, "estado": u.estado, "estado_texto": ESTADOS_PERSONAL.get(u.estado, u.estado),
                "desde": u.estado_desde, "recibe_trabajo": disponible(u),
                "capacitacion_pendiente": u.capacitacion_solicitada_en is not None,
                "capacitacion_motivo": u.capacitacion_motivo, "capacitacion_solicitada_en": u.capacitacion_solicitada_en,
                "opciones": [{"valor": k, "texto": ESTADOS_PERSONAL[k]} for k in ESTADOS_PERSONAL
                             if k in ELEGIBLES_EMPLEADO]}

    def cambiar_mio(self, estado: str, actor: Actor) -> dict:
        u = self._yo(actor)
        if u.rol not in ROLES_CON_ESTADO:
            raise ErrorNegocio("Tu rol no maneja estados", 403)
        if estado not in ELEGIBLES_EMPLEADO:
            raise ErrorNegocio("La capacitación se solicita al supervisor y Desconectado se registra al cerrar sesión")
        anterior = u.estado
        self.normalizar_usuario(u)
        self.cambiar(u, estado, "usuario", actor_id=u.id)
        self._repartir()  # al conectarse recibe trabajo; al desconectarse se reparten sus emergencias
        self.sesion.commit()
        self._bitacora("estado_personal", u, actor, {"estado": estado, "anterior": anterior})
        return self._salida_propia(u)

    def solicitar_capacitacion(self, motivo: str, actor: Actor) -> dict:
        u = self._yo(actor)
        if u.rol not in ROLES_CON_ESTADO:
            raise ErrorNegocio("Tu rol no maneja estados", 403)
        if u.estado == "capacitacion":
            raise Conflicto("Ya estás en capacitación")
        motivo = " ".join(motivo.split())
        u.capacitacion_solicitada_en, u.capacitacion_motivo = ahora(), motivo[:200]
        self.sesion.commit()
        self._bitacora("solicitar_capacitacion", u, actor, {"motivo": motivo})
        return self._salida_propia(u)

    def cancelar_solicitud(self, actor: Actor) -> dict:
        u = self._yo(actor)
        u.capacitacion_solicitada_en, u.capacitacion_motivo = None, None
        self.sesion.commit()
        return self._salida_propia(u)

    # ================= Supervisión =================
    def _empleado(self, usuario_id: int) -> Usuario:
        u = self.sesion.get(Usuario, usuario_id)
        if not u or not u.activo or u.rol not in ROLES_CON_ESTADO:
            raise NoEncontrado("Empleado no encontrado o su rol no maneja estados")
        return u

    def resolver_capacitacion(self, usuario_id: int, autorizar: bool, con_reparto: bool, motivo: str | None,
                              actor: Actor) -> dict:
        """Autoriza (con o sin reparto) o rechaza una solicitud. Sin solicitud, el supervisor la asigna directamente."""
        if actor.rol not in GESTION_PERSONAL:
            raise ErrorNegocio("Solo administración o supervisión autorizan capacitaciones", 403)
        u = self._empleado(usuario_id)
        motivo = " ".join((motivo or "").split()) or u.capacitacion_motivo
        if not autorizar:
            if not u.capacitacion_solicitada_en:
                raise Conflicto("No tiene una solicitud de capacitación pendiente")
            u.capacitacion_solicitada_en, u.capacitacion_motivo = None, None
            self.sesion.commit()
            self._bitacora("rechazar_capacitacion", u, actor, {"motivo": motivo})
            return {"ok": True, "liberados": 0}
        if u.estado == "capacitacion":
            raise Conflicto("Ya está en capacitación")
        if not motivo:
            raise ErrorNegocio("Indica el motivo de la capacitación")
        self.normalizar_usuario(u)
        liberados = self.cambiar(u, "capacitacion", "supervisor", actor_id=actor.id, nota=motivo[:200],
                                 con_reparto=con_reparto)
        self._repartir()
        self.sesion.commit()
        self._bitacora("autorizar_capacitacion", u, actor, {"motivo": motivo, "con_reparto": con_reparto,
                                                            "trabajos_repartidos": len(liberados)})
        return {"ok": True, "liberados": len(liberados)}

    def asignar_estado(self, usuario_id: int, estado: str, actor: Actor) -> dict:
        """El supervisor termina una capacitación o corrige un estado (ej. alguien olvidó desconectarse)."""
        if actor.rol not in GESTION_PERSONAL:
            raise ErrorNegocio("Solo administración o supervisión cambian el estado de otra persona", 403)
        if estado not in ELEGIBLES_SUPERVISOR:
            raise ErrorNegocio("Para capacitación usa Autorizar capacitación")
        u = self._empleado(usuario_id)
        anterior = u.estado
        self.normalizar_usuario(u)
        self.cambiar(u, estado, "supervisor", actor_id=actor.id)
        self._repartir()
        self.sesion.commit()
        self._bitacora("estado_personal", u, actor, {"estado": estado, "anterior": anterior, "por_supervisor": True})
        return {"ok": True}

    def _maximos(self) -> dict[str, int]:
        valores = {p.clave: p.valor for p in self.sesion.scalars(select(Parametro).where(
            Parametro.clave.in_(["max_refaccion", "max_almuerzo"])))}
        return {"refaccion": int(valores.get("max_refaccion", 15)), "almuerzo": int(valores.get("max_almuerzo", 60))}

    def tablero(self, actor: Actor) -> dict:
        if actor.rol not in LECTURA_PERSONAL:
            raise ErrorNegocio("No tienes permiso para ver el estado del personal", 403)
        if self.normalizar():
            self._repartir()
        self.sesion.commit()
        from app.servicios.recorrido import Motor
        ausentes = Motor(self.sesion).ausentes_hoy()
        maximos, momento = self._maximos(), ahora()
        personas = list(self.sesion.scalars(select(Usuario).options(selectinload(Usuario.areas)).where(
            Usuario.activo.is_(True), Usuario.rol.in_(ROLES_CON_ESTADO)).order_by(Usuario.nombre, Usuario.apellido)))
        ids = [u.id for u in personas] or [0]
        trabajos: dict[int, dict] = {}
        for p in self.sesion.scalars(select(SolicitudPaso).options(selectinload(SolicitudPaso.solicitud)).where(
                SolicitudPaso.tecnico_id.in_(ids),
                SolicitudPaso.estado.in_([PASO_ASIGNADO, PASO_EN_PROCESO, PASO_RECOLECTADO]))):
            t = trabajos.setdefault(p.tecnico_id, {"en_proceso": [], "asignados": [], "emergencias": 0})
            (t["en_proceso"] if p.estado in (PASO_EN_PROCESO, PASO_RECOLECTADO) else t["asignados"]).append(p.solicitud.codigo)
            t["emergencias"] += p.solicitud.prioridad == 1
        filas = []
        for u in personas:
            minutos = int((momento - u.estado_desde).total_seconds() // 60) if u.estado_desde else None
            maximo = maximos.get(u.estado)
            t = trabajos.get(u.id, {"en_proceso": [], "asignados": [], "emergencias": 0})
            filas.append({
                "id": u.id, "nombre": _nombre(u), "rol": u.rol, "areas": [a.nombre for a in u.areas],
                "estado": u.estado, "estado_texto": ESTADOS_PERSONAL.get(u.estado, u.estado), "desde": u.estado_desde,
                "minutos": minutos, "maximo": maximo, "excedido": bool(maximo and minutos is not None and minutos > maximo),
                "ausente_hoy": u.id in ausentes, "recibe_trabajo": disponible(u) and u.id not in ausentes,
                "capacitacion_pendiente": u.capacitacion_solicitada_en is not None,
                "capacitacion_motivo": u.capacitacion_motivo, "capacitacion_solicitada_en": u.capacitacion_solicitada_en,
                "en_proceso": t["en_proceso"], "asignados": t["asignados"], "emergencias_asignadas": t["emergencias"],
            })
        resumen = {k: sum(1 for f in filas if f["estado"] == k) for k in ESTADOS_PERSONAL}
        resumen.update({"pendientes": sum(f["capacitacion_pendiente"] for f in filas),
                        "excedidos": sum(f["excedido"] for f in filas), "ausentes": sum(f["ausente_hoy"] for f in filas)})
        return {"personas": filas, "resumen": resumen, "maximos": maximos, "momento": momento,
                "puede_gestionar": actor.rol in GESTION_PERSONAL}

    def historial(self, actor: Actor, desde: date | None, hasta: date | None, usuario_id: int | None) -> dict:
        if actor.rol not in LECTURA_PERSONAL:
            raise ErrorNegocio("No tienes permiso para ver el estado del personal", 403)
        hoy = datetime.now(ZONA).date()
        hasta = hasta or hoy
        desde = desde or hasta - timedelta(days=6)
        ini = datetime.combine(desde, time(0, 0), ZONA)
        fin = datetime.combine(hasta + timedelta(days=1), time(0, 0), ZONA)
        consulta = (select(EstadoPersonal).options(selectinload(EstadoPersonal.usuario),
                                                   selectinload(EstadoPersonal.registrado_por))
                    .where(EstadoPersonal.desde < fin, or_(EstadoPersonal.hasta.is_(None), EstadoPersonal.hasta > ini))
                    .order_by(EstadoPersonal.desde.desc()))
        if usuario_id:
            consulta = consulta.where(EstadoPersonal.usuario_id == usuario_id)
        momento = ahora()
        filas, resumen = [], {}
        for r in self.sesion.scalars(consulta):
            termino = r.hasta or momento
            minutos = int((min(termino, fin) - max(r.desde, ini)).total_seconds() // 60)
            filas.append({"id": r.id, "usuario_id": r.usuario_id, "nombre": _nombre(r.usuario), "rol": r.usuario.rol,
                          "estado": r.estado, "estado_texto": ESTADOS_PERSONAL.get(r.estado, r.estado),
                          "desde": r.desde, "hasta": r.hasta, "minutos": max(minutos, 0), "origen": r.origen,
                          "nota": r.nota, "con_reparto": r.con_reparto, "registrado_por": _nombre(r.registrado_por)})
            if r.estado in ("refaccion", "almuerzo", "capacitacion"):
                p = resumen.setdefault(r.usuario_id, {"usuario_id": r.usuario_id, "nombre": _nombre(r.usuario),
                                                      "rol": r.usuario.rol, "refaccion": 0, "almuerzo": 0,
                                                      "capacitacion": 0, "veces": 0})
                p[r.estado] += max(minutos, 0)
                p["veces"] += 1
        return {"desde": desde, "hasta": hasta, "registros": filas[:1000],
                "por_persona": sorted(resumen.values(), key=lambda x: x["nombre"] or "")}

    # ================= Tiempos =================
    def horas_fuera(self, usuario_id: int | None, desde: datetime | None, hasta: datetime | None) -> float:
        """Horas laborales en que el empleado no estuvo Conectado dentro del intervalo (no cuentan para su meta)."""
        if not usuario_id or not desde or not hasta or hasta <= desde:
            return 0.0
        self.sesion.flush()
        total = 0.0
        for r in self.sesion.scalars(select(EstadoPersonal).where(
                EstadoPersonal.usuario_id == usuario_id, EstadoPersonal.estado != DISPONIBLE,
                EstadoPersonal.desde < hasta, or_(EstadoPersonal.hasta.is_(None), EstadoPersonal.hasta > desde))):
            total += self.jornada.horas(max(r.desde, desde), min(r.hasta or hasta, hasta))
        return round(total, 2)

    # ================= Bitácora =================
    def _bitacora(self, accion: str, u: Usuario, actor: Actor, detalle: dict) -> None:
        if self.auditoria is None:
            from app.rutas.proveedores import servicio_auditoria
            self.auditoria = servicio_auditoria()
        self.auditoria.registrar(accion, "usuario", u.id, actor, {"empleado": _nombre(u), **detalle})
