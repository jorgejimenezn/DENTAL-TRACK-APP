/* ============ Tablero Kanban del doctor (el personal puede verlo por cliente) ============ */
const usuario = iniciarPagina(["doctor", "admin", "supervisor", "ingresos"]);
if (!usuario) throw new Error("sin acceso");
const esDoctor = usuario.rol === "doctor";
const fecha = s => new Date(s + "T12:00:00").toLocaleDateString("es-GT", { day: "numeric", month: "short" });
const hoy = (() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; })();
let clienteId = null;

function tarjeta(c) {
  const entregado = c.estado === "entregada";
  const tarde = !entregado && c.fecha_entrega < hoy;
  const pct = c.pasos_total ? Math.round(c.pasos_hechos * 100 / c.pasos_total) : 0;
  return `<a class="kcard ${c.emergencia ? "urgente" : ""}" href="caso.html?id=${c.id}">
    <div class="fila"><b class="codigo-caso">${escapar(c.codigo)}</b>
      ${c.emergencia ? '<span class="badge rojo">EMERGENCIA</span>' : ""}${c.tipo_caso === "RP" ? '<span class="badge azul">RP</span>' : ""}
      <span class="fecha ${tarde ? "tarde" : ""}">${entregado ? "Entregado " + escapar(fechaHora(c.entregado_en).split(",")[0]) : "Entrega " + escapar(fecha(c.fecha_entrega))}</span></div>
    <div class="pac">${escapar(c.paciente)}</div>
    <div class="trab">${escapar(c.trabajo)} · piezas ${escapar(c.piezas.join(", "))}</div>
    ${c.doctor_tratante ? `<div class="trab">${escapar(c.doctor_tratante)}</div>` : ""}
    ${entregado ? "" : `<div class="progreso" title="${c.pasos_hechos} de ${c.pasos_total} pasos"><span style="width:${pct}%"></span></div>
      <div class="estado">${escapar(c.estado_texto)}${c.caso_origen ? ` · reapertura de ${escapar(c.caso_origen)}` : ""}</div>`}
    ${entregado ? `<div class="acciones-k"><span class="btn chico verde-borde" data-reabrir="${c.id}">Reabrir (RP)</span></div>` : ""}
  </a>`;
}

async function cargar() {
  $("errorTablero").hidden = true;
  if (!esDoctor && !clienteId) { $("kanban").innerHTML = '<div class="vacio-card" style="grid-column:1/-1">Elige un cliente para ver su tablero.</div>'; return; }
  const params = new URLSearchParams();
  if ($("fTexto").value.trim()) params.set("q", $("fTexto").value.trim());
  if (clienteId) params.set("cliente_id", clienteId);
  try {
    const t = await api("GET", "/solicitudes/tablero?" + params);
    $("descripcion").textContent = `${esDoctor ? "Tus casos" : "Casos del cliente"} vigentes según la etapa en que van. En "Entregado" aparecen los últimos ${t.dias_entregados} días; los anteriores están en ${esDoctor ? "Mis casos" : "Solicitudes"} → Historial.`;
    $("kanban").innerHTML = t.columnas.map((col, i) => `
      <section class="kanban-col c${i + 1}"><h2>${escapar(col.nombre)}<span class="cuenta">${col.casos.length}</span></h2>
        <div class="kanban-lista">${col.casos.length ? col.casos.map(tarjeta).join("") : '<div class="kanban-vacio">Sin casos</div>'}</div>
      </section>`).join("");
  } catch (error) { mostrarErrores($("errorTablero"), error); $("kanban").innerHTML = ""; }
}

// "Reabrir" dentro de una tarjeta que ya es enlace
$("kanban").addEventListener("click", e => {
  const b = e.target.closest("[data-reabrir]");
  if (!b) return;
  e.preventDefault();
  location.href = `reapertura.html?caso=${b.dataset.reabrir}`;
});
$("fTexto").addEventListener("input", debounce(cargar, 300));
$("ayudaMovil").hidden = window.innerWidth > 1100;

if (!esDoctor) {
  $("campoCliente").hidden = false;
  api("GET", "/solicitudes/clientes").then(lista => {
    $("fCliente").innerHTML += lista.map(c => `<option value="${c.id}">${escapar(c.razon_social)}</option>`).join("");
  });
  $("fCliente").onchange = () => { clienteId = Number($("fCliente").value) || null; cargar(); };
}
cargar();
setInterval(cargar, 120000);
