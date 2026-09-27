/* ============ Lista de casos: vigentes, historial y todos ============ */
const usuario = iniciarPagina();
if (!usuario) throw new Error("sin acceso");
const esDoctor = usuario.rol === "doctor";
const COLOR_ESTADO = { entregada: "verde", cancelada: "rojo", validacion_qa: "azul", pendiente_recolecta: "azul" };
const fechaCorta = s => new Date(s + "T12:00:00").toLocaleDateString("es-GT", { day: "numeric", month: "short", year: "numeric" });
let vista = "true";

if (!esDoctor) {
  $("titulo").textContent = "Solicitudes";
  $("descripcion").textContent = "Todas las solicitudes del laboratorio. Las vigentes se ordenan por prioridad y fecha de entrega.";
} else document.querySelectorAll(".col-cliente").forEach(x => x.remove());
$("btnNueva").hidden = !(esDoctor || ROLES_CAPTURA.includes(usuario.rol));

async function cargar() {
  const params = new URLSearchParams();
  if (vista) params.set("vigentes", vista);
  if ($("fTexto").value.trim()) params.set("q", $("fTexto").value.trim());
  if ($("fTipo").value) params.set("tipo_caso", $("fTipo").value);
  const columnas = esDoctor ? 5 : 6;
  try {
    const casos = await api("GET", "/solicitudes?" + params);
    $("tabla").innerHTML = casos.length ? casos.map(c => `
      <tr>
        <td class="principal"><a href="caso.html?id=${c.id}" class="codigo-caso">${escapar(c.codigo)}</a>
          ${c.emergencia ? ' <span class="badge rojo">EMERGENCIA</span>' : ""}
          <span class="sub">${escapar(c.paciente)}${c.caso_origen ? ` · reapertura de ${escapar(c.caso_origen)}` : ""}</span></td>
        ${esDoctor ? "" : `<td data-label="Cliente">${escapar(c.cliente)}${c.prioridad ? `<span class="sub">Prioridad ${c.prioridad}</span>` : ""}</td>`}
        <td data-label="Trabajo">${escapar(c.trabajo)}<span class="sub">Piezas ${escapar(c.piezas.join(", "))}</span></td>
        <td data-label="Estado"><span class="badge ${COLOR_ESTADO[c.estado] || "gris"}">${escapar(c.estado_texto)}</span>${!esDoctor && c.area_actual ? `<span class="sub">${escapar(c.area_actual)}</span>` : ""}</td>
        <td data-label="Entrega">${escapar(fechaCorta(c.fecha_entrega))}</td>
        <td class="acciones"><a class="btn chico" href="caso.html?id=${c.id}">Ver</a>
          ${c.estado === "entregada" && (esDoctor || ROLES_CAPTURA.includes(usuario.rol)) ? `<a class="btn chico verde-borde" href="reapertura.html?caso=${c.id}">Reabrir</a>` : ""}</td>
      </tr>`).join("")
      : `<tr><td colspan="${columnas}" class="vacio">${vista === "true" ? "No hay casos vigentes." : "No hay casos para mostrar."}</td></tr>`;
  } catch (error) {
    $("tabla").innerHTML = `<tr><td colspan="${columnas}" class="vacio">${escapar(error.message)}</td></tr>`;
  }
}

$("pestanas").addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  vista = b.dataset.vista;
  $("pestanas").querySelectorAll("button").forEach(x => x.classList.toggle("activa", x === b));
  cargar();
});
$("fTexto").addEventListener("input", debounce(cargar, 300));
$("fTipo").onchange = cargar;
cargar();
