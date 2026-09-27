-- DENTAL TRACK · Datos de prueba (25 empleados, 20 clientes)
-- Idempotente: omite correos, NIT y relaciones que ya existan.
-- Las contraseñas iniciales están en credenciales_prueba.xlsx (aquí solo van cifradas).

BEGIN;

-- 1. Usuarios: empleados y cuentas de acceso de los clientes
INSERT INTO usuarios (nombre, apellido, email, telefono, direccion, password_hash, rol, activo)
SELECT v.nombre, v.apellido, v.email, v.telefono, v.direccion, v.hash, v.rol, TRUE
FROM (VALUES
  ('Carlos', 'Mendoza', 'c.mendoza@innovalab.com.gt', '45219876', '14 Calle 3-45, Zona 10, Ciudad de Guatemala', '$2b$12$IjL.u9LjkZhv9LpV9/DaUeIFhy1ST7Z.NoPZlHBRJeU5iVTzUUYvG', 'tecnico'),
  ('Juan Carlos', 'Morales', 'j.morales@innovalab.com.gt', '54123344', '5a Avenida 12-30, Zona 1, Ciudad de Guatemala', '$2b$12$IP2I1qpCeuvFD1uKpL3NA.Yn5S66Ii3j1K/z.KclSeCBmHpgjIVOe', 'tecnico'),
  ('Luis Fernando', 'Gómez', 'l.gomez@innovalab.com.gt', '42315566', 'Blvrd Principal San Cristóbal, Zona 8 de Mixco', '$2b$12$7V2.uClETVMPORBQZ5s5BOGcjL99J6iCNkaeFHU9bz6UKZmH8C7IC', 'tecnico'),
  ('Roberto', 'Estrada', 'r.estrada@innovalab.com.gt', '58901122', '20 Calle 10-15, Zona 14, Ciudad de Guatemala', '$2b$12$KtXVul2XoNFcrgswGM6tFepTBL3j0sdELR8QPzFzcCy5GrIAsefIG', 'logistica'),
  ('Mario Alberto', 'Ruano', 'm.ruano@innovalab.com.gt', '31458899', 'Km 14.5 Carretera a El Salvador, Santa Catarina Pinula', '$2b$12$DDCNqo0zi9/A3jPPgqp5DeIakEr0RqVuEQTS.0rE87bBj8sbB1DPy', 'logistica'),
  ('Diego Alejandro', 'Ortiz', 'd.ortiz@innovalab.com.gt', '41027788', '4a Calle 2-15, Zona 9, Ciudad de Guatemala', '$2b$12$YlVSPjdVVWSXZKYFqwZwtOwHnqs/AwgPmvxHSh42v05Klep61khQW', 'tecnico'),
  ('Francisco', 'Cifuentes', 'f.cifuentes@innovalab.com.gt', '55664433', 'Calzada Roosevelt 22-43, Zona 7, Ciudad de Guatemala', '$2b$12$t/Od7doF3axQIRMJcBRdZugv10jhGDjaUTJfsU/nmZ3anCEwU0ZXe', 'logistica'),
  ('José Manuel', 'Castro', 'j.castro@innovalab.com.gt', '49871100', '7a Avenida 3-12, Zona 4, Ciudad de Guatemala', '$2b$12$kQH41vln09Blc3tPxH9P/OkSQacSeBPI/JK7QEPVHXnkCecgeVpKG', 'tecnico'),
  ('Eduardo', 'Ramírez', 'e.ramirez@innovalab.com.gt', '53219988', '10a Calle 5-20, Zona 13, Ciudad de Guatemala', '$2b$12$eWfgebtMs1WV0yPB.lXGfeV09OaNKZ00hy92enlQhyGgbBkBB32OS', 'tecnico'),
  ('Ricardo Enrique', 'López', 'r.lopez@innovalab.com.gt', '47892233', '15 Avenida 8-40, Zona 15, Vista Hermosa I', '$2b$12$33qvRr113kfYbrKW9kisUuAuSmKLabi5ieHjqWG066C7563AFud9W', 'tecnico'),
  ('Sergio Armando', 'Pineda', 's.pineda@innovalab.com.gt', '51234455', 'C.C. Miraflores, Local 12, Zona 11, Guatemala', '$2b$12$ZC2G9ENTZnbti6KYzGMT1ukCd4hTc496CwxJlGWI/R1jKfqjCCpA6', 'tecnico'),
  ('Alejandro', 'Morales', 'a.morales@innovalab.com.gt', '43567890', '6a Calle 1-50, Zona 1, Mixco', '$2b$12$kbevphWMCbUDctj34UKCdOBl3G1ngQRlWmnzqLJceKl.8IFxJqCLW', 'tecnico'),
  ('Gabriel Antonio', 'Juárez', 'g.juarez@innovalab.com.gt', '59876543', '12 Calle 4-33, Zona 10, Ciudad de Guatemala', '$2b$12$ySrOsZvXH33CTsmS2nMOY.uVX88K3TjO9FIZiR5NobuT2qoeb4eRe', 'tecnico'),
  ('Óscar David', 'Hernández', 'o.hernandez@innovalab.com.gt', '46543210', '2a Avenida 5-60, Zona 9, Ciudad de Guatemala', '$2b$12$haVAVr0bbi07/0Jwr/XsWudIVz4.nY/qsCdGWXtdvOuAnfLeU0BGG', 'tecnico'),
  ('Héctor Julio', 'Mejía', 'h.mejia@innovalab.com.gt', '52345678', 'Diagonal 6 12-42, Zona 10, Ciudad de Guatemala', '$2b$12$OEND.dW2lsW0Nz/adA651eN8/NWhYOoUmTXdp8iHctCZhwsMZuTLa', 'tecnico'),
  ('Pablo Andrés', 'Vásquez', 'p.vasquez@innovalab.com.gt', '48765432', '18 Calle 0-25, Zona 1, Ciudad de Guatemala', '$2b$12$QJozAz4l5qZhHD5kEtSojemD4NmCZzUjygw4vhA6zIhd5ucGrdnJ2', 'tecnico'),
  ('María José', 'Hernández', 'm.hernandez@innovalab.com.gt', '51112233', '12 Calle 1-25, Zona 10, Ciudad de Guatemala', '$2b$12$YSjYZRZsrwGBd98zCkaNWOCnqs7qBCUlQajDJrGlmbuNU1Ja4WKwu', 'ingresos'),
  ('Ana Sofía', 'Castillo', 'a.castillo@innovalab.com.gt', '42223344', '6a Avenida 9-80, Zona 1, Ciudad de Guatemala', '$2b$12$dpsuGwgeNUoVrN943oboeeTU6LwUUQqbPy9hVFxnCJpXIX1j/0vxi', 'ingresos'),
  ('Claudia Patricia', 'Ramos', 'c.ramos@innovalab.com.gt', '53334455', 'Blvrd Los Próceres 24-69, Zona 10, Guatemala', '$2b$12$5zx3BXgvfxUbwTFQfLC79OKQw/gpOTIKXjEqWHBgQg8oCP9nRZAmy', 'qa'),
  ('Gabriela Michelle', 'Soto', 'g.soto@innovalab.com.gt', '44445566', '15 Calle 3-20, Zona 14, Ciudad de Guatemala', '$2b$12$7ptaSorFy/glT7lwq9rh.OGnExqzt.S78p/1uRWKZZCxMSOKXgqHS', 'qa'),
  ('Sofía Alejandra', 'Flores', 's.flores@innovalab.com.gt', '55556677', 'Km 12 Carretera al Atlántico, Zona 18, Guatemala', '$2b$12$dwA9s03V1gxjV3mpMwYx1.ujXt9Bnf5V8L6PVLUO2et.AKlgPTRpa', 'facturacion'),
  ('Daniela Andrea', 'Gutiérrez', 'd.gutierrez@innovalab.com.gt', '46667788', '4a Avenida 10-12, Zona 1, Mixco', '$2b$12$fjimAZosmELw6oTi7Hfqv.PK6uCbS7VOTcMcYgr1j5I0pEMPRYrDS', 'facturacion'),
  ('Andrea Lucía', 'Monzón', 'a.monzon@innovalab.com.gt', '57778899', '7a Calle 14-55, Zona 9, Ciudad de Guatemala', '$2b$12$Zs2cotnVeUj6XmIhcjBmbOb5KBfa51t3Wb.4kWQTB5XVWHHd/A48u', 'tecnico'),
  ('Jorge', 'Jimenez', 'j.jimenez@innovalab.com.gt', '57257080', NULL, '$2b$12$ScYE0xW4q7exPkhV9YGjGeFwBlSnkdrx4dhohoVfs.iVLbS7fESP.', 'admin'),
  ('Axel', 'Aguilar', 'a.aguilar@innovalab.com.gt', '51915256', NULL, '$2b$12$TXEKGmqhk7.XC1k.k0YVJe975W4AyRYQRMWywTL7R.4tXgeE7a9h6', 'admin'),
  ('Dra. Leslie Pérez', '', 'info@clinicsonrisas.gt', '23601234', NULL, '$2b$12$gcDY4rIJLlvP4gtRKrnQheRpa6Sg5L.HAUqYar6C3ZSfbqIiIxyQO', 'doctor'),
  ('Dr. Marco Tulio Escobar', '', 'dr.escobar@odonto.gt', '24715678', NULL, '$2b$12$XrH78pIDajus3Z3iTzpRP.2PItXYf.9p51k//J3B6989CK7YSQkJS', 'doctor'),
  ('Clínica Dental Sonrisa Perfecta S.A.', '', 'contacto@sonrisaperfecta.gt', '22359012', NULL, '$2b$12$JyuVFBn6/61ytKV8tLm11OXCA2TjnRys9fN6rVu2rd2pEfIRCRhtG', 'doctor'),
  ('Dr. Jorge Luis Mendoza', '', 'mendoza.dental@gmail.com', '23324321', NULL, '$2b$12$X4EyKUIfuSFK.oh1mVHP8uy8KEBDCT7ic5HjwG0VWa0EJiQGqqY.y', 'doctor'),
  ('Dra. Karen Vanessa Orozco', '', 'dra.orozco@gmail.com', '24318765', NULL, '$2b$12$YgCT.tpeAwrP42pNaJh3l.18R6R.8kt2o2J4kc3Hwlc1mhI2/CbZq', 'doctor'),
  ('Centro Odontológico Integral C&H', '', 'c.odontologicoh@gmail.com', '23854433', NULL, '$2b$12$bIJVDyRFQq0bxpZ4Xe5W..K3M/I8AXNN/COYmF40lK2jmoi5vXBL6', 'doctor'),
  ('Dr. Esteban Rivas Duarte', '', 'erivas@yahoo.com', '22209988', NULL, '$2b$12$hpFg/gPJXDIs6OYOgFeTJek7emDiBLzxwESBUijh0Vowyx5Hb.uvu', 'doctor'),
  ('Dra. Mónica Leticia Fuentes', '', 'monica.fuentes@dental.gt', '24761122', NULL, '$2b$12$Cn5LTnycxKzclSgF9Vh4CefSLDoFmxeT32GxSDxZ4VrAZpoNUrV.W', 'doctor'),
  ('Clínica Dental Guatemala Smile', '', 'info@gtsmile.com', '23627788', NULL, '$2b$12$zNe0AGTviwE6D8IsHT00w.jRG3U4HoHO09W/Ka2SRpE6cRixAGSya', 'doctor'),
  ('Dr. Carlos Humberto Paz', '', 'chpaz@gmail.com', '24403322', NULL, '$2b$12$KQ2T8SsGjiyto6/ByHGCJ.h0tKLfd9BcBc7Nn3jcNgbKGfQcH6l0a', 'doctor'),
  ('Dra. Brenda Marcela Morales', '', 'bmorales@odontologia.gt', '23391144', NULL, '$2b$12$EhlYL2PDw/udsZnrzccidOKZMIvKPyXr0.olLGocjACKqw30CJs7S', 'doctor'),
  ('Servicios Dentales Avanzados S.A.', '', 'ventas@sdasa.gt', '23805566', NULL, '$2b$12$mh0HetxH9clfJlxvWSgGbOv8Sdp0yXGpR9sXoHhvmLB0hwKrjexRG', 'doctor'),
  ('Dr. Mario Roberto Cáceres', '', 'mr_caceres@gmail.com', '22501199', NULL, '$2b$12$IKNipLw1gkyuqmA4tWf7pOAPQW7VqISdsNK73xIZ2KKlTjIgH66NW', 'doctor'),
  ('Dra. Silvia Elena Aguilar', '', 'silvia.aguilar@dental.com', '24356677', NULL, '$2b$12$uIsp7xDLOjUJITM.jI62F.tUV5Uv7WYBUj3hMA05FicZj30mSMRma', 'doctor'),
  ('Clínica Odontológica Sonrisas del Sur', '', 'sonrisas_sur@gmail.com', '24783344', NULL, '$2b$12$isOv0EIJmt53ZVYo2XUB3eXakI82a5WlfAMaUlu.o9qFrFhloAlCq', 'doctor'),
  ('Dr. Gustavo Adolfo Ramírez', '', 'gramirez@odonto.gt', '23664455', NULL, '$2b$12$y7qX2/THyPelxhyXpHVKgOryRUARMjU6rYmmani1MUqf0H5/aamuS', 'doctor'),
  ('Dra. Ana Patricia Chacón', '', 'ana.chacon@gmail.com', '22227788', NULL, '$2b$12$2GpH2ZL6o6IhECcr612lA.A2Vutph.MZ8Ij32na4rYEmV5Ho8hau6', 'doctor'),
  ('Centro Dental ProSalud', '', 'prosalud@dentalgt.com', '23349900', NULL, '$2b$12$DfLLIByknbzXaLv.S8T5Jer.uZHX9K2tiitZEJTFMoSIC41V7a5e.', 'doctor'),
  ('Dr. Rafael Ignacio Dávila', '', 'ridavila@gmail.com', '24431122', NULL, '$2b$12$Sr1sR75.uqs.n.Bps9qQQ.ihu9nrjEVOjm2oHdz/9FUNrEQkIcFkq', 'doctor'),
  ('Dra. Claudia Lorena Navas', '', 'claudia.navas@gmail.com', '23116655', NULL, '$2b$12$bFP2bg4HzLy4YcQjOVYqe.LuumKr1Qq02TYEIQm6ZSCuBW9KGWT1W', 'doctor')
) AS v(nombre, apellido, email, telefono, direccion, hash, rol)
ON CONFLICT (email) DO NOTHING;

-- 2. Áreas de cada empleado
INSERT INTO usuario_area (usuario_id, area_id)
SELECT u.id, a.id
FROM (VALUES
  ('c.mendoza@innovalab.com.gt', 'Yesos'),
  ('j.morales@innovalab.com.gt', 'Yesos'),
  ('l.gomez@innovalab.com.gt', 'Diseño'),
  ('r.estrada@innovalab.com.gt', 'Logística'),
  ('m.ruano@innovalab.com.gt', 'Logística'),
  ('d.ortiz@innovalab.com.gt', 'Diseño'),
  ('d.ortiz@innovalab.com.gt', 'CAD'),
  ('f.cifuentes@innovalab.com.gt', 'Logística'),
  ('j.castro@innovalab.com.gt', 'CAD'),
  ('e.ramirez@innovalab.com.gt', 'CAD'),
  ('r.lopez@innovalab.com.gt', 'CAM_IMP'),
  ('s.pineda@innovalab.com.gt', 'CAM_IMP'),
  ('a.morales@innovalab.com.gt', 'CAM_FRES'),
  ('g.juarez@innovalab.com.gt', 'CAM_FRES'),
  ('g.juarez@innovalab.com.gt', 'CAM_IMP'),
  ('o.hernandez@innovalab.com.gt', 'Finalización'),
  ('h.mejia@innovalab.com.gt', 'Finalización'),
  ('p.vasquez@innovalab.com.gt', 'Finalización'),
  ('p.vasquez@innovalab.com.gt', 'Yesos'),
  ('m.hernandez@innovalab.com.gt', 'Ingresos'),
  ('a.castillo@innovalab.com.gt', 'Ingresos'),
  ('c.ramos@innovalab.com.gt', 'QA'),
  ('g.soto@innovalab.com.gt', 'QA'),
  ('s.flores@innovalab.com.gt', 'Facturación_Cobros'),
  ('d.gutierrez@innovalab.com.gt', 'Facturación_Cobros'),
  ('a.monzon@innovalab.com.gt', 'CAD')
) AS v(email, area)
JOIN usuarios u ON u.email = v.email
JOIN areas a ON a.nombre = v.area
ON CONFLICT DO NOTHING;

-- 3. Datos comerciales de los clientes (solo sobre usuarios con rol doctor)
INSERT INTO clientes (usuario_id, razon_social, nombre_facturacion, clinica, es_red, telefono_celular,
                      telefono_fijo, tipo_documento, numero_documento, nivel_prioridad)
SELECT u.id, v.razon, v.facturacion, NULL, FALSE, v.celular, v.fijo, v.tipo, v.documento, v.nivel
FROM (VALUES
  ('info@clinicsonrisas.gt', 'Dra. Leslie Pérez', 'Leslie Dayana Pérez Morales', NULL, '23601234', 'NIT', '4589211', 2),
  ('dr.escobar@odonto.gt', 'Dr. Marco Tulio Escobar', 'Marco Tulio Escobar Fuentes', NULL, '24715678', 'NIT', '1245783', 2),
  ('contacto@sonrisaperfecta.gt', 'Clínica Dental Sonrisa Perfecta S.A.', 'Sonrisa Perfecta, S.A.', NULL, '22359012', 'NIT', '8974527', 2),
  ('mendoza.dental@gmail.com', 'Dr. Jorge Luis Mendoza', 'Jorge Luis Mendoza Castillo', NULL, '23324321', 'NIT', '3216543', 2),
  ('dra.orozco@gmail.com', 'Dra. Karen Vanessa Orozco', 'Karen Vanessa Orozco Pineda', NULL, '24318765', 'NIT', '6543219', 2),
  ('c.odontologicoh@gmail.com', 'Centro Odontológico Integral C&H', 'Centro Odontológico C&H, S.A.', NULL, '23854433', 'NIT', '9871233', 2),
  ('erivas@yahoo.com', 'Dr. Esteban Rivas Duarte', 'Esteban Rivas Duarte', NULL, '22209988', 'NIT', '7418523', 2),
  ('monica.fuentes@dental.gt', 'Dra. Mónica Leticia Fuentes', 'Mónica Leticia Fuentes Gómez', NULL, '24761122', 'NIT', '3692582', 2),
  ('info@gtsmile.com', 'Clínica Dental Guatemala Smile', 'Guatemala Smile, S.A.', NULL, '23627788', 'NIT', '1593579', 2),
  ('chpaz@gmail.com', 'Dr. Carlos Humberto Paz', 'Carlos Humberto Paz Arriaza', NULL, '24403322', 'NIT', '7539517', 2),
  ('bmorales@odontologia.gt', 'Dra. Brenda Marcela Morales', 'Brenda Marcela Morales Lémus', NULL, '23391144', 'NIT', '8524564', 2),
  ('ventas@sdasa.gt', 'Servicios Dentales Avanzados S.A.', 'Servicios Dentales Avanzados, S.A.', NULL, '23805566', 'NIT', '9513574', 2),
  ('mr_caceres@gmail.com', 'Dr. Mario Roberto Cáceres', 'Mario Roberto Cáceres Solís', NULL, '22501199', 'NIT', '1472585', 3),
  ('silvia.aguilar@dental.com', 'Dra. Silvia Elena Aguilar', 'Silvia Elena Aguilar Ruano', NULL, '24356677', 'NIT', '3698521', 3),
  ('sonrisas_sur@gmail.com', 'Clínica Odontológica Sonrisas del Sur', 'Sonrisas del Sur, S.A.', NULL, '24783344', 'NIT', '9638520', 3),
  ('gramirez@odonto.gt', 'Dr. Gustavo Adolfo Ramírez', 'Gustavo Adolfo Ramírez Mejía', NULL, '23664455', 'NIT', '741238K', 3),
  ('ana.chacon@gmail.com', 'Dra. Ana Patricia Chacón', 'Ana Patricia Chacón Villatoro', NULL, '22227788', 'NIT', '2583690', 3),
  ('prosalud@dentalgt.com', 'Centro Dental ProSalud', 'ProSalud Dental, S.A.', NULL, '23349900', 'NIT', '3579514', 3),
  ('ridavila@gmail.com', 'Dr. Rafael Ignacio Dávila', 'Rafael Ignacio Dávila Estrada', NULL, '24431122', 'NIT', '654987K', 3),
  ('claudia.navas@gmail.com', 'Dra. Claudia Lorena Navas', 'Claudia Lorena Navas Orellana', NULL, '23116655', 'NIT', '1237896', 3)
) AS v(email, razon, facturacion, celular, fijo, tipo, documento, nivel)
JOIN usuarios u ON u.email = v.email AND u.rol = 'doctor'
WHERE NOT EXISTS (SELECT 1 FROM clientes c WHERE c.usuario_id = u.id OR c.numero_documento = v.documento);

-- 4. Dirección principal de entrega de cada cliente
INSERT INTO direcciones (cliente_id, departamento, municipio, direccion, principal, activo)
SELECT c.id, v.departamento, v.municipio, v.direccion, TRUE, TRUE
FROM (VALUES
  ('info@clinicsonrisas.gt', 'Guatemala', 'Guatemala', '10 Calle 2-45, Zona 10'),
  ('dr.escobar@odonto.gt', 'Guatemala', 'Guatemala', '5a Avenida 4-12, Zona 1'),
  ('contacto@sonrisaperfecta.gt', 'Guatemala', 'Mixco', 'Blvrd San Cristóbal 1-89, Zona 8 Mixco'),
  ('mendoza.dental@gmail.com', 'Guatemala', 'Guatemala', '7a Avenida 12-50, Zona 9'),
  ('dra.orozco@gmail.com', 'Guatemala', 'Guatemala', '14 Calle 3-10, Zona 13'),
  ('c.odontologicoh@gmail.com', 'Guatemala', 'Guatemala', 'Diagonal 6 10-01, Zona 10'),
  ('erivas@yahoo.com', 'Guatemala', 'Guatemala', '6a Calle 3-40, Zona 1'),
  ('monica.fuentes@dental.gt', 'Guatemala', 'Guatemala', '20 Calle 5-88, Zona 14'),
  ('info@gtsmile.com', 'Guatemala', 'Santa Catarina Pinula', 'Km 13.5 Carretera a El Salvador'),
  ('chpaz@gmail.com', 'Guatemala', 'Guatemala', 'Calzada Roosevelt 25-10, Zona 7'),
  ('bmorales@odontologia.gt', 'Guatemala', 'Guatemala', '15 Avenida 10-20, Zona 15'),
  ('ventas@sdasa.gt', 'Guatemala', 'Guatemala', '12 Calle 4-80, Zona 10'),
  ('mr_caceres@gmail.com', 'Guatemala', 'Guatemala', '3a Avenida 8-12, Zona 1'),
  ('silvia.aguilar@dental.com', 'Guatemala', 'Guatemala', 'Blvrd Los Próceres 18-05, Zona 10'),
  ('sonrisas_sur@gmail.com', 'Guatemala', 'Guatemala', '4a Calle 1-30, Zona 11'),
  ('gramirez@odonto.gt', 'Guatemala', 'Guatemala', '7a Avenida 2-40, Zona 4'),
  ('ana.chacon@gmail.com', 'Guatemala', 'Guatemala', '10a Calle 4-15, Zona 1'),
  ('prosalud@dentalgt.com', 'Guatemala', 'Guatemala', '16 Calle 5-30, Zona 14'),
  ('ridavila@gmail.com', 'Guatemala', 'Guatemala', '5a Avenida 10-50, Zona 9'),
  ('claudia.navas@gmail.com', 'Guatemala', 'Guatemala', 'Diagonal 14 3-22, Zona 5')
) AS v(email, departamento, municipio, direccion)
JOIN usuarios u ON u.email = v.email
JOIN clientes c ON c.usuario_id = u.id
WHERE NOT EXISTS (SELECT 1 FROM direcciones d WHERE d.cliente_id = c.id);

COMMIT;

-- Verificación
SELECT rol, COUNT(*) AS usuarios FROM usuarios GROUP BY rol ORDER BY rol;
SELECT nivel_prioridad, COUNT(*) AS clientes FROM clientes GROUP BY nivel_prioridad ORDER BY nivel_prioridad;
