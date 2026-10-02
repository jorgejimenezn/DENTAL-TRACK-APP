-- DENTAL TRACK · Usuario supervisor con el área Validación de diseño
-- Idempotente: si el correo ya existe no lo duplica; la contraseña está en credenciales_supervisor.xlsx
INSERT INTO usuarios (nombre, apellido, email, password_hash, rol, activo)
SELECT 'Supervisor', 'Laboratorio', 'supervisor@innovalab.com.gt', '$2b$12$TJmB0oNOSanAVfI9YmS/8uxUYCMYxO1Ui8tT5PsSRnsn0TXTnZGae', 'supervisor', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE lower(email) = 'supervisor@innovalab.com.gt');

INSERT INTO usuario_area (usuario_id, area_id)
SELECT u.id, a.id FROM usuarios u, areas a
WHERE lower(u.email) = 'supervisor@innovalab.com.gt' AND a.nombre = 'Validación de diseño'
  AND NOT EXISTS (SELECT 1 FROM usuario_area ua WHERE ua.usuario_id = u.id AND ua.area_id = a.id);
