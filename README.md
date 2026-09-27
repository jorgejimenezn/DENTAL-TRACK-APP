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

## Recorrido y bandejas (Fase 3A)

Al crear un caso se copia el **flujo** de su tipo de trabajo y modalidad como su recorrido (ej. Logística → Ingresos → Yesos → CAD → CAM_FRES → Finalización → QA → Facturación_Cobros → Logística). Siempre hay un paso de Ingresos; un RP empieza con la validación de QA.

| Área | Qué hace en **Mi bandeja** |
|---|---|
| Logística | Marca **Recolectado** (analógico) y **Entregado**. Entregado finaliza el caso. |
| Ingresos | **Aprobar** (o "Material recibido · aprobar"), **Modificar** (asigna del catálogo lo que venía fuera de catálogo, piezas y fecha) o **Cancelar**. Al aprobar se arma el resto del recorrido con el flujo vigente. |
| Producción | El sistema asigna cada paso a un empleado con esa área y tipo de trabajo, con menos carga y sin pasar su **máximo de trabajos**. Si todos están al tope queda **en cola**; si nadie cubre el paso, **sin técnico**. El técnico ve su total, trabaja **uno a la vez** y el sistema le entrega el siguiente por prioridad (emergencia → VIP → normal, luego fecha de entrega). |
| QA | **Clasificar RP** (garantía total, parcial sin cobro, parcial con cobro o cobro + motivo) y control de calidad: **Aprobar** o **Devolver** a un paso de producción (por defecto el anterior); el caso repite desde ahí hasta QA. |
| Facturación | **Registrar factura** (número obligatorio) y empaque. |
| Admin / supervisor | **Bandeja del laboratorio**: carga por área, colas y casos sin técnico; detalle de cada área con el técnico asignado. Pueden cancelar un caso desde su detalle. |

Las colas se reparten solas cada vez que alguien termina un paso o abre su bandeja. Las áreas especiales se reconocen por su nombre: **Ingresos, Logística, QA y Facturación**; no las renombres a otra cosa. Los casos abiertos creados antes de esta versión arrancan su recorrido desde el primer paso al actualizar.

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
| GET | `/salud` | público |
