/* ============ Detalle de un caso (CN o RP) ============ */
const usuario = iniciarPagina();
if (!usuario) throw new Error("sin acceso");
const parametros = new URLSearchParams(location.search);
const casoId = Number(parametros.get("id"));
const ESTADOS = {
  validacion_diseno: "Validación de diseño", diseno_enviado: "Diseño enviado al cliente",
  pendiente_recolecta: "Pendiente de recolecta", material_en_camino: "Material en camino", espera_transporte: "Esperando transporte", validacion_qa: "Validación de QA", recibida: "Recibida",
  en_produccion: "En producción", control_calidad: "Control de calidad", facturacion: "Facturación y empaque",
  listo_entrega: "Listo para entrega", en_ruta: "En ruta de entrega", entregada: "Entregada", cancelada: "Cancelada",
};  // referencia de estados (el texto llega desde la API)
const COLOR_ESTADO = { entregada: "verde", cancelada: "rojo", validacion_qa: "azul", pendiente_recolecta: "azul", material_en_camino: "azul", espera_transporte: "azul" };
const fechaLarga = s => new Date(s + "T12:00:00").toLocaleDateString("es-GT", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
const dato = (etiqueta, valor, clase = "") => `<div class="${clase}"><span>${etiqueta}</span><b>${valor}</b></div>`;
const valorCat = v => !v ? "No aplica" : escapar(v.nombre) + (v.fuera_catalogo ? ' <span class="badge azul">fuera de catálogo</span>' : "");
const tamano = b => b >= 1048576 ? (b / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(b / 1024)) + " KB";
let caso = null;

function pintar() {
  const c = caso;
  document.title = `${c.codigo} · DENTAL TRACK`;
  $("titulo").innerHTML = `<span class="codigo-caso">${escapar(c.codigo)}</span>`;
  $("subtitulo").textContent = `${c.paciente} · ${c.trabajo}`;
  $("etiquetas").innerHTML = [
    `<span class="badge ${c.tipo_caso === "RP" ? "azul" : "blanco"}">${c.tipo_caso === "RP" ? "Reapertura" : "Caso nuevo"}</span>`,
    `<span class="badge ${COLOR_ESTADO[c.estado] || "gris"}">${escapar(c.estado_texto)}</span>`,
    c.emergencia ? '<span class="badge rojo">EMERGENCIA</span>' : "",
    c.fuera_catalogo ? '<span class="badge azul">Fuera de catálogo</span>' : "",
    c.pausada ? '<span class="badge naranja">En pausa</span>' : "",
    etiquetaManual(c, usuario.rol),
    c.prioridad ? `<span class="badge gris">Prioridad ${c.prioridad}</span>` : "",
  ].join("");

  if (c.caja) $("etiquetas").insertAdjacentHTML("beforeend", etiquetaCaja(c.caja));
  $("btnOrden").hidden = !(c.caja && usuario.rol !== "doctor");
  if (c.factura_numero && usuario.rol !== "doctor") $("etiquetas").insertAdjacentHTML("beforeend", `<span class="badge gris">Factura ${escapar(c.factura_numero)}</span>`);
  if (c.tipo_caso === "RP") {
    $("bloqueRp").hidden = false;
    $("datosRp").innerHTML =
      dato("Caso original", `<a href="caso.html?id=${c.caso_origen_id}" class="codigo-caso">${escapar(c.caso_origen)}</a>`)
      + dato("Solicitada como", c.reapertura_tipo === "garantia" ? "Garantía" : "Modificación o cambio")
      + dato("Validación de QA", c.qa_clasificacion ? `${escapar(c.qa_clasificacion)}<br><small style="color:var(--texto-3)">${escapar(c.qa_motivo || "")}${c.qa_observacion ? " · " + escapar(c.qa_observacion) : ""}</small>` : '<span class="badge azul">Pendiente</span>')
      + dato("Motivo del doctor", escapar(c.reapertura_motivo), "ancho");
  }
  $("datos").innerHTML =
    (usuario.rol !== "doctor" ? dato("Cliente", escapar(c.cliente) + (c.clinica ? `<br><small style="color:var(--texto-3)">${escapar(c.clinica)}</small>` : "")) : "")
    + dato("Paciente", escapar(c.paciente))
    + dato("Doctor tratante", escapar(c.doctor_tratante || "Titular de la cuenta"))
    + dato("Referencia de la clínica", escapar(c.referencia_clinica || "—"))
    + dato("Modalidad", c.modalidad === "digital" ? "Digital (STL)" : (c.recolecta_metodo === "transporte" ? "Analógico · llega por transporte" : "Analógico · recolecta con mensajero"))
    + dato("Tipo de trabajo", valorCat(c.tipo_trabajo))
    + dato("Material", valorCat(c.material))
    + dato("Unidades", valorCat(c.unidad))
    + dato("Color", c.color ? `${valorCat(c.guia_color)} · ${valorCat(c.color)}${c.colores_pieza.length ? " (base)" : ""}` : "No aplica")
    + (c.colores_pieza.length ? dato("Color por pieza", c.colores_pieza.map(x => `${x.pieza}: ${escapar(x.color)}`).join(" · "), "ancho") : "")
    + dato("Piezas", `<span class="piezas-lista">${c.piezas.map(p => `<span>${p}</span>`).join("")}</span>`, "ancho")
    + dato("Instrucciones", escapar(c.instrucciones || "Sin instrucciones"), "ancho")
    + dato("Registrado", `${escapar(fechaHora(c.creado_en))}${c.creado_por ? ` por ${escapar(c.creado_por)}` : ""}`, "ancho")
    + (c.manual && c.manual_motivo ? dato("Motivo de la orden manual", escapar(c.manual_motivo), "ancho") : "");
  const dir = d => `${escapar(d.direccion)}<br><small style="color:var(--texto-3)">${escapar(d.municipio)}, ${escapar(d.departamento)}</small>`;
  $("entrega").innerHTML = dato("Fecha de entrega", escapar(fechaLarga(c.fecha_entrega)))
    + dato("Dirección de entrega", dir(c.entrega))
    + (c.recolecta ? dato("Dirección de recolecta", dir(c.recolecta)) : "")
    + dato("Sale por", c.entrega_metodo === "transporte"
      ? "Transporte" + (c.entrega_transporte ? ` · ${escapar(c.entrega_transporte)}` : "") + (c.entrega_guia ? ` · guía <b>${escapar(c.entrega_guia)}</b>` : "")
      : "Mensajero del laboratorio")
    + (c.recolecta_guia ? dato("Guía de llegada", escapar(c.recolecta_guia)) : "");
  $("archivos").innerHTML = c.archivos.length ? c.archivos.map(a => `
    <div class="archivo"><span class="tipo ${a.tipo === "stl" ? "stl" : ""}">${escapar(a.nombre.split(".").pop().toUpperCase())}</span>
      <span class="nombre-archivo">${escapar(a.nombre)}</span><span class="peso">${tamano(a.tamano)}</span>
      <a href="#" data-archivo="${escapar(a.id)}" data-nombre="${escapar(a.nombre)}">Descargar</a></div>`).join("")
    : '<div class="vacio" style="padding:14px">Sin archivos adjuntos.</div>';

  // Acciones: reabrir solo desde un caso entregado
  const puedeCapturar = usuario.rol === "doctor" || ROLES_CAPTURA.includes(usuario.rol);
  $("acciones").innerHTML = c.puede_reabrir && puedeCapturar
    ? `<a class="btn verde" style="width:100%" href="reapertura.html?caso=${c.id}">Reabrir caso (RP)</a>
       <p class="nota">Para garantía o modificación. Pasa primero por QA, que define si aplica garantía o cobro.</p>`
    : `<p class="nota" style="margin:0">${escapar(c.motivo_no_reabrir || "Este caso no se puede reabrir")}.</p>`;
  $("formPrioridad").hidden = !(["admin", "supervisor"].includes(usuario.rol) && !["entregada", "cancelada"].includes(c.estado));
  $("nuevaPrioridad").value = c.prioridad || 3;
  $("formCancelar").hidden = !(["admin", "supervisor"].includes(usuario.rol) && !["entregada", "cancelada"].includes(c.estado));
  const supervisa = ["admin", "supervisor"].includes(usuario.rol) && !["entregada", "cancelada"].includes(c.estado);
  $("formPausa").hidden = !(supervisa && !c.pausada);
  $("formReanudar").hidden = !(supervisa && c.pausada);
  $("fechaReanudar").value = "";
  $("avisoPausa").hidden = !c.pausada;
  $("avisoPausa").innerHTML = c.pausada ? `<b>Caso en pausa</b> desde ${escapar(fechaHora(c.pausada_en))}: ${escapar(c.pausa_motivo || "")}`
    + (usuario.rol === "doctor" ? "<br><small>El laboratorio continuará cuando reciba lo pendiente.</small>" : "") : "";
  $("bloquePausas").hidden = !c.pausas.length;
  $("pausas").innerHTML = c.pausas.map(p => `<div class="item"><span class="nombre">${escapar(p.motivo)}<small>${escapar(fechaHora(p.pausado_en))}${p.pausado_por ? ` · ${escapar(p.pausado_por)}` : ""}${p.areas ? ` · ${escapar(p.areas)}` : ""}</small>
      ${p.reanudado_en ? `<small>Reanudado ${escapar(fechaHora(p.reanudado_en))} · ${p.horas_laborales ?? 0} h laborales${p.nota_reanudar ? ` · ${escapar(p.nota_reanudar)}` : ""}</small>` : ""}</span>
      <span class="badge ${p.reanudado_en ? "gris" : "naranja"}">${p.reanudado_en ? "Reanudado" : "En pausa"}</span></div>`).join("");
  // Recorrido: pasos del flujo de este caso
  const activos = ["en_area", "en_cola", "sin_tecnico", "asignado", "en_proceso", "recolectado", "enviado"];
  const TEXTO_PASO = { enviado: "Enviado al cliente", en_area: "En el área", en_cola: "En cola", sin_tecnico: "Sin técnico", asignado: "Asignado", en_proceso: "En proceso", recolectado: "Recolectado · en camino", terminado: "Hecho", pendiente: "Pendiente" };
  $("bloqueRecorrido").hidden = !c.recorrido.length;
  $("recorrido").innerHTML = c.recorrido.map((p, i) => `
    <li class="${p.estado === "terminado" ? "hecho" : activos.includes(p.estado) ? "ahora" : ""}"><span class="n">${i + 1}</span>
      <span><b>${escapar(p.area)}</b> <small style="color:var(--texto-3)">${escapar(p.etapa_texto)}${p.vuelta > 1 ? " · retrabajo" : ""}${p.grupo && c.recorrido.some(x => x !== p && x.grupo === p.grupo) ? " · en paralelo" : ""}</small></span>
      <span class="quien">${escapar(TEXTO_PASO[p.estado] || p.estado)}${p.tecnico || p.atendido_por ? ` · ${escapar(p.atendido_por || p.tecnico)}` : ""}${p.receptor ? ` · recibió ${escapar(p.receptor)}` : ""}</span></li>`).join("");
  $("bloqueReaperturas").hidden = !c.reaperturas.length;
  $("reaperturas").innerHTML = c.reaperturas.map(r => `
    <a class="item" href="caso.html?id=${r.id}" style="text-decoration:none;color:inherit">
      <span class="nombre codigo-caso">${escapar(r.codigo)}<small>${escapar(fechaHora(r.creado_en))}</small></span>
      <span class="badge ${COLOR_ESTADO[r.estado] || "gris"}">${escapar(r.estado_texto)}</span></a>`).join("");
  $("historial").innerHTML = [...c.historial].reverse().map(h => `
    <li><b>${escapar(h.estado_texto)}</b>${h.nota ? ` · ${escapar(h.nota)}` : ""}
      <small>${escapar(fechaHora(h.fecha))}${h.usuario ? ` · ${escapar(h.usuario)}` : ""}</small></li>`).join("");
  $("contenidoCaso").hidden = false;
}

async function cargar() {
  try { caso = await api("GET", `/solicitudes/${casoId}`); pintar(); }
  catch (error) { $("titulo").textContent = "Caso no disponible"; mostrarErrores($("errorCaso"), error); }
}

$("archivos").addEventListener("click", async e => {
  const a = e.target.closest("[data-archivo]");
  if (!a) return;
  e.preventDefault();
  a.textContent = "Descargando…";
  try { await descargarArchivo(`/solicitudes/${casoId}/archivos/${a.dataset.archivo}`, a.dataset.nombre); }
  catch (error) { toast(error.message, true); }
  a.textContent = "Descargar";
});

$("btnOrden").onclick = () => abrirPdf(`/solicitudes/${casoId}/orden.pdf`, `Orden ${caso.codigo}.pdf`).catch(e => toast(e.message, true));

$("formPrioridad").onsubmit = async e => {
  e.preventDefault();
  const motivo = $("motivoPrioridad").value.trim();
  if (motivo.length < 3) return toast("Escribe el motivo del cambio", true);
  try { caso = await api("POST", `/solicitudes/${casoId}/prioridad`, { prioridad: Number($("nuevaPrioridad").value), motivo }); $("motivoPrioridad").value = ""; toast("Prioridad actualizada"); pintar(); }
  catch (error) { toast(error.message, true); }
};

$("formPausa").onsubmit = async e => {
  e.preventDefault();
  const motivo = $("motivoPausa").value.trim();
  if (motivo.length < 3) return toast("Escribe el motivo de la pausa", true);
  try { caso = await api("POST", `/solicitudes/${casoId}/pausar`, { motivo }); $("motivoPausa").value = ""; toast("Caso en pausa"); pintar(); }
  catch (error) { toast(error.message, true); }
};

$("formReanudar").onsubmit = async e => {
  e.preventDefault();
  try {
    caso = await api("POST", `/solicitudes/${casoId}/reanudar`, { nota: $("notaReanudar").value.trim() || null, fecha_entrega: $("fechaReanudar").value || null });
    $("notaReanudar").value = ""; toast("Caso reanudado"); pintar();
  } catch (error) { toast(error.message, true); }
};

$("formCancelar").onsubmit = async e => {
  e.preventDefault();
  const motivo = $("motivoCancelar").value.trim();
  if (motivo.length < 3) return toast("Escribe el motivo de la cancelación", true);
  if (!confirm(`¿Cancelar ${caso.codigo}? Se retira de todas las bandejas.`)) return;
  try { caso = await api("POST", `/solicitudes/${casoId}/cancelar`, { motivo }); $("motivoCancelar").value = ""; toast("Caso cancelado"); pintar(); }
  catch (error) { toast(error.message, true); }
};

if (parametros.get("nuevo")) {
  cargar().then(() => {
    if (!caso) return;
    $("avisoNuevo").hidden = false;
    $("avisoNuevo").innerHTML = "<div>" + (caso.tipo_caso === "RP"
      ? `Reapertura <b>${escapar(caso.codigo)}</b> enviada. QA la revisará para definir si aplica garantía o cobro.`
      : `Solicitud <b>${escapar(caso.codigo)}</b> enviada. ${caso.modalidad === "analogo" ? (caso.recolecta_metodo === "transporte" ? "Envía el material por transporte: Logística registrará su llegada." : "Un mensajero pasará por el material en las próximas 2 horas laborales.") : "El laboratorio ya recibió tus archivos."}`) + "</div>";
    history.replaceState(null, "", `caso.html?id=${casoId}`);
  });
} else cargar();
