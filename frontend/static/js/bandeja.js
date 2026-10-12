/* ============ Mi bandeja: producción, áreas de apoyo y supervisión ============ */
const usuario = iniciarPagina(["admin", "supervisor", "ingresos", "tecnico", "qa", "facturacion", "logistica", "mensajero", "demo"]);
if (!usuario) throw new Error("sin acceso");
const esDemo = usuario.rol === "demo";
const esSupervision = ["admin", "supervisor"].includes(usuario.rol);
let datos = null, areaElegida = null, arbol = null, pasoActivo = null, modoTerminar = "terminar";
const VISTA_VALIDACION = !!window.VISTA_VALIDACION;  // tablero de validación de diseño (validaciones.html)
if (VISTA_VALIDACION && !["admin", "supervisor", "demo"].includes(usuario.rol)) { location.href = "inicio.html"; throw new Error("sin acceso"); }
const indice = new Map();  // paso_id → datos del paso (para los modales)

const ACCION = {
  iniciar: { texto: "Iniciar trabajo", clase: "verde" },
  terminar: { texto: "Terminar", clase: "verde", titulo: "Terminar trabajo" },
  aprobar: { texto: "Aprobar", clase: "verde", titulo: "Aprobar e ingresar a producción" },
  modificar: { texto: "Modificar", clase: "" },
  cancelar: { texto: "Cancelar", clase: "rojo-borde" },
  validar_rp: { texto: "Clasificar RP", clase: "verde" },
  aprobar_qa: { texto: "Aprobar", clase: "verde", titulo: "Aprobar control de calidad" },
  rechazar: { texto: "Devolver", clase: "rojo-borde" },
  facturar: { texto: "Registrar factura", clase: "verde", titulo: "Facturar y empacar" },
  recolectado: { texto: "Recolectado", clase: "verde" },
  entregado_lab: { texto: "Entregado en laboratorio", clase: "verde", titulo: "Material entregado en el laboratorio" },
  recibido_transporte: { texto: "Recibido", clase: "verde", titulo: "Material recibido por transporte" },
  entregado: { texto: "Entregado", clase: "verde", titulo: "Entregado al cliente" },
  entregado_transporte: { texto: "Entregado a transporte", clase: "verde", titulo: "Entregado a transporte" },
  cambiar_metodo: { texto: "Cambiar método", clase: "" },
  enviar_cliente: { texto: "Enviado al cliente", clase: "" },
  aprobar_diseno: { texto: "Cliente aprobó", clase: "verde", titulo: "Diseño aprobado por el cliente" },
  cambios_diseno: { texto: "Pidió cambios", clase: "rojo-borde" },
  asignar_mensajero: { texto: "Asignar mensajero", clase: "" },
  asignar: { texto: "Reasignar", clase: "" },
  prioridad: { texto: "Prioridad", clase: "" },
  hecho: { texto: "Hecho", clase: "verde" },
  no_se_pudo: { texto: "No se pudo", clase: "rojo-borde" },
};
const ES_RUTA = p => ["recolecta", "entrega"].includes(p.etapa);
const hoyTxt = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };

/* ---------- Tarjeta de un trabajo ---------- */
function tarjeta(p, { actual = false, mostrarTecnico = false } = {}) {
  indice.set(p.paso_id, p);
  const tarde = p.fecha_entrega <= hoyTxt();
  const etiquetas = [
    p.emergencia ? '<span class="badge rojo">EMERGENCIA</span>' : "",
    p.tipo_caso === "RP" ? '<span class="badge azul">Reapertura</span>' : "",
    p.fuera_catalogo ? '<span class="badge azul">Fuera de catálogo</span>' : "",
    p.manual ? '<span class="badge morado">Orden manual</span>' : "",
    p.vuelta > 1 ? `<span class="badge rojo">Retrabajo ${p.vuelta - 1}</span>` : "",
    p.pausada ? '<span class="badge naranja">En pausa</span>' : "",
    p.paralelo_con?.length ? '<span class="badge azul">En paralelo</span>' : "",
    p.modalidad === "analogo" ? '<span class="badge gris">Analógico</span>' : '<span class="badge gris">Digital</span>',
  ].join("");
  const extra = [];
  if (p.etapa === "validacion_rp") extra.push(`<div class="nota-caso"><b>${p.reapertura_tipo === "garantia" ? "Garantía" : "Modificación"}:</b> ${escapar(p.reapertura_motivo)}</div>`);
  if (p.qa_clasificacion && ["facturacion", "produccion"].includes(p.etapa)) extra.push(`<div class="linea">QA: <b>${escapar(p.qa_clasificacion)}</b></div>`);
  if (ES_RUTA(p)) {
    const transporte = p.metodo === "transporte";
    const chip = transporte ? '<span class="badge azul">Transporte</span>' : '<span class="badge gris">Mensajero</span>';
    const lugar = p.etapa === "recolecta" ? (transporte ? "Llega" : "Recoger en") : (transporte ? "Destino" : "Entregar en");
    extra.push(`<div class="linea">${chip} ${lugar}: <b>${escapar(p.direccion)}</b></div>`);
    if (p.limite && p.estado !== "recolectado") extra.push(`<div class="linea plazo ${p.vencida ? "vencido" : "ok"}">${p.vencida ? "Plazo de recolecta vencido" : "Recoger antes de"} · ${escapar(fechaHora(p.limite))}</div>`);
    if (p.estado === "recolectado") extra.push(`<div class="linea">Recolectado ${escapar(fechaHora(p.recolectado_en))}${p.vencida ? ' · <span class="plazo vencido">fuera de plazo</span>' : ""} · <b>llevar al laboratorio</b></div>`);
    if (p.guia) extra.push(`<div class="linea">Guía: <b>${escapar(p.guia)}</b></div>`);
  }
  if (p.etapa === "facturacion") extra.push(`<div class="linea">Cliente Odoo: <b>${escapar(p.cliente_odoo || "sin registrar")}</b> · ${p.credito ? '<span class="badge verde">Crédito: no pasa a Cobros</span>' : '<span class="badge gris">Contado</span>'}</div>`);
  if (p.pausada) extra.push(`<div class="aviso-pausa" style="margin:0"><b>En pausa:</b> ${escapar(p.pausa_motivo || "")}. Espera a que supervisión lo reanude.</div>`);
  if (p.paralelo_con?.length) extra.push(`<div class="linea">Al mismo tiempo en: <b>${escapar(p.paralelo_con.join(", "))}</b>. El caso avanza cuando todas terminan.</div>`);
  if (p.etapa === "validacion_diseno" && p.enviado_en) extra.push(`<div class="linea">Enviado al cliente ${escapar(fechaHora(p.enviado_en))}${p.dias ? ` · <b>${p.dias} día(s) sin respuesta</b>` : ""}</div>`);
  if (p.devolucion) extra.push(`<div class="aviso rojo" style="margin:0"><div><b>Retrabajo:</b> ${escapar(p.devolucion.replace("Devuelto por QA: ", ""))}</div></div>`);
  if (p.instrucciones) extra.push(`<div class="nota-caso">${escapar(p.instrucciones)}</div>`);
  if (ES_RUTA(p) && ["asignado", "recolectado"].includes(p.estado) && !mostrarTecnico && usuario.rol !== "mensajero") extra.push(`<div class="linea">Mensajero: <b>${escapar(p.tecnico)}</b></div>`);
  if (ES_RUTA(p) && p.telefono) extra.push(`<div class="linea">Teléfono: <a href="tel:${escapar(p.telefono)}">${escapar(p.telefono)}</a></div>`);
  if (mostrarTecnico) extra.push(`<div class="linea">Prioridad <b>${p.prioridad}</b></div>`);
  if (mostrarTecnico) extra.push(`<div class="linea">Estado: <b>${escapar(({ asignado: "Asignado", en_proceso: "En proceso", en_cola: "En cola (todos al tope)", sin_tecnico: "Sin técnico que cubra el paso", en_area: "En el área" })[p.estado] || p.estado)}</b>${p.tecnico ? ` · ${escapar(p.tecnico)}` : ""}</div>`);
  const botones = p.acciones.map(a => {
    let texto = ACCION[a].texto;
    if (a === "aprobar" && p.modalidad === "analogo") texto = "Material recibido · aprobar";
    if (a === "hecho") texto = p.etapa === "recolecta" ? "Recolectado" : "Entregado";
    if (a === "asignar_mensajero" && p.estado === "asignado") texto = "Cambiar mensajero";
    if (a === "asignar" && ["en_cola", "sin_tecnico"].includes(p.estado)) texto = "Asignar";
    if (a === "enviar_cliente" && p.estado === "enviado") texto = "Reenviar";
    if (a === "cambiar_metodo") texto = p.metodo === "transporte" ? "Cambiar a mensajero" : "Cambiar a transporte";
    if (a === "iniciar" && esDemo) texto = "Iniciar";
    return `<button class="btn ${ACCION[a].clase}" data-accion="${a}" data-paso="${p.paso_id}">${texto}</button>`;
  }).join("");
  return `<article class="trabajo ${p.emergencia ? "urgente" : ""} ${actual ? "actual" : ""}">
    <div class="cabeza"><a class="codigo-caso" href="caso.html?id=${p.solicitud_id}">${escapar(p.codigo)}</a>${etiquetas}
      <span class="fecha ${tarde ? "tarde" : ""}">Entrega ${escapar(fechaCorta(p.fecha_entrega))}</span></div>
    ${p.caja ? `<div>${etiquetaCaja(p.caja)}</div>` : ""}
    <div class="linea"><b>${escapar(p.trabajo)}</b>${p.color ? ` · ${escapar(p.color)}` : ""}</div>
    <div class="linea">Piezas <b>${escapar(p.piezas.join(", "))}</b> · ${escapar(p.paciente)} · ${escapar(p.cliente)}</div>
    ${extra.join("")}
    ${botones ? `<div class="botones">${botones}</div>` : ""}
  </article>`;
}

/* ---------- Pintar ---------- */
function pintarProduccion(pr) {
  if (!pr) { $("produccion").innerHTML = ""; return; }
  const carga = `${pr.total}${pr.max_trabajos ? ` de ${pr.max_trabajos}` : ""} asignado(s) en total`;
  const hayNormal = pr.actual || pr.siguiente || !pr.lotes.length;
  const normal = hayNormal ? `<section class="bandeja-seccion"><h2>Producción <span class="sub">${carga}</span></h2>
    <div class="produccion-grid">
      <div><div class="etiqueta-seccion">Trabajando ahora</div>${pr.actual ? tarjeta(pr.actual, { actual: true }) : '<div class="vacio-card">No tienes un trabajo en proceso.</div>'}</div>
      <div><div class="etiqueta-seccion">Siguiente</div>${pr.siguiente ? tarjeta(pr.siguiente) + (pr.actual ? '<p class="nota">Termina el trabajo actual para iniciar este.</p>' : "") : '<div class="vacio-card">No hay más trabajos asignados.</div>'}</div>
    </div>${pr.en_espera ? `<p class="nota">Después de este tienes <b>${pr.en_espera}</b> trabajo(s) más en espera. El sistema te los entrega en orden de prioridad.</p>` : ""}</section>` : "";
  // Áreas por lote: todo lo asignado a la vista y varios en proceso
  const lotes = pr.lotes.map(l => `<section class="bandeja-seccion"><h2>${escapar(l.area)} · por lote
      <span class="sub">${l.en_proceso.length} de ${l.max_simultaneos} en proceso · ${l.en_espera.length} en espera</span></h2>
    ${l.en_espera.length > 1 && l.en_espera[0].acciones.includes("iniciar") ? `<div style="margin-bottom:10px"><button class="btn verde" data-lote-iniciar="${l.area_id}">Iniciar ${Math.min(l.en_espera.length, l.max_simultaneos - l.en_proceso.length)} en orden de prioridad</button></div>` : ""}
    <div class="etiqueta-seccion">En proceso</div>
    ${l.en_proceso.length ? `<div class="trabajos" style="margin-bottom:14px">${l.en_proceso.map(p => tarjeta(p, { actual: true })).join("")}</div>` : '<div class="vacio-card" style="margin-bottom:14px">Nada en proceso.</div>'}
    <div class="etiqueta-seccion">En espera (${l.en_espera.length})</div>
    ${l.en_espera.length ? `<div class="trabajos">${l.en_espera.map(p => tarjeta(p)).join("")}</div>` : '<div class="vacio-card">Sin trabajos en espera.</div>'}
    ${l.en_espera.length && !l.en_espera[0].acciones.includes("iniciar") ? '<p class="nota">Llegaste al máximo de trabajos simultáneos: termina alguno para iniciar otro.</p>' : ""}
  </section>`).join("");
  const pausados = pr.pausados?.length ? `<section class="bandeja-seccion"><h2>En pausa <span class="sub">${pr.pausados.length} · supervisión los reanuda cuando llegue lo pendiente</span></h2>
    <div class="trabajos">${pr.pausados.map(p => tarjeta(p)).join("")}</div></section>` : "";
  $("produccion").innerHTML = normal + lotes + pausados;
}

function pintarRutas(rutas) {
  if (!rutas) { $("rutas").innerHTML = ""; return; }
  $("titulo").textContent = "Mis rutas";
  $("descripcion").textContent = "Recolectas y entregas que te asignó Logística, por prioridad.";
  const grupo = (etapa, titulo) => {
    const lista = rutas.filter(r => r.etapa === etapa);
    return `<section class="bandeja-seccion"><h2>${titulo} <span class="sub">${lista.length}</span></h2>
      ${lista.length ? `<div class="trabajos">${lista.map(p => tarjeta(p)).join("")}</div>` : '<div class="vacio-card">Nada pendiente.</div>'}</section>`;
  };
  $("rutas").innerHTML = grupo("recolecta", "Recolectas") + grupo("entrega", "Entregas");
}

function pintarAreas(areas) {
  if (!areas.length && !datos.produccion && !datos.rutas && !esSupervision) {
    $("areas").innerHTML = '<div class="vacio-card">No tienes áreas asignadas. Pide al administrador que te asigne una en Empleados.</div>';
    return;
  }
  $("areas").innerHTML = areas.map(a => {
    const detalleSupervision = (esSupervision && a.area_id === areaElegida) || (esDemo && a.tipo === "produccion");
    return `<section class="bandeja-seccion" id="area-${a.area_id}"><h2>${escapar(a.area)} <span class="sub">${a.pasos.length} caso(s)${detalleSupervision ? " · vista de supervisión" : ""}</span></h2>
      ${a.pasos.length ? `<div class="trabajos">${a.pasos.map(p => tarjeta(p, { mostrarTecnico: detalleSupervision })).join("")}</div>` : '<div class="vacio-card">Sin casos pendientes en esta área.</div>'}
    </section>`;
  }).join("");
}

function pintarSupervision(resumen) {
  if (!resumen) return;
  $("titulo").textContent = esDemo ? "Línea de producción · demostración" : "Bandeja del laboratorio";
  $("descripcion").textContent = esDemo
    ? "Perfil de demostración: puedes hacer cualquier paso de cualquier área. Toca un área para ir a sus casos."
    : "Carga de cada área. Toca un área para ver sus casos, técnicos asignados y colas.";
  $("supervision").innerHTML = `<section class="bandeja-seccion"><div class="areas-resumen">${resumen.map(a => `
    <button class="area-tile ${a.area_id === areaElegida ? "activa" : ""}" data-area="${a.area_id}">
      <span>${escapar(a.area)}</span><b>${a.activos}</b>
      <small>${a.tipo === "produccion" ? `${a.en_proceso} en proceso` : "casos en el área"}${a.en_cola ? ` · <span style="color:var(--rojo-texto)">${a.en_cola} en cola</span>` : ""}${a.sin_tecnico ? ` · <span style="color:var(--rojo-texto)">${a.sin_tecnico} sin técnico</span>` : ""}</small>
    </button>`).join("")}</div></section>`;
}

let pestanaValidacion = "por_enviar";
const RANGOS_VALIDACION = [["hoy", "Hoy"], ["1", "1 día"], ["2-3", "2–3 días"], ["4+", "4 días o más"]];
function pintarValidaciones(v) {
  indice.clear();
  const pestañas = [["por_enviar", "Por enviar", v.por_enviar.length], ...RANGOS_VALIDACION.map(([k, t]) => [k, `Enviados · ${t}`, v.rangos[k]])];
  if (!pestañas.some(p => p[0] === pestanaValidacion)) pestanaValidacion = "por_enviar";
  const lista = pestanaValidacion === "por_enviar" ? v.por_enviar : v.enviados.filter(e => e.rango === pestanaValidacion);
  $("supervision").innerHTML = `<div class="pestanas" id="pestanasValidacion">${pestañas.map(([k, t, n]) =>
    `<button class="${k === pestanaValidacion ? "activa" : ""} ${k === "4+" && n ? "alerta" : ""}" data-pv="${k}">${t} <b>${n}</b></button>`).join("")}</div>`;
  $("areas").innerHTML = `<section class="bandeja-seccion">${lista.length ? `<div class="trabajos">${lista.map(p => tarjeta(p)).join("")}</div>`
    : `<div class="vacio-card">${pestanaValidacion === "por_enviar" ? "No hay diseños por enviar al cliente." : "No hay diseños enviados en este rango."}</div>`}</section>`;
}

async function cargar() {
  $("errorBandeja").hidden = true;
  if (VISTA_VALIDACION) {
    try { pintarValidaciones(await api("GET", "/validaciones-diseno")); }
    catch (error) { mostrarErrores($("errorBandeja"), error); }
    return;
  }
  try {
    datos = await api("GET", "/bandeja" + (areaElegida ? `?area_id=${areaElegida}` : ""));
    indice.clear();
    pintarSupervision(datos.supervision);
    pintarProduccion(datos.produccion);
    pintarRutas(datos.rutas);
    pintarAreas(datos.areas);
  } catch (error) { mostrarErrores($("errorBandeja"), error); $("areas").innerHTML = ""; }
}

$("supervision").addEventListener("click", e => {
  const pv = e.target.closest("[data-pv]");
  if (pv) { pestanaValidacion = pv.dataset.pv; return cargar(); }
  const b = e.target.closest("[data-area]");
  if (!b) return;
  if (esDemo) return document.getElementById(`area-${b.dataset.area}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  areaElegida = Number(b.dataset.area) === areaElegida ? null : Number(b.dataset.area);
  cargar();
});
$("btnActualizar").onclick = cargar;
refrescoAutomatico(cargar, 30000);

/* ---------- Acciones ---------- */
async function ejecutar(boton, promesa, mensaje) {
  if (boton) boton.disabled = true;
  try { await promesa(); toast(mensaje); document.querySelectorAll("dialog[open]").forEach(d => d.close()); await cargar(); }
  catch (error) { toast(error.message, true); throw error; }
  finally { if (boton) boton.disabled = false; }
}

document.addEventListener("click", async e => {
  const b = e.target.closest("[data-accion]");
  if (!b) return;
  const accion = b.dataset.accion;
  pasoActivo = indice.get(Number(b.dataset.paso));
  if (!pasoActivo) return;
  const id = pasoActivo.paso_id;
  if (accion === "recolectado") return ejecutar(b, () => api("POST", `/pasos/${id}/recolectado`), `${pasoActivo.codigo}: material recolectado, llévalo al laboratorio`).catch(() => {});
  if (accion === "iniciar") return ejecutar(b, () => api("POST", `/pasos/${id}/iniciar`), `${pasoActivo.codigo} iniciado`).catch(() => {});
  if (accion === "rechazar") return abrirRechazo();
  if (accion === "cambios_diseno") return abrirRechazo(true);
  if (accion === "enviar_cliente") {
    modoTerminar = "enviar";
    $("tituloTerminar").textContent = `Diseño enviado · ${pasoActivo.codigo}`;
    $("textoTerminar").textContent = "Registra que enviaste el diseño al cliente (WhatsApp, correo…). Queda en espera de su respuesta en el tablero de validación.";
    ["campoFactura", "campoCaja", "campoReceptor", "campoGuia", "campoTransporte"].forEach(c => $(c).hidden = true);
    $("tNota").value = ""; $("errorTerminar").hidden = true;
    return $("modalTerminar").showModal();
  }
  if (accion === "validar_rp") return abrirValidacion();
  if (accion === "modificar") return abrirModificacion();
  if (accion === "cancelar" || accion === "no_se_pudo" || accion === "cambiar_metodo") {
    modoMotivo = accion;
    const nuevo = pasoActivo.metodo === "transporte" ? "mensajero" : "transporte";
    $("tituloCancelar").textContent = accion === "cancelar" ? `Cancelar ${pasoActivo.codigo}`
      : accion === "cambiar_metodo" ? `${pasoActivo.etapa === "recolecta" ? "Recolecta" : "Entrega"} por ${nuevo} · ${pasoActivo.codigo}`
      : `${pasoActivo.etapa === "recolecta" ? "Recolecta" : "Entrega"} no realizada · ${pasoActivo.codigo}`;
    $("btnMotivo").textContent = { cancelar: "Cancelar caso", no_se_pudo: "Regresar a Logística", cambiar_metodo: `Cambiar a ${nuevo}` }[accion];
    $("btnMotivo").className = accion === "cambiar_metodo" ? "btn verde" : "btn rojo-borde";
    $("cMotivo").placeholder = { cancelar: "Ej. Solicitud duplicada", no_se_pudo: "Ej. Clínica cerrada, nadie para recibir",
                                 cambiar_metodo: nuevo === "transporte" ? "Ej. El cliente lo enviará por Guatex" : "Ej. El cliente pidió que lo recojamos" }[accion];
    $("cMotivo").value = ""; $("errorCancelar").hidden = true; return $("modalCancelar").showModal();
  }
  if (accion === "asignar" || accion === "asignar_mensajero") return abrirAsignacion(accion);
  if (accion === "prioridad") return abrirPrioridad();
  modoTerminar = "terminar";
  // terminar / aprobar / aprobar_qa / facturar / recolectado / entregado
  $("tituloTerminar").textContent = `${ACCION[accion].titulo} · ${pasoActivo.codigo}`;
  $("textoTerminar").textContent = accion === "aprobar"
    ? (pasoActivo.modalidad === "analogo" ? "Confirmas que el material llegó y el caso está completo. Entra a producción y se asigna automáticamente." : "El caso entra a producción y se asigna automáticamente al primer paso.")
    : accion === "terminar" ? "El caso pasa al siguiente paso de su flujo." : "";
  if (accion === "hecho") $("tituloTerminar").textContent = `${pasoActivo.etapa === "recolecta" ? "Recolectado" : "Entregado"} · ${pasoActivo.codigo}`;
  $("campoFactura").hidden = accion !== "facturar";
  $("campoCaja").hidden = accion !== "aprobar";
  if (accion === "aprobar") prepararCaja();
  $("campoReceptor").hidden = !(accion === "entregado" || (accion === "hecho" && pasoActivo.etapa === "entrega"));
  $("tReceptor").value = "";
  const conGuia = ["entregado_transporte", "recibido_transporte"].includes(accion);
  $("campoGuia").hidden = !conGuia;
  $("campoTransporte").hidden = accion !== "entregado_transporte";
  $("reqGuia").hidden = accion !== "entregado_transporte";
  $("tGuia").value = ""; $("tTransporte").value = "";
  if (accion === "entregado_transporte") $("textoTerminar").textContent = "Registra la guía del envío. Con esto el caso queda entregado y finalizado.";
  if (accion === "recibido_transporte") $("textoTerminar").textContent = "Confirma que el material llegó por transporte. El caso pasa a Ingresos.";
  if (accion === "aprobar_diseno") $("textoTerminar").textContent = "El cliente aprobó el diseño. El caso continúa a impresión o fresado.";
  if (accion === "entregado_lab") $("textoTerminar").textContent = "El material ya está en el laboratorio. El caso pasa a Ingresos.";
  $("tFactura").value = pasoActivo.factura_numero || ""; $("tNota").value = ""; $("errorTerminar").hidden = true;
  $("modalTerminar").showModal();
});

$("formTerminar").onsubmit = async e => {
  e.preventDefault();
  if (!$("campoFactura").hidden && !$("tFactura").value.trim()) return mostrarErrores($("errorTerminar"), new Error("Ingresa el número de factura"));
  const cajaColor = document.querySelector("[name=cajaColor]:checked")?.value;
  if (!$("campoCaja").hidden && (!cajaColor || !$("tCajaNumero").value.trim())) return mostrarErrores($("errorTerminar"), new Error("Elige el color y escribe el número de caja"));
  if (!$("campoReceptor").hidden && $("tReceptor").value.trim().length < 2) return mostrarErrores($("errorTerminar"), new Error("Escribe el nombre de quien recibe"));
  if (!$("reqGuia").hidden && !$("tGuia").value.trim()) return mostrarErrores($("errorTerminar"), new Error("Ingresa el número de guía para finalizar el caso"));
  const cuerpo = { nota: $("tNota").value.trim() || null, factura_numero: $("campoFactura").hidden ? null : $("tFactura").value.trim(),
                   receptor: $("campoReceptor").hidden ? null : $("tReceptor").value.trim(),
                   caja_color_id: $("campoCaja").hidden ? null : Number(cajaColor),
                   caja_numero: $("campoCaja").hidden ? null : $("tCajaNumero").value.trim(),
                   guia: $("campoGuia").hidden ? null : ($("tGuia").value.trim() || null),
                   transporte: $("campoTransporte").hidden ? null : ($("tTransporte").value.trim() || null) };
  if (modoTerminar === "enviar")
    return ejecutar($("btnTerminar"), () => api("POST", `/pasos/${pasoActivo.paso_id}/enviar-cliente`, { nota: $("tNota").value.trim() || null }),
      `${pasoActivo.codigo}: diseño enviado al cliente`).catch(err => mostrarErrores($("errorTerminar"), err));
  const aprobado = !$("campoCaja").hidden ? { ...pasoActivo } : null;
  await ejecutar($("btnTerminar"), () => api("POST", `/pasos/${pasoActivo.paso_id}/terminar`, cuerpo), `${pasoActivo.codigo} avanzó al siguiente paso`)
    .then(() => { if (aprobado) ofrecerImpresion(aprobado); })
    .catch(err => mostrarErrores($("errorTerminar"), err));
};

let modoRechazo = "qa";
function abrirRechazo(diseno = false) {
  modoRechazo = diseno ? "diseno" : "qa";
  $("tituloRechazar").textContent = diseno ? `Cambios del cliente · ${pasoActivo.codigo}` : "Devolver a producción";
  $("campoModo").hidden = diseno;
  $("btnRechazar").textContent = diseno ? "Regresar a diseño" : "Devolver";
  $("rMotivo").placeholder = diseno ? "Ej. El doctor pide cerrar el contacto con la 12" : "Ej. Contacto abierto con la pieza 12";
  $("errorRechazar").hidden = true; $("rMotivo").value = "";
  const previos = pasoActivo.pasos_previos;
  $("rPaso").innerHTML = previos.map((p, i) => `<option value="${p.id}">${escapar(p.area)}${i === 0 && previos.length > 1 && modoRechazo !== "diseno" ? " (todo el trabajo)" : ""}</option>`).join("");
  $("rPaso").value = previos.at(-1)?.id || "";  // por defecto, el paso anterior
  document.querySelector("[name=rModo][value=desde]").checked = true;
  resumenRechazo();
  $("modalRechazar").showModal();
}
$("formRechazar").onsubmit = async e => {
  e.preventDefault();
  if ($("rMotivo").value.trim().length < 3) return mostrarErrores($("errorRechazar"), new Error("Describe el motivo"));
  const modo = document.querySelector("[name=rModo]:checked").value;
  if (modoRechazo === "diseno")
    return ejecutar(null, () => api("POST", `/pasos/${pasoActivo.paso_id}/cambios-diseno`, { volver_a_paso_id: Number($("rPaso").value) || null, motivo: $("rMotivo").value.trim() }),
      `${pasoActivo.codigo} regresó a diseño`).catch(err => mostrarErrores($("errorRechazar"), err));
  await ejecutar(null, () => api("POST", `/pasos/${pasoActivo.paso_id}/rechazar`, { volver_a_paso_id: Number($("rPaso").value), modo, motivo: $("rMotivo").value.trim() }),
    `${pasoActivo.codigo} regresó a producción`).catch(err => mostrarErrores($("errorRechazar"), err));
};

async function obtenerArbol() { if (!arbol) arbol = await api("GET", "/config/arbol"); return arbol; }

async function abrirValidacion() {
  $("errorValidar").hidden = true; $("vObs").value = "";
  document.querySelectorAll("[name=clasif]").forEach(r => r.checked = false);
  $("tituloValidar").textContent = `Validar ${pasoActivo.codigo}`;
  $("vMotivoDoctor").innerHTML = `<b>El doctor pide ${pasoActivo.reapertura_tipo === "garantia" ? "garantía" : "una modificación"}:</b> ${escapar(pasoActivo.reapertura_motivo)}`;
  const a = await obtenerArbol();
  $("vMotivo").innerHTML = '<option value="">Selecciona</option>' + a.motivos_rp.map(m => `<option value="${m.id}">${escapar(m.nombre)}</option>`).join("");
  $("modalValidar").showModal();
}
$("formValidar").onsubmit = async e => {
  e.preventDefault();
  const clasificacion = document.querySelector("[name=clasif]:checked")?.value;
  if (!clasificacion || !$("vMotivo").value) return mostrarErrores($("errorValidar"), new Error("Elige la clasificación y el motivo"));
  await ejecutar(null, () => api("POST", `/pasos/${pasoActivo.paso_id}/validar-rp`, { clasificacion, motivo_id: Number($("vMotivo").value), observacion: $("vObs").value.trim() || null }),
    `${pasoActivo.codigo} validado`).catch(err => mostrarErrores($("errorValidar"), err));
};

let modoMotivo = "cancelar";
$("formCancelar").onsubmit = async e => {
  e.preventDefault();
  if ($("cMotivo").value.trim().length < 3) return mostrarErrores($("errorCancelar"), new Error("Describe el motivo"));
  const motivo = $("cMotivo").value.trim();
  const llamada = modoMotivo === "cambiar_metodo"
    ? () => api("POST", `/pasos/${pasoActivo.paso_id}/metodo`, { metodo: pasoActivo.metodo === "transporte" ? "mensajero" : "transporte", motivo })
    : () => api("POST", `/pasos/${pasoActivo.paso_id}/${modoMotivo === "cancelar" ? "cancelar" : "no-se-pudo"}`, { motivo });
  await ejecutar(null, llamada, { cancelar: `${pasoActivo.codigo} cancelado`, no_se_pudo: `${pasoActivo.codigo} regresó a Logística`,
                                  cambiar_metodo: `${pasoActivo.codigo}: método actualizado` }[modoMotivo])
    .catch(err => mostrarErrores($("errorCancelar"), err));
};

/* ---------- Asignar mensajero (Logística) o reasignar técnico (supervisión) ---------- */
async function abrirAsignacion(accion) {
  $("errorAsignar").hidden = true; $("aNota").value = "";
  const mensajero = accion === "asignar_mensajero";
  $("tituloAsignar").textContent = `${mensajero ? "Mensajero para" : "Reasignar"} ${pasoActivo.codigo}`;
  $("etiquetaAsignar").textContent = mensajero ? "Mensajero" : `Técnico para ${pasoActivo.area}`;
  $("ayudaAsignar").textContent = mensajero
    ? `${pasoActivo.etapa === "recolecta" ? "Recoger en" : "Entregar en"}: ${pasoActivo.direccion}`
    : "Primero quienes tienen el área y el tipo de trabajo; después otros técnicos como apoyo. La asignación manual no respeta el máximo de trabajos.";
  try {
    const lista = await api("GET", `/pasos/${pasoActivo.paso_id}/candidatos`);
    if (!lista.length) return toast(mensajero ? "No hay mensajeros activos. Créalos en Empleados con el rol Mensajero." : "No hay técnicos activos", true);
    $("aPersona").innerHTML = lista.map(c => `<option value="${c.id}">${escapar(c.nombre)} · ${c.carga}${c.max_trabajos ? "/" + c.max_trabajos : ""} ${mensajero ? "pendiente(s)" : "trabajo(s)"}${!mensajero && !c.cubre ? " · apoyo" : ""}${c.estado_texto && !c.recibe_trabajo ? ` · ${escapar(c.estado_texto)}` : ""}</option>`).join("");
    $("modalAsignar").showModal();
  } catch (error) { toast(error.message, true); }
}
$("formAsignar").onsubmit = async e => {
  e.preventDefault();
  await ejecutar(null, () => api("POST", `/pasos/${pasoActivo.paso_id}/asignar`, { usuario_id: Number($("aPersona").value), nota: $("aNota").value.trim() || null }),
    `${pasoActivo.codigo} asignado`).catch(err => mostrarErrores($("errorAsignar"), err));
};

/* ---------- Prioridad (supervisión) ---------- */
function abrirPrioridad() {
  $("errorPrioridad").hidden = true; $("pMotivo").value = "";
  $("tituloPrioridad").textContent = `Prioridad de ${pasoActivo.codigo}`;
  $("pValor").value = pasoActivo.prioridad;
  $("modalPrioridad").showModal();
}
$("formPrioridad").onsubmit = async e => {
  e.preventDefault();
  if ($("pMotivo").value.trim().length < 3) return mostrarErrores($("errorPrioridad"), new Error("Escribe el motivo"));
  await ejecutar(null, () => api("POST", `/solicitudes/${pasoActivo.solicitud_id}/prioridad`, { prioridad: Number($("pValor").value), motivo: $("pMotivo").value.trim() }),
    "Prioridad actualizada").catch(err => mostrarErrores($("errorPrioridad"), err));
};


/* ---------- Ingresos: modificar (solo catálogo) ---------- */
let odontoModificar = null;
const opcion = (lista, vacio) => `<option value="">${vacio}</option>` + lista.map(x => `<option value="${x.id}">${escapar(x.nombre)}</option>`).join("");
function cascada(sel = {}) {
  const tipo = arbol.tipos.find(t => t.id == $("mTipo").value);
  if ("tipo" in sel) { $("mMaterial").innerHTML = opcion(tipo ? tipo.materiales : [], tipo ? "Selecciona" : "Primero el tipo"); if (sel.material) $("mMaterial").value = sel.material; }
  const material = tipo?.materiales.find(m => m.id == $("mMaterial").value);
  if ("tipo" in sel || "material" in sel) {
    $("mUnidad").innerHTML = opcion(material ? material.unidades : [], material ? "Selecciona" : "Primero el material");
    if (sel.unidad) $("mUnidad").value = sel.unidad;
    const guias = material ? material.guias : [];
    $("mGuia").innerHTML = material && !guias.length ? '<option value="">No aplica</option>' : opcion(guias, material ? "Selecciona" : "Primero el material");
    $("mGuia").disabled = material && !guias.length;
    if (sel.guia) $("mGuia").value = sel.guia;
  }
  const guia = material?.guias.find(g => g.id == $("mGuia").value);
  $("mColor").innerHTML = material && !material.guias.length ? '<option value="">No aplica</option>' : opcion(guia ? guia.colores : [], guia ? "Selecciona" : "Primero la guía");
  $("mColor").disabled = material && !material.guias.length;
  if (sel.color) $("mColor").value = sel.color;
}
$("mTipo").onchange = () => cascada({ tipo: 1 });
$("mMaterial").onchange = () => cascada({ material: 1 });
$("mGuia").onchange = () => cascada({});

async function abrirModificacion() {
  $("errorModificar").hidden = true; $("mNota").value = "";
  $("tituloModificar").textContent = `Modificar ${pasoActivo.codigo}`;
  try {
    const [a, caso] = await Promise.all([obtenerArbol(), api("GET", `/solicitudes/${pasoActivo.solicitud_id}`)]);
    $("mTipo").innerHTML = opcion(a.tipos, "Selecciona");
    $("mTipo").value = caso.tipo_trabajo.id || "";
    cascada({ tipo: 1, material: caso.material.id, unidad: caso.unidad.id, guia: caso.guia_color?.id, color: caso.color?.id });
    const fdc = [["Tipo", caso.tipo_trabajo], ["Material", caso.material], ["Unidades", caso.unidad], ["Guía", caso.guia_color], ["Color", caso.color]]
      .filter(([, v]) => v?.fuera_catalogo).map(([k, v]) => `${k}: <b>${escapar(v.nombre)}</b>`);
    $("mFdc").hidden = !fdc.length;
    $("mFdc").innerHTML = `<div>El doctor escribió fuera de catálogo → ${fdc.join(" · ")}. Elige la opción del catálogo que corresponde.</div>`;
    $("mFecha").value = caso.fecha_entrega;
    $("mEntrega").value = caso.entrega_metodo || "mensajero";
    odontoModificar = crearOdontograma($("mOdontograma"));
    odontoModificar.poner(caso.piezas);
    $("modalModificar").showModal();
  } catch (error) { toast(error.message, true); }
}
$("formModificar").onsubmit = async e => {
  e.preventDefault();
  const id = v => v ? { id: Number(v) } : null;
  const sinColor = $("mGuia").disabled;
  if (!$("mTipo").value || !$("mMaterial").value || !$("mUnidad").value || (!sinColor && (!$("mGuia").value || !$("mColor").value)))
    return mostrarErrores($("errorModificar"), new Error("Completa tipo, material, unidades, guía y color del catálogo"));
  if (!odontoModificar.lista().length) return mostrarErrores($("errorModificar"), new Error("Selecciona al menos una pieza"));
  if ($("mNota").value.trim().length < 3) return mostrarErrores($("errorModificar"), new Error("Explica qué se corrigió"));
  const cuerpo = {
    tipo_trabajo: id($("mTipo").value), material: id($("mMaterial").value), unidad: id($("mUnidad").value),
    guia_color: sinColor ? null : id($("mGuia").value), color: sinColor ? null : id($("mColor").value),
    piezas: odontoModificar.lista(), fecha_entrega: $("mFecha").value, entrega_metodo: $("mEntrega").value, nota: $("mNota").value.trim(),
  };
  await ejecutar(null, () => api("PUT", `/pasos/${pasoActivo.paso_id}/modificar`, cuerpo), `${pasoActivo.codigo} modificado. Ahora puedes aprobarlo`)
    .catch(err => mostrarErrores($("errorModificar"), err));
};

document.querySelectorAll("[data-cerrar]").forEach(b => b.onclick = () => b.closest("dialog").close());
cargar();

/* ---------- Caja al aprobar en Ingresos e impresión de la orden ---------- */
async function prepararCaja() {
  $("tCajaNumero").value = "";
  const a = await obtenerArbol();
  $("tCajaColor").innerHTML = a.colores_caja.length
    ? a.colores_caja.map(c => `<label><input type="radio" name="cajaColor" value="${c.id}"><i style="background:${COLORES_CAJA[c.nombre.toLowerCase()] || "#8a8a8a"}"></i>${escapar(c.nombre)}</label>`).join("")
    : '<span class="nota">No hay colores de caja activos. El administrador los crea en Catálogos → Colores de caja.</span>';
}
let porImprimir = null;
function ofrecerImpresion(p) {
  porImprimir = p;
  $("tituloImprimir").textContent = `${p.codigo} ingresado`;
  $("textoImprimir").textContent = "El caso entró a producción. Imprime la orden para colocarla en la caja.";
  $("modalImprimir").showModal();
}
$("btnImprimir").onclick = () => {
  const p = porImprimir;
  $("modalImprimir").close();
  abrirPdf(`/solicitudes/${p.solicitud_id}/orden.pdf`, `Orden ${p.codigo}.pdf`).catch(e => toast(e.message, true));
};

/* ---------- Iniciar varios en un área por lote ---------- */
document.addEventListener("click", async e => {
  const b = e.target.closest("[data-lote-iniciar]");
  if (!b) return;
  const lote = datos.produccion.lotes.find(l => l.area_id === Number(b.dataset.loteIniciar));
  const cupo = lote.max_simultaneos - lote.en_proceso.length;
  const elegidos = lote.en_espera.slice(0, cupo);
  b.disabled = true;
  let ok = 0;
  for (const p of elegidos) {
    try { await api("POST", `/pasos/${p.paso_id}/iniciar`); ok++; } catch (error) { toast(error.message, true); break; }
  }
  toast(`${ok} trabajo(s) iniciados en ${lote.area}`);
  cargar();
});

/* Resumen de lo que se repetirá al devolver */
function resumenRechazo() {
  const previos = pasoActivo.pasos_previos, i = previos.findIndex(p => p.id === Number($("rPaso").value));
  const modo = document.querySelector("[name=rModo]:checked")?.value;
  if (modoRechazo === "diseno") { $("rResumen").textContent = ""; return; }
  const areas = i < 0 ? [] : (modo === "solo" ? [previos[i]] : previos.slice(i)).map(p => p.area);
  $("rResumen").textContent = areas.length ? `Se repetirá: ${[...areas, "QA"].join(" → ")}` : "";
}
$("rPaso").addEventListener("change", resumenRechazo);
document.querySelectorAll("[name=rModo]").forEach(r => r.addEventListener("change", resumenRechazo));
