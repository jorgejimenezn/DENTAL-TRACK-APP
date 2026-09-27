"""Lógica de negocio de la configuración administrable."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session, selectinload

from app.core.dependencias import Actor
from app.core.errores import Conflicto, ErrorNegocio, NoEncontrado
from app.core.feriados import feriados_guatemala
from app.esquemas.configuracion import (Arbol, AsignacionArea, AsignacionEmpleado, AsignacionIn, CatalogoCompleto,
                                        DiaIn, DiaOut, FechaMinimaOut, FlujoIn, FlujoOut, GuiaOut, ItemOut,
                                        MaterialOut, NodoGuia, NodoMaterial, NodoTipo, Parametros, PasoOut, TipoOut)
from app.modelos import ROL_CLIENTE, Area, Usuario
from app.modelos.configuracion import (Color, ColorCaja, DiaNoLaborable, Flujo, FlujoPaso, GuiaColor, Material, MotivoRP,
                                       Parametro, TipoTrabajo, Unidad, usuario_area_tipo)
from app.servicios.auditoria_servicio import AuditoriaServicio

ZONA = ZoneInfo("America/Guatemala")
MODELOS = {"tipos": TipoTrabajo, "materiales": Material, "unidades": Unidad, "guias": GuiaColor,
           "motivos-rp": MotivoRP, "areas": Area, "colores-caja": ColorCaja}
NOMBRES = {"tipos": "tipo de trabajo", "materiales": "material", "unidades": "unidad", "guias": "guía de color",
           "motivos-rp": "motivo de RP", "areas": "área", "colores-caja": "color de caja"}


def _item(o) -> ItemOut:
    return ItemOut(id=o.id, nombre=o.nombre, activo=o.activo)


class _Base:
    def __init__(self, sesion: Session, auditoria: AuditoriaServicio):
        self.sesion = sesion
        self.auditoria = auditoria

    def _registrar(self, accion: str, actor: Actor, detalle: dict, entidad_id=None):
        self.auditoria.registrar(accion, "configuracion", entidad_id, actor, detalle)

    def _existentes(self, modelo, ids: list[int], etiqueta: str) -> list:
        ids = list(dict.fromkeys(ids))
        objetos = list(self.sesion.scalars(select(modelo).where(modelo.id.in_(ids)))) if ids else []
        if len(objetos) != len(ids):
            raise ErrorNegocio(f"Uno o más {etiqueta} no existen")
        return objetos


# ======================================================================
class CatalogoServicio(_Base):
    def completo(self) -> CatalogoCompleto:
        s = self.sesion
        tipos = s.scalars(select(TipoTrabajo).options(selectinload(TipoTrabajo.materiales)).order_by(TipoTrabajo.nombre))
        materiales = s.scalars(select(Material).options(selectinload(Material.unidades), selectinload(Material.guias))
                               .order_by(Material.nombre))
        guias = s.scalars(select(GuiaColor).options(selectinload(GuiaColor.colores)).order_by(GuiaColor.nombre))
        return CatalogoCompleto(
            tipos=[TipoOut(**_item(t).model_dump(), material_ids=[m.id for m in t.materiales]) for t in tipos],
            materiales=[MaterialOut(**_item(m).model_dump(), unidad_ids=[u.id for u in m.unidades],
                                    guia_ids=[g.id for g in m.guias]) for m in materiales],
            unidades=[_item(u) for u in s.scalars(select(Unidad).order_by(Unidad.id))],
            guias=[GuiaOut(**_item(g).model_dump(), colores=[_item(c) for c in g.colores]) for g in guias],
            motivos=[_item(m) for m in s.scalars(select(MotivoRP).order_by(MotivoRP.nombre))],
            areas=[_item(a) for a in s.scalars(select(Area).order_by(Area.id))],
            colores_caja=[_item(c) for c in s.scalars(select(ColorCaja).order_by(ColorCaja.id))],
        )

    def _validar_unico(self, modelo, nombre: str, excluir_id=None, etiqueta="elemento"):
        consulta = select(modelo.id).where(func.lower(modelo.nombre) == nombre.lower())
        if excluir_id:
            consulta = consulta.where(modelo.id != excluir_id)
        if self.sesion.scalar(consulta):
            raise Conflicto(f"Ya existe un {etiqueta} con ese nombre")

    def crear(self, catalogo: str, nombre: str, actor: Actor) -> ItemOut:
        modelo = MODELOS[catalogo]
        self._validar_unico(modelo, nombre, etiqueta=NOMBRES[catalogo])
        obj = modelo(nombre=nombre, activo=True)
        self.sesion.add(obj)
        self.sesion.commit()
        self._registrar("crear", actor, {"catalogo": NOMBRES[catalogo], "nombre": nombre}, obj.id)
        return _item(obj)

    def actualizar(self, catalogo: str, item_id: int, nombre: str, activo: bool, actor: Actor) -> ItemOut:
        modelo = MODELOS[catalogo]
        obj = self.sesion.get(modelo, item_id)
        if not obj:
            raise NoEncontrado(f"No existe ese {NOMBRES[catalogo]}")
        self._validar_unico(modelo, nombre, item_id, NOMBRES[catalogo])
        if catalogo == "areas" and obj.activo and not activo:
            en_uso = self.sesion.scalar(select(func.count(func.distinct(FlujoPaso.flujo_id)))
                                        .join(Flujo).where(FlujoPaso.area_id == item_id, Flujo.activo.is_(True)))
            if en_uso:
                raise ErrorNegocio(f"No se puede desactivar: el área se usa en {en_uso} flujo(s) activo(s)")
        cambios = {}
        if obj.nombre != nombre:
            cambios["nombre"] = [obj.nombre, nombre]
        if obj.activo != activo:
            cambios["activo"] = [obj.activo, activo]
        obj.nombre, obj.activo = nombre, activo
        self.sesion.commit()
        if cambios:
            self._registrar("editar", actor, {"catalogo": NOMBRES[catalogo], "cambios": cambios}, item_id)
        return _item(obj)

    def materiales_de_tipo(self, tipo_id: int, ids: list[int], actor: Actor) -> TipoOut:
        tipo = self.sesion.get(TipoTrabajo, tipo_id)
        if not tipo:
            raise NoEncontrado("No existe ese tipo de trabajo")
        tipo.materiales = self._existentes(Material, ids, "materiales")
        self.sesion.commit()
        self._registrar("relaciones", actor, {"tipo": tipo.nombre,
                                               "materiales": [m.nombre for m in tipo.materiales]}, tipo_id)
        return TipoOut(**_item(tipo).model_dump(), material_ids=[m.id for m in tipo.materiales])

    def relaciones_material(self, material_id: int, unidad_ids: list[int], guia_ids: list[int],
                            actor: Actor) -> MaterialOut:
        material = self.sesion.get(Material, material_id)
        if not material:
            raise NoEncontrado("No existe ese material")
        material.unidades = self._existentes(Unidad, unidad_ids, "unidades")
        material.guias = self._existentes(GuiaColor, guia_ids, "guías de color")
        self.sesion.commit()
        self._registrar("relaciones", actor, {"material": material.nombre,
                                               "unidades": [u.nombre for u in material.unidades],
                                               "guias": [g.nombre for g in material.guias]}, material_id)
        return MaterialOut(**_item(material).model_dump(), unidad_ids=[u.id for u in material.unidades],
                           guia_ids=[g.id for g in material.guias])

    def crear_color(self, guia_id: int, nombre: str, actor: Actor) -> GuiaOut:
        guia = self.sesion.get(GuiaColor, guia_id)
        if not guia:
            raise NoEncontrado("No existe esa guía de color")
        if any(c.nombre.lower() == nombre.lower() for c in guia.colores):
            raise Conflicto("Ese color ya existe en la guía")
        guia.colores.append(Color(nombre=nombre, activo=True))
        self.sesion.commit()
        self._registrar("crear", actor, {"catalogo": "color", "guia": guia.nombre, "nombre": nombre}, guia_id)
        return GuiaOut(**_item(guia).model_dump(), colores=[_item(c) for c in guia.colores])

    def actualizar_color(self, color_id: int, nombre: str, activo: bool, actor: Actor) -> GuiaOut:
        color = self.sesion.get(Color, color_id)
        if not color:
            raise NoEncontrado("No existe ese color")
        guia = color.guia
        if any(c.id != color_id and c.nombre.lower() == nombre.lower() for c in guia.colores):
            raise Conflicto("Ese color ya existe en la guía")
        antes = {"nombre": color.nombre, "activo": color.activo}
        color.nombre, color.activo = nombre, activo
        self.sesion.commit()
        self._registrar("editar", actor, {"catalogo": "color", "guia": guia.nombre,
                                           "cambios": {k: [antes[k], v] for k, v in
                                                       {"nombre": nombre, "activo": activo}.items() if antes[k] != v}},
                        color_id)
        return GuiaOut(**_item(guia).model_dump(), colores=[_item(c) for c in guia.colores])

    def arbol(self) -> Arbol:
        """Catálogo activo y anidado, listo para los formularios de solicitud."""
        tipos = self.sesion.scalars(select(TipoTrabajo).where(TipoTrabajo.activo.is_(True))
                                    .options(selectinload(TipoTrabajo.materiales).selectinload(Material.unidades),
                                             selectinload(TipoTrabajo.materiales).selectinload(Material.guias)
                                             .selectinload(GuiaColor.colores))
                                    .order_by(TipoTrabajo.nombre))
        modalidades = {}
        for tipo_id, modalidad in self.sesion.execute(select(Flujo.tipo_trabajo_id, Flujo.modalidad)
                                                      .where(Flujo.activo.is_(True))):
            modalidades.setdefault(tipo_id, []).append(modalidad)
        nodos = []
        for t in tipos:
            materiales = [NodoMaterial(
                id=m.id, nombre=m.nombre,
                unidades=[_item(u) for u in m.unidades if u.activo],
                guias=[NodoGuia(id=g.id, nombre=g.nombre, colores=[_item(c) for c in g.colores if c.activo])
                       for g in m.guias if g.activo])
                for m in t.materiales if m.activo]
            nodos.append(NodoTipo(id=t.id, nombre=t.nombre, materiales=materiales,
                                  modalidades=sorted(modalidades.get(t.id, []))))
        motivos = self.sesion.scalars(select(MotivoRP).where(MotivoRP.activo.is_(True)).order_by(MotivoRP.nombre))
        cajas = self.sesion.scalars(select(ColorCaja).where(ColorCaja.activo.is_(True)).order_by(ColorCaja.id))
        return Arbol(tipos=nodos, motivos_rp=[_item(m) for m in motivos], colores_caja=[_item(c) for c in cajas])


# ======================================================================
class AsignacionServicio(_Base):
    def _empleados(self):
        return list(self.sesion.scalars(select(Usuario).options(selectinload(Usuario.areas))
                                        .where(Usuario.rol != ROL_CLIENTE, Usuario.activo.is_(True))
                                        .order_by(Usuario.nombre, Usuario.apellido)))

    def _restricciones(self) -> dict[tuple[int, int], set[int]]:
        filas = self.sesion.execute(select(usuario_area_tipo.c.usuario_id, usuario_area_tipo.c.area_id,
                                           usuario_area_tipo.c.tipo_trabajo_id))
        resultado: dict[tuple[int, int], set[int]] = {}
        for usuario_id, area_id, tipo_id in filas:
            resultado.setdefault((usuario_id, area_id), set()).add(tipo_id)
        return resultado

    def cobertura(self) -> dict[tuple[int, int], int]:
        """(area_id, tipo_id) → cantidad de empleados activos que pueden hacer ese paso."""
        restricciones = self._restricciones()
        tipos = list(self.sesion.scalars(select(TipoTrabajo.id)))
        conteo: dict[tuple[int, int], int] = {}
        for empleado in self._empleados():
            for area in empleado.areas:
                permitidos = restricciones.get((empleado.id, area.id)) or tipos
                for tipo_id in permitidos:
                    conteo[(area.id, tipo_id)] = conteo.get((area.id, tipo_id), 0) + 1
        return conteo

    def listar(self) -> list[AsignacionEmpleado]:
        restricciones = self._restricciones()
        return [AsignacionEmpleado(
            usuario_id=e.id, nombre=f"{e.nombre} {e.apellido}".strip(), rol=e.rol, max_trabajos=e.max_trabajos,
            areas=[AsignacionArea(area_id=a.id, area=a.nombre,
                                  tipo_ids=sorted(restricciones.get((e.id, a.id), set()))) for a in e.areas])
            for e in self._empleados() if e.areas]

    def guardar(self, usuario_id: int, datos: AsignacionIn, actor: Actor) -> AsignacionEmpleado:
        empleado = self.sesion.get(Usuario, usuario_id)
        if not empleado or empleado.rol == ROL_CLIENTE:
            raise NoEncontrado("Empleado no encontrado")
        areas_empleado = {a.id: a.nombre for a in empleado.areas}
        tipos = {t.id: t.nombre for t in self.sesion.scalars(select(TipoTrabajo))}
        for asignacion in datos.areas:
            if asignacion.area_id not in areas_empleado:
                raise ErrorNegocio("Solo puedes restringir áreas que el empleado ya tiene asignadas")
            if any(t not in tipos for t in asignacion.tipo_ids):
                raise ErrorNegocio("Uno o más tipos de trabajo no existen")
        self.sesion.execute(delete(usuario_area_tipo).where(usuario_area_tipo.c.usuario_id == usuario_id))
        filas = [{"usuario_id": usuario_id, "area_id": a.area_id, "tipo_trabajo_id": t}
                 for a in datos.areas for t in dict.fromkeys(a.tipo_ids)]
        if filas:
            self.sesion.execute(insert(usuario_area_tipo), filas)
        self.sesion.commit()
        self._registrar("asignacion", actor, {
            "empleado": f"{empleado.nombre} {empleado.apellido}",
            "areas": {areas_empleado[a.area_id]: ([tipos[t] for t in a.tipo_ids] or ["Todos"]) for a in datos.areas},
        }, usuario_id)
        return next(e for e in self.listar() if e.usuario_id == usuario_id)


# ======================================================================
class FlujoServicio(_Base):
    def _salida(self, flujo: Flujo, cobertura: dict) -> FlujoOut:
        return FlujoOut(id=flujo.id, tipo_trabajo_id=flujo.tipo_trabajo_id, tipo_trabajo=flujo.tipo_trabajo.nombre,
                        modalidad=flujo.modalidad, activo=flujo.activo,
                        pasos=[PasoOut(orden=p.orden, area_id=p.area_id, area=p.area.nombre,
                                       tecnicos=cobertura.get((p.area_id, flujo.tipo_trabajo_id), 0))
                               for p in flujo.pasos])

    def listar(self) -> list[FlujoOut]:
        cobertura = AsignacionServicio(self.sesion, self.auditoria).cobertura()
        flujos = self.sesion.scalars(select(Flujo).options(selectinload(Flujo.pasos).selectinload(FlujoPaso.area),
                                                           selectinload(Flujo.tipo_trabajo)))
        return sorted((self._salida(f, cobertura) for f in flujos), key=lambda f: (f.tipo_trabajo, f.modalidad))

    def guardar(self, datos: FlujoIn, actor: Actor) -> FlujoOut:
        tipo = self.sesion.get(TipoTrabajo, datos.tipo_trabajo_id)
        if not tipo:
            raise NoEncontrado("No existe ese tipo de trabajo")
        areas = {a.id: a for a in self.sesion.scalars(select(Area).where(Area.id.in_(set(datos.area_ids))))}
        if any(i not in areas for i in datos.area_ids):
            raise ErrorNegocio("Una o más áreas no existen")
        if any(not areas[i].activo for i in datos.area_ids):
            raise ErrorNegocio("No se pueden usar áreas inactivas en un flujo")
        flujo = self.sesion.scalar(select(Flujo).where(Flujo.tipo_trabajo_id == tipo.id,
                                                       Flujo.modalidad == datos.modalidad))
        antes = [p.area.nombre for p in flujo.pasos] if flujo else []
        if not flujo:
            flujo = Flujo(tipo_trabajo=tipo, modalidad=datos.modalidad)
            self.sesion.add(flujo)
        flujo.pasos.clear()
        self.sesion.flush()  # libera los "orden" anteriores antes de insertar los nuevos
        flujo.pasos.extend(FlujoPaso(orden=i + 1, area_id=a) for i, a in enumerate(datos.area_ids))
        flujo.activo = datos.activo
        self.sesion.commit()
        self._registrar("flujo", actor, {"tipo": tipo.nombre, "modalidad": datos.modalidad, "activo": datos.activo,
                                          "cambios": {"pasos": [antes, [areas[i].nombre for i in datos.area_ids]]}},
                        flujo.id)
        self.sesion.refresh(flujo)
        return self._salida(flujo, AsignacionServicio(self.sesion, self.auditoria).cobertura())


# ======================================================================
class CalendarioServicio(_Base):
    def listar(self, anio: int | None) -> list[DiaOut]:
        consulta = select(DiaNoLaborable).order_by(DiaNoLaborable.fecha)
        if anio:
            consulta = consulta.where(DiaNoLaborable.fecha.between(date(anio, 1, 1), date(anio, 12, 31)))
        return [DiaOut(id=d.id, fecha=d.fecha, motivo=d.motivo, hora_corte=d.hora_corte) for d in self.sesion.scalars(consulta)]

    def agregar(self, datos: DiaIn, actor: Actor) -> DiaOut:
        if self.sesion.scalar(select(DiaNoLaborable.id).where(DiaNoLaborable.fecha == datos.fecha)):
            raise Conflicto("Esa fecha ya está bloqueada")
        dia = DiaNoLaborable(fecha=datos.fecha, motivo=datos.motivo.strip(), hora_corte=datos.hora_corte)
        self.sesion.add(dia)
        self.sesion.commit()
        self._registrar("calendario", actor, {
            "accion": f"horario especial hasta {dia.hora_corte}" if dia.hora_corte else "bloquear",
            "fecha": str(dia.fecha), "motivo": dia.motivo}, dia.id)
        return DiaOut(id=dia.id, fecha=dia.fecha, motivo=dia.motivo, hora_corte=dia.hora_corte)

    def eliminar(self, dia_id: int, actor: Actor) -> None:
        dia = self.sesion.get(DiaNoLaborable, dia_id)
        if not dia:
            raise NoEncontrado("Fecha no encontrada")
        self.sesion.delete(dia)
        self.sesion.commit()
        self._registrar("calendario", actor, {"accion": "desbloquear", "fecha": str(dia.fecha), "motivo": dia.motivo},
                        dia_id)

    def cargar_feriados(self, anio: int, actor: Actor) -> list[DiaOut]:
        existentes = set(self.sesion.scalars(select(DiaNoLaborable.fecha)))
        nuevos = [DiaNoLaborable(fecha=f, motivo=m, hora_corte=h) for f, m, h in feriados_guatemala(anio)
                  if f not in existentes]
        self.sesion.add_all(nuevos)
        self.sesion.commit()
        self._registrar("calendario", actor, {"accion": "cargar_feriados", "anio": anio, "agregados": len(nuevos)})
        return self.listar(anio)

    # --- Parámetros ---
    def parametros(self) -> Parametros:
        valores = {p.clave: p.valor for p in self.sesion.scalars(select(Parametro))}
        return Parametros(corte_semana=valores.get("corte_semana", "18:00"),
                          corte_sabado=valores.get("corte_sabado", "12:00"),
                          min_digital=int(valores.get("min_digital", 2)),
                          min_analogo=int(valores.get("min_analogo", 3)),
                          min_emergencia=int(valores.get("min_emergencia", 1)))

    def guardar_parametros(self, datos: Parametros, actor: Actor) -> Parametros:
        antes = self.parametros().model_dump()
        for clave, valor in datos.model_dump().items():
            parametro = self.sesion.get(Parametro, clave)
            if parametro:
                parametro.valor = str(valor)
            else:
                self.sesion.add(Parametro(clave=clave, valor=str(valor)))
        self.sesion.commit()
        cambios = {k: [antes[k], v] for k, v in datos.model_dump().items() if antes[k] != v}
        if cambios:
            self._registrar("parametros", actor, {"cambios": cambios})
        return self.parametros()

    # --- Regla de fecha mínima de entrega ---
    def fecha_minima(self, modalidad: str, emergencia: bool, ahora: datetime | None = None) -> FechaMinimaOut:
        p = self.parametros()
        ahora = (ahora.astimezone(ZONA) if ahora and ahora.tzinfo else (ahora.replace(tzinfo=ZONA) if ahora
                                                                           else datetime.now(ZONA)))
        especiales = {d.fecha: d.hora_corte for d in self.sesion.scalars(select(DiaNoLaborable).where(
            DiaNoLaborable.fecha.between(ahora.date() - timedelta(days=1), ahora.date() + timedelta(days=120))))}
        bloqueados = {f for f, h in especiales.items() if not h}   # sin labores
        horarios = {f: h for f, h in especiales.items() if h}        # se labora con cierre anticipado

        def habil(d: date) -> bool:
            return d.weekday() < 5 and d not in bloqueados

        def siguiente_habil(d: date) -> date:
            d += timedelta(days=1)
            while not habil(d):
                d += timedelta(days=1)
            return d

        hoy, hora = ahora.date(), ahora.strftime("%H:%M")
        if hoy in horarios and hora < horarios[hoy]:
            base, nota = hoy, f"Horario especial: registrado antes de las {horarios[hoy]}"
        elif hoy in horarios:
            base = siguiente_habil(hoy)
            nota = f"Horario especial (cierre {horarios[hoy]}): se cuenta desde el siguiente día hábil"
        elif habil(hoy) and hora < p.corte_semana:
            base, nota = hoy, f"Registrado antes de las {p.corte_semana}"
        elif hoy.weekday() == 5 and hoy not in bloqueados and hora < p.corte_sabado:
            base, nota = hoy, f"Sábado antes de las {p.corte_sabado}"
        else:
            base = siguiente_habil(hoy)
            nota = "Fuera de horario: se cuenta desde el siguiente día hábil"
        dias = p.min_emergencia if emergencia else (p.min_digital if modalidad == "digital" else p.min_analogo)
        fecha = base
        for _ in range(dias):
            fecha = siguiente_habil(fecha)
        return FechaMinimaOut(registro=ahora.strftime("%Y-%m-%d %H:%M"), cuenta_desde=base, dias_minimos=dias,
                              primera_fecha=fecha, nota=nota)
