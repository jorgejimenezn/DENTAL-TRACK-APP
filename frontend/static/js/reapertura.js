/* ============ Formulario de reapertura (RP) de un caso entregado ============ */
const usuario = iniciarPagina(["doctor", ...ROLES_CAPTURA]);
if (!usuario) throw new Error("sin acceso");
const origenId = Number(new URLSearchParams(location.search).get("caso"));
const AYUDA_TIPO = {
  garantia: "El trabajo presenta un defecto (fractura, desajuste, color distinto al solicitado…). QA confirma si aplica garantía.",
  modificacion: "Quieres un cambio sobre el trabajo entregado (forma, color, contactos…). Normalmente tiene costo; QA lo confirma.",
};
let origen = null, tipoReapertura = "garantia", odontograma, dirEntrega, dirRecolecta, stl, otros, fecha, modalidad;

$("volver").href = $("btnCancelar").href = `caso.html?id=${origenId}`;

function elegirTipo(t) {
  tipoReapertura = t;
  $("tipoReapertura").querySelectorAll("button").forEach(b => b.classList.toggle("activo", b.dataset.t === t));
  $("ayudaTipo").textContent = AYUDA_TIPO[t];
  actualizar();
}
$("tipoReapertura").querySelectorAll("button").forEach(b => b.onclick = () => elegirTipo(b.dataset.t));

function recolectaPendiente(mostrar) {
  if (modalidad.valor() !== "analogo" || $("recolectaIgual").checked) return null;
  return dirRecolecta.validar(mostrar);
}
function estado() {
  return [
    ["Motivo", $("motivo").value.trim().length >= 5],
    ["Piezas", odontograma.lista().length > 0],
    ["Cómo llega el trabajo", modalidad.valor() === "digital" ? stl.hayStl() && !stl.subiendo() : !recolectaPendiente(false)],
    ["Fecha de entrega", !fecha.validar(false)],
    ["Dirección de entrega", !dirEntrega.validar(false)],
  ];
}
function actualizar() {
  if (!origen) return;
  $("rTipo").textContent = tipoReapertura === "garantia" ? "Garantía" : "Modificación";
  $("rPiezas").textContent = odontograma.lista().join(", ") || "—";
  $("rModalidad").textContent = modalidad.valor() === "digital" ? "Nuevo escaneo (STL)" : "Recolecta física";
  $("rFecha").textContent = fecha.valor() ? fechaCorta(fecha.valor()) : "—";
  $("rDireccion").textContent = dirEntrega.texto();
  $("rPrioridad").innerHTML = $("emergencia").checked ? '<span class="badge rojo">EMERGENCIA</span>' : '<span class="badge gris">Según la cuenta</span>';
  $("checklist").innerHTML = estado().map(([t, ok]) => `<li class="${ok ? "ok" : ""}">${t}</li>`).join("");
}

function pintarOrigen() {
  const o = origen;
  const valor = v => v ? escapar(v.nombre) : "No aplica";
  $("origenCodigo").innerHTML = `<a href="caso.html?id=${o.id}" class="codigo-caso">${escapar(o.codigo)}</a>`;
  $("rOrigen").textContent = `Reapertura de ${o.codigo}`;
  $("origen").innerHTML = [
    ["Paciente", escapar(o.paciente)], ["Doctor", escapar(o.doctor_tratante || "Titular")],
    ["Trabajo", valor(o.tipo_trabajo)], ["Material", valor(o.material)], ["Unidades", valor(o.unidad)],
    ["Color", o.color ? `${valor(o.guia_color)} · ${valor(o.color)}` : "No aplica"],
    ["Piezas", escapar(o.piezas.join(", "))], ["Entregado", escapar(fechaCorta(o.fecha_entrega))],
  ].map(([k, v]) => `<div><span>${k}</span>${v}</div>`).join("");
  $("rPaciente").textContent = o.paciente;
  $("rTrabajo").textContent = o.trabajo;
}

$("form").addEventListener("input", e => { e.target.closest(".campo")?.classList.remove("error"); actualizar(); });

$("form").onsubmit = async e => {
  e.preventDefault();
  $("errorEnvio").hidden = true;
  let primero = null;
  const anotar = el => { if (el && !primero) primero = el; };
  const motivoOk = $("motivo").value.trim().length >= 5;
  $("campoMotivo").classList.toggle("error", !motivoOk); if (!motivoOk) anotar($("campoMotivo"));
  anotar(odontograma.validar(true));
  if (modalidad.valor() === "digital") {
    const ok = stl.hayStl(); $("dropStl").classList.toggle("error", !ok); $("errStl").hidden = ok; if (!ok) anotar($("dropStl"));
  } else anotar(recolectaPendiente(true));
  anotar(fecha.validar(true));
  anotar(dirEntrega.validar(true));
  if (primero) return irAlError(primero);
  if (stl.subiendo() || otros.subiendo()) return toast("Espera a que terminen de subir los archivos", true);
  const analogo = modalidad.valor() === "analogo";
  const datos = {
    tipo_reapertura: tipoReapertura, motivo: $("motivo").value.trim(),
    modalidad: modalidad.valor(), piezas: odontograma.lista(), fecha_entrega: fecha.valor(),
    emergencia: $("emergencia").checked, direccion_entrega: dirEntrega.valor(),
    direccion_recolecta: !analogo ? null : ($("recolectaIgual").checked ? { tipo: "misma_que_entrega" } : dirRecolecta.valor()),
    instrucciones: $("instrucciones").value.trim() || null,
    archivo_ids: [...(analogo ? [] : stl.ids()), ...otros.ids()],
  };
  $("btnEnviar").disabled = true; $("btnEnviar").textContent = "Enviando…";
  try {
    const rp = await api("POST", `/solicitudes/${origenId}/reapertura`, datos);
    location.href = `caso.html?id=${rp.id}&nuevo=1`;
  } catch (err) {
    mostrarErrores($("errorEnvio"), err);
    toast("No se pudo enviar la reapertura", true);
    $("btnEnviar").disabled = false; $("btnEnviar").textContent = "Enviar reapertura";
  }
};

(async () => {
  try {
    origen = await api("GET", `/solicitudes/${origenId}`);
    if (!origen.puede_reabrir) throw new Error(`${origen.codigo}: ${origen.motivo_no_reabrir}.`);
    const perfil = await api("GET", "/solicitudes/perfil" + (usuario.rol === "doctor" ? "" : `?cliente_id=${origen.cliente_id}`));
    $("contenido").hidden = false;
    odontograma = crearOdontograma($("odontograma"), { permitidas: origen.piezas, alCambiar: () => actualizar() });
    dirEntrega = crearDireccion($("dirEntrega"), "ent", () => actualizar());
    dirRecolecta = crearDireccion($("dirRecolecta"), "rec", () => actualizar());
    stl = crearAdjuntos({ zona: $("dropStl"), input: $("inputStl"), lista: $("listaStl"), soloStl: true,
      alCambiar: () => { if (stl.hayStl()) { $("dropStl").classList.remove("error"); $("errStl").hidden = true; } actualizar(); } });
    otros = crearAdjuntos({ zona: $("dropOtros"), input: $("inputOtros"), lista: $("listaOtros"), alCambiar: () => actualizar() });
    fecha = crearFechaEntrega({ alCambiar: () => actualizar() });
    modalidad = crearModalidad(() => { fecha.recalcular(modalidad.valor(), $("emergencia").checked); actualizar(); });
    prepararEmergencia(on => fecha.recalcular(modalidad.valor(), on));
    $("recolectaIgual").onchange = () => { $("bloqueRecolecta").hidden = $("recolectaIgual").checked; actualizar(); };
    dirEntrega.poner(perfil.direcciones); dirRecolecta.poner(perfil.direcciones);
    // Se propone la misma dirección de entrega del caso original si sigue guardada
    const igual = perfil.direcciones.find(d => d.direccion === origen.entrega.direccion && d.municipio === origen.entrega.municipio);
    if (igual) { $("entSel").value = igual.id; }
    pintarOrigen();
    odontograma.poner(origen.piezas);
    // Por defecto recolecta física: en garantía normalmente hay que revisar la pieza
    modalidad.elegir("analogo");
    const arbol = await api("GET", "/config/arbol");
    const tipo = arbol.tipos.find(t => t.id === origen.tipo_trabajo.id);
    if (tipo) modalidad.limitar(tipo.modalidades);  // solo modalidades con flujo activo
    elegirTipo("garantia");
  } catch (error) {
    mostrarErrores($("errorCarga"), error);
    $("errorCarga").insertAdjacentHTML("beforeend", `<div style="margin-top:8px"><a href="caso.html?id=${origenId}">Ver el caso</a></div>`);
  }
})();
