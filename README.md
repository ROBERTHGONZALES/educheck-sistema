# EduCheck — Parte 1: Backend (Django + DRF)

API REST del sistema de asistencia escolar EduCheck. Esta parte contiene **solo el servidor**:
modelos, endpoints, permisos por colegio, generación de PDF/XLSX, alertas de ausencias e
importación de estudiantes desde Excel.

> Proyecto dividido en 3 repositorios:
> 1. **Backend Django** — este repositorio
> 2. Frontend React — https://github.com/ROBERTHGONZALES/educheck-frontend
> 3. Documentación y despliegue — https://github.com/ROBERTHGONZALES/educheck-documentacion

## Tecnologías

- Python 3.13
- Django 5.2 + Django REST Framework 3.16
- MariaDB / MySQL (utf8mb4)
- WeasyPrint (PDF), openpyxl (XLSX), segno (QR), argon2-cffi (contraseñas)
- pytest + pytest-django

## Puesta en marcha

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # edita MARIADB_URL y DJANGO_SECRET_KEY
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

La base de datos debe existir antes de migrar:

```bash
mysql -u root -p < sql/create_database.sql
```

## Variables de entorno

| Variable | Descripción |
| --- | --- |
| `MARIADB_URL` | `mysql://usuario:clave@host:puerto/educheck?charset=utf8mb4` |
| `DJANGO_SECRET_KEY` | Clave larga y aleatoria |
| `DJANGO_DEBUG` | `1` en desarrollo, `0` en producción |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos, separados por coma |
| `EDUCHECK_ALLOWED_ORIGINS` | Orígenes del frontend (CORS) |
| `CSRF_TRUSTED_ORIGINS` | Orígenes de confianza para CSRF |

No subas tu archivo `.env` al repositorio: ya está en `.gitignore`.

## Endpoints principales

| Método | Ruta | Rol |
| --- | --- | --- |
| GET | `/api/educheck/auth/csrf` | público (inicializa cookie CSRF) |
| POST | `/api/educheck/auth/login` | público |
| GET | `/api/educheck/auth/session` | autenticado |
| POST | `/api/educheck/auth/logout` | autenticado |
| GET | `/api/educheck/director/dashboard` | director |
| GET/POST | `/api/educheck/director/students` | director |
| GET/POST | `/api/educheck/director/grades` | director |
| POST | `/api/educheck/director/sections` | director |
| DELETE | `/api/educheck/director/sections/{id}` | director |
| GET/POST | `/api/educheck/director/assistants` | director |
| PUT | `/api/educheck/director/assistants/{id}/sections` | director |
| GET | `/api/educheck/director/alerts` | director |
| GET | `/api/educheck/director/attendance` | director |
| GET | `/api/educheck/director/reports/summary` | director |
| GET | `/api/educheck/director/reports/export/pdf` | director |
| GET | `/api/educheck/director/reports/export/xlsx` | director |
| GET | `/api/educheck/assistant/sections` | auxiliar |
| GET | `/api/educheck/assistant/sections/{id}/students` | auxiliar |
| POST | `/api/educheck/assistant/attendance/scan` | auxiliar |
| POST | `/api/educheck/assistant/students/import` | auxiliar |
| GET | `/api/educheck/assistant/students/{id}/card.pdf` | auxiliar |

Formato de errores: `{"detail": "mensaje"}` o errores por campo
`{"campo": ["mensaje"]}`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Los tests usan SQLite en memoria (`EDUCHECK_TEST_SQLITE=1`) para no tocar la base real.

## Estructura

```
manage.py
educheck_project/     configuración Django (settings, urls, wsgi)
core/                 modelos, vistas, serializers, permisos, reportes
core/tests/           pruebas de alertas, auxiliares y cookies
tests/                pruebas de aislamiento entre colegios
sql/create_database.sql
```
