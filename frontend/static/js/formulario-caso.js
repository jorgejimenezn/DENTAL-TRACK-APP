/* ============ Piezas comunes de los formularios de caso nuevo (CN) y reapertura (RP) ============ */
const ymd = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const fechaCorta = s => new Date(s + "T12:00:00").toLocaleDateString("es-GT", { weekday: "short", day: "numeric", month: "short", year: "numeric" });
const PIEZAS_SUP = [11, 12, 13, 14, 15, 16, 17, 18, 21, 22, 23, 24, 25, 26, 27, 28];
const PIEZAS_INF = [31, 32, 33, 34, 35, 36, 37, 38, 41, 42, 43, 44, 45, 46, 47, 48];

/* ---------------- Odontograma FDI ---------------- */
const FORMAS = {
  incisivo: { w: 24, raiz: '<path class="raiz" d="M7 36 C8 20 10 7 12 3 C14 7 16 20 17 36 Z"/>',
    corona: '<path class="corona" d="M5 36 Q12 32 19 36 L20 58 Q12 67 4 58 Z"/><path class="surco" d="M8 58 Q12 61 16 58"/>' },
  canino: { w: 26, raiz: '<path class="raiz" d="M8 36 C9 18 11 3 13 1 C15 3 17 18 18 36 Z"/>',
    corona: '<path class="corona" d="M5 36 Q13 32 21 36 L21 55 L13 67 L5 55 Z"/>' },
  premolar: { w: 28, raiz: '<path class="raiz" d="M8 36 C9 20 12 7 14 4 C16 7 19 20 20 36 Z"/>',
    corona: '<path class="corona" d="M4 36 Q14 31 24 36 Q26 50 23 61 Q14 67 5 61 Q2 50 4 36 Z"/><path class="surco" d="M14 44 L14 58"/>' },
  molar: { w: 36, raiz: '<path class="raiz" d="M5 36 C5 22 7 11 10 6 C12 13 14 24 16 35 Z"/><path class="raiz" d="M20 35 C22 24 24 13 26 6 C29 11 31 22 31 36 Z"/>',
    corona: '<path class="corona" d="M3 36 Q18 30 33 36 Q35 50 32 62 Q18 68 4 62 Q1 50 3 36 Z"/><path class="surco" d="M10 48 Q18 54 26 48 M18 40 L18 60"/>' },
};
const tipoDiente = n => { const u = n % 10; return u <= 2 ? "incisivo" : u === 3 ? "canino" : u <= 5 ? "premolar" : "molar"; };

/**
 * Dibuja el odontograma dentro de `contenedor`.
 * permitidas: lista de piezas habilitadas (null = todas). Se usa en la reapertura.
 */
function crearOdontograma(contenedor, { permitidas = null, alCambiar = () => {} } = {}) {
  const seleccion = new Set();
  const habilitada = n => !permitidas || permitidas.includes(n);
  const orden = { q1: [18, 17, 16, 15, 14, 13, 12, 11], q2: [21, 22, 23, 24, 25, 26, 27, 28],
                  q4: [48, 47, 46, 45, 44, 43, 42, 41], q3: [31, 32, 33, 34, 35, 36, 37, 38] };
  const diente = (n, superior) => {
    const f = FORMAS[tipoDiente(n)];
    const g = superior ? f.raiz + f.corona : `<g transform="translate(0,70) scale(1,-1)">${f.raiz + f.corona}</g>`;
    const svg = `<svg viewBox="0 0 ${f.w} 70" style="width:${(f.w * 0.92).toFixed(1)}px" aria-hidden="true">${g}</svg>`;
    const num = `<span class="num">${n}</span>`;
    return `<button type="button" class="diente" data-n="${n}" title="Pieza ${n}" aria-pressed="false" ${habilitada(n) ? "" : "disabled"}>${superior ? svg + num : num + svg}</button>`;
  };
  const cuadrante = q => `<div class="cuadrante">${orden[q].map(n => diente(n, q === "q1" || q === "q2")).join("")}</div>`;
  const hay = lista => lista.some(habilitada);
  contenedor.innerHTML = `
    <div class="odonto-wrap"><div class="odonto">
      <div class="etiqueta-arcada">Arcada superior</div>
      <div class="arcada sup">${cuadrante("q1")}<div class="linea-media"></div>${cuadrante("q2")}</div>
      <div class="arcada inf">${cuadrante("q4")}<div class="linea-media"></div>${cuadrante("q3")}</div>
      <div class="etiqueta-arcada">Arcada inferior</div>
    </div></div>
    <div class="acciones-odonto">
      ${hay(PIEZAS_SUP) ? '<button type="button" class="btn chico" data-sel="sup">Arcada superior</button>' : ""}
      ${hay(PIEZAS_INF) ? '<button type="button" class="btn chico" data-sel="inf">Arcada inferior</button>' : ""}
      <button type="button" class="btn chico" data-sel="todo">${permitidas ? "Todas las del caso" : "Boca completa"}</button>
      <button type="button" class="btn chico rojo-borde" data-sel="limpiar">Limpiar</button>
      <div class="resumen-piezas">Ninguna pieza seleccionada</div>
    </div>
    <div class="aviso rojo" data-error hidden>Selecciona al menos una pieza dental.</div>`;

  const pintar = () => {
    contenedor.querySelectorAll(".diente").forEach(d => {
      const on = seleccion.has(Number(d.dataset.n));
      d.classList.toggle("sel", on); d.setAttribute("aria-pressed", on);
    });
    const lista = [...seleccion].sort((a, b) => a - b);
    contenedor.querySelector(".resumen-piezas").innerHTML = lista.length
      ? `<b>${lista.length}</b> pieza(s): ${lista.join(", ")}` : "Ninguna pieza seleccionada";
    if (lista.length) contenedor.querySelector("[data-error]").hidden = true;
    alCambiar();
  };
  contenedor.addEventListener("click", e => {
    const d = e.target.closest(".diente");
    if (d && !d.disabled) { const n = Number(d.dataset.n); seleccion.has(n) ? seleccion.delete(n) : seleccion.add(n); return pintar(); }
    const b = e.target.closest("[data-sel]");
    if (!b) return;
    const t = b.dataset.sel;
    if (t === "limpiar") seleccion.clear();
    if (t === "sup" || t === "todo") PIEZAS_SUP.filter(habilitada).forEach(n => seleccion.add(n));
    if (t === "inf" || t === "todo") PIEZAS_INF.filter(habilitada).forEach(n => seleccion.add(n));
    pintar();
  });
  return {
    lista: () => [...seleccion].sort((a, b) => a - b),
    poner(lista) { seleccion.clear(); lista.filter(habilitada).forEach(n => seleccion.add(n)); pintar(); },
    validar(mostrar) {
      const ok = seleccion.size > 0;
      if (mostrar) contenedor.querySelector("[data-error]").hidden = ok;
      return ok ? null : contenedor.querySelector("[data-error]");
    },
  };
}

/* ---------------- Dirección existente / nueva ---------------- */
function crearDireccion(contenedor, prefijo, alCambiar = () => {}) {
  const p = prefijo;
  let modo = "existente", direcciones = [];
  contenedor.innerHTML = `
    <div class="segmento"><button type="button" data-m="existente" class="activo">Dirección existente</button><button type="button" data-m="nueva">Nueva dirección</button></div>
    <div class="campo" id="${p}CampoEx">
      <select id="${p}Sel"></select>
      <div class="msg-error">Selecciona una dirección.</div>
    </div>
    <div class="grid" id="${p}Nueva" hidden>
      <div class="campo" id="${p}CDep"><label>Departamento <span class="req">*</span></label>
        <select id="${p}Dep"><option value="">Selecciona</option>${DEPARTAMENTOS.map(d => `<option>${d}</option>`).join("")}</select><div class="msg-error">Requerido.</div></div>
      <div class="campo" id="${p}CMun"><label>Municipio <span class="req">*</span></label>
        <input id="${p}Mun" list="${p}MunList" placeholder="Escribe o elige" maxlength="80"><datalist id="${p}MunList"></datalist><div class="msg-error">Requerido.</div></div>
      <div class="campo span2" id="${p}CDir"><label>Dirección completa <span class="req">*</span></label>
        <input id="${p}Dir" placeholder="Calle o avenida, número, zona, edificio, referencia" maxlength="250"><div class="msg-error">Mínimo 5 caracteres.</div></div>
      <label class="check-linea span2"><input type="checkbox" id="${p}Guardar" checked> Guardar en mis direcciones</label>
    </div>`;
  const cambiarModo = m => {
    modo = m;
    contenedor.querySelectorAll(".segmento button").forEach(x => x.classList.toggle("activo", x.dataset.m === m));
    $(p + "CampoEx").hidden = m !== "existente";
    $(p + "Nueva").hidden = m !== "nueva";
    alCambiar();
  };
  contenedor.querySelectorAll(".segmento button").forEach(b => b.onclick = () => cambiarModo(b.dataset.m));
  $(p + "Dep").onchange = () => {
    $(p + "MunList").innerHTML = (MUNICIPIOS[$(p + "Dep").value] || []).map(m => `<option value="${escapar(m)}">`).join("");
    $(p + "Mun").value = "";
  };
  const texto = d => `${d.direccion} · ${d.municipio}, ${d.departamento}`;
  return {
    poner(lista) {
      direcciones = lista;
      $(p + "Sel").innerHTML = `<option value="">${lista.length ? "Selecciona una dirección" : "No hay direcciones guardadas"}</option>`
        + lista.map(d => `<option value="${d.id}">${escapar(texto(d))}${d.principal ? " (principal)" : ""}</option>`).join("");
      const principal = lista.find(d => d.principal) || lista[0];
      if (principal) $(p + "Sel").value = principal.id;
      cambiarModo(lista.length ? "existente" : "nueva");
    },
    validar(mostrar) {
      const reglas = modo === "existente" ? [[p + "CampoEx", !!$(p + "Sel").value]]
        : [[p + "CDep", !!$(p + "Dep").value], [p + "CMun", $(p + "Mun").value.trim().length >= 2],
           [p + "CDir", $(p + "Dir").value.trim().length >= 5]];
      let primero = null;
      reglas.forEach(([id, ok]) => { if (!ok && !primero) primero = $(id); if (mostrar) $(id).classList.toggle("error", !ok); });
      return primero;
    },
    valor() {
      return modo === "existente" ? { tipo: "existente", direccion_id: Number($(p + "Sel").value) || null }
        : { tipo: "nueva", departamento: $(p + "Dep").value || null, municipio: $(p + "Mun").value.trim() || null,
            direccion: $(p + "Dir").value.trim() || null, guardar: $(p + "Guardar").checked };
    },
    texto() {
      if (modo === "existente") { const d = direcciones.find(x => x.id == $(p + "Sel").value); return d ? `${d.municipio}, ${d.departamento}` : "—"; }
      return $(p + "Mun").value.trim() ? `${$(p + "Mun").value.trim()}, ${$(p + "Dep").value} (nueva)` : "Nueva · pendiente";
    },
  };
}

/* ---------------- Modalidad digital / analógico ---------------- */
function crearModalidad(alCambiar = () => {}) {
  let actual = "digital", disponibles = ["digital", "analogo"];
  const tarjetas = document.querySelectorAll(".opcion-mod");
  const elegir = m => {
    actual = m;
    tarjetas.forEach(o => { o.classList.toggle("activa", o.dataset.mod === m); o.querySelector("input").checked = o.dataset.mod === m; });
    $("panelDigital").hidden = m !== "digital";
    $("panelAnalogo").hidden = m !== "analogo";
    alCambiar(m);
  };
  tarjetas.forEach(o => o.addEventListener("click", e => {
    e.preventDefault();
    if (!disponibles.includes(o.dataset.mod)) return toast("Ese tipo de trabajo no se recibe en esta modalidad", true);
    if (o.dataset.mod !== actual) elegir(o.dataset.mod);
  }));
  return {
    valor: () => actual,
    /** Limita las modalidades según los flujos activos del tipo de trabajo. */
    limitar(lista) {
      disponibles = lista && lista.length ? lista : ["digital", "analogo"];
      tarjetas.forEach(o => o.classList.toggle("no-disponible", !disponibles.includes(o.dataset.mod)));
      if (!disponibles.includes(actual)) { elegir(disponibles[0]); toast(`Se cambió a modalidad ${disponibles[0] === "digital" ? "digital" : "analógica"}: es la única disponible para ese trabajo`); }
    },
    elegir,
  };
}

/* ---------------- Adjuntos (se suben al elegirlos, a MongoDB) ---------------- */
function crearAdjuntos({ zona, input, lista, soloStl = false, alCambiar = () => {} }) {
  const items = [];  // {clave, archivo, id, progreso, error}
  let clave = 0;
  const tamano = b => b >= 1048576 ? (b / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(b / 1024)) + " KB";
  const pintar = () => {
    lista.innerHTML = items.map(it => {
      const ext = it.archivo.name.split(".").pop().toUpperCase();
      const estado = it.error ? escapar(it.error) : it.id ? "Listo" : `Subiendo ${it.progreso}%`;
      return `<div class="archivo ${it.error ? "falla" : ""}"><span class="tipo ${ext === "STL" ? "stl" : ""}">${escapar(ext)}</span>
        <span class="nombre-archivo">${escapar(it.archivo.name)}</span><span class="peso">${tamano(it.archivo.size)}</span>
        <span class="estado-archivo">${estado}</span>
        <button type="button" data-quitar="${it.clave}" title="Quitar" aria-label="Quitar ${escapar(it.archivo.name)}">×</button>
        ${!it.id && !it.error ? `<span class="barra" style="width:${it.progreso}%"></span>` : ""}</div>`;
    }).join("");
    alCambiar();
  };
  const agregar = archivos => {
    for (const archivo of archivos) {
      const ext = "." + archivo.name.split(".").pop().toLowerCase();
      const permitidas = soloStl ? [".stl"] : [".jpg", ".jpeg", ".png", ".pdf", ".stl"];
      if (!permitidas.includes(ext)) { toast(`${archivo.name}: solo se permiten ${soloStl ? "archivos STL" : "JPG, PNG, PDF o STL"}`, true); continue; }
      const it = { clave: ++clave, archivo, id: null, progreso: 0, error: null };
      items.push(it);
      subirArchivo(archivo, pct => { it.progreso = pct; pintar(); })
        .then(r => { it.id = r.id; pintar(); })
        .catch(e => { it.error = e.message; pintar(); });
    }
    pintar();
  };
  zona.onclick = () => input.click();
  zona.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } };
  zona.ondragover = e => { e.preventDefault(); zona.classList.add("sobre"); };
  zona.ondragleave = () => zona.classList.remove("sobre");
  zona.ondrop = e => { e.preventDefault(); zona.classList.remove("sobre"); agregar([...e.dataTransfer.files]); };
  input.onchange = () => { agregar([...input.files]); input.value = ""; };
  lista.addEventListener("click", e => {
    const b = e.target.closest("[data-quitar]");
    if (!b) return;
    const i = items.findIndex(x => x.clave === Number(b.dataset.quitar));
    if (i < 0) return;
    const [it] = items.splice(i, 1);
    if (it.id) api("DELETE", `/archivos/${it.id}`).catch(() => {});
    pintar();
  });
  return {
    ids: () => items.filter(x => x.id).map(x => x.id),
    subiendo: () => items.some(x => !x.id && !x.error),
    conError: () => items.some(x => x.error),
    hayStl: () => items.some(x => x.id && x.archivo.name.toLowerCase().endsWith(".stl")),
    cantidad: () => items.filter(x => x.id).length,
  };
}

/* ---------------- Fecha de entrega con las reglas del laboratorio ---------------- */
function crearFechaEntrega({ alCambiar = () => {} } = {}) {
  let primera = null, bloqueados = {};
  const cargarCalendario = async () => {
    const anio = new Date().getFullYear();
    const [a, b] = await Promise.all([api("GET", `/config/calendario?anio=${anio}`), api("GET", `/config/calendario?anio=${anio + 1}`)]);
    bloqueados = Object.fromEntries([...a, ...b].filter(d => !d.hora_corte).map(d => [d.fecha, d.motivo]));
  };
  const listo = cargarCalendario().catch(() => {});
  const validar = mostrar => {
    const v = $("fecha").value;
    let msg = "";
    if (!v) msg = "Selecciona una fecha de entrega.";
    else {
      const d = new Date(v + "T12:00:00");
      if (d.getDay() === 0 || d.getDay() === 6) msg = "Los sábados y domingos no hay entregas.";
      else if (bloqueados[v]) msg = `Ese día no se labora: ${bloqueados[v]}.`;
      else if (primera && v < primera) msg = `La fecha más cercana disponible es ${fechaCorta(primera)}.`;
    }
    if (mostrar) { $("campoFecha").classList.toggle("error", !!msg); $("msgFecha").textContent = msg; }
    return msg ? $("campoFecha") : null;
  };
  $("fecha").addEventListener("change", () => { validar(true); alCambiar(); });
  return {
    async recalcular(modalidad, emergencia) {
      await listo;
      try {
        const r = await api("GET", `/config/fecha-minima?modalidad=${modalidad}&emergencia=${emergencia}`);
        primera = r.primera_fecha;
        $("fecha").min = primera;
        const max = new Date(); max.setDate(max.getDate() + 180); $("fecha").max = ymd(max);
        $("fechaInfo").innerHTML = `<span class="chip">${escapar(r.nota)}</span>`
          + `<span class="chip ${emergencia ? "rojo" : ""}">Mínimo ${r.dias_minimos} día(s) hábil(es)${emergencia ? " · emergencia" : ""}</span>`
          + `<span class="chip azul">Primera fecha: ${escapar(fechaCorta(primera))}</span>`;
        if (!$("fecha").value || $("fecha").value < primera) $("fecha").value = primera;
        validar(true);
      } catch (e) { $("fechaInfo").innerHTML = `<span class="chip rojo">${escapar(e.message)}</span>`; }
      alCambiar();
    },
    validar,
    valor: () => $("fecha").value || null,
  };
}

/** Enlaza el interruptor de emergencia (la tarjeta completa es clicable). */
function prepararEmergencia(alCambiar) {
  $("cajaEmergencia").addEventListener("click", e => {
    if (e.target.closest(".switch")) return;
    $("emergencia").checked = !$("emergencia").checked;
    $("emergencia").dispatchEvent(new Event("change"));
  });
  $("emergencia").addEventListener("change", () => {
    $("cajaEmergencia").classList.toggle("on", $("emergencia").checked);
    alCambiar($("emergencia").checked);
  });
}

/** Muestra el primer error y lleva la pantalla hasta él. */
function irAlError(elemento) {
  elemento.scrollIntoView({ behavior: "smooth", block: "center" });
  toast("Revisa los campos marcados en rojo", true);
}
