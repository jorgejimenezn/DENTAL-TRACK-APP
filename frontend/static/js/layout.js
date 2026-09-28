/* ============ Menú lateral, protección de páginas y marca de agua ============ */
const ICONOS = {
  inicio: '<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  clientes: '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><path d="M16 4.5a3 3 0 0 1 0 6M18 14c2 .8 3 2.8 3 6"/>',
  empleados: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/>',
  bitacora: '<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h7M9 17h5"/>',
  solicitud: '<path d="M12 5v14M5 12h14"/>',
  catalogos: '<rect x="3" y="4" width="7" height="7" rx="1.5"/><rect x="14" y="4" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  flujos: '<circle cx="5" cy="6" r="2"/><circle cx="19" cy="6" r="2"/><circle cx="12" cy="18" r="2"/><path d="M7 6h10M6 8l5 8M18 8l-5 8"/>',
  asignaciones: '<circle cx="8" cy="8" r="3"/><path d="M3 19c0-2.8 2.2-5 5-5s5 2.2 5 5"/><path d="M15 9l2 2 4-4"/>',
  calendario: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  bandeja: '<path d="M3 13l3-8h12l3 8v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M3 13h5l1 3h6l1-3h5"/>',
  tablero: '<rect x="3" y="4" width="5" height="16" rx="1.5"/><rect x="10" y="4" width="5" height="11" rx="1.5"/><rect x="17" y="4" width="4" height="7" rx="1.5"/>',
  dashboard: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  metas: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1"/>',
  ausencias: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4M9 14l6 5M15 14l-6 5"/>',
  cobros: '<rect x="2" y="6" width="20" height="13" rx="2"/><path d="M2 10h20M6 15h4"/>',
  casos: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
};

const MENU = [
  { href: "inicio.html", texto: "Inicio", icono: "inicio", roles: null },
  { grupo: "Administración", roles: ["admin", "demo"] },
  { href: "clientes.html", texto: "Clientes", icono: "clientes", roles: ["admin", "demo"] },
  { href: "empleados.html", texto: "Empleados", icono: "empleados", roles: ["admin", "demo"] },
  { href: "bitacora.html", texto: "Bitácora", icono: "bitacora", roles: ["admin", "demo"] },
  { grupo: "Configuración", roles: ["admin", "demo"] },
  { href: "catalogos.html", texto: "Catálogos", icono: "catalogos", roles: ["admin", "demo"] },
  { href: "flujos.html", texto: "Flujos de trabajo", icono: "flujos", roles: ["admin", "demo"] },
  { href: "asignaciones.html", texto: "Asignaciones", icono: "asignaciones", roles: ["admin", "demo"] },
  { href: "calendario.html", texto: "Calendario y reglas", icono: "calendario", roles: ["admin", "demo"] },
  { href: "areas.html", texto: "Áreas y metas", icono: "metas", roles: ["admin", "demo"] },
  { grupo: "Operación", roles: ["admin", "supervisor", "operaciones", "facturacion", "demo"] },
  { href: "dashboard.html", texto: "Dashboard", icono: "dashboard", roles: ["admin", "supervisor", "operaciones", "demo"] },
  { href: "ausencias.html", texto: "Ausencias", icono: "ausencias", roles: ["admin", "supervisor", "demo"] },
  { href: "cobros.html", texto: "Cobros", icono: "cobros", roles: ["admin", "supervisor", "operaciones", "facturacion", "demo"] },
  { grupo: "Solicitudes", roles: null },
  { href: "nueva-solicitud.html", texto: "Nueva solicitud", icono: "solicitud", roles: ["doctor", "admin", "supervisor", "ingresos", "demo"] },
  { href: "bandeja.html", texto: "Mi bandeja", icono: "bandeja", roles: ["ingresos", "tecnico", "qa", "facturacion", "logistica"] },
  { href: "bandeja.html", texto: "Mis rutas", icono: "bandeja", roles: ["mensajero"] },
  { href: "bandeja.html", texto: "Bandeja del laboratorio", icono: "bandeja", roles: ["admin", "supervisor"] },
  { href: "bandeja.html", texto: "Línea de producción", icono: "bandeja", roles: ["demo"] },
  { href: "tablero.html", texto: "Mi tablero", icono: "tablero", roles: ["doctor"] },
  { href: "casos.html", texto: "Mis casos", icono: "casos", roles: ["doctor"] },
  { href: "clientes.html", texto: "Clientes", icono: "clientes", roles: ["supervisor", "ingresos", "facturacion"] },
  { href: "tablero.html", texto: "Tablero por cliente", icono: "tablero", roles: ["admin", "supervisor", "ingresos", "demo"] },
  { href: "casos.html", texto: "Solicitudes", icono: "casos", roles: ["admin", "demo", "supervisor", "operaciones", "ingresos", "tecnico", "qa", "facturacion", "logistica", "mensajero"] },
  { href: "mis-metricas.html", texto: "Mis métricas", icono: "dashboard", roles: ["ingresos", "tecnico", "qa", "facturacion", "logistica", "mensajero"] },
];
// Pantallas que el perfil demo solo consulta (el backend rechaza cualquier cambio)
const SOLO_LECTURA_DEMO = ["clientes.html", "empleados.html", "bitacora.html", "catalogos.html", "flujos.html", "asignaciones.html",
                           "calendario.html", "areas.html", "ausencias.html", "cobros.html"];
// Pantallas que no están en el menú: se marca la opción de la que dependen
const PADRES = { "caso.html": "casos.html", "reapertura.html": "casos.html" };

const LOGO = '<svg viewBox="0 0 40 40" fill="none"><path d="M12 5c-5 0-8 4-8 10 0 5 2 8 3 13 1 5 2 8 4 8 3 0 3-8 5-11 1-2 3-2 4 0 2 3 2 11 5 11 2 0 3-3 4-8 1-5 3-8 3-13 0-6-3-10-8-10-3 0-5 2-8 2s-5-2-8-2z" stroke="#fff" stroke-width="2.4" stroke-linejoin="round"/></svg>';

/**
 * Verifica la sesión y el rol, dibuja el menú y devuelve el usuario.
 * rolesPermitidos = null → cualquier usuario con sesión.
 */
function iniciarPagina(rolesPermitidos = null) {
  const sesion = Sesion.obtener();
  if (!sesion?.token) { location.href = "login.html"; return null; }
  const usuario = sesion.usuario;
  if (rolesPermitidos && !rolesPermitidos.includes(usuario.rol)) { location.href = "inicio.html"; return null; }

  const pagina = location.pathname.split("/").pop() || "inicio.html";
  const actual = PADRES[pagina] || pagina;
  const visibles = MENU.filter(m => !m.roles || m.roles.includes(usuario.rol));
  const enlaces = visibles.map(m => m.grupo
    ? `<div class="titulo-menu">${m.grupo}</div>`
    : `<a href="${m.href}" class="${m.href === actual ? "activo" : ""}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round">${ICONOS[m.icono]}</svg>${m.texto}</a>`
  ).join("");

  $("lateral").innerHTML = `
    <div class="logo">${LOGO}<span>DENTAL TRACK</span></div>
    <nav class="menu">${enlaces}</nav>
    <div class="usuario-lateral">
      <b>${escapar(usuario.nombre)} ${escapar(usuario.apellido)}</b>
      <span>${escapar(NOMBRES_ROL[usuario.rol] || usuario.rol)}</span>
      <button class="btn chico" id="btnSalir">Cerrar sesión</button>
    </div>`;
  $("btnSalir").onclick = () => Sesion.cerrar();
  prepararMenuMovil(visibles.find(m => m.href === pagina)?.texto || document.title.split("·")[0].trim());
  if (usuario.rol === "demo" && SOLO_LECTURA_DEMO.includes(pagina)) {
    document.body.classList.add("solo-lectura");
    const aviso = document.createElement("div");
    aviso.className = "aviso-demo";
    aviso.innerHTML = "<b>Modo demostración:</b> puedes consultar esta pantalla, pero los cambios no se guardan.";
    document.querySelector(".contenido")?.prepend(aviso);
  }
  dibujarMarcaAgua();
  return usuario;
}

/** Diente en malla de líneas y puntos, generado con código (marca de agua). */
function dibujarMarcaAgua() {
  const cont = $("marca");
  if (!cont) return;
  const contorno = [[60,95],[75,55],[105,30],[140,22],[172,30],[195,48],[210,52],[228,45],[255,26],[290,20],[325,32],[350,60],[362,100],[360,150],[350,200],[342,245],
    [348,290],[350,340],[348,400],[340,460],[328,515],[312,560],[292,566],[282,540],[276,480],[265,420],[248,370],[228,335],[210,328],[192,335],[172,370],[155,420],
    [142,480],[132,540],[118,566],[98,560],[84,515],[72,460],[64,400],[62,340],[66,290],[72,245],[62,200],[55,150]];
  let semilla = 11;
  const aleatorio = () => { semilla = (semilla * 16807) % 2147483647; return (semilla - 1) / 2147483646; };
  const dentro = (x, y) => {
    let c = false;
    for (let i = 0, j = contorno.length - 1; i < contorno.length; j = i++) {
      const [xi, yi] = contorno[i], [xj, yj] = contorno[j];
      if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) c = !c;
    }
    return c;
  };
  const puntos = [];
  contorno.forEach((p, i) => {
    const q = contorno[(i + 1) % contorno.length];
    puntos.push(p);
    const partes = Math.floor(Math.hypot(q[0] - p[0], q[1] - p[1]) / 38);
    for (let k = 1; k < partes; k++) puntos.push([p[0] + (q[0] - p[0]) * k / partes, p[1] + (q[1] - p[1]) * k / partes]);
  });
  const borde = puntos.length;
  while (puntos.length < borde + 60) { const x = 40 + aleatorio() * 330, y = 20 + aleatorio() * 545; if (dentro(x, y)) puntos.push([x, y]); }
  const segmentoDentro = (a, b) => { for (let t = .15; t < .9; t += .15) if (!dentro(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)) return false; return true; };
  const vistas = new Set();
  let lineas = "";
  puntos.forEach((a, i) => {
    const candidatos = puntos.map((b, j) => [j, Math.hypot(a[0] - b[0], a[1] - b[1])]).filter(([j, d]) => j !== i && d < 190).sort(() => aleatorio() - .5);
    let usadas = 0;
    for (const [j] of candidatos) {
      if (usadas >= 4) break;
      const clave = i < j ? i + "-" + j : j + "-" + i;
      if (vistas.has(clave) || !segmentoDentro(a, puntos[j])) continue;
      vistas.add(clave); usadas++;
      lineas += `<line x1="${a[0].toFixed(1)}" y1="${a[1].toFixed(1)}" x2="${puntos[j][0].toFixed(1)}" y2="${puntos[j][1].toFixed(1)}"/>`;
    }
  });
  cont.innerHTML = `<svg viewBox="0 0 420 590"><g stroke="var(--marca-linea)" stroke-width="1" fill="none">${lineas}<polygon points="${contorno.map(p => p.join(",")).join(" ")}" stroke-width="1.6"/></g><g fill="var(--marca-punto)">${puntos.map(p => `<circle cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="3"/>`).join("")}</g></svg>`;
}

/** Barra superior con botón ☰ para celular y tablet (el menú lateral se abre como cajón). */
function prepararMenuMovil(tituloActual) {
  if (document.querySelector(".barra-movil")) return;
  const barra = document.createElement("header");
  barra.className = "barra-movil";
  barra.innerHTML = `
    <button class="btn-menu" type="button" aria-label="Abrir menú"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>
    <div class="logo">${LOGO}<span>DENTAL TRACK</span></div>
    <span class="titulo-actual">${escapar(tituloActual)}</span>`;
  const velo = document.createElement("div");
  velo.className = "velo-menu";
  document.body.prepend(velo);
  document.body.prepend(barra);
  const cerrar = () => document.body.classList.remove("menu-abierto");
  barra.querySelector(".btn-menu").onclick = () => document.body.classList.add("menu-abierto");
  velo.onclick = cerrar;
  $("lateral").querySelectorAll("a").forEach(a => a.addEventListener("click", cerrar));
  document.addEventListener("keydown", e => { if (e.key === "Escape") cerrar(); });
}
