/* ============ Dashboard de operación (admin, supervisor, operaciones) ============ */
if (!iniciarPagina(["admin", "supervisor", "operaciones", "demo"])) throw new Error("sin acceso");
const ymdL = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const hoyD = new Date(), hace30 = new Date(); hace30.setDate(hoyD.getDate() - 29);
$("fDesde").value = ymdL(hace30); $("fHasta").value = ymdL(hoyD);

function pintarVivo(v) {
  $("kpisVivo").innerHTML = kpi("Casos vigentes", num(v.vigentes))
    + kpi("Vencidos", num(v.vencidos), "fecha de entrega ya pasó", v.vencidos > 0)
    + kpi("Vencen hoy", num(v.vencen_hoy), "", v.vencen_hoy > 0)
    + kpi("Vencen mañana", num(v.vencen_manana))
    + kpi("Emergencias abiertas", num(v.emergencias), "", v.emergencias > 0)
    + kpi("En cola", num(v.en_cola), "técnicos al tope", v.en_cola > 0)
    + kpi("Sin técnico", num(v.sin_tecnico), "nadie cubre el paso", v.sin_tecnico > 0)
    + kpi("Devoluciones de QA hoy", num(v.devoluciones_hoy))
    + kpi("Casos en pausa", num(v.pausados), "", v.pausados > 0)
    + kpi("Diseños con el cliente", num(v.validaciones_enviadas), `${num(v.validaciones_por_enviar)} por enviar`)
    + kpi("Recolectas pendientes", num(v.recolectas_pendientes), `${num(v.recolectas_vencidas)} fuera del plazo de 2 h`, v.recolectas_vencidas > 0);
  $("cargaAreas").innerHTML = barras(v.areas.map(a => ({ nombre: a.area, valor: a.activos,
    detalle: [a.en_proceso && `${a.en_proceso} en proceso`, a.en_cola && `${a.en_cola} en cola`, a.sin_tecnico && `${a.sin_tecnico} sin técnico`].filter(Boolean).join(", ") })),
    { vacio: "No hay casos en el laboratorio" })
    + `<p class="nota"><a href="bandeja.html">Ver la bandeja del laboratorio →</a></p>`;
  const bloques = [];
  if (v.en_proceso_ausentes.length) bloques.push(`<div class="aviso rojo" style="margin:0 0 10px"><div><b>En proceso con personal ausente:</b> ${v.en_proceso_ausentes.map(p => `<a href="caso.html?id=${p.solicitud_id}">${escapar(p.codigo)}</a> (${escapar(p.area)}, ${escapar(p.tecnico)})`).join(", ")}. Reasígnalos desde la bandeja.</div></div>`);
  bloques.push(`<div class="etiqueta-seccion">Ausentes hoy</div>` + (v.ausentes.length ? `<div class="chips" style="margin-bottom:12px">${v.ausentes.map(a => `<span class="badge gris">${escapar(a.nombre)}</span>`).join("")}</div>` : '<p class="nota" style="margin:0 0 12px">Todo el personal disponible.</p>'));
  if (v.pausados_lista.length) bloques.push(`<div class="etiqueta-seccion">En pausa · <a href="pausas.html">ver auditoría</a></div><div class="espera" style="margin-bottom:12px">${v.pausados_lista.map(p => `<a href="caso.html?id=${p.id}"><b class="codigo-caso">${escapar(p.codigo)}</b><span>${escapar(p.cliente)} · ${escapar(p.motivo || "")}</span><span class="fecha">desde ${escapar(fechaHora(p.desde))}</span></a>`).join("")}</div>`);
  if (v.recolectas_lista.length) bloques.push(`<div class="etiqueta-seccion">Recolectas por hacer (plazo 2 h laborales)</div><div class="espera" style="margin-bottom:12px">${v.recolectas_lista.map(r => `<a href="caso.html?id=${r.id}"><b class="codigo-caso">${escapar(r.codigo)}</b><span>${escapar(r.cliente)}${r.mensajero ? ` · ${escapar(r.mensajero)}` : " · sin mensajero"}</span><span class="fecha" style="${r.vencida ? "color:var(--rojo-texto)" : ""}">${r.vencida ? "vencida " : "antes de "}${escapar(fechaHora(r.limite))}</span></a>`).join("")}</div>`);
  bloques.push(`<div class="etiqueta-seccion">Vencidos y por vencer hoy</div>` + (v.vencidos_lista.length
    ? `<div class="espera">${v.vencidos_lista.map(s => `<a href="caso.html?id=${s.id}"><b class="codigo-caso">${escapar(s.codigo)}</b>${s.prioridad === 1 ? '<span class="badge rojo">EMERGENCIA</span>' : ""}<span>${escapar(s.paciente)}</span><span class="fecha" style="${s.fecha_entrega < ymdL(hoyD) ? "color:var(--rojo-texto)" : ""}">${escapar(fechaCortaM(s.fecha_entrega))}</span></a>`).join("")}</div>`
    : '<p class="nota" style="margin:0">Nada vencido ni por vencer hoy.</p>'));
  $("atencion").innerHTML = bloques.join("");
}

function pintarPeriodo(p) {
  const retrabajos = p.por_area.reduce((t, a) => t + a.retrabajos, 0);
  $("kpisMetas").innerHTML = kpi("Dentro de meta (producción)", pct(p.cumplimiento_general), "pasos terminados a tiempo", p.cumplimiento_general !== null && p.cumplimiento_general < 90)
    + kpi("Entregas a tiempo", pct(p.puntualidad), `${num(p.a_tiempo)} de ${num(p.entregados)} entregados`, p.puntualidad !== null && p.puntualidad < 90)
    + kpi("Pasos repetidos", num(retrabajos), "por devoluciones de QA")
    + kpi("Visitas fallidas", num(p.visitas_fallidas), "recolectas o entregas")
    + kpi("Días promedio de cobro", p.cobro_dias_promedio === null ? "—" : num(p.cobro_dias_promedio), `${num(p.cobros_pendientes)} facturas pendientes`);
  $("kpisVolumen").innerHTML = kpi("Casos recibidos", num(p.creados), `${num(p.cn)} CN · ${num(p.rp)} RP`)
    + kpi("Digital / analógico", `${num(p.digital)} / ${num(p.analogo)}`)
    + kpi("Emergencias", num(p.emergencias))
    + kpi("Órdenes manuales", num(p.manuales), p.creados ? `${pct(100 * p.manuales / p.creados)} de lo recibido` : "capturadas por el laboratorio")
    + kpi("Tasa de reapertura", p.creados ? pct(100 * p.rp / p.creados) : "—", "RP sobre casos recibidos");
  $("tablaAreas").innerHTML = p.por_area.map(a => `<tr>
      <td class="principal"><b>${escapar(a.area)}</b></td>
      <td data-label="Meta">${horas(a.meta_horas)}</td>
      <td data-label="Terminados">${num(a.terminados)}</td>
      <td data-label="Promedio">${horas(a.promedio_horas)}</td>
      <td data-label="Mediana">${horas(a.mediana_horas)}</td>
      <td data-label="Dentro de meta">${estadoMeta(a.cumplimiento)}</td>
      <td data-label="Retrabajos">${num(a.retrabajos)}</td></tr>`).join("");
  $("porTipo").innerHTML = barras(p.por_tipo.map(x => ({ nombre: x.nombre, valor: x.total })));
  $("rpClas").innerHTML = barras(p.rp_clasificacion.map(x => ({ nombre: x.nombre, valor: x.total })), { vacio: "Sin reaperturas en el periodo" });
  $("rpMotivos").innerHTML = barras(p.rp_motivos.map(x => ({ nombre: x.nombre, valor: x.total })), { vacio: "Sin motivos registrados" });
  $("tablaTecnicos").innerHTML = p.por_tecnico.length ? p.por_tecnico.map(t => `<tr>
      <td class="principal"><b>${escapar(t.nombre)}</b></td>
      <td data-label="Áreas">${escapar(t.areas.join(", "))}</td>
      <td data-label="Terminados">${num(t.terminados)}</td>
      <td data-label="Promedio de trabajo">${horas(t.promedio_trabajo)}</td>
      <td data-label="Dentro de meta">${estadoMeta(t.cumplimiento)}</td>
      <td data-label="Devueltos por QA">${num(t.devueltos)}</td></tr>`).join("")
    : '<tr><td colspan="6" class="vacio">Sin pasos de producción terminados en el periodo.</td></tr>';
}

async function cargar() {
  $("errorDash").hidden = true;
  try {
    const d = await api("GET", `/metricas/operacion?desde=${$("fDesde").value}&hasta=${$("fHasta").value}`);
    pintarVivo(d.vivo); pintarPeriodo(d.periodo);
  } catch (error) { mostrarErrores($("errorDash"), error); }
}
/* Pestañas (se recuerda la elegida en la dirección) */
function mostrarTab(tab) {
  if (!document.querySelector(`[data-panel="${tab}"]`)) tab = "vivo";
  document.querySelectorAll("#pestanasDash button").forEach(b => b.classList.toggle("activa", b.dataset.tab === tab));
  document.querySelectorAll("[data-panel]").forEach(p => p.hidden = p.dataset.panel !== tab);
  $("rango").hidden = tab === "vivo";
  history.replaceState(null, "", "#" + tab);
}
$("pestanasDash").onclick = e => { const b = e.target.closest("[data-tab]"); if (b) mostrarTab(b.dataset.tab); };
mostrarTab(location.hash.slice(1));
$("btnActualizar").onclick = cargar;
$("btnPeriodo").onclick = cargar;
cargar();
setInterval(cargar, 120000);
