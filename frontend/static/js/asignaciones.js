/* ============ Pantalla de asignaciones ============ */
if (!iniciarPagina(["admin"])) throw new Error("sin acceso");

let catalogo = null, asignaciones = [], actual = null;

async function cargar() {
  try {
    [catalogo, asignaciones] = await Promise.all([api("GET", "/config/catalogos"), api("GET", "/config/asignaciones")]);
    const areas = [...new Map(asignaciones.flatMap(a => a.areas).map(x => [x.area_id, x.area])).entries()]
      .sort((a, b) => a[1].localeCompare(b[1]));
    const previo = $("fArea").value;
    $("fArea").innerHTML = '<option value="">Todas las áreas</option>' + areas.map(([id, n]) => `<option value="${id}">${escapar(n)}</option>`).join("");
    $("fArea").value = previo;
    pintar();
  } catch (error) {
    $("tabla").innerHTML = `<tr><td colspan="3" class="vacio">${escapar(error.message)}</td></tr>`;
  }
}

const nombreTipo = id => catalogo.tipos.find(t => t.id === id)?.nombre || "?";

function pintar() {
  const texto = $("fTexto").value.trim().toLowerCase(), area = Number($("fArea").value);
  const lista = asignaciones.filter(a => (!texto || a.nombre.toLowerCase().includes(texto))
    && (!area || a.areas.some(x => x.area_id === area)));
  $("tabla").innerHTML = lista.length ? lista.map(a => `
    <tr>
      <td class="principal"><b>${escapar(a.nombre)}</b><span class="sub">${escapar(NOMBRES_ROL[a.rol] || a.rol)} · ${a.max_trabajos ? `máx. ${a.max_trabajos} trabajos` : "sin límite de trabajos"}</span></td>
      <td data-label="Áreas"><div class="chips" style="flex-direction:column;align-items:flex-end;gap:6px">${a.areas.map(x => `
        <span><span class="badge azul">${escapar(x.area)}</span>
          <span class="sub" style="display:inline;margin-left:4px">${x.tipo_ids.length ? x.tipo_ids.map(nombreTipo).map(escapar).join(", ") : "Todos"}</span></span>`).join("")}
      </div></td>
      <td class="acciones"><button class="btn chico" data-editar="${a.usuario_id}">Editar</button></td>
    </tr>`).join("") : '<tr><td colspan="3" class="vacio">No hay empleados con áreas asignadas.</td></tr>';
}

$("fTexto").addEventListener("input", debounce(pintar, 150));
$("fArea").onchange = pintar;

$("tabla").addEventListener("click", e => {
  const b = e.target.closest("[data-editar]");
  if (b) abrir(Number(b.dataset.editar));
});

function abrir(usuarioId) {
  actual = asignaciones.find(a => a.usuario_id === usuarioId);
  $("tituloAsig").textContent = actual.nombre;
  $("errorAsig").hidden = true;
  const tipos = catalogo.tipos.filter(t => t.activo);
  $("cuerpoAsig").innerHTML = actual.areas.map(x => `
    <div class="seccion-form">${escapar(x.area)}</div>
    <label class="check-linea" style="margin-bottom:10px"><input type="checkbox" class="todos" data-area="${x.area_id}" ${x.tipo_ids.length ? "" : "checked"}>
      Atiende todos los tipos de trabajo</label>
    <div class="selector-chips" data-tipos="${x.area_id}" ${x.tipo_ids.length ? "" : "hidden"}>
      ${tipos.map(t => `<label><input type="checkbox" value="${t.id}" ${x.tipo_ids.includes(t.id) ? "checked" : ""}>${escapar(t.nombre)}</label>`).join("")}
    </div>`).join("");
  $("cuerpoAsig").querySelectorAll(".todos").forEach(c => c.onchange = () => {
    document.querySelector(`[data-tipos="${c.dataset.area}"]`).hidden = c.checked;
  });
  $("modalAsig").showModal();
}

$("formAsig").onsubmit = async e => {
  e.preventDefault();
  const areas = actual.areas.map(x => {
    const todos = document.querySelector(`.todos[data-area="${x.area_id}"]`).checked;
    const tipo_ids = todos ? [] : [...document.querySelectorAll(`[data-tipos="${x.area_id}"] input:checked`)].map(i => Number(i.value));
    return { area_id: x.area_id, tipo_ids, vacio: !todos && !tipo_ids.length, area: x.area };
  });
  const sinTipos = areas.filter(a => a.vacio).map(a => a.area);
  if (sinTipos.length) return mostrarErrores($("errorAsig"), new Error(`Marca al menos un tipo en: ${sinTipos.join(", ")} (o elige "todos").`));
  try {
    await api("PUT", `/config/asignaciones/${actual.usuario_id}`, { areas: areas.map(({ area_id, tipo_ids }) => ({ area_id, tipo_ids })) });
    $("modalAsig").close(); toast("Asignación guardada"); cargar();
  } catch (error) { mostrarErrores($("errorAsig"), error); }
};

document.querySelectorAll("[data-cerrar]").forEach(b => b.onclick = () => b.closest("dialog").close());
cargar();
