/* ============ Pantalla de clientes ============ */
if (!iniciarPagina(["admin"])) throw new Error("sin acceso");

let clientes = [];
let modo = "crear";            // crear | editar
let clienteActual = null;      // cliente en edición (con sus direcciones del servidor)
let direccionesLocales = [];   // direcciones al crear (aún no guardadas)
let direccionEditando = null;  // id (editar) o índice (crear) de la dirección en el formulario

/* ---------- Listado ---------- */
const formatoDocumento = c => c.tipo_documento === "NIT" && c.numero_documento.length > 1
  ? c.numero_documento.slice(0, -1) + "-" + c.numero_documento.slice(-1)
  : c.numero_documento;

async function cargar() {
  const params = new URLSearchParams();
  if ($("fTexto").value.trim()) params.set("q", $("fTexto").value.trim());
  if ($("fEstado").value) params.set("activo", $("fEstado").value);
  if ($("fNivel").value) params.set("nivel", $("fNivel").value);
  try {
    clientes = await api("GET", "/clientes?" + params);
    pintarTabla();
  } catch (error) {
    $("tabla").innerHTML = `<tr><td colspan="7" class="vacio">${escapar(error.message)}</td></tr>`;
  }
}

function pintarTabla() {
  if (!clientes.length) {
    $("tabla").innerHTML = '<tr><td colspan="7" class="vacio">No hay clientes con esos filtros.</td></tr>';
    return;
  }
  $("tabla").innerHTML = clientes.map(c => `
    <tr>
      <td class="principal"><b>${escapar(c.razon_social)}</b><span class="sub">${escapar(c.nombre_facturacion)}</span><span class="sub">${escapar(c.email)}</span></td>
      <td data-label="Clínica">${escapar(c.clinica || "—")} ${c.es_red ? '<span class="badge azul">Red</span>' : ""}</td>
      <td data-label="Documento">${escapar(c.tipo_documento)}<span class="sub">${escapar(formatoDocumento(c))}</span></td>
      <td data-label="Teléfono">${escapar(c.telefono_celular || "")}${c.telefono_celular && c.telefono_fijo ? "<br>" : ""}${escapar(c.telefono_fijo || "")}</td>
      <td data-label="Prioridad"><span class="badge ${c.nivel_prioridad === 2 ? "blanco" : "gris"}">${c.nivel_prioridad === 2 ? "2 · VIP" : "3 · Normal"}</span></td>
      <td data-label="Estado"><span class="badge ${c.activo ? "verde" : "rojo"}">${c.activo ? "Activo" : "Inactivo"}</span></td>
      <td class="acciones">
        <button class="btn chico" data-editar="${c.id}">Editar</button>
        <button class="btn chico ${c.activo ? "rojo-borde" : "verde-borde"}" data-estado="${c.id}">${c.activo ? "Desactivar" : "Activar"}</button>
      </td>
    </tr>`).join("");
}

$("tabla").addEventListener("click", async e => {
  const editar = e.target.closest("[data-editar]"), estado = e.target.closest("[data-estado]");
  if (editar) abrirEditar(+editar.dataset.editar);
  if (estado) {
    const c = clientes.find(x => x.id === +estado.dataset.estado);
    const accion = c.activo ? "desactivar" : "activar";
    if (!confirm(`¿Seguro que quieres ${accion} a ${c.razon_social}?${c.activo ? " No podrá iniciar sesión." : ""}`)) return;
    try {
      await api("PATCH", `/clientes/${c.id}/estado`, { activo: !c.activo });
      toast(`Cliente ${c.activo ? "desactivado" : "activado"}`);
      cargar();
    } catch (error) { toast(error.message, true); }
  }
});

$("fTexto").addEventListener("input", debounce(cargar));
$("fEstado").onchange = cargar;
$("fNivel").onchange = cargar;

/* ---------- Modal cliente ---------- */
function limpiarFormulario() {
  $("formCliente").reset();
  document.querySelectorAll("#formCliente .campo.error").forEach(c => c.classList.remove("error"));
  $("errorCliente").hidden = true;
  $("errorDireccion").hidden = true;
  cerrarFormDireccion();
}

$("btnNuevo").onclick = () => {
  modo = "crear"; clienteActual = null; direccionesLocales = [];
  limpiarFormulario();
  $("tituloModal").textContent = "Nuevo cliente";
  $("bloquePassword").hidden = false;
  $("btnResetPass").hidden = true;
  $("cNivel").value = "3";
  pintarDirecciones();
  abrirFormDireccion();
  $("modalCliente").showModal();
};

async function abrirEditar(id) {
  try {
    clienteActual = await api("GET", `/clientes/${id}`);
  } catch (error) { toast(error.message, true); return; }
  modo = "editar";
  limpiarFormulario();
  const c = clienteActual;
  $("tituloModal").textContent = `Editar · ${c.razon_social}`;
  $("bloquePassword").hidden = true;
  $("btnResetPass").hidden = false;
  $("cRazon").value = c.razon_social; $("cFacturacion").value = c.nombre_facturacion; $("cEmail").value = c.email;
  $("cCelular").value = c.telefono_celular || ""; $("cFijo").value = c.telefono_fijo || "";
  $("cClinica").value = c.clinica || ""; $("cRed").checked = c.es_red; $("cNivel").value = String(c.nivel_prioridad);
  $("cTipoDoc").value = c.tipo_documento; $("cDocumento").value = c.numero_documento;
  pintarDirecciones();
  $("modalCliente").showModal();
}

function validarCliente() {
  const errores = {};
  if ($("cRazon").value.trim().length < 2) errores.razon_social = true;
  if ($("cFacturacion").value.trim().length < 2) errores.nombre_facturacion = true;
  if (!correoValido($("cEmail").value)) errores.email = true;
  const celular = $("cCelular").value.trim(), fijo = $("cFijo").value.trim();
  $("msgCelular").textContent = "Debe tener 8 dígitos.";
  if (celular && !telefonoValido(celular)) errores.telefono_celular = true;
  if (fijo && !telefonoValido(fijo)) errores.telefono_fijo = true;
  if (!celular && !fijo) { errores.telefono_celular = true; $("msgCelular").textContent = "Ingresa al menos un teléfono."; }
  const tipo = $("cTipoDoc").value, doc = $("cDocumento").value;
  if (tipo === "NIT" ? !nitValido(doc) : !dpiValido(doc)) {
    errores.numero_documento = true;
    $("msgDoc").textContent = tipo === "NIT" ? "NIT no válido (revisa el dígito verificador)." : "DPI no válido (13 dígitos).";
  }
  if (modo === "crear" && $("cPassword").value.length < 8) errores.password = true;
  document.querySelectorAll("#formCliente [data-campo]").forEach(c => {
    if (["razon_social","nombre_facturacion","email","telefono_celular","telefono_fijo","numero_documento","password"].includes(c.dataset.campo))
      c.classList.toggle("error", !!errores[c.dataset.campo]);
  });
  return Object.keys(errores).length === 0;
}

function datosCliente() {
  return {
    razon_social: $("cRazon").value.trim(), nombre_facturacion: $("cFacturacion").value.trim(), email: $("cEmail").value.trim(),
    clinica: $("cClinica").value.trim() || null, es_red: $("cRed").checked,
    telefono_celular: limpiarNumero($("cCelular").value) || null, telefono_fijo: limpiarNumero($("cFijo").value) || null,
    tipo_documento: $("cTipoDoc").value, numero_documento: limpiarNumero($("cDocumento").value),
    nivel_prioridad: Number($("cNivel").value),
  };
}

$("formCliente").onsubmit = async e => {
  e.preventDefault();
  $("errorCliente").hidden = true;
  if (!validarCliente()) { mostrarErrores($("errorCliente"), new Error("Revisa los campos marcados en rojo.")); return; }
  if (modo === "crear" && !direccionesLocales.length) {
    mostrarErrores($("errorCliente"), new Error("Agrega al menos una dirección de entrega.")); return;
  }
  $("btnGuardar").disabled = true;
  try {
    if (modo === "crear") {
      await api("POST", "/clientes", { ...datosCliente(), password: $("cPassword").value, direcciones: direccionesLocales });
      toast("Cliente creado");
    } else {
      await api("PUT", `/clientes/${clienteActual.id}`, datosCliente());
      toast("Cambios guardados");
    }
    $("modalCliente").close();
    cargar();
  } catch (error) {
    mostrarErrores($("errorCliente"), error);
  } finally {
    $("btnGuardar").disabled = false;
  }
};

$("btnGenerar").onclick = () => {
  const letras = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789";
  $("cPassword").value = Array.from(crypto.getRandomValues(new Uint32Array(10)), n => letras[n % letras.length]).join("");
  $("cPassword").closest(".campo").classList.remove("error");
};

/* ---------- Direcciones ---------- */
$("dDepartamento").innerHTML = '<option value="">Selecciona</option>' + DEPARTAMENTOS.map(d => `<option>${d}</option>`).join("");
$("dDepartamento").onchange = () => {
  $("listaMunicipios").innerHTML = (MUNICIPIOS[$("dDepartamento").value] || []).map(m => `<option value="${m}">`).join("");
};

const listaDirecciones = () => modo === "crear" ? direccionesLocales : (clienteActual?.direcciones || []);

function pintarDirecciones() {
  const lista = listaDirecciones();
  $("listaDirecciones").innerHTML = lista.length ? lista.map((d, i) => `
    <div class="direccion-item">
      <div class="texto">${escapar(d.direccion)}<span>${escapar(d.municipio)}, ${escapar(d.departamento)}</span></div>
      <div class="botones">
        ${d.principal ? '<span class="badge blanco">Principal</span>' : ""}
        <button type="button" class="btn chico" data-edir="${modo === "crear" ? i : d.id}">Editar</button>
        <button type="button" class="btn chico rojo-borde" data-bdir="${modo === "crear" ? i : d.id}">Quitar</button>
      </div>
    </div>`).join("") : '<div class="ayuda" style="color:var(--texto-3);font-size:12px">Sin direcciones todavía.</div>';
}

function abrirFormDireccion(d = null, clave = null) {
  direccionEditando = clave;
  $("errorDireccion").hidden = true;
  document.querySelectorAll("#formDireccion .campo").forEach(c => c.classList.remove("error"));
  $("dDepartamento").value = d?.departamento || "Guatemala";
  $("dDepartamento").onchange();
  $("dMunicipio").value = d?.municipio || "";
  $("dDireccion").value = d?.direccion || "";
  $("dPrincipal").checked = d ? d.principal : !listaDirecciones().length;
  $("formDireccion").hidden = false;
  $("btnAgregarDir").hidden = true;
}

function cerrarFormDireccion() {
  $("formDireccion").hidden = true;
  $("btnAgregarDir").hidden = false;
  direccionEditando = null;
}

$("btnAgregarDir").onclick = () => abrirFormDireccion();
$("btnCancelarDir").onclick = cerrarFormDireccion;

$("listaDirecciones").addEventListener("click", async e => {
  const editar = e.target.closest("[data-edir]"), borrar = e.target.closest("[data-bdir]");
  if (editar) {
    const clave = +editar.dataset.edir;
    const d = modo === "crear" ? direccionesLocales[clave] : clienteActual.direcciones.find(x => x.id === clave);
    abrirFormDireccion(d, clave);
  }
  if (borrar) {
    const clave = +borrar.dataset.bdir;
    if (modo === "crear") {
      const eraPrincipal = direccionesLocales[clave].principal;
      direccionesLocales.splice(clave, 1);
      if (eraPrincipal && direccionesLocales.length) direccionesLocales[0].principal = true;
      pintarDirecciones();
      return;
    }
    if (!confirm("¿Quitar esta dirección?")) return;
    try {
      clienteActual = await api("DELETE", `/clientes/${clienteActual.id}/direcciones/${clave}`);
      pintarDirecciones(); cargar();
    } catch (error) { mostrarErrores($("errorDireccion"), error); }
  }
});

$("btnGuardarDir").onclick = async () => {
  const d = {
    departamento: $("dDepartamento").value, municipio: $("dMunicipio").value.trim(),
    direccion: $("dDireccion").value.trim(), principal: $("dPrincipal").checked,
  };
  const errores = { departamento: !d.departamento, municipio: d.municipio.length < 2, direccion: d.direccion.length < 5 };
  document.querySelectorAll("#formDireccion [data-campo]").forEach(c => c.classList.toggle("error", errores[c.dataset.campo]));
  if (Object.values(errores).some(Boolean)) return;

  if (modo === "crear") {
    if (d.principal) direccionesLocales.forEach(x => x.principal = false);
    if (direccionEditando === null) direccionesLocales.push(d);
    else direccionesLocales[direccionEditando] = d;
    if (!direccionesLocales.some(x => x.principal)) direccionesLocales[0].principal = true;
    cerrarFormDireccion(); pintarDirecciones();
    return;
  }
  try {
    clienteActual = direccionEditando === null
      ? await api("POST", `/clientes/${clienteActual.id}/direcciones`, d)
      : await api("PUT", `/clientes/${clienteActual.id}/direcciones/${direccionEditando}`, d);
    cerrarFormDireccion(); pintarDirecciones(); toast("Dirección guardada");
  } catch (error) { mostrarErrores($("errorDireccion"), error); }
};

/* ---------- Contraseña ---------- */
$("btnResetPass").onclick = () => {
  $("formPassword").reset(); $("errorPassword").hidden = true;
  $("textoPassword").textContent = `Nueva contraseña para ${clienteActual.razon_social} (${clienteActual.email}).`;
  $("modalPassword").showModal();
};
$("formPassword").onsubmit = async e => {
  e.preventDefault();
  try {
    await api("POST", `/clientes/${clienteActual.id}/password`, { password: $("nuevaPassword").value });
    $("modalPassword").close(); toast("Contraseña actualizada");
  } catch (error) { mostrarErrores($("errorPassword"), error); }
};

document.querySelectorAll("[data-cerrar]").forEach(b => b.onclick = () => b.closest("dialog").close());
cargar();
