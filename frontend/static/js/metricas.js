/* ============ Utilidades de métricas (tiles, barras, estado de meta) ============ */
const num = v => v === null || v === undefined ? "—" : Number(v).toLocaleString("es-GT", { maximumFractionDigits: 1 });
const pct = v => v === null || v === undefined ? "—" : `${num(v)} %`;
const horas = v => v === null || v === undefined ? "—" : `${num(v)} h`;
function kpi(etiqueta, valor, detalle = "", alerta = false) {
  return `<div class="kpi ${alerta ? "alerta" : ""}"><span>${etiqueta}</span><b>${valor}</b>${detalle ? `<small>${detalle}</small>` : ""}</div>`;
}
/** Barras horizontales de una sola serie (magnitud): un solo color, valor al final de cada barra. */
function barras(filas, { formato = num, vacio = "Sin datos en el periodo" } = {}) {
  if (!filas.length) return `<div class="vacio" style="padding:18px">${vacio}</div>`;
  const max = Math.max(...filas.map(f => f.valor), 1);
  return `<div class="barras">${filas.map(f => `
    <div class="barra-fila" title="${escapar(f.nombre)}: ${escapar(formato(f.valor))}${f.detalle ? " · " + escapar(f.detalle) : ""}">
      <span class="n">${escapar(f.nombre)}</span>
      <span class="pista-b"><i style="width:${Math.max(2, f.valor * 100 / max)}%"></i></span>
      <span class="v">${escapar(formato(f.valor))}</span></div>`).join("")}</div>`;
}
/** Estado frente a la meta: siempre con texto, nunca solo color. */
function estadoMeta(cumplimiento, umbral = 90) {
  if (cumplimiento === null || cumplimiento === undefined) return '<span class="estado-meta na">Sin datos</span>';
  return cumplimiento >= umbral ? `<span class="estado-meta ok">✓ ${pct(cumplimiento)}</span>` : `<span class="estado-meta mal">▲ ${pct(cumplimiento)}</span>`;
}
const fechaCortaM = s => new Date(s + "T12:00:00").toLocaleDateString("es-GT", { day: "numeric", month: "short" });
