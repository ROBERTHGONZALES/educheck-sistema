# EduCheck local para Windows

Este paquete reúne la interfaz React/Vite y el cliente API del proyecto en un workspace npm autónomo. Reemplaza los protocolos `catalog:` y `workspace:*` propios del workspace de Replit por dependencias de npm y un paquete local. También elimina los plugins de desarrollo exclusivos de Replit.

## Ejecutar y compilar la interfaz

Instala Node.js 20.19 o superior (se recomienda Node.js 22 LTS). En PowerShell, desde la carpeta `educheck-local`:

```powershell
npm install
npm run dev
```

Abre `http://127.0.0.1:5173`. Para generar los archivos estáticos, ejecuta:

```powershell
npm run build
```

La compilación queda en `dist/`; `npm run preview` la sirve localmente en `http://127.0.0.1:4173`.

La portada ofrece “Solicitar demostración” si configuras `VITE_CONTACT_EMAIL` en un archivo `.env` en la raíz del frontend. Si no defines un correo, el botón principal lleva al ingreso del sistema.

## Conectar la aplicación completa

La compilación estática solo entrega la interfaz. Inicio de sesión, estudiantes, asistencia y reportes necesitan también el backend Django y MariaDB: no se reemplazaron por datos simulados. El servidor Vite ya reenvía `/api/*` a `http://127.0.0.1:8000`, así que inicia Django en ese puerto para conectar la interfaz.

El código del backend se incluye en `backend/`. Para ponerlo en marcha se necesita Python 3.13, un servidor MariaDB local y las dependencias del archivo `backend/requirements.txt`. Para exportar PDF en Windows, WeasyPrint también necesita las bibliotecas GTK/Pango de MSYS2. Instálalas una vez y configura `WEASYPRINT_DLL_DIRECTORY` en `backend/.env` con la carpeta `bin` del entorno UCRT64:

```powershell
& 'C:\msys64\usr\bin\pacman.exe' -S --needed mingw-w64-ucrt-x86_64-gtk3
```

La compilación del frontend no necesita Python ni MariaDB.

En la instalación local preparada, los datos de MariaDB se guardan fuera del proyecto, en `%LOCALAPPDATA%\EduCheck\mariadb-data\data`, y el servidor solo escucha en `127.0.0.1`. Para volver a iniciarlo después de reiniciar Windows, ejecuta esto en una terminal PowerShell y déjala abierta:

```powershell
& 'C:\Program Files\MariaDB 13.0\bin\mariadbd.exe' --no-defaults --basedir='C:\Program Files\MariaDB 13.0' --datadir="$env:LOCALAPPDATA\EduCheck\mariadb-data\data" --bind-address=127.0.0.1 --port=3306 --innodb-buffer-pool-size=256M --console
```

Pasos generales para el backend:

1. Inicia MariaDB y crea la base vacía con `backend/sql/create_database.sql`.
2. Crea un usuario MariaDB local exclusivo para la aplicación y dale permisos sobre `educheck`. No conectes Django con la cuenta root.
3. Copia `backend/.env.example` como `backend/.env` y reemplaza los valores de muestra por la URL de MariaDB local y una clave secreta aleatoria.
4. Desde la raíz del paquete, crea y activa el entorno virtual, instala requisitos y aplica migraciones:

   ```powershell
   py -3.13 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r backend\requirements.txt
   python backend\manage.py migrate
   ```

5. Inicia la API en la raíz del paquete:

   ```powershell
   python backend\manage.py runserver 127.0.0.1:8000
   ```

6. En otra terminal, dentro de la raíz, ejecuta `npm run dev`.

Después de las migraciones, crea las cuentas iniciales con `python backend\manage.py create_school_user --school "Nombre del colegio" --username director --role director` y sigue el aviso interactivo para establecer la contraseña.

El panel del director incluye **Alertas de inasistencia** en `/director/alertas`. Cuenta como días revisados las fechas en que el colegio registró al menos una asistencia; por defecto muestra estudiantes con tres faltas seguidas, sin contar días previos a su matrícula. Las alertas se calculan sobre los últimos 60 días registrados y no envían mensajes automáticamente.

## Alcance de esta adaptación

- Las dependencias del frontend están declaradas con versiones compatibles de npm; no se necesita pnpm ni el workspace de Replit.
- El paquete conserva el cliente API generado y lo enlaza localmente mediante `file:`.
- Los datos binarios de MariaDB y los archivos de compilación de Replit no se incluyen.
- El backend conserva su configuración de MariaDB; no se cambió a SQLite ni se incluyeron credenciales o una base de datos precargada.
