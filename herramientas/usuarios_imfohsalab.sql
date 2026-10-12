-- DENTAL TRACK · Usuarios de ImfohsaLab
-- Ejecutar en la consola Query de la base Postgres en Railway.
-- Idempotente: si un correo ya existe no se duplica ni se cambia su contraseña.
-- Las contraseñas iniciales están en credenciales_imfohsalab.xlsx (no se sube al repositorio).
BEGIN;

-- Luis Chacón · Supervisor
INSERT INTO usuarios (nombre, apellido, email, password_hash, rol, activo)
SELECT 'Luis', 'Chacón', 'lchacon@imfohsalab.com', '$2b$12$oLWErAJd9CAhwTPP9TAlI.cRI4nbjlgeuk5AVrAJJw2xvqKSmsYj6', 'supervisor', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE lower(email) = 'lchacon@imfohsalab.com');
INSERT INTO usuario_area (usuario_id, area_id)
SELECT u.id, a.id FROM usuarios u, areas a
WHERE lower(u.email) = 'lchacon@imfohsalab.com' AND a.nombre = 'Validación de diseño'
  AND NOT EXISTS (SELECT 1 FROM usuario_area ua WHERE ua.usuario_id = u.id AND ua.area_id = a.id);

-- Damaris Pérez · Supervisor
INSERT INTO usuarios (nombre, apellido, email, password_hash, rol, activo)
SELECT 'Damaris', 'Pérez', 'dperez@imfohsalab.com', '$2b$12$kUfILsoD93xsQL1DXrI95.k5vU6HBOts4aZDFxtrhspREIiHsxCmi', 'supervisor', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE lower(email) = 'dperez@imfohsalab.com');
INSERT INTO usuario_area (usuario_id, area_id)
SELECT u.id, a.id FROM usuarios u, areas a
WHERE lower(u.email) = 'dperez@imfohsalab.com' AND a.nombre = 'Validación de diseño'
  AND NOT EXISTS (SELECT 1 FROM usuario_area ua WHERE ua.usuario_id = u.id AND ua.area_id = a.id);

-- Katherine Rubio · QA
INSERT INTO usuarios (nombre, apellido, email, password_hash, rol, activo)
SELECT 'Katherine', 'Rubio', 'krubio@imfohsalab.com', '$2b$12$3msuk16u0AMbl/43c4H5J.vyH8aEK2BH5GHO53KSi99SczZ1KddYe', 'qa', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE lower(email) = 'krubio@imfohsalab.com');
INSERT INTO usuario_area (usuario_id, area_id)
SELECT u.id, a.id FROM usuarios u, areas a
WHERE lower(u.email) = 'krubio@imfohsalab.com' AND a.nombre = 'QA'
  AND NOT EXISTS (SELECT 1 FROM usuario_area ua WHERE ua.usuario_id = u.id AND ua.area_id = a.id);

-- Ingresos ImfohsaLab · Ingresos
INSERT INTO usuarios (nombre, apellido, email, password_hash, rol, activo)
SELECT 'Ingresos', 'ImfohsaLab', 'ingresos@imfohsalab.com', '$2b$12$b.jReUF6x7zbzQGMToUKleVX5VYK5a.Sg4uJ4ShQZU4Sf8zkneBne', 'ingresos', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE lower(email) = 'ingresos@imfohsalab.com');
INSERT INTO usuario_area (usuario_id, area_id)
SELECT u.id, a.id FROM usuarios u, areas a
WHERE lower(u.email) = 'ingresos@imfohsalab.com' AND a.nombre = 'Ingresos'
  AND NOT EXISTS (SELECT 1 FROM usuario_area ua WHERE ua.usuario_id = u.id AND ua.area_id = a.id);

-- Logística ImfohsaLab · Logística
INSERT INTO usuarios (nombre, apellido, email, password_hash, rol, activo)
SELECT 'Logística', 'ImfohsaLab', 'logistica@imfohsalab.com', '$2b$12$U7cnsD3696jPi01xclqiS.6lDFMB8iV4S2yy/avAp7CGGOOUGvrKW', 'logistica', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE lower(email) = 'logistica@imfohsalab.com');
INSERT INTO usuario_area (usuario_id, area_id)
SELECT u.id, a.id FROM usuarios u, areas a
WHERE lower(u.email) = 'logistica@imfohsalab.com' AND a.nombre = 'Logística'
  AND NOT EXISTS (SELECT 1 FROM usuario_area ua WHERE ua.usuario_id = u.id AND ua.area_id = a.id);

-- Mensajero ImfohsaLab · Mensajero
INSERT INTO usuarios (nombre, apellido, email, password_hash, rol, activo)
SELECT 'Mensajero', 'ImfohsaLab', 'mensajero@imfohsalab.com', '$2b$12$BzVM.KuqofznjcrZ5gMK7.gO2siYb9lgP47drIJV/p1J25UTLdNva', 'mensajero', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE lower(email) = 'mensajero@imfohsalab.com');

-- Técnico Yesos · Técnico
INSERT INTO usuarios (nombre, apellido, email, password_hash, rol, activo)
SELECT 'Técnico', 'Yesos', 'yesos@imfohsalab.com', '$2b$12$iT7YkIAunSHmFqiyoAEL/ew9bscTjJ1EiteM7vjdbSzrx5FLtudz6', 'tecnico', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE lower(email) = 'yesos@imfohsalab.com');
INSERT INTO usuario_area (usuario_id, area_id)
SELECT u.id, a.id FROM usuarios u, areas a
WHERE lower(u.email) = 'yesos@imfohsalab.com' AND a.nombre = 'Yesos'
  AND NOT EXISTS (SELECT 1 FROM usuario_area ua WHERE ua.usuario_id = u.id AND ua.area_id = a.id);

-- Técnico Diseño · Técnico
INSERT INTO usuarios (nombre, apellido, email, password_hash, rol, activo)
SELECT 'Técnico', 'Diseño', 'diseno@imfohsalab.com', '$2b$12$l1tNGlBEZLdG/rKMDbhtReqd5Dw6kH8eigjX5f0oHLAbhQTD8RO3W', 'tecnico', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE lower(email) = 'diseno@imfohsalab.com');
INSERT INTO usuario_area (usuario_id, area_id)
SELECT u.id, a.id FROM usuarios u, areas a
WHERE lower(u.email) = 'diseno@imfohsalab.com' AND a.nombre = 'Diseño'
  AND NOT EXISTS (SELECT 1 FROM usuario_area ua WHERE ua.usuario_id = u.id AND ua.area_id = a.id);

-- Técnico CAD · Técnico
INSERT INTO usuarios (nombre, apellido, email, password_hash, rol, activo)
SELECT 'Técnico', 'CAD', 'cad@imfohsalab.com', '$2b$12$h/3B/Ov5XoAupZI8VlDLp.icRwiMn6mYhjNxCqhg70H2dUYCBoS.u', 'tecnico', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE lower(email) = 'cad@imfohsalab.com');
INSERT INTO usuario_area (usuario_id, area_id)
SELECT u.id, a.id FROM usuarios u, areas a
WHERE lower(u.email) = 'cad@imfohsalab.com' AND a.nombre = 'CAD'
  AND NOT EXISTS (SELECT 1 FROM usuario_area ua WHERE ua.usuario_id = u.id AND ua.area_id = a.id);

-- Técnico Impresión · Técnico
INSERT INTO usuarios (nombre, apellido, email, password_hash, rol, activo)
SELECT 'Técnico', 'Impresión', 'impresion@imfohsalab.com', '$2b$12$hDRfu/ttQ2kNM1liXtHa3OTDxcJe7IFJNhjNc4QxARPFUOqJUlpSG', 'tecnico', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE lower(email) = 'impresion@imfohsalab.com');
INSERT INTO usuario_area (usuario_id, area_id)
SELECT u.id, a.id FROM usuarios u, areas a
WHERE lower(u.email) = 'impresion@imfohsalab.com' AND a.nombre = 'CAM_IMP'
  AND NOT EXISTS (SELECT 1 FROM usuario_area ua WHERE ua.usuario_id = u.id AND ua.area_id = a.id);

-- Técnico Fresado · Técnico
INSERT INTO usuarios (nombre, apellido, email, password_hash, rol, activo)
SELECT 'Técnico', 'Fresado', 'fresado@imfohsalab.com', '$2b$12$qWYW0cUHVpEp1cT6tYRzsOWaAUyc1ENOZyK7BDHnOo4GtQ33yLHhe', 'tecnico', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE lower(email) = 'fresado@imfohsalab.com');
INSERT INTO usuario_area (usuario_id, area_id)
SELECT u.id, a.id FROM usuarios u, areas a
WHERE lower(u.email) = 'fresado@imfohsalab.com' AND a.nombre = 'CAM_FRES'
  AND NOT EXISTS (SELECT 1 FROM usuario_area ua WHERE ua.usuario_id = u.id AND ua.area_id = a.id);

-- Técnico Finalización · Técnico
INSERT INTO usuarios (nombre, apellido, email, password_hash, rol, activo)
SELECT 'Técnico', 'Finalización', 'finalizacion@imfohsalab.com', '$2b$12$i5qbIwdrATchlmURfKiif.D7TrH64AsYnRT4X0BjwT2GYWTuz8vKy', 'tecnico', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE lower(email) = 'finalizacion@imfohsalab.com');
INSERT INTO usuario_area (usuario_id, area_id)
SELECT u.id, a.id FROM usuarios u, areas a
WHERE lower(u.email) = 'finalizacion@imfohsalab.com' AND a.nombre = 'Finalización'
  AND NOT EXISTS (SELECT 1 FROM usuario_area ua WHERE ua.usuario_id = u.id AND ua.area_id = a.id);

-- Facturación ImfohsaLab · Facturación
INSERT INTO usuarios (nombre, apellido, email, password_hash, rol, activo)
SELECT 'Facturación', 'ImfohsaLab', 'facturacion@imfohsalab.com', '$2b$12$nyaC07h6TenuYn8lwW2/HOSUWqMof4ZrwVXOsoOGIPebM5mIs/UHG', 'facturacion', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE lower(email) = 'facturacion@imfohsalab.com');
INSERT INTO usuario_area (usuario_id, area_id)
SELECT u.id, a.id FROM usuarios u, areas a
WHERE lower(u.email) = 'facturacion@imfohsalab.com' AND a.nombre = 'Facturación_Cobros'
  AND NOT EXISTS (SELECT 1 FROM usuario_area ua WHERE ua.usuario_id = u.id AND ua.area_id = a.id);

-- Operaciones ImfohsaLab · Operaciones
INSERT INTO usuarios (nombre, apellido, email, password_hash, rol, activo)
SELECT 'Operaciones', 'ImfohsaLab', 'operaciones@imfohsalab.com', '$2b$12$1hIlaWsQqq8wl4OMo6jen.u5YRFUv5yOoLiS9CbNQk.d8C0rtPwpK', 'operaciones', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE lower(email) = 'operaciones@imfohsalab.com');

COMMIT;

-- Verificación: cada usuario con su rol y sus áreas (si un área sale vacía, revisa que exista con ese nombre)
SELECT u.id, u.nombre, u.apellido, u.email, u.rol, u.activo, string_agg(a.nombre, ', ') AS areas
FROM usuarios u LEFT JOIN usuario_area ua ON ua.usuario_id = u.id LEFT JOIN areas a ON a.id = ua.area_id
WHERE lower(u.email) IN ('lchacon@imfohsalab.com', 'dperez@imfohsalab.com', 'krubio@imfohsalab.com', 'ingresos@imfohsalab.com', 'logistica@imfohsalab.com', 'mensajero@imfohsalab.com', 'yesos@imfohsalab.com', 'diseno@imfohsalab.com', 'cad@imfohsalab.com', 'impresion@imfohsalab.com', 'fresado@imfohsalab.com', 'finalizacion@imfohsalab.com', 'facturacion@imfohsalab.com', 'operaciones@imfohsalab.com')
GROUP BY u.id ORDER BY u.id;
