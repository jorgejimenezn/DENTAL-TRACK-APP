# DENTAL TRACK · Sistema de gestión de laboratorio dental

Proyecto de graduación. Arquitectura en N capas con cinco servicios en Railway que se comunican por API.

```
 Navegador
    │ HTTPS
    ▼
┌───────────┐  HTTPS + JWT   ┌───────────┐  red privada + X-Internal-Key  ┌───────────┐
│ frontend  │ ─────────────► │    api    │ ─────────────────────────────► │  backend  │
│ HTML/CSS  │                │ FastAPI   │                                │  FastAPI  │
│ JS        │                │ Swagger   │                                │  lógica   │
└───────────┘                └───────────┘                                └─────┬─────┘
   público                      público                           privado       │
                                                                   ┌────────────┴────────────┐
                                                                   ▼                         ▼
                                                           ┌──────────────┐          ┌──────────────┐
                                                           │  PostgreSQL  │          │   MongoDB    │
                                                           │ (relacional) │          │ (bitácora)   │
                                                           └──────────────┘          └──────────────┘
```

| Servicio | Carpeta | Qué hace | Público |
|---|---|---|---|
| **frontend** | `frontend/` | Pantallas HTML + CSS + JS. Solo habla con la API. | Sí |
| **api** | `api/` | Puerta de entrada: login, tokens JWT, permisos por rol, Swagger en `/docs`. | Sí |
| **backend** | `backend/` | Lógica de negocio y acceso a datos (repositorios → PostgreSQL y MongoDB). | No |
| **Postgres** | plantilla de Railway | Usuarios, clientes, direcciones, áreas. | No |
| **MongoDB** | plantilla de Railway | Bitácora de auditoría (accesos y cambios). | No |

## Fase 1 (incluida)

- **Login** con token JWT, contraseñas cifradas con bcrypt y redirección según rol.
- **Clientes**: razón social y nombre de facturación, alta, edición, activar/desactivar, restablecer contraseña, varias direcciones de entrega (una principal), clínica en red, prioridad 2 (VIP) o 3 (normal), visible solo para el laboratorio. La prioridad 1 queda reservada para emergencias. Validación real de **NIT** (dígito verificador) y **DPI** (CUI de 13 dígitos) en el frontend y en el backend.
- **Empleados**: alta, edición, roles, áreas del laboratorio, **máximo de trabajos activos** (vacío = sin límite), activar/desactivar, restablecer contraseña. No se puede desactivar ni quitar el rol al último administrador.

### Roles y áreas
El **rol** define qué puede hacer una persona en el sistema (pantallas y permisos) y está fijo en el código porque cada uno tiene lógica propia. El **área** define dónde trabaja dentro del laboratorio y es administrable (Catálogos → Áreas).

| Rol | Función |
|---|---|
| Administrador | Usuarios, clientes, configuración completa. |
| Supervisor | Supervisión general del laboratorio: todas las órdenes, reasignaciones y pendientes de autorizar. Sin acceso a configuración ni usuarios. |
| Ingresos | Recibe y valida solicitudes nuevas. |
| Técnico | Trabaja las órdenes de su bandeja, una a la vez. |
| QA | Valida los RP (garantía o cobro) y hace el control de calidad final. |
| Facturación | Facturación, empaque y cobros. |
| Logística | Coordina rutas y asigna recolectas y entregas. |
| Mensajero | Ejecuta las recolectas y entregas asignadas desde su celular. |
| Operaciones | Gerencia: consulta dashboard, métricas, cobros y solicitudes. No modifica nada. |
| Demostración | Para demos: ve todo lo del administrador **sin poder modificar** y puede hacer **cualquier paso de la línea de producción** (recolecta, Ingresos, producción, QA, facturación, entrega) y capturar solicitudes. No necesita áreas. |
| Doctor | Cliente: crea solicitudes y sigue sus casos. |

**Máximo de trabajos activos:** si todos los empleados que pueden atender un paso llegaron a su tope, la orden espera en la cola del área y se asigna cuando alguien libera cupo.
- **Bitácora** en MongoDB: inicios de sesión (exitosos y fallidos), creaciones, ediciones con valores antes/después.
- **Registro público de clientes** desde el login (`registro.html`): la cuenta se crea siempre como cliente (rol doctor) con prioridad 3 (normal); el servidor ignora cualquier otro rol o prioridad enviados. Al terminar, la sesión queda iniciada.
- **Prototipo** del formulario de nueva solicitud (`nueva-solicitud.html`).

## Configuración administrable (Fase 2A)

Todo lo que define cómo trabaja el laboratorio se administra desde el menú **Configuración** (solo administradores) y queda registrado en la bitácora:

| Pantalla | Qué se administra |
|---|---|
| **Catálogos** | Tipos de trabajo → materiales → (unidades y guías de color) → colores; motivos de RP; áreas. Activar/desactivar sin borrar historial y vista previa de la cadena. |
| **Flujos de trabajo** | Pasos (áreas en orden) por tipo de trabajo y modalidad digital/analógica. Cada paso muestra cuántos empleados pueden atenderlo; en rojo si nadie. |
| **Asignaciones** | Por empleado y área: todos los tipos de trabajo o solo algunos (ej. CAD solo coronas). Las áreas se asignan en Empleados. |
| **Calendario y reglas** | Horas de corte (lun-vie y sábado), días hábiles mínimos (digital, analógico, emergencia), días **sin labores** y días con **horario especial** (se trabaja pero cierra antes, ej. 24 y 31 de diciembre hasta las 12:00), carga de feriados de Guatemala (Semana Santa calculada por año) y un probador de la fecha mínima de entrega. |

Al primer arranque se cargan datos iniciales de ejemplo (6 tipos de trabajo, 6 materiales, guías VITA Classic y 3D-Master, 12 flujos, 8 motivos de RP y feriados del año actual y el siguiente). Solo se cargan si las tablas están vacías, así que tus cambios nunca se sobrescriben.

La regla de **fecha mínima de entrega** se calcula en el servidor (`GET /config/fecha-minima`) con la hora de Guatemala.

## Solicitudes: caso nuevo (CN) y reapertura (RP) (Fase 2B)

| Pantalla | Quién | Qué hace |
|---|---|---|
| **Nueva solicitud** | doctor; admin, supervisor e ingresos (a nombre de un cliente) | Caso nuevo **CN-00001…**: modalidad digital (STL obligatorio) o analógica (genera recolecta), paciente, doctor tratante, tipo → material → unidades / guía → color (cada uno con "fuera de catálogo"), odontograma FDI, emergencia, fecha de entrega con las reglas del calendario, dirección existente o nueva, instrucciones y adjuntos. |
| **Mis casos / Solicitudes** | todos | Pestañas vigentes, historial y todos; búsqueda por código, paciente o doctor. El personal ve el cliente y la prioridad; el doctor no ve su nivel. |
| **Detalle del caso** | todos | Datos, archivos descargables, línea de tiempo, reaperturas. Botón **Reabrir caso (RP)** solo si el caso está entregado y no tiene otra reapertura en curso. Admin y supervisor pueden cambiar el estado manualmente (temporal, para probar el recorrido). |
| **Reabrir caso** | doctor; admin, supervisor, ingresos | Reapertura **RP-00001…** ligada al caso original: garantía o modificación, motivo obligatorio, solo piezas del caso original, recolecta física o nuevo STL. Entra en estado **Validación de QA**. |

Reglas que valida el servidor (aunque se use Swagger directamente): cadena de catálogos, modalidad con flujo activo, fecha mínima, fines de semana y días sin labores, piezas FDI válidas, dirección del propio cliente, STL obligatorio en digital, un solo RP abierto por caso.

**Archivos:** se suben primero con `POST /archivos` (STL hasta 80 MB; JPG, PNG y PDF hasta 15 MB) y se guardan en **MongoDB con GridFS**; PostgreSQL guarda la referencia en `solicitud_archivos`. Los que no se usan en 24 h se borran solos.

**Estados:** pendiente de recolecta · validación de QA · en revisión de Ingresos · en producción · control de calidad · facturación y empaque · en ruta · entregada · cancelada. El estado se calcula solo según el paso en que va el caso.

## Operación: lotes, ausencias, tiempos, cobros y dashboards

| Módulo | Qué hace |
|---|---|
| **Áreas y metas** (admin) | Por área: **trabajo por lote** (solo producción) con máximo de trabajos simultáneos por técnico y **meta en horas laborales**. Por defecto Yesos, CAM_IMP y CAM_FRES trabajan por lote con 15; CAM tiene meta de 8 h y el resto 4 h. El **inicio de jornada** se configura en Calendario y reglas. |
| **Bandeja por lote** | En áreas por lote el técnico ve todo lo asignado, inicia varios (uno por uno o "Iniciar N en orden de prioridad") hasta el máximo y los termina por separado. En las demás áreas solo ve el trabajo actual, el siguiente y cuántos esperan. |
| **Retrabajos** | QA elige el paso y **qué se repite**: *desde ese paso en adelante* (ese y los de producción que siguen, luego QA; para rehacer todo se elige el primero, marcado "todo el trabajo") o *solo ese paso* (y regresa directo a QA). Las tarjetas del paso repetido muestran "Retrabajo" con el motivo de QA; la auditoría marca como devuelto el paso original. |
| **Ausencias** (admin, supervisor) | Empleado, fechas y motivo ("Solo hoy" en un clic). Mientras no labora no recibe trabajo; lo que tenía asignado sin iniciar se reparte solo y las rutas de un mensajero vuelven a Logística. Lo que tenía en proceso aparece en el Dashboard para reasignarlo. |
| **Auditoría de tiempos** | Tabla `tiempos_paso`: una fila por paso terminado con espera, tiempo de trabajo y tiempo total en **horas laborales** (sin noches, domingos ni días sin labores), la meta vigente y si la cumplió. Cambiar una meta no altera el histórico. |
| **Cobros** (facturación; admin y supervisor; operaciones consulta) | Facturas pendientes por días calendario desde que se facturaron: **Hoy · 1–5 · 6–10 · 11–15 · Más de 15**, más pagados de los últimos 30 días. **Marcar pagado** con fecha y referencia. Las RP con garantía total o parcial sin cobro no entran. |
| **Dashboard** (admin, supervisor, operaciones) | En pestañas: **En vivo** ·  **Metas por área** · **Volumen y reaperturas** · **Técnicos** (las tres últimas con rango de fechas). En vivo: vigentes, vencidos, vencen hoy/mañana, emergencias, colas, sin técnico, devoluciones de QA, carga por área, ausentes y trabajos en proceso de ausentes. Periodo: cumplimiento de meta por área, puntualidad de entregas, volumen CN/RP y por tipo, reaperturas por clasificación y motivo, visitas fallidas, días de cobro y producción por técnico. |
| **Mis métricas** (cada empleado) | Solo sus datos: terminados hoy/semana/30 días, tiempos frente a la meta por área, devueltos por QA y próximos vencimientos. |
| **Rol Operaciones** | Gerencia de área: solo consulta Dashboard, Cobros y Solicitudes. |

## Clientes: datos comerciales y color por pieza

- **Clientes** también para **Supervisor, Ingresos y Facturación**: consultan, administran **direcciones de entrega** y **datos comerciales**: **Cliente Odoo** (número del sistema de facturación) y **Crédito**. Los datos principales (razón social, NIT, prioridad, acceso) siguen siendo solo del admin. El crédito lo puede activar cualquiera de esos roles, pero **solo el admin lo quita**.
- Un cliente **con crédito no pasa a Cobros**: al facturar su caso queda como "crédito". Facturación ve en la tarjeta el Cliente Odoo y si es crédito o contado; la orden PDF también los muestra.
- **Color por pieza**: con una guía del catálogo y dos o más piezas, el doctor puede marcar "Colores distintos por pieza". El color elegido queda como base y cada pieza puede cambiarlo (misma guía). Se ve en el detalle, en las bandejas y en el odontograma de la orden PDF. Una reapertura conserva los colores de sus piezas; si Ingresos cambia la guía, se limpian.

## Tablero Kanban del doctor

**Mi tablero** es la pantalla principal del doctor (entra ahí al iniciar sesión). Columnas: **Recibido** (recolecta, Ingresos o validación de QA) · **En producción** · **Control de calidad** · **Listo para entrega** (facturación, listo y en ruta) · **Entregado** (últimos 15 días, con botón para reabrir). Cada tarjeta muestra el avance en pasos, la fecha de entrega (en rojo si ya pasó) y si es emergencia o RP. En celular las columnas se deslizan de lado. Admin, supervisor e Ingresos pueden ver el tablero de cualquier cliente en **Tablero por cliente**. API: `GET /solicitudes/tablero`.

## Recorrido y bandejas (Fase 3A)

Al crear un caso se copia el **flujo** de su tipo de trabajo y modalidad como su recorrido (ej. Logística → Ingresos → Yesos → CAD → CAM_FRES → Finalización → QA → Facturación_Cobros → Logística). Siempre hay un paso de Ingresos; un RP empieza con la validación de QA.

| Área | Qué hace en **Mi bandeja** |
|---|---|
| Logística | Marca **Recolectado** (analógico) y **Entregado**. Entregado finaliza el caso. |
| Ingresos | **Aprobar** (o "Material recibido · aprobar"), **Modificar** (asigna del catálogo lo que venía fuera de catálogo, piezas y fecha) o **Cancelar**. Al aprobar se arma el resto del recorrido con el flujo vigente. |
| Ingresos · caja | Al **aprobar** es obligatorio elegir el **color de caja** (catálogo administrable en Catálogos → Colores de caja: Azul, Celeste, Verde, Naranja, Roja) y el **número de caja**. Una caja no puede estar en dos casos abiertos. La caja se ve en todas las bandejas, la vista del supervisor, Solicitudes (se puede buscar "azul 12"), el detalle y el tablero por cliente. |
| Orden de trabajo (PDF) | Después del Ok de Ingresos se ofrece **Imprimir orden (PDF)**; también desde el detalle del caso (solo personal). Incluye logo y DENTAL TRACK, CN o RP con código de barras, caja en grande, entrega, prioridad, cliente y paciente, trabajo, odontograma, instrucciones, direcciones, datos de la reapertura y QA (RP) y el recorrido con columna de firma. Se genera en el backend con reportlab (`GET /solicitudes/{id}/orden.pdf`). |
| Producción | El sistema asigna cada paso a un empleado con esa área y tipo de trabajo, con menos carga y sin pasar su **máximo de trabajos**. Si todos están al tope queda **en cola**; si nadie cubre el paso, **sin técnico**. El técnico ve su total, trabaja **uno a la vez** y el sistema le entrega el siguiente por prioridad (emergencia → VIP → normal, luego fecha de entrega). |
| QA | **Clasificar RP** (garantía total, parcial sin cobro, parcial con cobro o cobro + motivo) y control de calidad: **Aprobar** o **Devolver** a un paso de producción (por defecto el anterior); el caso repite desde ahí hasta QA. |
| Facturación | **Registrar factura** (número obligatorio) y empaque. |
| Logística + mensajero | Ver **Logística: recolecta y transporte** abajo. |
| Admin / supervisor | **Reasignar** cualquier trabajo de producción (en cola, sin técnico, asignado o en proceso) a otro técnico, y **cambiar la prioridad** de un caso (1 emergencia, 2 VIP, 3 normal) con motivo; el doctor no ve la prioridad. |
| Admin / supervisor | **Bandeja del laboratorio**: carga por área, colas y casos sin técnico; detalle de cada área con el técnico asignado. Pueden cancelar un caso desde su detalle. |

Las colas se reparten solas cada vez que alguien termina un paso o abre su bandeja. Las áreas especiales se reconocen por su nombre: **Ingresos, Logística, QA y Facturación**; no las renombres a otra cosa. Los casos abiertos creados antes de esta versión arrancan su recorrido desde el primer paso al actualizar.

## Logística: recolecta y transporte

Al crear la solicitud (doctor o personal) se indica:
- **Cómo llega el material** (solo analógico): **recolecta con mensajero** o **el cliente lo envía por transporte**.
- **Cómo sale el trabajo terminado**: **mensajero** o **transporte**. Ingresos puede cambiarlo al modificar el caso y Logística mientras el paso está en su área (con motivo, queda en el historial).

| Situación | Estados | Quién |
|---|---|---|
| Recolecta con mensajero | **Asignado** → **Recolectado** (el mensajero ya tiene el material) → **Entregado en laboratorio** (pasa a Ingresos). Plazo de **2 horas laborales** desde que se crea la solicitud: la tarjeta muestra la hora límite y se marca en rojo si vence; el Dashboard cuenta recolectas pendientes y vencidas y la auditoría de tiempos mide el plazo (meta 2 h). | Logística asigna; mensajero marca |
| Material por transporte | **Esperando material por transporte** → **Recibido** (guía opcional). Sin plazo de 2 h. | Logística |
| Entrega con mensajero | **Asignado** (en ruta) → **Entregado** con nombre de quien recibe. | Logística asigna; mensajero marca |
| Entrega por transporte | **Entregado a transporte** con **número de guía** (obligatorio) y empresa (opcional): el caso queda finalizado. Logística lo registra o se lo asigna a un mensajero para que lo lleve a la agencia. | Logística o mensajero |

"No se pudo" (con motivo) regresa la recolecta o entrega a Logística. La guía de salida aparece en el detalle del caso (también para el doctor) y en la orden PDF.

## Quién ve qué solicitudes

| Rol | Ve en Solicitudes, detalle, archivos y orden PDF |
|---|---|
| Administrador, Supervisor, Operaciones, Ingresos, Facturación, Demostración | Todas |
| Técnico, Mensajero | Solo los casos con un paso que tuvieron asignado o atendieron |
| Logística, QA | Esos y los que ya llegaron a su área |
| Doctor | Solo los de su cuenta |

Un caso fuera de su alcance responde "no encontrado" (no se revela que existe). El filtro se aplica en el servidor.

## Pausas

Administración y supervisión pausan un caso desde su detalle, con **motivo obligatorio** (ej. "falta registro de mordida").
- Mientras está en pausa nadie lo puede trabajar: las bandejas lo muestran "En pausa" sin botones y no ocupa el tope de los técnicos.
- El doctor ve **"En pausa"** con el motivo.
- Al **reanudar** se registra qué se recibió y, si hace falta, una nueva fecha de entrega. Las **horas laborales en pausa se descuentan** de la meta del paso (espera o trabajo) y del plazo de recolecta.
- Cada pausa queda en la tabla de auditoría `pausas` (quién pausó, motivo, dónde estaba el caso, quién reanudó, horas, cambio de fecha) y en la bitácora. Conteo en el Dashboard.
- Pantalla **Pausas** (admin, supervisor, operaciones), como la de cobros: pestañas de casos en pausa por antigüedad (Hoy, 1–2 días, 3–5 días, más de 5 días en alerta) y una pestaña **Historial (auditoría)** con filtro de fechas.

## Validación de diseño con el cliente

Área **Validación de diseño** (no renombrar) entre el diseño (Diseño/CAD) y la impresión o fresado. Al actualizar se agrega una sola vez a los flujos donde Diseño/CAD va seguido de CAM; el administrador puede quitarla o moverla.
- El supervisor envía el diseño al cliente fuera de la plataforma y registra **Enviado al cliente**; luego **Cliente aprobó** (sigue a CAM) o **Pidió cambios** (motivo; regresa al paso de diseño elegido y vuelve a validarse).
- Pantalla **Validación de diseño**: "Por enviar" y enviados sin respuesta por antigüedad (Hoy, 1 día, 2–3 días, 4 días o más).
- El doctor ve "Diseño enviado: pendiente de tu aprobación".
- Al desplegar, los casos abiertos que aún no llegan a CAM (su siguiente paso de impresión o fresado está pendiente y justo antes va Diseño/CAD) reciben la validación en su recorrido. Se hace una sola vez.

## Agenda de entregas

Pantalla **Agenda de entregas** (admin, supervisor, operaciones, logística, demo) para ver de un vistazo qué está por salir:
- Pestañas **Atrasados**, **Hoy**, **Siguiente día** (siguiente día hábil, de lunes a viernes según el calendario), **Próximos** (los 5 días hábiles siguientes) y **Listos para salir** (facturación, listo para entrega o en ruta).
- Cada caso muestra dónde va (área actual o estado), fecha de entrega y días de atraso, caja y si sale por mensajero o transporte.
- **En riesgo**: vence hoy o el siguiente día hábil y todavía no termina producción ni QA. Filtro "Solo en riesgo" y búsqueda por código, cliente, paciente o caja. Se actualiza sola cada 2 minutos.

## Mapas de calor (Dashboard → Mapas)

Dos mapas independientes, cada uno con su filtro de **tipo de trabajo** y **material**, sobre el periodo del Dashboard:
- **Entregas** (tonos azules): dirección de entrega de los casos entregados.
- **Recolectas** (tonos rojos): dirección de recolecta de las recolectas terminadas.
- Debajo de cada mapa, las 10 zonas o municipios con más casos.
- Ubicación aproximada, sin la casa exacta: en la Ciudad de Guatemala se usa la **zona** de la dirección ("Zona 10"); en el área metropolitana, el municipio (tabla incluida); otros municipios se consultan una vez a Nominatim (OpenStreetMap) y se guardan en la tabla `geocodigos`; si no se encuentra, el centro del departamento (cuenta como "aproximado").
- Los mapas base (CARTO/OpenStreetMap) y Nominatim requieren internet. Para no consultar Nominatim: `GEOCODIFICAR=false` en el backend. Leaflet y leaflet.heat van incluidos en `frontend/static/vendor/leaflet`.

## Pasos en paralelo

En **Flujos**, un paso de producción puede marcarse **"en paralelo con el anterior"** (ej. CAM_IMP y CAM_FRES con el mismo diseño). Ambos se asignan e inician a la vez y el caso pasa al siguiente paso cuando **todos** terminan. Si QA devuelve desde uno de ellos, los pasos paralelos se repiten juntos.

## Órdenes manuales

Administración, Supervisión, Ingresos y Facturación (y el perfil demo) pueden crear una orden desde **Nueva solicitud** eligiendo el cliente, con un **motivo** opcional (ej. "pedido por teléfono").
- Quedan marcadas como **Orden manual** en Solicitudes (con filtro "Solo órdenes manuales"), tablero, bandejas, detalle (quién la capturó y el motivo) y en la orden PDF.
- El doctor las ve en su historial como **"Creada por el laboratorio"**, sin nombres del personal ni el motivo interno.
- El Dashboard (Volumen) cuenta cuántas órdenes del periodo fueron manuales.
- Al actualizar, los casos existentes capturados por el personal se marcan como manuales automáticamente.

## Perfil de demostración

Rol `demo` (Empleados → Rol **Demostración**, sin áreas). También puede crearse al arrancar con las variables opcionales del backend `DEMO_EMAIL` y `DEMO_PASSWORD`.
- Menú de administrador completo en **solo consulta** (aviso "Modo demostración"; el backend rechaza cualquier cambio con 403).
- **Línea de producción**: todas las áreas con sus casos y botones para hacer cualquier paso, sin reglas de turno. Lo que inicia en producción queda a su nombre para no alterar las métricas de los técnicos.
- Puede crear solicitudes a nombre de un cliente e imprimir la orden. No cancela, no cambia prioridades ni reasigna.

## Diseño adaptable

Todas las pantallas se ajustan a celular, tablet y computadora: en pantallas de hasta 900 px el menú lateral se abre como cajón con el botón ☰, las tablas se convierten en tarjetas en pantallas de hasta 760 px y los formularios modales ocupan toda la pantalla en celular.

## Estructura

```
DENTAL-TRACK-APP/
├── herramientas/          conversión del Excel de datos simulados
├── backend/
│   ├── app/
│   │   ├── core/          configuración, errores, seguridad, validaciones NIT/DPI
│   │   ├── db/            conexión PostgreSQL, MongoDB y datos iniciales
│   │   ├── modelos/       tablas (SQLAlchemy)
│   │   ├── esquemas/      contratos de entrada/salida (Pydantic)
│   │   ├── repositorios/  acceso a datos
│   │   ├── servicios/     reglas de negocio
│   │   ├── rutas/         endpoints internos
│   │   └── main.py
│   ├── requirements.txt
│   └── railway.json
├── api/
│   ├── app/
│   │   ├── rutas/         endpoints públicos (documentados en Swagger)
│   │   ├── backend.py     cliente HTTP hacia el backend
│   │   ├── seguridad.py   JWT y roles
│   │   └── main.py
│   ├── requirements.txt
│   └── railway.json
└── frontend/
    ├── static/            login, inicio, clientes, empleados, bitácora, css, js, img
    ├── server.py          sirve los archivos e inyecta la URL de la API
    ├── requirements.txt
    └── railway.json
```

## Despliegue en Railway

### 1. Bases de datos
En el proyecto de Railway: **+ New → Database → PostgreSQL** y luego **+ New → Database → MongoDB**.
Railway los llama `Postgres` y `MongoDB`; si les cambias el nombre, ajusta las referencias de abajo.

### 2. Tres servicios desde el mismo repositorio de GitHub
Crea tres veces **+ New → GitHub Repo → DENTAL-TRACK-APP** y en cada uno ve a **Settings**:

| Servicio (nombre exacto) | Root Directory | Config file path | Watch paths |
|---|---|---|---|
| `backend` | `/backend` | `/backend/railway.json` | `/backend/**` |
| `api` | `/api` | `/api/railway.json` | `/api/**` |
| `frontend` | `/frontend` | `/frontend/railway.json` | `/frontend/**` |

> El archivo `railway.json` no sigue al Root Directory, por eso se indica su ruta completa. Si prefieres no usarlo, copia su `startCommand` en **Settings → Deploy → Start Command**.

Los nombres `backend`, `api` y `frontend` importan porque las variables se refieren a ellos.

### 3. Variables de entorno (pestaña **Variables** de cada servicio)

Genera dos claves largas y aleatorias (una para `INTERNAL_KEY`, otra para `JWT_SECRET`).

**backend**
```
DATABASE_URL=${{Postgres.DATABASE_URL}}
MONGO_URL=${{MongoDB.MONGO_URL}}
MONGO_DB=dentaltrack
INTERNAL_KEY=<clave-interna>
ADMIN_EMAIL=<tu correo de administrador>
ADMIN_PASSWORD=<contraseña inicial del administrador>
PORT=8000
# opcional: GEOCODIFICAR=false para no consultar Nominatim en los mapas
# opcional: usuario de demostración
DEMO_EMAIL=<correo del usuario demo>
DEMO_PASSWORD=<contraseña del usuario demo>
```

**api**
```
BACKEND_URL=http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:8000
INTERNAL_KEY=<la misma clave-interna del backend>
JWT_SECRET=<secreto-jwt>
JWT_HORAS=10
CORS_ORIGINS=https://${{frontend.RAILWAY_PUBLIC_DOMAIN}}
```

Opcional, para cargar los datos simulados (25 empleados y 20 clientes) al arrancar:
```
CARGAR_DATOS_PRUEBA=true
```
La carga no duplica registros: omite correos o NIT que ya existan. Cuando termines las pruebas puedes quitar la variable.

**frontend**
```
API_URL=https://${{api.RAILWAY_PUBLIC_DOMAIN}}
```

### 4. Dominios
- **api** y **frontend**: Settings → Networking → **Generate Domain**.
- **backend**: **no** generes dominio público. Solo se alcanza por la red privada.

### 5. Verificar
- `https://<api>/salud` debe mostrar backend, postgres y mongo en `ok`.
- `https://<api>/docs` abre Swagger. Usa **POST /auth/login**, copia el `access_token` y presiona **Authorize**.
- `https://<frontend>` abre el login. Entra con `ADMIN_EMAIL` / `ADMIN_PASSWORD`.

El administrador inicial y las 10 áreas del laboratorio se crean solos al primer arranque del backend. Las tablas se crean con `create_all` (suficiente para esta fase; más adelante se puede migrar a Alembic).

## Datos de prueba

`backend/app/db/datos_prueba.json` contiene los empleados y clientes simulados, con contraseñas **cifradas** (bcrypt). Las contraseñas iniciales en texto están en `credenciales_prueba.xlsx`, que **no** se sube al repositorio.

Para regenerar ambos archivos desde el Excel de datos simulados:

```bash
pip install openpyxl bcrypt
python herramientas/preparar_datos_prueba.py datos_simulados_de_prueba.xlsx
```

Reglas aplicadas en la conversión:
- **Prioridad:** 1 = emergencia (se marca en la solicitud), 2 = cliente VIP, 3 = cliente normal.
- **NIT:** se conserva el número y se recalcula el dígito verificador, porque los del Excel son ficticios.
- **Teléfonos de clientes:** se guardan como fijo. El sistema exige al menos un teléfono.
- **Direcciones:** departamento y municipio se deducen del texto (por defecto Guatemala, Guatemala).
- **Empleados:** Jorge Jimenez y Axel Aguilar son administradores; el resto se reparte entre ingresos, técnicos por área, QA, facturación y logística.

> **Actualización desde la versión anterior:** el backend incluye una migración automática (`backend/app/db/migraciones.py`). Al arrancar agrega las columnas nuevas, llena la razón social con el nombre del doctor y convierte las prioridades (1 → 2 VIP, 2 → 3 normal) sin borrar datos. Es segura de ejecutar en cada reinicio.

## Ejecución local (opcional)

Requiere Python 3.12, PostgreSQL y MongoDB locales.

```bash
# backend (puerto 8001)
cd backend && pip install -r requirements.txt
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dentaltrack \
MONGO_URL=mongodb://localhost:27017 INTERNAL_KEY=local \
uvicorn app.main:app --port 8001

# api (puerto 8002)
cd api && pip install -r requirements.txt
BACKEND_URL=http://localhost:8001 INTERNAL_KEY=local JWT_SECRET=local \
uvicorn app.main:app --port 8002

# frontend (puerto 8003)
cd frontend && pip install -r requirements.txt
API_URL=http://localhost:8002 uvicorn server:app --port 8003
```

Sin servidor Mongo se puede probar con `MONGO_URL=mongomock://local` (requiere `pip install mongomock`).

## Endpoints públicos (API)

| Método | Ruta | Rol |
|---|---|---|
| POST | `/auth/login` | público |
| POST | `/auth/registro` | público (crea cliente con prioridad normal) |
| GET | `/auth/yo` | cualquiera con sesión |
| GET/POST | `/clientes` | admin |
| GET/PUT | `/clientes/{id}` | admin |
| PATCH | `/clientes/{id}/estado` | admin |
| PATCH | `/clientes/{id}/comercial` | admin, supervisor, ingresos, facturación (crédito: solo admin lo quita) |
| POST | `/clientes/{id}/password` | admin |
| POST | `/clientes/{id}/direcciones` | admin |
| PUT/DELETE | `/clientes/{id}/direcciones/{dir}` | admin |
| GET/POST | `/empleados` | admin |
| GET/PUT | `/empleados/{id}` | admin |
| PATCH | `/empleados/{id}/estado` | admin |
| POST | `/empleados/{id}/password` | admin |
| GET | `/areas`, `/departamentos` | cualquiera con sesión |
| GET | `/auditoria` | admin |
| GET | `/config/arbol`, `/config/parametros`, `/config/calendario`, `/config/fecha-minima` | cualquiera con sesión |
| GET/POST/PUT | `/config/catalogos`, `/config/tipos/…`, `/config/materiales/…`, `/config/guias/…`, `/config/colores/…` | admin |
| GET/PUT | `/config/flujos`, `/config/asignaciones`, `/config/parametros` | admin |
| POST/DELETE | `/config/calendario`, `/config/calendario/feriados/{anio}` | admin |
| POST/DELETE | `/archivos`, `/archivos/{id}` | cualquiera con sesión |
| GET | `/solicitudes`, `/solicitudes/{id}`, `/solicitudes/{id}/archivos/{archivo}` | con sesión (el doctor solo lo suyo) |
| GET | `/solicitudes/perfil`, `/solicitudes/clientes` | doctor / admin, supervisor, ingresos |
| POST | `/solicitudes`, `/solicitudes/{id}/reapertura` | doctor, admin, supervisor, ingresos |
| POST | `/solicitudes/{id}/cancelar` | admin, supervisor |
| GET | `/bandeja` (`?area_id=` para supervisión) | personal del laboratorio |
| POST | `/pasos/{id}/iniciar`, `/pasos/{id}/terminar` | técnico asignado / integrantes del área |
| POST | `/pasos/{id}/validar-rp`, `/pasos/{id}/rechazar` | QA |
| PUT/POST | `/pasos/{id}/modificar`, `/pasos/{id}/cancelar` | Ingresos |
| GET/POST | `/pasos/{id}/candidatos`, `/pasos/{id}/asignar` | Logística (mensajero) · admin y supervisor (técnico) |
| POST | `/pasos/{id}/no-se-pudo` | mensajero asignado, Logística |
| POST | `/pasos/{id}/recolectado` | mensajero asignado, Logística |
| POST | `/pasos/{id}/metodo` | Logística: cambiar entre mensajero y transporte |
| POST | `/solicitudes/{id}/pausar`, `/solicitudes/{id}/reanudar` | admin, supervisor |
| GET | `/pausas` | admin, supervisor, operaciones (auditoría; `?abiertas=true` solo las vigentes) |
| GET | `/agenda-entregas` | admin, supervisor, operaciones, logística, demo |
| GET | `/metricas/mapa?capa=entregas\|recolectas` | roles de métricas (filtros `desde`, `hasta`, `tipo_trabajo_id`, `material_id`) |
| POST | `/pasos/{id}/enviar-cliente`, `/pasos/{id}/cambios-diseno` | supervisión (validación de diseño) |
| GET | `/validaciones-diseno` | admin, supervisor |
| POST | `/solicitudes/{id}/prioridad` | admin, supervisor |
| GET/PUT | `/config/areas-operacion` | lectura con sesión · edición admin |
| GET/POST/DELETE | `/ausencias` | admin, supervisor (operaciones consulta) |
| GET / POST | `/cobros`, `/cobros/{id}/pagar` | facturación, admin, supervisor (operaciones consulta) |
| GET | `/metricas/operacion`, `/metricas/mias` | admin, supervisor, operaciones · cada empleado |
| GET | `/salud` | público |
