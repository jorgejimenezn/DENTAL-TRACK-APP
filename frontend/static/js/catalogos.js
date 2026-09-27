/* ============ Pantalla de catálogos ============ */
if (!iniciarPagina(["admin"])) throw new Error("sin acceso");

const TABS = {
  tipos: { titulo: "Tipos de trabajo", singular: "tipo de trabajo", clave: "tipos",
    ayuda: "Cada tipo define qué materiales puede elegir el doctor." },
  materiales: { titulo: "Materiales", singular: "material", clave: "materiales",
    ayuda: "Cada material define sus unidades y guías de color." },
  unidades: { titulo: "Unidades", singular: "unidad", clave: "unidades",
    ayuda: "Forma en que se trabaja: pieza individual, puente, arcada… La cantidad sale de las piezas marcadas." },
  "motivos-rp": { titulo: "Motivos de RP", singular: "motivo", clave: "motivos",
    ayuda: "Motivos que QA elige al validar un reproceso (garantía o cobro). También podrá escribir \"Otro\"." },
  "colores-caja": { titulo: "Colores de caja", singular: "color de caja", clave: "colores_caja",
    ayuda: "Colores de las cajas físicas. Ingresos elige color y número al aprobar un caso; una caja no puede estar en dos casos abiertos." },
  areas: { titulo: "Áreas", singular: "área", clave: "areas",
    ayuda: "Departamentos del laboratorio. Se usan en los flujos y en las asignaciones de empleados." },
};

let datos = null;
let tab = "tipos";
let guiaSeleccionada = null;
let editando = null;     // `${catalogo}:${id}` en renombrado
let relacion = null;     // { tipo: "tipo"|"material", id }

const porId = (lista, id) => lista.find(x => x.id === id);
const nombres = (lista, ids) => ids.map(i => porId(lista, i)?.nombre).filter(Boolean);

async function cargar() {
  try {
    datos = await api("GET", "/config/catalogos");
    if (!guiaSeleccionada && datos.guias.length) guiaSeleccionada = datos.guias[0].id;
    pintar();
  } catch (error) {
    $("panel").innerHTML = `<div class="vacio">${escapar(error.message)}</div>`;
  }
}

$("pestanas").onclick = e => {
  const b = e.target.closest("button[data-tab]");
  if (!b) return;
  tab = b.dataset.tab; editando = null;
  document.querySelectorAll("#pestanas button").forEach(x => x.classList.toggle("activa", x === b));
  pintar();
};

function pintar() {
  if (!datos) return;
  if (tab === "guias") return pintarGuias();
  if (tab === "vista") return pintarVista();
  pintarLista(tab);
}

/* ---------- Listas simples ---------- */
function resumen(catalogo, item) {
  if (catalogo === "tipos") {
    const m = nombres(datos.materiales, item.material_ids);
    return m.length ? `Materiales: ${m.join(", ")}` : '<span style="color:var(--rojo-texto)">Sin materiales: no aparecerá completo en la solicitud</span>';
  }
  if (catalogo === "materiales") {
    const u = nombres(datos.unidades, item.unidad_ids), g = nombres(datos.guias, item.guia_ids);
    return `Unidades: ${u.join(", ") || "—"} · Guías: ${g.join(", ") || "sin color"}`;
  }
  return "";
}

function filaItem(catalogo, item) {
  const clave = `${catalogo}:${item.id}`;
  if (editando === clave) {
    return `<div class="item">
      <input class="renombrar" id="inpRenombrar" value="${escapar(item.nombre)}" maxlength="120">
      <div class="botones">
        <button class="btn chico" data-accion="cancelar">Cancelar</button>
        <button class="btn chico verde" data-accion="guardar-nombre" data-id="${item.id}">Guardar</button>
      </div></div>`;
  }
  const rel = catalogo === "tipos" || catalogo === "materiales";
  return `<div class="item ${item.activo ? "" : "inactivo"}">
    <div class="nombre">${escapar(item.nombre)} ${item.activo ? "" : '<span class="badge rojo">Inactivo</span>'}
      ${rel ? `<small>${resumen(catalogo, item)}</small>` : ""}</div>
    <div class="botones">
      ${rel ? `<button class="btn chico" data-accion="relaciones" data-id="${item.id}">${catalogo === "tipos" ? "Materiales" : "Unidades y guías"}</button>` : ""}
      <button class="btn chico" data-accion="renombrar" data-id="${item.id}">Renombrar</button>
      <button class="btn chico ${item.activo ? "rojo-borde" : "verde-borde"}" data-accion="estado" data-id="${item.id}">${item.activo ? "Desactivar" : "Activar"}</button>
    </div></div>`;
}

function pintarLista(catalogo) {
  const t = TABS[catalogo];
  const items = datos[t.clave];
  $("panel").innerHTML = `
    <div class="agregar-linea">
      <div class="campo"><input id="inpNuevo" placeholder="Nuevo ${t.singular}" maxlength="120"></div>
      <button class="btn verde" data-accion="agregar">+ Agregar</button>
    </div>
    <div class="error-form" id="errorPanel" hidden></div>
    <div class="lista-items">${items.length ? items.map(i => filaItem(catalogo, i)).join("") : '<div class="vacio">Sin elementos.</div>'}</div>
    <p class="nota">${t.ayuda} Desactivar oculta el elemento en formularios nuevos sin borrar el historial.</p>`;
  $("inpNuevo").onkeydown = e => { if (e.key === "Enter") { e.preventDefault(); agregar(catalogo); } };
  $("inpRenombrar")?.focus();
  $("inpRenombrar")?.addEventListener("keydown", e => { if (e.key === "Enter") guardarNombre(catalogo, editandoId()); if (e.key === "Escape") { editando = null; pintar(); } });
}

const editandoId = () => Number(editando?.split(":")[1]);

$("panel").addEventListener("click", e => {
  const b = e.target.closest("[data-accion]");
  if (!b) return;
  const id = Number(b.dataset.id);
  const acciones = {
    agregar: () => agregar(tab),
    renombrar: () => { editando = `${tab}:${id}`; pintar(); },
    cancelar: () => { editando = null; pintar(); },
    "guardar-nombre": () => guardarNombre(tab, id),
    estado: () => cambiarEstado(tab, id),
    relaciones: () => abrirRelaciones(tab === "tipos" ? "tipo" : "material", id),
    "sel-guia": () => { guiaSeleccionada = id; pintar(); },
    "agregar-color": agregarColor,
    "color-estado": () => cambiarColor(id, "estado"),
    "color-renombrar": () => cambiarColor(id, "renombrar"),
  };
  acciones[b.dataset.accion]?.();
});

async function agregar(catalogo) {
  const nombre = $("inpNuevo").value.trim();
  if (!nombre) return $("inpNuevo").focus();
  try {
    await api("POST", `/config/catalogos/${catalogo}`, { nombre });
    toast("Agregado");
    await cargar();
    $("inpNuevo")?.focus();
  } catch (error) { mostrarErrores($("errorPanel"), error); }
}

async function guardarNombre(catalogo, id) {
  const item = porId(datos[TABS[catalogo]?.clave || "guias"], id);
  const nombre = $("inpRenombrar").value.trim();
  if (!nombre) return;
  try {
    await api("PUT", `/config/catalogos/${catalogo}/${id}`, { nombre, activo: item.activo });
    editando = null; toast("Nombre actualizado"); cargar();
  } catch (error) { mostrarErrores($("errorPanel"), error); }
}

async function cambiarEstado(catalogo, id) {
  const item = porId(datos[TABS[catalogo]?.clave || "guias"], id);
  if (item.activo && !confirm(`¿Desactivar "${item.nombre}"? Dejará de aparecer en formularios nuevos.`)) return;
  try {
    await api("PUT", `/config/catalogos/${catalogo}/${id}`, { nombre: item.nombre, activo: !item.activo });
    toast(item.activo ? "Desactivado" : "Activado"); cargar();
  } catch (error) { toast(error.message, true); }
}

/* ---------- Guías y colores ---------- */
function pintarGuias() {
  const guia = porId(datos.guias, guiaSeleccionada);
  $("panel").innerHTML = `
    <div class="error-form" id="errorPanel" hidden></div>
    <div class="dos-columnas">
      <div>
        <div class="agregar-linea">
          <div class="campo"><input id="inpNuevo" placeholder="Nueva guía de color" maxlength="120"></div>
          <button class="btn verde" data-accion="agregar">+ Agregar</button>
        </div>
        <div class="lista-items">${datos.guias.map(g => editando === `guias:${g.id}` ? filaItem("guias", g) : `
          <div class="item ${g.activo ? "" : "inactivo"} ${g.id === guiaSeleccionada ? "seleccionado" : ""}">
            <div class="nombre">${escapar(g.nombre)} ${g.activo ? "" : '<span class="badge rojo">Inactiva</span>'}
              <small>${g.colores.filter(c => c.activo).length} colores activos</small></div>
            <div class="botones">
              <button class="btn chico" data-accion="sel-guia" data-id="${g.id}">Ver colores</button>
              <button class="btn chico" data-accion="renombrar" data-id="${g.id}">Renombrar</button>
              <button class="btn chico ${g.activo ? "rojo-borde" : "verde-borde"}" data-accion="estado" data-id="${g.id}">${g.activo ? "Desactivar" : "Activar"}</button>
            </div></div>`).join("")}</div>
      </div>
      <div class="card" style="background:rgba(0,0,0,.35)">
        ${guia ? `
          <h3 style="font-size:15px;margin-bottom:10px">Colores de ${escapar(guia.nombre)}</h3>
          <div class="agregar-linea">
            <div class="campo"><input id="inpColor" placeholder="Ej. A3.5 o 2M2" maxlength="20"></div>
            <button class="btn verde" data-accion="agregar-color">+ Color</button>
          </div>
          <div class="colores-grid">${guia.colores.map(c => `
            <span class="color-chip ${c.activo ? "" : "inactivo"}">${escapar(c.nombre)}
              <button data-accion="color-renombrar" data-id="${c.id}" title="Renombrar">✎</button>
              <button data-accion="color-estado" data-id="${c.id}" title="${c.activo ? "Desactivar" : "Activar"}">${c.activo ? "✕" : "↺"}</button>
            </span>`).join("") || '<span class="nota">Sin colores.</span>'}</div>
          <p class="nota">✕ desactiva un color; ↺ lo vuelve a activar.</p>` : '<div class="vacio">Agrega una guía de color.</div>'}
      </div>
    </div>`;
  $("inpNuevo").onkeydown = e => { if (e.key === "Enter") { e.preventDefault(); agregar("guias"); } };
  $("inpColor")?.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); agregarColor(); } });
  $("inpRenombrar")?.focus();
}

async function agregarColor() {
  const nombre = $("inpColor").value.trim();
  if (!nombre) return $("inpColor").focus();
  try {
    await api("POST", `/config/guias/${guiaSeleccionada}/colores`, { nombre });
    await cargar(); $("inpColor")?.focus();
  } catch (error) { mostrarErrores($("errorPanel"), error); }
}

async function cambiarColor(id, modo) {
  const color = datos.guias.flatMap(g => g.colores).find(c => c.id === id);
  let nombre = color.nombre, activo = color.activo;
  if (modo === "renombrar") {
    nombre = (prompt("Nuevo nombre del color", color.nombre) || "").trim();
    if (!nombre || nombre === color.nombre) return;
  } else activo = !activo;
  try { await api("PUT", `/config/colores/${id}`, { nombre, activo }); cargar(); }
  catch (error) { mostrarErrores($("errorPanel"), error); }
}

/* ---------- Relaciones ---------- */
function chips(lista, seleccionados, nombre) {
  return `<div class="selector-chips">${lista.map(x => `
    <label><input type="checkbox" name="${nombre}" value="${x.id}" ${seleccionados.includes(x.id) ? "checked" : ""}>
      ${escapar(x.nombre)}${x.activo ? "" : " (inactivo)"}</label>`).join("")}</div>`;
}

function abrirRelaciones(tipo, id) {
  relacion = { tipo, id };
  $("errorRel").hidden = true;
  if (tipo === "tipo") {
    const t = porId(datos.tipos, id);
    $("tituloRel").textContent = `Materiales · ${t.nombre}`;
    $("cuerpoRel").innerHTML = `<p class="nota" style="margin:0 0 12px">Materiales que el doctor podrá elegir para este tipo de trabajo.</p>
      ${chips(datos.materiales, t.material_ids, "rel")}`;
  } else {
    const m = porId(datos.materiales, id);
    $("tituloRel").textContent = `Unidades y guías · ${m.nombre}`;
    $("cuerpoRel").innerHTML = `
      <div class="seccion-form">Unidades</div>${chips(datos.unidades, m.unidad_ids, "uni")}
      <div class="seccion-form">Guías de color</div>${chips(datos.guias, m.guia_ids, "gui")}
      <p class="nota">Sin guías de color, el campo de color aparecerá como "No aplica" (por ejemplo, modelos impresos).</p>`;
  }
  $("modalRel").showModal();
}

const marcados = n => [...document.querySelectorAll(`#cuerpoRel input[name="${n}"]:checked`)].map(i => Number(i.value));

$("formRel").onsubmit = async e => {
  e.preventDefault();
  try {
    if (relacion.tipo === "tipo") await api("PUT", `/config/tipos/${relacion.id}/materiales`, { ids: marcados("rel") });
    else await api("PUT", `/config/materiales/${relacion.id}/relaciones`, { unidad_ids: marcados("uni"), guia_ids: marcados("gui") });
    $("modalRel").close(); toast("Relaciones guardadas"); cargar();
  } catch (error) { mostrarErrores($("errorRel"), error); }
};

/* ---------- Vista previa de la cadena ---------- */
function pintarVista() {
  const activos = l => l.filter(x => x.activo);
  $("panel").innerHTML = `
    <p class="nota" style="margin:0 0 14px">Así se encadenan las opciones en la solicitud del doctor (solo elementos activos).</p>
    <div class="grid tres">
      <div class="campo"><label>Tipo de trabajo</label><select id="vTipo"></select></div>
      <div class="campo"><label>Material</label><select id="vMaterial"></select></div>
      <div class="campo"><label>Unidades</label><select id="vUnidad"></select></div>
      <div class="campo"><label>Guía de color</label><select id="vGuia"></select></div>
      <div class="campo"><label>Color</label><select id="vColor"></select></div>
    </div>`;
  const llenar = (sel, items, vacio) => {
    sel.innerHTML = items.length ? items.map(x => `<option value="${x.id}">${escapar(x.nombre)}</option>`).join("") : `<option>${vacio}</option>`;
    sel.disabled = !items.length;
  };
  const alTipo = () => {
    const t = porId(datos.tipos, Number($("vTipo").value));
    llenar($("vMaterial"), t ? activos(t.material_ids.map(i => porId(datos.materiales, i))) : [], "Sin materiales");
    alMaterial();
  };
  const alMaterial = () => {
    const m = porId(datos.materiales, Number($("vMaterial").value));
    llenar($("vUnidad"), m ? activos(m.unidad_ids.map(i => porId(datos.unidades, i))) : [], "Sin unidades");
    llenar($("vGuia"), m ? activos(m.guia_ids.map(i => porId(datos.guias, i))) : [], "No aplica");
    alGuia();
  };
  const alGuia = () => {
    const g = porId(datos.guias, Number($("vGuia").value));
    llenar($("vColor"), g ? activos(g.colores) : [], "No aplica");
  };
  llenar($("vTipo"), activos(datos.tipos), "Sin tipos");
  $("vTipo").onchange = alTipo; $("vMaterial").onchange = alMaterial; $("vGuia").onchange = alGuia;
  alTipo();
}

document.querySelectorAll("[data-cerrar]").forEach(b => b.onclick = () => b.closest("dialog").close());
cargar();
