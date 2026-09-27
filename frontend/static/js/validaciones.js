/* ============ Validaciones de Guatemala (mismas reglas que el backend) ============ */
const DEPARTAMENTOS = ["Alta Verapaz","Baja Verapaz","Chimaltenango","Chiquimula","El Progreso","Escuintla","Guatemala","Huehuetenango","Izabal","Jalapa","Jutiapa","Petén","Quetzaltenango","Quiché","Retalhuleu","Sacatepéquez","San Marcos","Santa Rosa","Sololá","Suchitepéquez","Totonicapán","Zacapa"];

const MUNICIPIOS = {
  "Guatemala": ["Guatemala","Santa Catarina Pinula","San José Pinula","San José del Golfo","Palencia","Chinautla","San Pedro Ayampuc","Mixco","San Pedro Sacatepéquez","San Juan Sacatepéquez","San Raymundo","Chuarrancho","Fraijanes","Amatitlán","Villa Nueva","Villa Canales","San Miguel Petapa"],
  "Sacatepéquez": ["Antigua Guatemala","Jocotenango","Pastores","Sumpango","Santo Domingo Xenacoj","Santiago Sacatepéquez","San Bartolomé Milpas Altas","San Lucas Sacatepéquez","Santa Lucía Milpas Altas","Magdalena Milpas Altas","Santa María de Jesús","Ciudad Vieja","San Miguel Dueñas","Alotenango","San Antonio Aguas Calientes","Santa Catarina Barahona"],
};

const limpiarNumero = v => String(v || "").replace(/[\s-]/g, "").toUpperCase();

function nitValido(nit) {
  nit = limpiarNumero(nit);
  if (nit.length < 2) return false;
  const cuerpo = nit.slice(0, -1), verificador = nit.slice(-1);
  if (!/^\d+$/.test(cuerpo) || !/^[\dK]$/.test(verificador)) return false;
  const total = [...cuerpo].reverse().reduce((s, d, i) => s + Number(d) * (i + 2), 0);
  const calculado = (11 - (total % 11)) % 11;
  return verificador === (calculado === 10 ? "K" : String(calculado));
}

function dpiValido(dpi) {
  dpi = limpiarNumero(dpi);
  if (!/^\d{13}$/.test(dpi)) return false;
  const depto = Number(dpi.slice(9, 11)), muni = Number(dpi.slice(11, 13));
  if (depto < 1 || depto > 22 || muni < 1) return false;
  const total = [...dpi.slice(0, 8)].reduce((s, d, i) => s + Number(d) * (i + 2), 0);
  return total % 11 === Number(dpi[8]);
}

const telefonoValido = t => /^\d{8}$/.test(limpiarNumero(t));
const correoValido = c => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(c || "").trim());
