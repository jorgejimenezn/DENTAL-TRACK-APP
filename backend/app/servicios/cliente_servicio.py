"""Lógica de negocio de clientes (doctores/clínicas) y sus direcciones."""
from sqlalchemy.orm import Session

from app.core.dependencias import Actor
from app.core.errores import Conflicto, ErrorNegocio, NoEncontrado
from app.core.seguridad import cifrar_password
from app.esquemas.cliente import (ClienteActualizar, ClienteCrear, ClienteOut, DireccionIn, DireccionOut,
                                  RegistroCliente)
from app.modelos import ROL_CLIENTE, Cliente, Direccion, Usuario
from app.repositorios.cliente_repo import ClienteRepositorio
from app.repositorios.usuario_repo import UsuarioRepositorio
from app.servicios.auditoria_servicio import AuditoriaServicio

CAMPOS_CLIENTE = ["razon_social", "nombre_facturacion", "clinica", "es_red", "telefono_celular",
                  "telefono_fijo", "tipo_documento", "numero_documento", "nivel_prioridad"]


class ClienteServicio:
    def __init__(self, sesion: Session, auditoria: AuditoriaServicio):
        self.sesion = sesion
        self.clientes = ClienteRepositorio(sesion)
        self.usuarios = UsuarioRepositorio(sesion)
        self.auditoria = auditoria

    # ---------- Salida ----------
    @staticmethod
    def a_salida(c: Cliente) -> ClienteOut:
        u = c.usuario
        return ClienteOut(
            id=c.id, usuario_id=u.id, razon_social=c.razon_social, nombre_facturacion=c.nombre_facturacion,
            email=u.email,
            clinica=c.clinica, es_red=c.es_red, telefono_celular=c.telefono_celular,
            telefono_fijo=c.telefono_fijo, tipo_documento=c.tipo_documento,
            numero_documento=c.numero_documento, nivel_prioridad=c.nivel_prioridad,
            activo=u.activo, creado_en=c.creado_en,
            direcciones=[DireccionOut(id=d.id, departamento=d.departamento, municipio=d.municipio,
                                      direccion=d.direccion, principal=d.principal, activo=d.activo)
                         for d in c.direcciones if d.activo],
        )

    def _obtener(self, cliente_id: int) -> Cliente:
        cliente = self.clientes.por_id(cliente_id)
        if not cliente:
            raise NoEncontrado("Cliente no encontrado")
        return cliente

    def _validar_unicos(self, email: str, documento: str, usuario_id=None, cliente_id=None):
        if self.usuarios.email_existe(email, usuario_id):
            raise Conflicto("Ya existe un usuario con ese correo")
        if self.clientes.documento_existe(documento, cliente_id):
            raise Conflicto("Ya existe un cliente con ese NIT/DPI")

    # ---------- Consultas ----------
    def listar(self, texto=None, activo=None, nivel=None) -> list[ClienteOut]:
        return [self.a_salida(c) for c in self.clientes.listar(texto, activo, nivel)]

    def obtener(self, cliente_id: int) -> ClienteOut:
        return self.a_salida(self._obtener(cliente_id))

    # ---------- Comandos ----------
    def registrar(self, datos: RegistroCliente) -> ClienteOut:
        """Auto-registro desde el login. El rol (doctor) y la prioridad (3) los fija el servidor."""
        datos_cliente = datos.model_dump(exclude={"direccion"})
        nuevo = ClienteCrear(**datos_cliente, nivel_prioridad=3, direcciones=[datos.direccion])
        return self.crear(nuevo, Actor(None, datos.email.lower()), accion="registro")

    def crear(self, datos: ClienteCrear, actor: Actor, accion: str = "crear") -> ClienteOut:
        self._validar_unicos(datos.email, datos.numero_documento)
        # El usuario de acceso del cliente se muestra con su razón social
        usuario = self.usuarios.agregar(Usuario(
            nombre=datos.razon_social, apellido="", email=datos.email.lower(),
            telefono=datos.telefono_celular or datos.telefono_fijo,
            password_hash=cifrar_password(datos.password), rol=ROL_CLIENTE, activo=True,
        ))
        direcciones = [Direccion(**d.model_dump()) for d in datos.direcciones]
        self._normalizar_principal(direcciones)
        cliente = self.clientes.agregar(Cliente(
            usuario_id=usuario.id, razon_social=datos.razon_social, nombre_facturacion=datos.nombre_facturacion,
            clinica=datos.clinica, es_red=datos.es_red,
            telefono_celular=datos.telefono_celular, telefono_fijo=datos.telefono_fijo,
            tipo_documento=datos.tipo_documento, numero_documento=datos.numero_documento,
            nivel_prioridad=datos.nivel_prioridad, direcciones=direcciones,
        ))
        self.sesion.commit()
        if actor.id is None and accion == "registro":
            actor = Actor(usuario.id, usuario.email)
        self.auditoria.registrar(accion, "cliente", cliente.id, actor, {
            "razon_social": datos.razon_social, "nivel_prioridad": datos.nivel_prioridad,
            "documento": f"{datos.tipo_documento} {datos.numero_documento}",
        })
        return self.obtener(cliente.id)

    def actualizar(self, cliente_id: int, datos: ClienteActualizar, actor: Actor) -> ClienteOut:
        cliente = self._obtener(cliente_id)
        self._validar_unicos(datos.email, datos.numero_documento, cliente.usuario_id, cliente.id)
        nuevos = datos.model_dump()
        nuevos["email"] = nuevos["email"].lower()
        cambios = {}
        if cliente.usuario.email != nuevos["email"]:
            cambios["email"] = [cliente.usuario.email, nuevos["email"]]
            cliente.usuario.email = nuevos["email"]
        cliente.usuario.nombre = nuevos["razon_social"]
        for campo in CAMPOS_CLIENTE:
            if getattr(cliente, campo) != nuevos[campo]:
                cambios[campo] = [getattr(cliente, campo), nuevos[campo]]
                setattr(cliente, campo, nuevos[campo])
        self.sesion.commit()
        if cambios:
            self.auditoria.registrar("editar", "cliente", cliente.id, actor, {"cambios": cambios})
        return self.obtener(cliente.id)

    def cambiar_estado(self, cliente_id: int, activo: bool, actor: Actor) -> ClienteOut:
        cliente = self._obtener(cliente_id)
        cliente.usuario.activo = activo
        self.sesion.commit()
        self.auditoria.registrar("activar" if activo else "desactivar", "cliente", cliente.id, actor)
        return self.obtener(cliente.id)

    def cambiar_password(self, cliente_id: int, password: str, actor: Actor) -> None:
        cliente = self._obtener(cliente_id)
        cliente.usuario.password_hash = cifrar_password(password)
        self.sesion.commit()
        self.auditoria.registrar("cambiar_password", "cliente", cliente.id, actor)

    # ---------- Direcciones ----------
    @staticmethod
    def _normalizar_principal(direcciones: list[Direccion], preferida: Direccion | None = None) -> None:
        """Siempre exactamente una dirección principal entre las activas."""
        activas = [d for d in direcciones if d.activo is not False]
        if not activas:
            return
        principales = [d for d in activas if d.principal]
        if preferida is not None and preferida.principal and preferida.activo is not False:
            elegida = preferida
        else:
            elegida = principales[0] if principales else activas[0]
        for d in direcciones:
            d.principal = d is elegida

    def agregar_direccion(self, cliente_id: int, datos: DireccionIn, actor: Actor) -> ClienteOut:
        cliente = self._obtener(cliente_id)
        nueva = Direccion(**datos.model_dump())
        cliente.direcciones.append(nueva)
        self._normalizar_principal(cliente.direcciones, nueva)
        self.sesion.commit()
        self.auditoria.registrar("agregar_direccion", "cliente", cliente.id, actor,
                                 {"municipio": datos.municipio, "departamento": datos.departamento})
        return self.obtener(cliente.id)

    def actualizar_direccion(self, cliente_id: int, direccion_id: int, datos: DireccionIn,
                             actor: Actor) -> ClienteOut:
        cliente = self._obtener(cliente_id)
        direccion = self.clientes.direccion_por_id(cliente_id, direccion_id)
        if not direccion or not direccion.activo:
            raise NoEncontrado("Dirección no encontrada")
        era_principal = direccion.principal
        for campo, valor in datos.model_dump().items():
            setattr(direccion, campo, valor)
        if era_principal:
            direccion.principal = True  # la principal solo cambia marcando otra como principal
        self._normalizar_principal(cliente.direcciones, direccion)
        self.sesion.commit()
        self.auditoria.registrar("editar_direccion", "cliente", cliente.id, actor, {"direccion_id": direccion_id})
        return self.obtener(cliente.id)

    def eliminar_direccion(self, cliente_id: int, direccion_id: int, actor: Actor) -> ClienteOut:
        cliente = self._obtener(cliente_id)
        direccion = self.clientes.direccion_por_id(cliente_id, direccion_id)
        if not direccion or not direccion.activo:
            raise NoEncontrado("Dirección no encontrada")
        if sum(1 for d in cliente.direcciones if d.activo) <= 1:
            raise ErrorNegocio("El cliente debe tener al menos una dirección de entrega")
        direccion.activo = False  # baja lógica: las solicitudes antiguas conservan la referencia
        direccion.principal = False
        self._normalizar_principal(cliente.direcciones)
        self.sesion.commit()
        self.auditoria.registrar("eliminar_direccion", "cliente", cliente.id, actor, {"direccion_id": direccion_id})
        return self.obtener(cliente.id)
