/* ============ Formulario de caso nuevo (CN) ============ */
const usuario = iniciarPagina(["doctor", ...ROLES_CAPTURA]);
if (!usuario) throw new Error("sin acceso");
const esPersonal = usuario.rol !== "doctor";
const FDC = "__fdc__";

let arbol = { tipos: [] }, perfil = null, clienteId = null, colorNoAplica = false;
let todos = { materiales: [], unidades: [], guias: [] };  // para cuando el nivel anterior es "fuera de catálogo"

/* ---------- Componentes ---------- */
const odontograma = crearOdontograma($("odontograma"), { alCambiar: () => actualizar() });
const dirEntrega = crearDireccion($("dirEntrega"), "ent", () => actualizar());
const dirRecolecta = crearDireccion($("dirRecolecta"), "rec", () => actualizar());
const stl = crearAdjuntos({ zona: $("dropStl"), input: $("inputStl"), lista: $("listaStl"), soloStl: true,
  alCambiar: () => { if (stl?.hayStl()) { $("dropStl").classList.remove("error"); $("errStl").hidden = true; } actualizar(); } });
const otros = crearAdjuntos({ zona: $("dropOtros"), input: $("inputOtros"), lista: $("listaOtros"), alCambiar: () => actualizar() });
const fecha = crearFechaEntrega({ alCambiar: () => actualizar() });
const logistica = crearLogistica(() => actualizar());
const modalidad = crearModalidad(() => { fecha.recalcular(modalidad.valor(), $("emergencia").checked); actualizar(); });
prepararEmergencia(on => fecha.recalcular(modalidad.valor(), on));
$("recolectaIgual").onchange = () => { $("bloqueRecolecta").hidden = $("recolectaIgual").checked; actualizar(); };

/* ---------- Catálogos dependientes: Tipo → Material → (Unidad, Guía) → Color ---------- */
const unicos = lista => [...new Map(lista.map(x => [x.id, x])).values()].sort((a, b) => a.nombre.localeCompare(b.nombre));
const buscar = (lista, id) => lista.find(x => String(x.id) === String(id));

function llenar(sel, items, vacio) {
  sel.innerHTML = `<option value="">${vacio}</option>` + items.map(x => `<option value="${x.id}">${escapar(x.nombre)}</option>`).join("")
    + `<option value="${FDC}">Fuera de catálogo…</option>`;
  sel.disabled = false;
  alternarFdc(sel);
}
function bloquear(sel, texto) { sel.innerHTML = `<option value="">${texto}</option>`; sel.disabled = true; alternarFdc(sel); }
function alternarFdc(sel) {
  const entrada = $(sel.id + "Fdc"), on = sel.value === FDC;
  entrada.hidden = !on;
  if (!on) entrada.value = "";
}
/** Valor para la API: {id} del catálogo o {fuera_catalogo: texto}. */
function seleccion(id) {
  const sel = $(id);
  if (sel.value === FDC) { const t = $(id + "Fdc").value.trim(); return t ? { fuera_catalogo: t } : null; }
  return sel.value ? { id: Number(sel.value) } : null;
}
function textoDe(id) {
  const sel = $(id);
  if (sel.value === FDC) return $(id + "Fdc").value.trim() ? `${$(id + "Fdc").value.trim()} (fuera de catálogo)` : "";
  return sel.value ? sel.options[sel.selectedIndex].text : "";
}

const tipoActual = () => buscar(arbol.tipos, $("tipo").value);
const materialActual = () => { const t = tipoActual(); return t ? buscar(t.materiales, $("material").value) : buscar(todos.materiales, $("material").value); };
const guiaActual = () => { const m = materialActual(); return buscar(m ? m.guias : todos.guias, $("guia").value); };

$("tipo").onchange = () => {
  alternarFdc($("tipo"));
  const t = tipoActual();
  if (!$("tipo").value) bloquear($("material"), "Primero elige el tipo");
  else llenar($("material"), t ? t.materiales : todos.materiales, "Selecciona el material");
  modalidad.limitar(t ? t.modalidades : null);
  $("material").onchange();
};
$("material").onchange = () => {
  alternarFdc($("material"));
  const m = materialActual();
  colorNoAplica = false;
  if (!$("material").value) { bloquear($("unidad"), "Primero elige el material"); bloquear($("guia"), "Primero elige el material"); }
  else {
    llenar($("unidad"), m ? m.unidades : todos.unidades, "Selecciona");
    const guias = m ? m.guias : todos.guias;
    if (m && !guias.length) { bloquear($("guia"), "No aplica"); colorNoAplica = true; }
    else llenar($("guia"), guias, "Selecciona la guía");
  }
  $("guia").onchange();
};
$("guia").onchange = () => {
  alternarFdc($("guia"));
  const g = guiaActual();
  if (colorNoAplica) bloquear($("color"), "No aplica");
  else if (!$("guia").value) bloquear($("color"), "Primero elige la guía");
  else if ($("guia").value === FDC) { llenar($("color"), [], "Selecciona"); $("color").value = FDC; alternarFdc($("color")); }
  else llenar($("color"), g ? g.colores : [], "Selecciona el color");
  actualizar();
};
$("unidad").onchange = () => { alternarFdc($("unidad")); actualizar(); };
$("color").onchange = () => { alternarFdc($("color")); actualizar(); };

/* ---------- Cliente (personal del laboratorio) ---------- */
async function cargarPerfil() {
  perfil = await api("GET", "/solicitudes/perfil" + (esPersonal ? `?cliente_id=${clienteId}` : ""));
  dirEntrega.poner(perfil.direcciones);
  dirRecolecta.poner(perfil.direcciones);
  $("listaDoctores").innerHTML = perfil.doctores.map(d => `<option value="${escapar(d)}">`).join("");
  $("doctorTratante").placeholder = `${perfil.titular} (titular de la cuenta)`;
  $("ayudaDoctor").textContent = perfil.es_red
    ? "Clínica en red: indica qué doctor atiende al paciente. Vacío = titular de la cuenta."
    : "Si lo dejas vacío se usa el titular de la cuenta.";
  actualizar();
}

async function prepararClientes() {
  $("bloqueCliente").hidden = false;
  $("rClienteT").hidden = $("rCliente").hidden = false;
  const clientes = await api("GET", "/solicitudes/clientes");
  const etiqueta = c => c.clinica ? `${c.razon_social} · ${c.clinica}` : c.razon_social;
  $("listaClientes").innerHTML = clientes.map(c => `<option value="${escapar(etiqueta(c))}">`).join("");
  $("buscarCliente").addEventListener("change", async () => {
    const c = clientes.find(x => etiqueta(x) === $("buscarCliente").value);
    clienteId = c ? c.id : null;
    $("campoCliente").classList.toggle("error", !c);
    if (c) { await cargarPerfil().catch(e => toast(e.message, true)); }
    else { perfil = null; dirEntrega.poner([]); dirRecolecta.poner([]); }
    actualizar();
  });
  dirEntrega.poner([]); dirRecolecta.poner([]);
}

/* ---------- Resumen y validación ---------- */
function recolectaPendiente(mostrar) {
  if (modalidad.valor() !== "analogo" || logistica.recolecta() === "transporte" || $("recolectaIgual").checked) return null;
  return dirRecolecta.validar(mostrar);
}
function estado() {
  return [
    ...(esPersonal ? [["Cliente", !!clienteId]] : []),
    ["Modalidad y archivos", modalidad.valor() === "digital" ? stl.hayStl() && !stl.subiendo() : !recolectaPendiente(false)],
    ["Paciente", $("paciente").value.trim().length >= 2],
    ["Tipo, material y unidades", !!(seleccion("tipo") && seleccion("material") && seleccion("unidad"))],
    ["Guía y color", colorNoAplica || !!(seleccion("guia") && seleccion("color"))],
    ["Piezas dentales", odontograma.lista().length > 0],
    ["Fecha de entrega", !fecha.validar(false)],
    ["Dirección de entrega", !dirEntrega.validar(false)],
  ];
}
/* ---------- Color por pieza ---------- */
const coloresElegidos = {};  // pieza → color_id (se conserva al volver a dibujar)
let claveColores = "";
function colorPorPiezaDisponible() {
  const g = $("guia").value && $("guia").value !== FDC ? guiaActual() : null;
  return !colorNoAplica && g && g.colores.length && odontograma.lista().length > 1 && $("color").value && $("color").value !== FDC;
}
function pintarColoresPieza() {
  const disponible = colorPorPiezaDisponible();
  $("bloqueColorPieza").hidden = !disponible;
  if (!disponible) { $("colorPorPieza").checked = false; $("coloresPieza").hidden = true; claveColores = ""; return; }
  $("coloresPieza").hidden = !$("colorPorPieza").checked;
  const piezas = odontograma.lista(), g = guiaActual();
  const clave = `${g.id}|${piezas.join(",")}|${$("color").value}|${$("colorPorPieza").checked}`;
  if (clave === claveColores) return;
  claveColores = clave;
  $("coloresPieza").innerHTML = piezas.map(n => {
    const actual = coloresElegidos[n] && g.colores.some(c => c.id == coloresElegidos[n]) ? coloresElegidos[n] : $("color").value;
    return `<label>${n}<select data-pieza="${n}">${g.colores.map(c => `<option value="${c.id}" ${c.id == actual ? "selected" : ""}>${escapar(c.nombre)}</option>`).join("")}</select></label>`;
  }).join("");
}
$("colorPorPieza").addEventListener("change", () => { claveColores = ""; pintarColoresPieza(); actualizar(); });
$("coloresPieza").addEventListener("change", e => { const s = e.target.closest("[data-pieza]"); if (s) coloresElegidos[s.dataset.pieza] = Number(s.value); actualizar(); });
function valorColoresPieza() {
  if (!$("colorPorPieza").checked || $("bloqueColorPieza").hidden) return [];
  return [...document.querySelectorAll("#coloresPieza [data-pieza]")].map(s => ({ pieza: Number(s.dataset.pieza), color_id: Number(s.value) }));
}

function actualizar() {
  pintarColoresPieza();
  const hayFdc = ["tipo", "material", "unidad", "guia", "color"].some(id => $(id).value === FDC);
  $("avisoFdc").hidden = !hayFdc;
  if (esPersonal) $("rCliente").textContent = perfil?.razon_social || "—";
  $("rModalidad").textContent = modalidad.valor() === "digital" ? "Digital (STL)" : "Analógico";
  $("rPaciente").textContent = $("paciente").value.trim() || "—";
  $("rDoctor").textContent = $("doctorTratante").value.trim() || perfil?.titular || "—";
  $("rTipo").textContent = textoDe("tipo") || "—";
  $("rMaterial").textContent = textoDe("material") || "—";
  $("rUnidad").textContent = textoDe("unidad") || "—";
  const porPieza = valorColoresPieza();
  $("rColor").textContent = colorNoAplica ? "No aplica" : (textoDe("color") ? `${textoDe("guia")} · ${textoDe("color")}` : "—")
    + (porPieza.length ? ` · por pieza: ${[...document.querySelectorAll("#coloresPieza [data-pieza]")].map(s => `${s.dataset.pieza} ${s.options[s.selectedIndex].text}`).join(", ")}` : "");
  $("rPiezas").textContent = odontograma.lista().join(", ") || "—";
  $("rFecha").textContent = fecha.valor() ? fechaCorta(fecha.valor()) : "—";
  $("rDireccion").textContent = dirEntrega.texto();
  $("rLogistica").textContent = logistica.texto(modalidad.valor() === "analogo");
  $("rPrioridad").innerHTML = $("emergencia").checked ? '<span class="badge rojo">EMERGENCIA</span>' : '<span class="badge gris">Según tu cuenta</span>';
  $("checklist").innerHTML = estado().map(([t, ok]) => `<li class="${ok ? "ok" : ""}">${t}</li>`).join("");
}
$("form").addEventListener("input", e => { e.target.closest(".campo")?.classList.remove("error"); actualizar(); });

function validarTodo() {
  let primero = null;
  const anotar = el => { if (el && !primero) primero = el; };
  const marcar = (id, ok) => { $(id).classList.toggle("error", !ok); if (!ok) anotar($(id)); };
  if (esPersonal) marcar("campoCliente", !!clienteId);
  if (modalidad.valor() === "digital") {
    const ok = stl.hayStl();
    $("dropStl").classList.toggle("error", !ok); $("errStl").hidden = ok;
    if (!ok) anotar($("dropStl"));
  } else anotar(recolectaPendiente(true));
  marcar("campoPaciente", $("paciente").value.trim().length >= 2);
  marcar("campoTipo", !!seleccion("tipo"));
  marcar("campoMaterial", !!seleccion("material"));
  marcar("campoUnidad", !!seleccion("unidad"));
  if (!colorNoAplica) { marcar("campoGuia", !!seleccion("guia")); marcar("campoColor", !!seleccion("color")); }
  anotar(odontograma.validar(true));
  anotar(fecha.validar(true));
  anotar(dirEntrega.validar(true));
  return primero;
}

/* ---------- Envío ---------- */
$("form").onsubmit = async e => {
  e.preventDefault();
  $("errorEnvio").hidden = true;
  const error = validarTodo();
  if (error) return irAlError(error);
  if (stl.subiendo() || otros.subiendo()) return toast("Espera a que terminen de subir los archivos", true);
  const analogo = modalidad.valor() === "analogo";
  const datos = {
    cliente_id: esPersonal ? clienteId : null,
    motivo_manual: esPersonal ? ($("motivoManual").value.trim() || null) : null,
    modalidad: modalidad.valor(),
    paciente: $("paciente").value.trim(),
    referencia_clinica: $("referencia").value.trim() || null,
    doctor_tratante: $("doctorTratante").value.trim() || null,
    tipo_trabajo: seleccion("tipo"), material: seleccion("material"), unidad: seleccion("unidad"),
    guia_color: colorNoAplica ? null : seleccion("guia"), color: colorNoAplica ? null : seleccion("color"),
    colores_pieza: colorNoAplica ? [] : valorColoresPieza(),
    piezas: odontograma.lista(),
    fecha_entrega: fecha.valor(),
    emergencia: $("emergencia").checked,
    direccion_entrega: dirEntrega.valor(),
    direccion_recolecta: !analogo || logistica.recolecta() === "transporte" ? null : ($("recolectaIgual").checked ? { tipo: "misma_que_entrega" } : dirRecolecta.valor()),
    recolecta_metodo: analogo ? logistica.recolecta() : null,
    entrega_metodo: logistica.entrega(),
    instrucciones: $("instrucciones").value.trim() || null,
    archivo_ids: [...(analogo ? [] : stl.ids()), ...otros.ids()],
  };
  $("btnEnviar").disabled = true; $("btnEnviar").textContent = "Enviando…";
  try {
    const caso = await api("POST", "/solicitudes", datos);
    location.href = `caso.html?id=${caso.id}&nuevo=1`;
  } catch (err) {
    mostrarErrores($("errorEnvio"), err);
    toast("No se pudo enviar la solicitud", true);
    $("btnEnviar").disabled = false; $("btnEnviar").textContent = "Enviar solicitud";
  }
};
$("btnCancelar").onclick = () => { if (confirm("¿Descartar la solicitud?")) location.href = esPersonal ? "casos.html" : "inicio.html"; };

/* ---------- Inicio ---------- */
(async () => {
  bloquear($("tipo"), "Cargando catálogo…");
  bloquear($("material"), "Primero elige el tipo");
  bloquear($("unidad"), "Primero elige el material");
  bloquear($("guia"), "Primero elige el material");
  bloquear($("color"), "Primero elige la guía");
  actualizar();
  try {
    arbol = await api("GET", "/config/arbol");
    const materiales = arbol.tipos.flatMap(t => t.materiales);
    todos = { materiales: unicos(materiales), unidades: unicos(materiales.flatMap(m => m.unidades)),
              guias: unicos(materiales.flatMap(m => m.guias)) };
    llenar($("tipo"), arbol.tipos, "Selecciona el tipo");
    if (esPersonal) await prepararClientes(); else await cargarPerfil();
  } catch (err) { mostrarErrores($("errorEnvio"), err); }
  fecha.recalcular(modalidad.valor(), false);
})();
