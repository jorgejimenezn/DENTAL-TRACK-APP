/* ============ Pantalla de flujos de trabajo ============ */
if (!iniciarPagina(["admin", "demo"])) throw new Error("sin acceso");

const MODALIDADES = { digital: "Digital", analogo: "Analógico" };
let catalogo = null, flujos = [], edicion = null; // edicion: { tipo, modalidad, pasos: [area_id] }

async function cargar() {
  try {
    [catalogo, flujos] = await Promise.all([api("GET", "/config/catalogos"), api("GET", "/config/flujos")]);
    pintar();
  } catch (error) {
    $("lista").innerHTML = `<div class="card vacio">${escapar(error.message)}</div>`;
  }
}

const buscarFlujo = (tipoId, modalidad) => flujos.find(f => f.tipo_trabajo_id === tipoId && f.modalidad === modalidad);

function celda(tipo, modalidad) {
  const f = buscarFlujo(tipo.id, modalidad);
  let estado = '<span class="badge gris">Sin configurar</span>', cuerpo = '<span class="nota" style="margin:0">Aún no tiene pasos.</span>';
  if (f) {
    estado = f.activo ? '<span class="badge verde">Activo</span>' : '<span class="badge rojo">Inactivo</span>';
    cuerpo = `<div class="pasos">${f.pasos.map((p, i) => `
      ${i ? '<span class="flecha">→</span>' : ""}
      <span class="paso ${p.tecnicos ? "" : "sin-tecnicos"}" title="${p.tecnicos} empleado(s) pueden hacer este paso">
        <span class="n">${p.orden}</span>${escapar(p.area)}<span class="t">${p.tecnicos}</span></span>`).join("")}</div>`;
  }
  return `<div class="flujo-celda">
    <div class="cabecera"><b>${MODALIDADES[modalidad]}</b>${estado}
      <button class="btn chico" data-editar="${tipo.id}" data-modalidad="${modalidad}">${f ? "Editar" : "Configurar"}</button></div>
    ${cuerpo}</div>`;
}

function pintar() {
  const sinTecnicos = flujos.filter(f => f.activo).flatMap(f => f.pasos.filter(p => !p.tecnicos)
    .map(p => `${f.tipo_trabajo} (${MODALIDADES[f.modalidad]}) → ${p.area}`));
  const aviso = $("avisoCobertura");
  aviso.hidden = !sinTecnicos.length;
  if (sinTecnicos.length) {
    aviso.innerHTML = `Hay ${sinTecnicos.length} paso(s) sin ningún empleado que pueda atenderlos; esas órdenes quedarían pendientes de autorización:
      <ul>${sinTecnicos.slice(0, 8).map(t => `<li>${escapar(t)}</li>`).join("")}</ul>
      Revisa <a href="asignaciones.html">Asignaciones</a> o las áreas de los <a href="empleados.html">Empleados</a>.`;
  }
  const tipos = [...catalogo.tipos].sort((a, b) => Number(b.activo) - Number(a.activo) || a.nombre.localeCompare(b.nombre));
  $("lista").innerHTML = tipos.map(t => `
    <section class="flujo-tarjeta" ${t.activo ? "" : 'style="opacity:.6"'}>
      <h3>${escapar(t.nombre)} ${t.activo ? "" : '<span class="badge rojo">Tipo inactivo</span>'}</h3>
      <div class="flujo-modalidades">${celda(t, "digital")}${celda(t, "analogo")}</div>
    </section>`).join("") || '<div class="card vacio">No hay tipos de trabajo. Créalos en Catálogos.</div>';
}

$("lista").addEventListener("click", e => {
  const b = e.target.closest("[data-editar]");
  if (b) abrir(Number(b.dataset.editar), b.dataset.modalidad);
});

/* ---------- Editor ---------- */
const areaNombre = id => catalogo.areas.find(a => a.id === id)?.nombre || "?";

function abrir(tipoId, modalidad) {
  const tipo = catalogo.tipos.find(t => t.id === tipoId);
  const f = buscarFlujo(tipoId, modalidad);
  edicion = { tipo, modalidad, pasos: f ? f.pasos.map(p => p.area_id) : [] };
  $("tituloFlujo").textContent = `${tipo.nombre} · ${MODALIDADES[modalidad]}`;
  $("chkActivo").checked = f ? f.activo : true;
  $("selArea").innerHTML = catalogo.areas.filter(a => a.activo).map(a => `<option value="${a.id}">${escapar(a.nombre)}</option>`).join("");
  $("errorFlujo").hidden = true;
  pintarEditor();
  $("modalFlujo").showModal();
}

function pintarEditor() {
  $("editorPasos").innerHTML = edicion.pasos.map((a, i) => `
    <div class="editor-paso">
      <span class="num">${i + 1}</span><span class="area">${escapar(areaNombre(a))}</span>
      <button type="button" class="btn" data-mover="${i}" data-dir="-1" ${i ? "" : "disabled"} aria-label="Subir">↑</button>
      <button type="button" class="btn" data-mover="${i}" data-dir="1" ${i < edicion.pasos.length - 1 ? "" : "disabled"} aria-label="Bajar">↓</button>
      <button type="button" class="btn rojo-borde" data-quitar="${i}" aria-label="Quitar">✕</button>
    </div>`).join("") || '<div class="nota" style="margin:0 0 6px">Agrega el primer paso.</div>';
}

$("editorPasos").addEventListener("click", e => {
  const mover = e.target.closest("[data-mover]"), quitar = e.target.closest("[data-quitar]");
  if (mover) {
    const i = Number(mover.dataset.mover), j = i + Number(mover.dataset.dir);
    [edicion.pasos[i], edicion.pasos[j]] = [edicion.pasos[j], edicion.pasos[i]];
  }
  if (quitar) edicion.pasos.splice(Number(quitar.dataset.quitar), 1);
  pintarEditor();
});

$("btnAgregarPaso").onclick = () => {
  const area = Number($("selArea").value);
  if (!area) return;
  edicion.pasos.push(area);
  pintarEditor();
};

$("formFlujo").onsubmit = async e => {
  e.preventDefault();
  if (!edicion.pasos.length) return mostrarErrores($("errorFlujo"), new Error("El flujo necesita al menos un paso."));
  try {
    await api("PUT", "/config/flujos", { tipo_trabajo_id: edicion.tipo.id, modalidad: edicion.modalidad,
      activo: $("chkActivo").checked, area_ids: edicion.pasos });
    $("modalFlujo").close(); toast("Flujo guardado"); cargar();
  } catch (error) { mostrarErrores($("errorFlujo"), error); }
};

document.querySelectorAll("[data-cerrar]").forEach(b => b.onclick = () => b.closest("dialog").close());
cargar();
