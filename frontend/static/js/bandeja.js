/* ============ Mi bandeja: producción, áreas de apoyo y supervisión ============ */
const usuario = iniciarPagina(["admin", "supervisor", "ingresos", "tecnico", "qa", "facturacion", "logistica", "mensajero"]);
if (!usuario) throw new Error("sin acceso");
const esSupervision = ["admin", "supervisor"].includes(usuario.rol);
let datos = null, areaElegida = null, arbol = null, pasoActivo = null;
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
  recolectado: { texto: "Recolectado", clase: "verde", titulo: "Material recolectado" },
  entregado: { texto: "Entregado", clase: "verde", titulo: "Entregado al cliente" },
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
    p.vuelta > 1 ? `<span class="badge rojo">Retrabajo ${p.vuelta - 1}</span>` : "",
    p.modalidad === "analogo" ? '<span class="badge gris">Analógico</span>' : '<span class="badge gris">Digital</span>',
  ].join("");
  const extra = [];
  if (p.etapa === "validacion_rp") extra.push(`<div class="nota-caso"><b>${p.reapertura_tipo === "garantia" ? "Garantía" : "Modificación"}:</b> ${escapar(p.reapertura_motivo)}</div>`);
  if (p.qa_clasificacion && ["facturacion", "produccion"].includes(p.etapa)) extra.push(`<div class="linea">QA: <b>${escapar(p.qa_clasificacion)}</b></div>`);
  if (["recolecta", "entrega"].includes(p.etapa)) extra.push(`<div class="linea">${p.etapa === "recolecta" ? "Recoger en" : "Entregar en"}: <b>${escapar(p.direccion)}</b></div>`);
  if (p.instrucciones) extra.push(`<div class="nota-caso">${escapar(p.instrucciones)}</div>`);
  if (ES_RUTA(p) && p.estado === "asignado" && !mostrarTecnico && usuario.rol !== "mensajero") extra.push(`<div class="linea">Mensajero: <b>${escapar(p.tecnico)}</b></div>`);
  if (ES_RUTA(p) && p.telefono) extra.push(`<div class="linea">Teléfono: <a href="tel:${escapar(p.telefono)}">${escapar(p.telefono)}</a></div>`);
  if (mostrarTecnico) extra.push(`<div class="linea">Prioridad <b>${p.prioridad}</b></div>`);
  if (mostrarTecnico) extra.push(`<div class="linea">Estado: <b>${escapar(({ asignado: "Asignado", en_proceso: "En proceso", en_cola: "En cola (todos al tope)", sin_tecnico: "Sin técnico que cubra el paso", en_area: "En el área" })[p.estado] || p.estado)}</b>${p.tecnico ? ` · ${escapar(p.tecnico)}` : ""}</div>`);
  const botones = p.acciones.map(a => {
    let texto = ACCION[a].texto;
    if (a === "aprobar" && p.modalidad === "analogo") texto = "Material recibido · aprobar";
    if (a === "hecho") texto = p.etapa === "recolecta" ? "Recolectado" : "Entregado";
    if (a === "asignar_mensajero" && p.estado === "asignado") texto = "Cambiar mensajero";
    if (a === "asignar" && ["en_cola", "sin_tecnico"].includes(p.estado)) texto = "Asignar";
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
  const carga = `${pr.total}${pr.max_trabajos ? ` de ${pr.max_trabajos}` : ""} asignado(s)`;
  const espera = pr.asignados.length ? `<div class="bandeja-seccion"><div class="etiqueta-seccion">En espera (${pr.asignados.length}) · el sistema te los entrega en este orden</div>
    <div class="espera">${pr.asignados.map(p => `<a href="caso.html?id=${p.solicitud_id}"><b class="codigo-caso">${escapar(p.codigo)}</b>
      ${p.emergencia ? '<span class="badge rojo">EMERGENCIA</span>' : ""}<span>${escapar(p.area)} · ${escapar(p.trabajo)}</span>
      <span class="fecha">Entrega ${escapar(fechaCorta(p.fecha_entrega))}</span></a>`).join("")}</div></div>` : "";
  $("produccion").innerHTML = `<section class="bandeja-seccion"><h2>Producción <span class="sub">${carga}</span></h2>
    <div class="produccion-grid">
      <div><div class="etiqueta-seccion">Trabajando ahora</div>${pr.actual ? tarjeta(pr.actual, { actual: true }) : '<div class="vacio-card">No tienes un trabajo en proceso.</div>'}</div>
      <div><div class="etiqueta-seccion">Siguiente</div>${pr.siguiente ? tarjeta(pr.siguiente) + (pr.actual ? '<p class="nota">Termina el trabajo actual para iniciar este.</p>' : "") : '<div class="vacio-card">No hay más trabajos asignados.</div>'}</div>
    </div></section>${espera}`;
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
    const detalleSupervision = esSupervision && a.area_id === areaElegida;
    return `<section class="bandeja-seccion"><h2>${escapar(a.area)} <span class="sub">${a.pasos.length} caso(s)${detalleSupervision ? " · vista de supervisión" : ""}</span></h2>
      ${a.pasos.length ? `<div class="trabajos">${a.pasos.map(p => tarjeta(p, { mostrarTecnico: detalleSupervision })).join("")}</div>` : '<div class="vacio-card">Sin casos pendientes en esta área.</div>'}
    </section>`;
  }).join("");
}

function pintarSupervision(resumen) {
  if (!resumen) return;
  $("titulo").textContent = "Bandeja del laboratorio";
  $("descripcion").textContent = "Carga de cada área. Toca un área para ver sus casos, técnicos asignados y colas.";
  $("supervision").innerHTML = `<section class="bandeja-seccion"><div class="areas-resumen">${resumen.map(a => `
    <button class="area-tile ${a.area_id === areaElegida ? "activa" : ""}" data-area="${a.area_id}">
      <span>${escapar(a.area)}</span><b>${a.activos}</b>
      <small>${a.tipo === "produccion" ? `${a.en_proceso} en proceso` : "casos en el área"}${a.en_cola ? ` · <span style="color:var(--rojo-texto)">${a.en_cola} en cola</span>` : ""}${a.sin_tecnico ? ` · <span style="color:var(--rojo-texto)">${a.sin_tecnico} sin técnico</span>` : ""}</small>
    </button>`).join("")}</div></section>`;
}

async function cargar() {
  $("errorBandeja").hidden = true;
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
  const b = e.target.closest("[data-area]");
  if (!b) return;
  areaElegida = Number(b.dataset.area) === areaElegida ? null : Number(b.dataset.area);
  cargar();
});
$("btnActualizar").onclick = cargar;
setInterval(() => { if (!document.querySelector("dialog[open]")) cargar(); }, 60000);

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
  if (accion === "iniciar") return ejecutar(b, () => api("POST", `/pasos/${id}/iniciar`), `${pasoActivo.codigo} iniciado`).catch(() => {});
  if (accion === "rechazar") return abrirRechazo();
  if (accion === "validar_rp") return abrirValidacion();
  if (accion === "modificar") return abrirModificacion();
  if (accion === "cancelar" || accion === "no_se_pudo") {
    modoMotivo = accion;
    $("tituloCancelar").textContent = accion === "cancelar" ? `Cancelar ${pasoActivo.codigo}` : `${pasoActivo.etapa === "recolecta" ? "Recolecta" : "Entrega"} no realizada · ${pasoActivo.codigo}`;
    $("btnMotivo").textContent = accion === "cancelar" ? "Cancelar caso" : "Regresar a Logística";
    $("cMotivo").placeholder = accion === "cancelar" ? "Ej. Solicitud duplicada" : "Ej. Clínica cerrada, nadie para recibir";
    $("cMotivo").value = ""; $("errorCancelar").hidden = true; return $("modalCancelar").showModal();
  }
  if (accion === "asignar" || accion === "asignar_mensajero") return abrirAsignacion(accion);
  if (accion === "prioridad") return abrirPrioridad();
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
  $("tFactura").value = pasoActivo.factura_numero || ""; $("tNota").value = ""; $("errorTerminar").hidden = true;
  $("modalTerminar").showModal();
});

$("formTerminar").onsubmit = async e => {
  e.preventDefault();
  if (!$("campoFactura").hidden && !$("tFactura").value.trim()) return mostrarErrores($("errorTerminar"), new Error("Ingresa el número de factura"));
  const cajaColor = document.querySelector("[name=cajaColor]:checked")?.value;
  if (!$("campoCaja").hidden && (!cajaColor || !$("tCajaNumero").value.trim())) return mostrarErrores($("errorTerminar"), new Error("Elige el color y escribe el número de caja"));
  if (!$("campoReceptor").hidden && $("tReceptor").value.trim().length < 2) return mostrarErrores($("errorTerminar"), new Error("Escribe el nombre de quien recibe"));
  const cuerpo = { nota: $("tNota").value.trim() || null, factura_numero: $("campoFactura").hidden ? null : $("tFactura").value.trim(),
                   receptor: $("campoReceptor").hidden ? null : $("tReceptor").value.trim(),
                   caja_color_id: $("campoCaja").hidden ? null : Number(cajaColor),
                   caja_numero: $("campoCaja").hidden ? null : $("tCajaNumero").value.trim() };
  const aprobado = !$("campoCaja").hidden ? { ...pasoActivo } : null;
  await ejecutar($("btnTerminar"), () => api("POST", `/pasos/${pasoActivo.paso_id}/terminar`, cuerpo), `${pasoActivo.codigo} avanzó al siguiente paso`)
    .then(() => { if (aprobado) ofrecerImpresion(aprobado); })
    .catch(err => mostrarErrores($("errorTerminar"), err));
};

function abrirRechazo() {
  $("errorRechazar").hidden = true; $("rMotivo").value = "";
  $("rPaso").innerHTML = pasoActivo.pasos_previos.map(p => `<option value="${p.id}">${escapar(p.area)}</option>`).join("");
  $("rPaso").value = pasoActivo.pasos_previos.at(-1)?.id || "";  // por defecto, el paso anterior
  $("modalRechazar").showModal();
}
$("formRechazar").onsubmit = async e => {
  e.preventDefault();
  if ($("rMotivo").value.trim().length < 3) return mostrarErrores($("errorRechazar"), new Error("Describe el motivo"));
  await ejecutar(null, () => api("POST", `/pasos/${pasoActivo.paso_id}/rechazar`, { volver_a_paso_id: Number($("rPaso").value), motivo: $("rMotivo").value.trim() }),
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
  const ruta = modoMotivo === "cancelar" ? "cancelar" : "no-se-pudo";
  await ejecutar(null, () => api("POST", `/pasos/${pasoActivo.paso_id}/${ruta}`, { motivo: $("cMotivo").value.trim() }),
    modoMotivo === "cancelar" ? `${pasoActivo.codigo} cancelado` : `${pasoActivo.codigo} regresó a Logística`)
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
    $("aPersona").innerHTML = lista.map(c => `<option value="${c.id}">${escapar(c.nombre)} · ${c.carga}${c.max_trabajos ? "/" + c.max_trabajos : ""} ${mensajero ? "pendiente(s)" : "trabajo(s)"}${!mensajero && !c.cubre ? " · apoyo" : ""}</option>`).join("");
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
    piezas: odontoModificar.lista(), fecha_entrega: $("mFecha").value, nota: $("mNota").value.trim(),
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
