# EduCheck — Sistema de asistencia escolar

Aplicación web para registrar y controlar la asistencia de estudiantes mediante **código QR
o DNI**, con paneles separados para **director** y **auxiliar**, reportes en **PDF/XLSX**,
**alertas de ausencias consecutivas** y aislamiento de datos por colegio.

El repositorio reúne las 3 partes del proyecto en una sola estructura ejecutable:

| Parte | Contenido | Carpeta |
| --- | --- | --- |
| 1 | Backend Django + DRF (API REST) | `backend/` |
| 2 | Frontend React + Vite | raíz (`src/`, `packages/`, `public/`) |
| 3 | Documentación, build y despliegue | `deploy/`, `dist/`, README |

## Tecnologías

**Backend:** Python 3.13, Django 5.2, Django REST Framework 3.16, MariaDB/MySQL,
WeasyPrint (PDF), openpyxl (XLSX), segno (QR), argon2-cffi (contraseñas), pytest.

**Frontend:** React 19, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query.

## Estructura

```text
.
├── backend/                 API Django
│   ├── core/                modelos, vistas, serializers, permisos, reportes
│   ├── educheck_project/    configuración (settings, urls, wsgi)
│   ├── core/tests/          pruebas de alertas, auxiliares y cookies
│   ├── tests/               pruebas de aislamiento entre colegios
│   ├── sql/                 script de creación de la base de datos
│   └── requirements*.txt
├── src/                     interfaz React (páginas, componentes, hooks)
├── packages/api-client-react/  cliente de la API
├── public/                  imágenes y favicons
├── dist/                    build del frontend listo para servir
├── deploy/                  arranque local, configuración MariaDB y datos demo
├── index.html
├── package.json
├── vite.config.ts
└── README-LOCAL-WINDOWS.md  guía de instalación en Windows
```

## Puesta en marcha

### 1. Base de datos

```bash
mysql -u root -p < backend/sql/create_database.sql
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # edita MARIADB_URL y DJANGO_SECRET_KEY
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

### 3. Frontend

```bash
npm install
npm run dev
```

Abre `http://127.0.0.1:5173`. Vite reenvía `/api/*` a `http://127.0.0.1:8000`.

### 4. Arranque automático (Linux/macOS)

```bash
./deploy/educheck.sh start     # MariaDB + Django + Vite
./deploy/educheck.sh status
./deploy/educheck.sh stop
```

## Usuarios de demostración

| Usuario | Contraseña | Rol |
| --- | --- | --- |
| `director` | `EduCheck2026!` | director |
| `auxiliar` | `EduCheck2026!` | auxiliar |

Los datos de ejemplo (colegio, grados, secciones y alumnos) se cargan con:

```bash
cd backend && source .venv/bin/activate
python ../deploy/seed_demo.py
```

## Funcionalidades

- **Autenticación** con sesión, cookie CSRF y roles director/auxiliar.
- **Estudiantes**: alta, búsqueda, filtros, estado activo/inactivo, QR único.
- **Asistencia**: escaneo por QR o DNI, turnos mañana/tarde, detección de duplicados.
- **Reportes**: resumen por rango de fechas, exportación a PDF y XLSX.
- **Alertas**: ausencias consecutivas configurables por grado o sección.
- **Auxiliares**: creación, asignación de secciones, importación de estudiantes por Excel
  y generación de carnés PDF.
- **Multi-colegio**: cada cuenta solo ve los datos de su institución.

## API

Base: `/api/educheck/`. Endpoints principales:

| Método | Ruta | Rol |
| --- | --- | --- |
| GET | `/auth/csrf` | público |
| POST | `/auth/login` | público |
| GET | `/auth/session` | autenticado |
| POST | `/auth/logout` | autenticado |
| GET | `/director/dashboard` | director |
| GET/POST | `/director/students` | director |
| GET/POST | `/director/grades` | director |
| POST | `/director/sections` | director |
| DELETE | `/director/sections/{id}` | director |
| GET/POST | `/director/assistants` | director |
| PUT | `/director/assistants/{id}/sections` | director |
| GET | `/director/alerts` | director |
| GET | `/director/attendance` | director |
| GET | `/director/reports/summary` | director |
| GET | `/director/reports/export/pdf` | director |
| GET | `/director/reports/export/xlsx` | director |
| GET | `/assistant/sections` | auxiliar |
| GET | `/assistant/sections/{id}/students` | auxiliar |
| POST | `/assistant/attendance/scan` | auxiliar |
| POST | `/assistant/students/import` | auxiliar |
| GET | `/assistant/students/{id}/card.pdf` | auxiliar |

Los errores se devuelven como `{"detail": "mensaje"}` o por campo
`{"campo": ["mensaje"]}`.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Los tests usan SQLite en memoria (`EDUCHECK_TEST_SQLITE=1`) y no tocan la base real.

## Documentación adicional

- `README-LOCAL-WINDOWS.md` — instalación paso a paso en Windows (incluye WeasyPrint/GTK).
- `COMO-UNIR-LAS-PARTES.md` — cómo se compone el proyecto a partir de sus 3 partes.
- `backend/README.md` — detalle del backend, variables de entorno y endpoints.
