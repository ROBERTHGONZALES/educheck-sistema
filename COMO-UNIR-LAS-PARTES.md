# Cómo se compone el proyecto

> **Nota:** este repositorio ya contiene las 3 partes en la estructura descrita.
> Este documento sirve para reconstruir el proyecto si trabajas con las partes por separado.

Cada parte puede mantenerse en un repositorio independiente. Para ejecutar el sistema
completo, colócalas en una sola carpeta con esta estructura:

```text
educheck/
├── backend/                     ← contenido de parte-1-backend-django
├── src/                         ← contenido de parte-2-frontend-react
├── packages/
├── public/
├── index.html
├── package.json
├── package-lock.json
├── tsconfig.json
├── vite.config.ts
├── .env.example
├── dist/                        ← contenido de parte-3
├── deploy/                      ← contenido de parte-3
├── README.md                    ← contenido de parte-3
└── README-LOCAL-WINDOWS.md      ← contenido de parte-3
```

## Pasos

1. Copia el contenido de **parte 1** dentro de `educheck/backend/`.
2. Copia el contenido de **parte 2** directamente en `educheck/`.
3. Copia el contenido de **parte 3** en `educheck/` (la carpeta `deploy/`, `dist/`, los
   README y este archivo quedan en la raíz).

## Preparar el backend

```bash
cd educheck/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # edita MARIADB_URL y DJANGO_SECRET_KEY
python manage.py migrate
```

Crea la base de datos antes de migrar:

```bash
mysql -u root -p < sql/create_database.sql
```

Crea un director (el script de demo lo necesita):

```bash
python manage.py create_school_user --username director --role director \
  --first-name Director --last-name Demo --password 'EduCheck2026!'
```

## Preparar el frontend

```bash
cd educheck
npm install
```

`vite.config.ts` reenvía `/api/*` a `http://127.0.0.1:8000`.

## Ejecutar

Opción manual (dos terminales):

```bash
# terminal 1
cd educheck/backend && source .venv/bin/activate
python manage.py runserver 127.0.0.1:8000

# terminal 2
cd educheck && npm run dev
```

Opción automática en Linux/macOS:

```bash
./deploy/educheck.sh start     # levanta MariaDB + Django + Vite
./deploy/educheck.sh status
./deploy/educheck.sh stop
```

## Datos de demostración

```bash
cd educheck/backend
source .venv/bin/activate
python ../deploy/seed_demo.py
```

## Usuarios y puertos

| Elemento | Valor |
| --- | --- |
| Frontend (Vite) | `http://127.0.0.1:5173` |
| Backend (Django) | `http://127.0.0.1:8000` |
| Base de datos | MariaDB/MySQL, esquema `educheck` |
| Director demo | `director` / `EduCheck2026!` |
| Auxiliar demo | `auxiliar` / `EduCheck2026!` |
