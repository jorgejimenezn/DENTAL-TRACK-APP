-- DENTAL TRACK · Usuarios de demostración (rol demo)
-- Idempotente: omite correos que ya existan. Contraseñas en credenciales_demo.xlsx (aquí solo van cifradas).
-- Ejecutar DESPUÉS de desplegar la versión que incluye el rol demo.

INSERT INTO usuarios (nombre, apellido, email, password_hash, rol, activo)
SELECT v.nombre, v.apellido, v.email, v.hash, 'demo', TRUE
FROM (VALUES
  ('Andres', 'Acevedo', 'andres.acevedo@demo.gt', '$2b$12$VUES3/9E.7FgikWHfSat7ORLfas8CWVrsygsPiwpJ5e/En1OnaLNS'),
  ('Gustavo', 'Cordon', 'gustavo.cordon@demo.gt', '$2b$12$2RKPy.UlGTjrIHHjVLht1.8MccD7EYHwgWtIe/deW2nK5PkH46pNO'),
  ('Marcela', 'Molina', 'marcela.molina@demo.gt', '$2b$12$YuoPfSs1Dd7HYMuWB4Gz8OgIhcMa1ebtFnQ5lbNTj1v55TAzcru7u'),
  ('Luis', 'Chacon', 'luis.chacon@demo.gt', '$2b$12$rVAjuegsY3O3tjsfhFE89epUPkRBUMeoZTcSytgrCE/kqZoQGVZjK'),
  ('Stefan', 'Bruns', 'stefan.bruns@demo.gt', '$2b$12$i7RloRuSbuWS795mxLbo5e1hAiLlom0zQCwR7uDTUdm3DjyqKyyS6'),
  ('Enrique', 'Meza', 'enrique.meza@demo.gt', '$2b$12$X5BMOf.Ay.6lmWomOzSyyeoUCoKssQybwvCrgrxVuDxTVbBjDJjpi')
) AS v(nombre, apellido, email, hash)
WHERE NOT EXISTS (SELECT 1 FROM usuarios u WHERE lower(u.email) = lower(v.email));
