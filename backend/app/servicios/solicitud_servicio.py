"""Lógica de negocio de las solicitudes: casos nuevos (CN) y reaperturas (RP).

Todas las reglas se validan aquí aunque el formulario ya las revise, porque la API
también se puede usar directamente desde Swagger.
"""
from datetime import date, datetime, timedelta
from pathlib import PurePath

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from app.core.dependencias import Actor
from app.core.errores import Conflicto, ErrorNegocio, NoEncontrado
from app.esquemas.solicitud import (ArchivoOut, CasoRef, ClienteBreve, DireccionPerfil, DireccionSel, DireccionTexto,
                                    HistorialOut, PerfilSolicitud, ReaperturaIn, RecorridoPaso, SolicitudIn,
                                    SolicitudOut, SolicitudResumen, ValorOut)
from app.modelos import ROL_CLIENTE, Cliente, Direccion, Usuario
from app.modelos.configuracion import Color, DiaNoLaborable, Flujo, GuiaColor, Material, MotivoRP, TipoTrabajo, Unidad
from app.modelos.solicitud import (COLUMNAS_TABLERO, ESTADOS, ESTADOS_CERRADOS, Correlativo, Solicitud, SolicitudArchivo,
                                   SolicitudHistorial)
from app.repositorios.archivo_repo import ArchivoRepositorio
from app.servicios.auditoria_servicio import AuditoriaServicio
from app.servicios.configuracion_servicio import ZONA, CalendarioServicio
from app.servicios.recorrido import NOMBRE_ETAPA, Motor

# Personal que puede ingresar solicitudes a nombre de un cliente (pedidos por teléfono, etc.)
ROLES_CAPTURA = {"admin", "supervisor", "ingresos"}
# Quién puede mover estados manualmente mientras no existen las bandejas de cada área
ROLES_ESTADO = {"admin", "supervisor"}

EXTENSIONES = {".stl": "stl", ".jpg": "imagen", ".jpeg": "imagen", ".png": "imagen", ".pdf": "pdf"}
LIMITE_MB = {"stl": 80, "imagen": 15, "pdf": 15}
DIAS_MAXIMOS = 180
MODALIDADES = {"digital": "digital", "analogo": "analógica"}


def _fecha_texto(d: date) -> str:
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
             "noviembre", "diciembre"]
    return f"{dias[d.weekday()]} {d.day} de {meses[d.month - 1]} de {d.year}"


def _valor(item_id, nombre) -> ValorOut | None:
    return None if nombre is None else ValorOut(id=item_id, nombre=nombre, fuera_catalogo=item_id is None)


class SolicitudServicio:
    def __init__(self, sesion: Session, auditoria: AuditoriaServicio, archivos: ArchivoRepositorio):
        self.sesion = sesion
        self.auditoria = auditoria
        self.archivos = archivos
        self.calendario = CalendarioServicio(sesion, auditoria)

    # ================= Permisos y cliente =================
    @staticmethod
    def _es_doctor(actor: Actor) -> bool:
        return actor.rol == ROL_CLIENTE

    def _cliente_del_doctor(self, actor: Actor) -> Cliente:
        cliente = self.sesion.scalar(select(Cliente).where(Cliente.usuario_id == actor.id))
        if not cliente:
            raise NoEncontrado("Tu usuario no tiene un cliente asociado")
        return cliente

    def _cliente_para_captura(self, actor: Actor, cliente_id: int | None) -> Cliente:
        if self._es_doctor(actor):
            return self._cliente_del_doctor(actor)
        if actor.rol not in ROLES_CAPTURA:
            raise ErrorNegocio("Tu rol no puede ingresar solicitudes", 403)
        if not cliente_id:
            raise ErrorNegocio("Selecciona el cliente de la solicitud")
        cliente = self.sesion.get(Cliente, cliente_id)
        if not cliente or not cliente.usuario.activo:
            raise NoEncontrado("Cliente no encontrado o inactivo")
        return cliente

    def _visible(self, solicitud_id: int, actor: Actor) -> Solicitud:
        solicitud = self.sesion.get(Solicitud, solicitud_id)
        if not solicitud:
            raise NoEncontrado("Solicitud no encontrada")
        if self._es_doctor(actor) and solicitud.cliente_id != self._cliente_del_doctor(actor).id:
            raise NoEncontrado("Solicitud no encontrada")  # no se revela que existe
        return solicitud

    # ================= Datos para el formulario =================
    def clientes(self, actor: Actor) -> list[ClienteBreve]:
        if actor.rol not in ROLES_CAPTURA:
            raise ErrorNegocio("Tu rol no puede ingresar solicitudes", 403)
        filas = self.sesion.scalars(select(Cliente).join(Usuario).where(Usuario.activo.is_(True))
                                    .order_by(Cliente.razon_social))
        return [ClienteBreve(id=c.id, razon_social=c.razon_social, clinica=c.clinica, es_red=c.es_red) for c in filas]

    def perfil(self, actor: Actor, cliente_id: int | None) -> PerfilSolicitud:
        cliente = self._cliente_para_captura(actor, cliente_id)
        doctores = self.sesion.execute(
            select(Solicitud.doctor_tratante).where(Solicitud.cliente_id == cliente.id,
                                                    Solicitud.doctor_tratante.is_not(None))
            .group_by(Solicitud.doctor_tratante).order_by(Solicitud.doctor_tratante).limit(40)).scalars()
        return PerfilSolicitud(
            cliente_id=cliente.id, razon_social=cliente.razon_social, clinica=cliente.clinica, es_red=cliente.es_red,
            titular=cliente.razon_social,
            direcciones=[DireccionPerfil(id=d.id, departamento=d.departamento, municipio=d.municipio,
                                         direccion=d.direccion, principal=d.principal)
                         for d in cliente.direcciones if d.activo],
            doctores=list(doctores))

    # ================= Archivos =================
    def subir_archivo(self, contenido: bytes, nombre: str, tipo_mime: str | None, actor: Actor) -> ArchivoOut:
        nombre = PurePath((nombre or "archivo").replace("\\", "/")).name[-200:] or "archivo"
        tipo = EXTENSIONES.get(PurePath(nombre).suffix.lower())
        if not tipo:
            raise ErrorNegocio("Tipo de archivo no permitido. Usa STL, JPG, PNG o PDF")
        if not contenido:
            raise ErrorNegocio("El archivo está vacío")
        if len(contenido) > LIMITE_MB[tipo] * 1024 * 1024:
            raise ErrorNegocio(f"El archivo supera el máximo de {LIMITE_MB[tipo]} MB para {tipo.upper()}")
        guardado = self.archivos.guardar(contenido, nombre, tipo_mime or "application/octet-stream", tipo, actor.id)
        return ArchivoOut(**guardado)

    def quitar_archivo(self, archivo_id: str, actor: Actor) -> None:
        if not self.archivos.eliminar_pendiente(archivo_id, actor.id):
            raise NoEncontrado("Archivo no encontrado o ya forma parte de una solicitud")

    def descargar(self, solicitud_id: int, archivo_id: str, actor: Actor):
        solicitud = self._visible(solicitud_id, actor)
        if not any(a.mongo_id == archivo_id for a in solicitud.archivos):
            raise NoEncontrado("Archivo no encontrado")
        archivo = self.archivos.abrir(archivo_id)
        if not archivo:
            raise NoEncontrado("El archivo ya no está disponible")
        return archivo

    def _tomar_archivos(self, ids: list[str], modalidad: str, actor: Actor) -> list[dict]:
        ids = list(dict.fromkeys(ids))
        encontrados = self.archivos.pendientes(ids, actor.id)
        if len(encontrados) != len(ids):
            raise ErrorNegocio("Uno o más archivos ya no están disponibles. Vuelve a adjuntarlos")
        if modalidad == "digital" and not any(a["tipo"] == "stl" for a in encontrados):
            raise ErrorNegocio("La modalidad digital requiere al menos un archivo STL")
        return encontrados

    # ================= Reglas =================
    def _catalogo(self, datos: SolicitudIn) -> dict:
        """Valida la cadena Tipo → Material → (Unidad, Guía) → Color y devuelve los campos a guardar."""
        s = self.sesion

        def activo(modelo, item_id, etiqueta):
            obj = s.get(modelo, item_id)
            if not obj or not obj.activo:
                raise ErrorNegocio(f"{etiqueta} ya no está disponible. Actualiza el formulario")
            return obj

        campos, tipo, material, guia = {}, None, None, None
        if datos.tipo_trabajo.id:
            tipo = activo(TipoTrabajo, datos.tipo_trabajo.id, "El tipo de trabajo")
        campos.update(tipo_trabajo_id=tipo and tipo.id, tipo_trabajo=tipo.nombre if tipo else datos.tipo_trabajo.fuera_catalogo)

        if datos.material.id:
            material = activo(Material, datos.material.id, "El material")
            if tipo and material not in tipo.materiales:
                raise ErrorNegocio(f"{material.nombre} no es un material permitido para {tipo.nombre}")
        campos.update(material_id=material and material.id,
                      material=material.nombre if material else datos.material.fuera_catalogo)

        unidad = None
        if datos.unidad.id:
            unidad = activo(Unidad, datos.unidad.id, "La unidad")
            if material and unidad not in material.unidades:
                raise ErrorNegocio(f"{unidad.nombre} no aplica para {material.nombre}")
        campos.update(unidad_id=unidad and unidad.id, unidad=unidad.nombre if unidad else datos.unidad.fuera_catalogo)

        usa_color = not material or any(g.activo for g in material.guias)
        if not usa_color and datos.guia_color:
            raise ErrorNegocio(f"{material.nombre} no usa guía de color")
        if usa_color and not datos.guia_color:
            raise ErrorNegocio("Indica la guía de color y el color")
        campos.update(guia_id=None, guia=None, color_id=None, color=None)
        if datos.guia_color:
            if datos.guia_color.id:
                guia = activo(GuiaColor, datos.guia_color.id, "La guía de color")
                if material and guia not in material.guias:
                    raise ErrorNegocio(f"La guía {guia.nombre} no aplica para {material.nombre}")
            color = None
            if datos.color.id:
                if not guia:
                    raise ErrorNegocio("Con una guía fuera de catálogo, describe también el color")
                color = activo(Color, datos.color.id, "El color")
                if color.guia_id != guia.id:
                    raise ErrorNegocio(f"El color {color.nombre} no pertenece a la guía {guia.nombre}")
            campos.update(guia_id=guia and guia.id, guia=guia.nombre if guia else datos.guia_color.fuera_catalogo,
                          color_id=color and color.id, color=color.nombre if color else datos.color.fuera_catalogo)

        campos["fuera_catalogo"] = any(campos[k] is None and campos[n] is not None for k, n in (
            ("tipo_trabajo_id", "tipo_trabajo"), ("material_id", "material"), ("unidad_id", "unidad"),
            ("guia_id", "guia"), ("color_id", "color")))
        return campos

    def _validar_modalidad(self, tipo_id: int | None, nombre_tipo: str, modalidad: str) -> None:
        if not tipo_id:
            return  # fuera de catálogo: el laboratorio lo revisa
        existe = self.sesion.scalar(select(Flujo.id).where(Flujo.tipo_trabajo_id == tipo_id,
                                                           Flujo.modalidad == modalidad, Flujo.activo.is_(True)))
        if not existe:
            raise ErrorNegocio(f"{nombre_tipo} no se recibe en modalidad {MODALIDADES[modalidad]}")

    def _validar_fecha(self, modalidad: str, emergencia: bool, fecha: date) -> date:
        minima = self.calendario.fecha_minima(modalidad, emergencia).primera_fecha
        hoy = datetime.now(ZONA).date()
        if fecha < minima:
            raise ErrorNegocio(f"La fecha de entrega más cercana disponible es el {_fecha_texto(minima)}")
        if fecha > hoy + timedelta(days=DIAS_MAXIMOS):
            raise ErrorNegocio(f"La fecha de entrega no puede ser mayor a {DIAS_MAXIMOS} días")
        if fecha.weekday() >= 5:
            raise ErrorNegocio("Los sábados y domingos no hay entregas")
        bloqueo = self.sesion.scalar(select(DiaNoLaborable).where(DiaNoLaborable.fecha == fecha,
                                                                  DiaNoLaborable.hora_corte.is_(None)))
        if bloqueo:
            raise ErrorNegocio(f"El {_fecha_texto(fecha)} no se labora ({bloqueo.motivo})")
        return minima

    def _direccion(self, cliente: Cliente, sel: DireccionSel, entrega: DireccionTexto | None = None) -> DireccionTexto:
        if sel.tipo == "misma_que_entrega":
            return entrega
        if sel.tipo == "existente":
            d = next((d for d in cliente.direcciones if d.id == sel.direccion_id and d.activo), None)
            if not d:
                raise ErrorNegocio("La dirección seleccionada no existe")
            return DireccionTexto(departamento=d.departamento, municipio=d.municipio, direccion=d.direccion)
        texto = DireccionTexto(departamento=sel.departamento, municipio=sel.municipio, direccion=sel.direccion)
        if sel.guardar:
            repetida = any(d.activo and d.direccion.lower() == sel.direccion.lower()
                           and d.municipio.lower() == sel.municipio.lower() for d in cliente.direcciones)
            if not repetida:
                cliente.direcciones.append(Direccion(**texto.model_dump(), principal=not any(
                    d.activo for d in cliente.direcciones), activo=True))
        return texto

    def _codigo(self, prefijo: str) -> str:
        """Correlativo por prefijo, seguro ante dos solicitudes al mismo tiempo (bloqueo de fila)."""
        self.sesion.execute(pg_insert(Correlativo).values(prefijo=prefijo, ultimo=0)
                            .on_conflict_do_nothing(index_elements=["prefijo"]))
        fila = self.sesion.scalar(select(Correlativo).where(Correlativo.prefijo == prefijo).with_for_update())
        fila.ultimo += 1
        return f"{prefijo}-{fila.ultimo:05d}"

    def _puede_reabrir(self, s: Solicitud) -> tuple[bool, str | None]:
        if s.estado != "entregada":
            return False, "Solo se pueden reabrir casos entregados"
        abierta = self.sesion.scalar(select(Solicitud.codigo).where(Solicitud.caso_origen_id == s.id,
                                                                   Solicitud.estado.not_in(ESTADOS_CERRADOS)))
        if abierta:
            return False, f"Ya existe la reapertura {abierta} en curso para este caso"
        return True, None

    # ================= Comandos =================
    def _entrega_comun(self, cliente: Cliente, datos, actor: Actor) -> dict:
        minima = self._validar_fecha(datos.modalidad, datos.emergencia, datos.fecha_entrega)
        entrega = self._direccion(cliente, datos.direccion_entrega)
        recolecta = self._direccion(cliente, datos.direccion_recolecta, entrega) if datos.direccion_recolecta else None
        archivos = self._tomar_archivos(datos.archivo_ids, datos.modalidad, actor)
        return {
            "campos": dict(
                modalidad=datos.modalidad, requiere_recolecta=datos.modalidad == "analogo",
                piezas=datos.piezas, emergencia=datos.emergencia,
                prioridad=1 if datos.emergencia else cliente.nivel_prioridad,
                fecha_minima=minima, fecha_entrega=datos.fecha_entrega,
                entrega_departamento=entrega.departamento, entrega_municipio=entrega.municipio,
                entrega_direccion=entrega.direccion,
                recolecta_departamento=recolecta and recolecta.departamento,
                recolecta_municipio=recolecta and recolecta.municipio,
                recolecta_direccion=recolecta and recolecta.direccion,
                instrucciones=datos.instrucciones),
            "archivos": archivos,
        }

    def _guardar(self, solicitud: Solicitud, archivos: list[dict], nota: str, actor: Actor) -> Solicitud:
        for a in archivos:
            solicitud.archivos.append(SolicitudArchivo(mongo_id=a["id"], nombre=a["nombre"], tipo=a["tipo"],
                                                       tamano=a["tamano"]))
        self.sesion.add(solicitud)
        Motor(self.sesion).iniciar(solicitud, actor.id, nota)  # arma el recorrido y activa el primer paso
        self.sesion.commit()
        self.archivos.enlazar([a["id"] for a in archivos], solicitud.id)
        return solicitud

    def crear(self, datos: SolicitudIn, actor: Actor) -> SolicitudOut:
        cliente = self._cliente_para_captura(actor, datos.cliente_id)
        catalogo = self._catalogo(datos)
        self._validar_modalidad(catalogo["tipo_trabajo_id"], catalogo["tipo_trabajo"], datos.modalidad)
        comun = self._entrega_comun(cliente, datos, actor)
        solicitud = Solicitud(
            codigo=self._codigo("CN"), tipo_caso="CN", cliente_id=cliente.id, creado_por_id=actor.id,
            estado="pendiente_recolecta" if datos.modalidad == "analogo" else "recibida",
            paciente=datos.paciente, referencia_clinica=datos.referencia_clinica,
            doctor_tratante=datos.doctor_tratante, **catalogo, **comun["campos"])
        nota = "Solicitud creada" + (" · se generó recolecta para Logística" if datos.modalidad == "analogo" else "")
        self._guardar(solicitud, comun["archivos"], nota, actor)
        self.auditoria.registrar("crear", "solicitud", solicitud.id, actor, {
            "codigo": solicitud.codigo, "cliente": cliente.razon_social, "modalidad": solicitud.modalidad,
            "emergencia": solicitud.emergencia, "fuera_catalogo": solicitud.fuera_catalogo})
        return self.obtener(solicitud.id, actor)

    def reabrir(self, origen_id: int, datos: ReaperturaIn, actor: Actor) -> SolicitudOut:
        origen = self._visible(origen_id, actor)
        if not self._es_doctor(actor) and actor.rol not in ROLES_CAPTURA:
            raise ErrorNegocio("Tu rol no puede reabrir casos", 403)
        puede, motivo = self._puede_reabrir(origen)
        if not puede:
            raise Conflicto(motivo)
        fuera = [p for p in datos.piezas if p not in (origen.piezas or [])]
        if fuera:
            raise ErrorNegocio(f"Solo puedes reabrir piezas del caso original ({', '.join(map(str, origen.piezas))})")
        self._validar_modalidad(origen.tipo_trabajo_id, origen.tipo_trabajo, datos.modalidad)
        cliente = origen.cliente
        comun = self._entrega_comun(cliente, datos, actor)
        copia = {k: getattr(origen, k) for k in (
            "paciente", "referencia_clinica", "doctor_tratante", "tipo_trabajo_id", "tipo_trabajo", "material_id",
            "material", "unidad_id", "unidad", "guia_id", "guia", "color_id", "color", "fuera_catalogo")}
        solicitud = Solicitud(
            codigo=self._codigo("RP"), tipo_caso="RP", cliente_id=cliente.id, creado_por_id=actor.id,
            estado="validacion_qa", caso_origen_id=origen.id, reapertura_tipo=datos.tipo_reapertura,
            reapertura_motivo=datos.motivo, **copia, **comun["campos"])
        tipo = "garantía" if datos.tipo_reapertura == "garantia" else "modificación"
        self._guardar(solicitud, comun["archivos"], f"Reapertura de {origen.codigo} por {tipo} · pendiente de QA", actor)
        self.auditoria.registrar("reabrir", "solicitud", solicitud.id, actor, {
            "codigo": solicitud.codigo, "origen": origen.codigo, "tipo": datos.tipo_reapertura,
            "cliente": cliente.razon_social})
        return self.obtener(solicitud.id, actor)

    def cancelar(self, solicitud_id: int, motivo: str, actor: Actor) -> SolicitudOut:
        if actor.rol not in ROLES_ESTADO:
            raise ErrorNegocio("Solo administración o supervisión pueden cancelar un caso en cualquier etapa", 403)
        solicitud = self._visible(solicitud_id, actor)
        if solicitud.estado in ESTADOS_CERRADOS:
            raise ErrorNegocio("El caso ya está cerrado")
        Motor(self.sesion).cancelar(solicitud, actor.id, f"Cancelado: {motivo}")
        self.sesion.commit()
        self.auditoria.registrar("cancelar", "solicitud", solicitud.id, actor,
                                 {"codigo": solicitud.codigo, "motivo": motivo})
        return self.obtener(solicitud.id, actor)

    def cambiar_prioridad(self, solicitud_id: int, prioridad: int, motivo: str, actor: Actor) -> SolicitudOut:
        if actor.rol not in ROLES_ESTADO:
            raise ErrorNegocio("Solo administración o supervisión cambian la prioridad", 403)
        solicitud = self._visible(solicitud_id, actor)
        if solicitud.estado in ESTADOS_CERRADOS:
            raise ErrorNegocio("El caso ya está cerrado")
        if solicitud.prioridad == prioridad:
            raise ErrorNegocio("El caso ya tiene esa prioridad")
        anterior, solicitud.prioridad = solicitud.prioridad, prioridad
        motivo = " ".join(motivo.split())
        # visible solo para el laboratorio: el doctor no ve su nivel de prioridad
        solicitud.historial.append(SolicitudHistorial(estado=solicitud.estado,
                                                      nota=f"Prioridad ajustada por supervisión: {motivo}"[:300],
                                                      usuario_id=actor.id))
        Motor(self.sesion).repartir_colas()
        self.sesion.commit()
        self.auditoria.registrar("prioridad", "solicitud", solicitud.id, actor, {
            "codigo": solicitud.codigo, "cambios": {"prioridad": [anterior, prioridad]}, "motivo": motivo})
        return self.obtener(solicitud.id, actor)

    def orden_pdf(self, solicitud_id: int, actor: Actor) -> tuple[bytes, str]:
        """PDF de la orden de trabajo. Solo personal del laboratorio y después del Ok de Ingresos."""
        if self._es_doctor(actor):
            raise ErrorNegocio("La orden de trabajo es un documento interno del laboratorio", 403)
        s = self._visible(solicitud_id, actor)
        if not s.caja_numero:
            raise ErrorNegocio("La orden se imprime cuando Ingresos aprueba el caso y le asigna caja")
        from app.servicios.orden_pdf import generar_orden
        usuario = self.sesion.get(Usuario, actor.id) if actor.id else None
        contenido = generar_orden(s, f"{usuario.nombre} {usuario.apellido}".strip() if usuario else "sistema")
        self.auditoria.registrar("imprimir_orden", "solicitud", s.id, actor, {"codigo": s.codigo})
        return contenido, f"Orden {s.codigo}.pdf"

    # ================= Consultas =================
    def _resumen(self, s: Solicitud, actor: Actor) -> dict:
        texto, columna = ESTADOS[s.estado]
        partes = [s.tipo_trabajo, s.material]
        return dict(
            id=s.id, codigo=s.codigo, tipo_caso=s.tipo_caso, estado=s.estado, estado_texto=texto, columna=columna,
            cliente_id=s.cliente_id, cliente=s.cliente.razon_social, paciente=s.paciente,
            doctor_tratante=s.doctor_tratante, trabajo=" · ".join(p for p in partes if p), piezas=s.piezas or [],
            modalidad=s.modalidad, emergencia=s.emergencia,
            prioridad=None if self._es_doctor(actor) else s.prioridad,  # el nivel del cliente no se muestra al doctor
            fecha_entrega=s.fecha_entrega, creado_en=s.creado_en,
            caso_origen=s.caso_origen.codigo if s.caso_origen else None, fuera_catalogo=s.fuera_catalogo,
            area_actual=(lambda p: p.area.nombre if p else None)(Motor.paso_actual(s)),
            caja=None if self._es_doctor(actor) or not s.caja_numero else f"{s.caja_color} {s.caja_numero}",
            pasos_total=len([p for p in s.pasos if p.estado != "omitido"]),
            pasos_hechos=len([p for p in s.pasos if p.estado == "terminado"]),
            entregado_en=next((h.fecha for h in reversed(s.historial) if h.estado == "entregada"), None)
            if s.estado == "entregada" else None)

    def tablero(self, actor: Actor, dias_entregados: int = 15, q: str | None = None,
                cliente_id: int | None = None) -> dict:
        """Kanban: casos vigentes por columna + los entregados en los últimos días."""
        vigentes = self.listar(actor, vigentes=True, q=q, cliente_id=cliente_id, limite=500)
        desde = datetime.now(ZONA) - timedelta(days=dias_entregados)
        entregados = [s for s in self.listar(actor, estado="entregada", q=q, cliente_id=cliente_id, limite=200)
                      if s.entregado_en and s.entregado_en >= desde]
        entregados.sort(key=lambda s: s.entregado_en, reverse=True)
        columnas = {c: [] for c in COLUMNAS_TABLERO}
        for s in vigentes + entregados:
            columnas.setdefault(s.columna, []).append(s)
        return {"columnas": [{"nombre": c, "casos": columnas[c]} for c in COLUMNAS_TABLERO],
                "dias_entregados": dias_entregados}

    def listar(self, actor: Actor, vigentes: bool | None = None, estado: str | None = None,
               tipo_caso: str | None = None, q: str | None = None, cliente_id: int | None = None,
               limite: int = 200) -> list[SolicitudResumen]:
        consulta = select(Solicitud).options(selectinload(Solicitud.cliente), selectinload(Solicitud.caso_origen),
                                             selectinload(Solicitud.pasos), selectinload(Solicitud.historial))
        if self._es_doctor(actor):
            consulta = consulta.where(Solicitud.cliente_id == self._cliente_del_doctor(actor).id)
        elif cliente_id:
            consulta = consulta.where(Solicitud.cliente_id == cliente_id)
        if vigentes is True:
            consulta = consulta.where(Solicitud.estado.not_in(ESTADOS_CERRADOS))
        elif vigentes is False:
            consulta = consulta.where(Solicitud.estado.in_(ESTADOS_CERRADOS))
        if estado:
            consulta = consulta.where(Solicitud.estado == estado)
        if tipo_caso:
            consulta = consulta.where(Solicitud.tipo_caso == tipo_caso.upper())
        if q:
            patron = f"%{q.strip()}%"
            condiciones = [Solicitud.codigo.ilike(patron), Solicitud.paciente.ilike(patron),
                           Solicitud.doctor_tratante.ilike(patron)]
            if not self._es_doctor(actor):  # el personal también busca por caja: "azul 12"
                condiciones.append(func.concat(Solicitud.caja_color, " ", Solicitud.caja_numero).ilike(patron))
            consulta = consulta.where(or_(*condiciones))
        orden = ((Solicitud.prioridad, Solicitud.fecha_entrega, Solicitud.id) if vigentes
                 else (Solicitud.creado_en.desc(), Solicitud.id.desc()))
        filas = self.sesion.scalars(consulta.order_by(*orden).limit(limite))
        return [SolicitudResumen(**self._resumen(s, actor)) for s in filas]

    def obtener(self, solicitud_id: int, actor: Actor) -> SolicitudOut:
        s = self._visible(solicitud_id, actor)
        puede, motivo = self._puede_reabrir(s)
        reaperturas = self.sesion.scalars(select(Solicitud).where(Solicitud.caso_origen_id == s.id)
                                          .order_by(Solicitud.id))
        nombre = lambda u: f"{u.nombre} {u.apellido}".strip() if u else None  # noqa: E731
        return SolicitudOut(
            **self._resumen(s, actor), clinica=s.cliente.clinica, creado_por=nombre(s.creado_por),
            caso_origen_id=s.caso_origen_id, reapertura_tipo=s.reapertura_tipo,
            reapertura_motivo=s.reapertura_motivo,
            qa_clasificacion={"garantia_total": "Garantía total", "garantia_parcial_sin_cobro": "Garantía parcial sin cobro",
                              "garantia_parcial_con_cobro": "Garantía parcial con cobro",
                              "cobro": "Cobro"}.get(s.qa_clasificacion),
            qa_motivo=s.qa_motivo_id and self.sesion.get(MotivoRP, s.qa_motivo_id).nombre,
            qa_observacion=s.qa_observacion, referencia_clinica=s.referencia_clinica,
            requiere_recolecta=s.requiere_recolecta,
            tipo_trabajo=_valor(s.tipo_trabajo_id, s.tipo_trabajo), material=_valor(s.material_id, s.material),
            unidad=_valor(s.unidad_id, s.unidad), guia_color=_valor(s.guia_id, s.guia),
            color=_valor(s.color_id, s.color), fecha_minima=s.fecha_minima,
            entrega=DireccionTexto(departamento=s.entrega_departamento, municipio=s.entrega_municipio,
                                   direccion=s.entrega_direccion),
            recolecta=DireccionTexto(departamento=s.recolecta_departamento, municipio=s.recolecta_municipio,
                                     direccion=s.recolecta_direccion) if s.recolecta_direccion else None,
            instrucciones=s.instrucciones,
            archivos=[ArchivoOut(id=a.mongo_id, nombre=a.nombre, tipo=a.tipo, tamano=a.tamano, subido_en=a.subido_en)
                      for a in s.archivos],
            historial=[HistorialOut(estado=h.estado, estado_texto=ESTADOS[h.estado][0], nota=h.nota,
                                    usuario=nombre(h.usuario), fecha=h.fecha) for h in s.historial],
            reaperturas=[CasoRef(id=r.id, codigo=r.codigo, estado=r.estado, estado_texto=ESTADOS[r.estado][0],
                                 creado_en=r.creado_en) for r in reaperturas],
            puede_reabrir=puede, motivo_no_reabrir=motivo, factura_numero=s.factura_numero,
            recorrido=[RecorridoPaso(
                id=p.id, orden=p.orden, area=p.area.nombre, etapa=p.etapa, etapa_texto=NOMBRE_ETAPA[p.etapa],
                estado=p.estado, activado_en=p.activado_en, terminado_en=p.terminado_en, nota=p.nota, vuelta=p.vuelta,
                receptor=p.receptor,
                # los nombres del personal no se muestran al doctor
                tecnico=None if self._es_doctor(actor) else nombre(p.tecnico),
                atendido_por=None if self._es_doctor(actor) else nombre(p.atendido_por))
                for p in s.pasos if p.estado != "omitido"])
