/* ============ Pantalla de calendario y reglas ============ */
if (!iniciarPagina(["admin"])) throw new Error("sin acceso");

const hoy = new Date();
const ymd = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const fechaLarga = s => new Date(s + "T12:00:00").toLocaleDateString("es-GT", { weekday: "short", day: "numeric", month: "long", year: "numeric" });

/* ---------- Reglas ---------- */
async function cargarReglas() {
  try {
    const p = await api("GET", "/config/parametros");
    $("pCorteSemana").value = p.corte_semana; $("pCorteSabado").value = p.corte_sabado;
    $("pMinDigital").value = p.min_digital; $("pMinAnalogo").value = p.min_analogo; $("pMinEmergencia").value = p.min_emergencia;
  } catch (error) { mostrarErrores($("errorReglas"), error); }
}

$("formReglas").onsubmit = async e => {
  e.preventDefault();
  $("errorReglas").hidden = true;
  try {
    await api("PUT", "/config/parametros", {
      corte_semana: $("pCorteSemana").value, corte_sabado: $("pCorteSabado").value,
      min_digital: Number($("pMinDigital").value), min_analogo: Number($("pMinAnalogo").value),
      min_emergencia: Number($("pMinEmergencia").value),
    });
    toast("Reglas guardadas"); probar();
  } catch (error) { mostrarErrores($("errorReglas"), error); }
};

/* ---------- Probador ---------- */
async function probar() {
  const params = new URLSearchParams({ modalidad: $("tModalidad").value, emergencia: $("tEmergencia").checked });
  if ($("tAhora").value) params.set("ahora", $("tAhora").value);
  try {
    const r = await api("GET", "/config/fecha-minima?" + params);
    $("resultadoPrueba").innerHTML = `
      <div class="chips" style="gap:8px">
        <span class="badge gris">${escapar(r.nota)}</span>
        <span class="badge gris">Cuenta desde: ${escapar(fechaLarga(r.cuenta_desde))}</span>
        <span class="badge ${$("tEmergencia").checked ? "rojo" : "gris"}">Mínimo: ${r.dias_minimos} día(s) hábil(es)</span>
      </div>
      <p style="margin-top:12px;font-size:15px">Primera fecha de entrega: <b style="color:var(--azul-texto)">${escapar(fechaLarga(r.primera_fecha))}</b></p>`;
  } catch (error) { $("resultadoPrueba").innerHTML = `<span style="color:var(--rojo-texto)">${escapar(error.message)}</span>`; }
}
["tModalidad", "tEmergencia", "tAhora"].forEach(id => $(id).addEventListener("change", probar));

/* ---------- Días no laborables ---------- */
for (let a = hoy.getFullYear() - 1; a <= hoy.getFullYear() + 2; a++) $("fAnio").innerHTML += `<option ${a === hoy.getFullYear() ? "selected" : ""}>${a}</option>`;
const anio = () => Number($("fAnio").value);
const actualizarBoton = () => { $("btnFeriados").textContent = `Cargar feriados de Guatemala ${anio()}`; };

async function cargarDias() {
  actualizarBoton();
  try {
    const dias = await api("GET", `/config/calendario?anio=${anio()}`);
    const hoyTxt = ymd(hoy);
    $("listaDias").innerHTML = dias.length ? dias.map(d => `
      <div class="item ${d.fecha < hoyTxt ? "pasado" : ""}">
        <span class="fecha">${escapar(fechaLarga(d.fecha))}</span>
        <span class="nombre" style="font-weight:400">${escapar(d.motivo)}
          <small>${d.hora_corte ? `<span class="badge azul">Horario especial · cierra ${escapar(d.hora_corte)}</span>` : '<span class="badge rojo">Sin labores</span>'}</small></span>
        <div class="botones"><button class="btn chico rojo-borde" data-quitar="${d.id}" data-fecha="${d.fecha}">Quitar</button></div>
      </div>`).join("") : `<div class="vacio">No hay días bloqueados en ${anio()}.</div>`;
  } catch (error) { mostrarErrores($("errorCal"), error); }
}

$("fAnio").onchange = cargarDias;

$("btnFeriados").onclick = async () => {
  try {
    await api("POST", `/config/calendario/feriados/${anio()}`);
    toast("Feriados cargados (los existentes no se duplican)"); cargarDias(); probar();
  } catch (error) { mostrarErrores($("errorCal"), error); }
};

$("dTipo").onchange = () => { $("campoHora").hidden = $("dTipo").value !== "especial"; };

$("formDia").onsubmit = async e => {
  e.preventDefault();
  $("errorCal").hidden = true;
  const especial = $("dTipo").value === "especial";
  if (!$("dFecha").value || $("dMotivo").value.trim().length < 2 || (especial && !$("dHora").value)) {
    return mostrarErrores($("errorCal"), new Error(especial ? "Indica la fecha, el motivo y la hora de cierre." : "Indica la fecha y un motivo."));
  }
  try {
    await api("POST", "/config/calendario", { fecha: $("dFecha").value, motivo: $("dMotivo").value.trim(),
      hora_corte: especial ? $("dHora").value : null });
    const a = Number($("dFecha").value.slice(0, 4));
    if (a !== anio() && [...$("fAnio").options].some(o => Number(o.value) === a)) $("fAnio").value = a;
    $("formDia").reset(); $("dHora").value = "12:00"; $("campoHora").hidden = true;
    toast(especial ? "Horario especial agregado" : "Día bloqueado"); cargarDias(); probar();
  } catch (error) { mostrarErrores($("errorCal"), error); }
};

$("listaDias").addEventListener("click", async e => {
  const b = e.target.closest("[data-quitar]");
  if (!b || !confirm(`¿Quitar el ${fechaLarga(b.dataset.fecha)} del calendario?`)) return;
  try { await api("DELETE", `/config/calendario/${b.dataset.quitar}`); toast("Fecha quitada del calendario"); cargarDias(); probar(); }
  catch (error) { toast(error.message, true); }
});

cargarReglas();
cargarDias();
probar();
