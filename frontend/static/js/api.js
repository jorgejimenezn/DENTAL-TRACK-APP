/* ============ Cliente de la API y utilidades comunes ============ */
const API = (window.API_URL || "").replace(/\/$/, "");
const CLAVE_SESION = "dentaltrack_sesion";

const Sesion = {
  obtener() {
    try { return JSON.parse(localStorage.getItem(CLAVE_SESION)); } catch { return null; }
  },
  guardar(datos) {
    try { localStorage.setItem(CLAVE_SESION, JSON.stringify(datos)); } catch { /* navegador sin almacenamiento */ }
  },
  cerrar() {
    try { localStorage.removeItem(CLAVE_SESION); } catch { /* nada */ }
    location.href = "login.html";
  },
};

/** Convierte cualquier error de la API en un texto (o lista) legible. */
function mensajesDeError(detalle) {
  if (!detalle) return ["Ocurrió un error inesperado"];
  if (typeof detalle === "string") return [detalle];
  if (Array.isArray(detalle)) {
    return detalle.map(e => (e.campo ? `${ETIQUETAS[e.campo] || e.campo}: ` : "") + (e.mensaje || e.msg || "Dato no válido"));
  }
  return [JSON.stringify(detalle)];
}

const ETIQUETAS = {
  nombre: "Nombre", apellido: "Apellido", razon_social: "Razón social", nombre_facturacion: "Nombre de facturación",
  telefono: "Teléfono", email: "Correo", password: "Contraseña",
  telefono_celular: "Celular", telefono_fijo: "Teléfono fijo", numero_documento: "Documento",
  tipo_documento: "Tipo de documento", nivel_prioridad: "Nivel", clinica: "Clínica",
  direcciones: "Direcciones", departamento: "Departamento", municipio: "Municipio",
  direccion: "Dirección", rol: "Rol", area_ids: "Áreas",
};

class ErrorApi extends Error {
  constructor(status, detalle) {
    const mensajes = mensajesDeError(detalle);
    super(mensajes.join(" · "));
    this.status = status;
    this.mensajes = mensajes;
  }
}

/** Llamada a la API con el token de la sesión. */
async function api(metodo, ruta, cuerpo) {
  const sesion = Sesion.obtener();
  const opciones = { method: metodo, headers: {} };
  if (sesion?.token) opciones.headers.Authorization = "Bearer " + sesion.token;
  if (cuerpo !== undefined) {
    opciones.headers["Content-Type"] = "application/json";
    opciones.body = JSON.stringify(cuerpo);
  }
  let respuesta;
  try {
    respuesta = await fetch(API + ruta, opciones);
  } catch {
    throw new ErrorApi(0, "No se pudo conectar con la API. Revisa tu conexión.");
  }
  if (respuesta.status === 401 && ruta !== "/auth/login") {
    Sesion.cerrar();
    throw new ErrorApi(401, "Tu sesión expiró");
  }
  if (respuesta.status === 204) return null;
  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) throw new ErrorApi(respuesta.status, datos.detail);
  return datos;
}

/* ---------- Utilidades de interfaz ---------- */
const $ = id => document.getElementById(id);

function escapar(texto) {
  return String(texto ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function toast(texto, esError = false) {
  let t = $("toast");
  if (!t) { t = document.createElement("div"); t.id = "toast"; t.className = "toast"; document.body.appendChild(t); }
  t.textContent = texto;
  t.classList.toggle("rojo", esError);
  t.classList.add("ver");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("ver"), 3500);
}

function mostrarErrores(contenedor, error) {
  const mensajes = error instanceof ErrorApi ? error.mensajes : [error.message || String(error)];
  contenedor.hidden = false;
  contenedor.innerHTML = mensajes.length === 1
    ? escapar(mensajes[0])
    : "Revisa lo siguiente:<ul>" + mensajes.map(m => `<li>${escapar(m)}</li>`).join("") + "</ul>";
  contenedor.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function fechaHora(valor) {
  if (!valor) return "—";
  const d = new Date(valor);
  return d.toLocaleString("es-GT", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

const NOMBRES_ROL = {
  admin: "Administrador", ingresos: "Ingresos", tecnico: "Técnico", qa: "Control de calidad",
  facturacion: "Facturación", logistica: "Logística", doctor: "Doctor",
};

function debounce(fn, ms = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}
