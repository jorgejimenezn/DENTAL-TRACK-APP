/* ============ Pantalla de empleados ============ */
const yo = iniciarPagina(["admin"]);
if (!yo) throw new Error("sin acceso");

const ROLES = {
  admin: "Administra usuarios, clientes, catálogos y flujos.",
  supervisor: "Supervisa todo el laboratorio: ve todas las órdenes, reasigna, cambia prioridades, registra ausencias y cancela. Sin acceso a configuración ni usuarios.",
  operaciones: "Gerencia de área: solo consulta el dashboard de operación, métricas, cobros y solicitudes. No modifica nada.",
  ingresos: "Recibe y valida las solicitudes nuevas.",
  tecnico: "Trabaja las órdenes asignadas en la línea de producción.",
  qa: "Valida los RP y hace el control de calidad final.",
  facturacion: "Facturación, empaque y cobros.",
  logistica: "Coordina rutas y asigna recolectas y entregas a los mensajeros.",
  mensajero: "Realiza las recolectas y entregas asignadas y las marca desde su celular.",
};

let empleados = [];
let areas = [];
let modo = "crear";
let actual = null;

$("fRol").innerHTML += Object.keys(ROLES).map(r => `<option value="${r}">${NOMBRES_ROL[r]}</option>`).join("");
$("eRol").innerHTML = Object.keys(ROLES).map(r => `<option value="${r}">${NOMBRES_ROL[r]}</option>`).join("");
$("eRol").onchange = () => { $("ayudaRol").textContent = ROLES[$("eRol").value]; };

async function cargarAreas() {
  try {
    areas = await api("GET", "/areas");
    $("eAreas").innerHTML = areas.map(a => `<label><input type="checkbox" value="${a.id}">${escapar(a.nombre)}</label>`).join("");
  } catch (error) { toast(error.message, true); }
}

async function cargar() {
  const params = new URLSearchParams();
  if ($("fTexto").value.trim()) params.set("q", $("fTexto").value.trim());
  if ($("fRol").value) params.set("rol", $("fRol").value);
  if ($("fEstado").value) params.set("activo", $("fEstado").value);
  try {
    empleados = await api("GET", "/empleados?" + params);
    pintar();
  } catch (error) {
    $("tabla").innerHTML = `<tr><td colspan="7" class="vacio">${escapar(error.message)}</td></tr>`;
  }
}

function pintar() {
  if (!empleados.length) {
    $("tabla").innerHTML = '<tr><td colspan="7" class="vacio">No hay empleados con esos filtros.</td></tr>';
    return;
  }
  $("tabla").innerHTML = empleados.map(e => `
    <tr>
      <td class="principal"><b>${escapar(e.nombre)} ${escapar(e.apellido)}</b>${e.id === yo.id ? ' <span class="badge gris">Tú</span>' : ""}<span class="sub">${escapar(e.email)}${e.telefono ? " · " + escapar(e.telefono) : ""}</span></td>
      <td data-label="Máx. trabajos">${e.max_trabajos ? `<span class="badge gris">${e.max_trabajos}</span>` : '<span class="sub" style="display:inline">Sin límite</span>'}</td>
      <td data-label="Rol"><span class="badge ${e.rol === "admin" ? "blanco" : "gris"}">${NOMBRES_ROL[e.rol] || e.rol}</span></td>
      <td data-label="Áreas"><div class="chips">${e.areas.length ? e.areas.map(a => `<span class="badge azul">${escapar(a.nombre)}</span>`).join("") : '<span style="color:var(--texto-3)">—</span>'}</div></td>
      <td data-label="Último acceso">${fechaHora(e.ultimo_acceso)}</td>
      <td data-label="Estado"><span class="badge ${e.activo ? "verde" : "rojo"}">${e.activo ? "Activo" : "Inactivo"}</span></td>
      <td class="acciones">
        <button class="btn chico" data-editar="${e.id}">Editar</button>
        ${e.id === yo.id ? "" : `<button class="btn chico ${e.activo ? "rojo-borde" : "verde-borde"}" data-estado="${e.id}">${e.activo ? "Desactivar" : "Activar"}</button>`}
      </td>
    </tr>`).join("");
}

$("tabla").addEventListener("click", async ev => {
  const editar = ev.target.closest("[data-editar]"), estado = ev.target.closest("[data-estado]");
  if (editar) abrir(empleados.find(x => x.id === +editar.dataset.editar));
  if (estado) {
    const e = empleados.find(x => x.id === +estado.dataset.estado);
    if (!confirm(`¿Seguro que quieres ${e.activo ? "desactivar" : "activar"} a ${e.nombre} ${e.apellido}?`)) return;
    try {
      await api("PATCH", `/empleados/${e.id}/estado`, { activo: !e.activo });
      toast(`Empleado ${e.activo ? "desactivado" : "activado"}`);
      cargar();
    } catch (error) { toast(error.message, true); }
  }
});

$("fTexto").addEventListener("input", debounce(cargar));
$("fRol").onchange = cargar;
$("fEstado").onchange = cargar;

function abrir(empleado = null) {
  modo = empleado ? "editar" : "crear";
  actual = empleado;
  $("formEmpleado").reset();
  $("errorEmpleado").hidden = true;
  document.querySelectorAll("#formEmpleado .campo.error").forEach(c => c.classList.remove("error"));
  $("tituloModal").textContent = empleado ? `Editar · ${empleado.nombre} ${empleado.apellido}` : "Nuevo empleado";
  $("bloquePassword").hidden = !!empleado;
  $("btnResetPass").hidden = !empleado;
  $("eNombre").value = empleado?.nombre || "";
  $("eApellido").value = empleado?.apellido || "";
  $("eEmail").value = empleado?.email || "";
  $("eTelefono").value = empleado?.telefono || "";
  $("eDireccion").value = empleado?.direccion || "";
  $("eMax").value = empleado?.max_trabajos ?? "";
  $("eRol").value = empleado?.rol || "tecnico";
  $("eRol").onchange();
  const ids = new Set((empleado?.areas || []).map(a => a.id));
  $("eAreas").querySelectorAll("input").forEach(i => { i.checked = ids.has(+i.value); });
  $("modalEmpleado").showModal();
}
$("btnNuevo").onclick = () => abrir();

$("formEmpleado").onsubmit = async ev => {
  ev.preventDefault();
  const errores = {
    nombre: $("eNombre").value.trim().length < 2,
    apellido: $("eApellido").value.trim().length < 2,
    email: !correoValido($("eEmail").value),
    telefono: !!$("eTelefono").value.trim() && !telefonoValido($("eTelefono").value),
    max_trabajos: !!$("eMax").value && !(Number.isInteger(Number($("eMax").value)) && Number($("eMax").value) >= 1 && Number($("eMax").value) <= 200),
    password: modo === "crear" && $("ePassword").value.length < 8,
  };
  document.querySelectorAll("#formEmpleado [data-campo]").forEach(c => c.classList.toggle("error", !!errores[c.dataset.campo]));
  if (Object.values(errores).some(Boolean)) { mostrarErrores($("errorEmpleado"), new Error("Revisa los campos marcados en rojo.")); return; }

  const datos = {
    nombre: $("eNombre").value.trim(), apellido: $("eApellido").value.trim(), email: $("eEmail").value.trim(),
    telefono: limpiarNumero($("eTelefono").value) || null, direccion: $("eDireccion").value.trim() || null,
    max_trabajos: $("eMax").value ? Number($("eMax").value) : null,
    rol: $("eRol").value, area_ids: [...$("eAreas").querySelectorAll("input:checked")].map(i => +i.value),
  };
  $("btnGuardar").disabled = true;
  try {
    if (modo === "crear") await api("POST", "/empleados", { ...datos, password: $("ePassword").value });
    else await api("PUT", `/empleados/${actual.id}`, datos);
    $("modalEmpleado").close();
    toast(modo === "crear" ? "Empleado creado" : "Cambios guardados");
    cargar();
  } catch (error) {
    mostrarErrores($("errorEmpleado"), error);
  } finally {
    $("btnGuardar").disabled = false;
  }
};

$("btnGenerar").onclick = () => {
  const letras = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789";
  $("ePassword").value = Array.from(crypto.getRandomValues(new Uint32Array(10)), n => letras[n % letras.length]).join("");
  $("ePassword").closest(".campo").classList.remove("error");
};

$("btnResetPass").onclick = () => {
  $("formPassword").reset(); $("errorPassword").hidden = true;
  $("textoPassword").textContent = `Nueva contraseña para ${actual.nombre} ${actual.apellido} (${actual.email}).`;
  $("modalPassword").showModal();
};
$("formPassword").onsubmit = async ev => {
  ev.preventDefault();
  try {
    await api("POST", `/empleados/${actual.id}/password`, { password: $("nuevaPassword").value });
    $("modalPassword").close(); toast("Contraseña actualizada");
  } catch (error) { mostrarErrores($("errorPassword"), error); }
};

document.querySelectorAll("[data-cerrar]").forEach(b => b.onclick = () => b.closest("dialog").close());
cargarAreas().then(cargar);
