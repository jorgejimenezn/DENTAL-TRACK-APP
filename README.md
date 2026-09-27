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
- **Empleados**: alta, edición, roles (admin, ingresos, técnico, QA, facturación, logística), áreas del laboratorio, activar/desactivar, restablecer contraseña. No se puede desactivar ni quitar el rol al último administrador.
- **Bitácora** en MongoDB: inicios de sesión (exitosos y fallidos), creaciones, ediciones con valores antes/después.
- **Registro público de clientes** desde el login (`registro.html`): la cuenta se crea siempre como cliente (rol doctor) con prioridad 3 (normal); el servidor ignora cualquier otro rol o prioridad enviados. Al terminar, la sesión queda iniciada.
- **Prototipo** del formulario de nueva solicitud (`nueva-solicitud.html`).

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
| GET | `/salud` | público |
