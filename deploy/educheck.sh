#!/usr/bin/env bash
# Arranque local de EduCheck (Linux/macOS): MariaDB + Django (8000) + Vite (5173).
#
# Uso:  ./deploy/educheck.sh {start|stop|restart|status}
#
# Variables opcionales:
#   EDUCHECK_HOME     carpeta de datos/logs (por defecto ~/.local/share/educheck)
#   EDUCHECK_PROJECT  raíz del proyecto (por defecto la carpeta padre de deploy/)
#   MYSQLD            binario de mariadbd/mysqld (por defecto se busca en el PATH)
set -uo pipefail

BASE="${EDUCHECK_HOME:-$HOME/.local/share/educheck}"
PROJECT="${EDUCHECK_PROJECT:-$(cd "$(dirname "$0")/.." && pwd)}"
CNF="$BASE/my.cnf"
LOGS="$BASE/logs"
MYSQLD="${MYSQLD:-$(command -v mariadbd || command -v mysqld || true)}"

mkdir -p "$LOGS"

db_running() {
  mysqladmin --defaults-file="$CNF" -h 127.0.0.1 ping >/dev/null 2>&1
}

backend_running() {
  curl -sf -o /dev/null http://127.0.0.1:8000/api/educheck/auth/csrf
}

frontend_running() {
  curl -sf -o /dev/null http://127.0.0.1:5173/
}

start_db() {
  if db_running; then echo "MariaDB (3306): ya está en marcha"; return; fi
  if [ -z "$MYSQLD" ]; then echo "MariaDB: no se encontró mariadbd/mysqld"; return 1; fi
  setsid nohup "$MYSQLD" --defaults-file="$CNF" >/dev/null 2>&1 < /dev/null &
  for _ in $(seq 1 30); do db_running && { echo "MariaDB: iniciado"; return; }; sleep 1; done
  echo "MariaDB: ERROR, revisa $LOGS/mysqld.log"; return 1
}

start_backend() {
  if backend_running; then echo "Django (8000): ya está en marcha"; return; fi
  PYTHON="$PROJECT/.venv/bin/python"; [ -x "$PYTHON" ] || PYTHON=python3
  ( cd "$PROJECT/backend" && setsid nohup "$PYTHON" manage.py runserver 127.0.0.1:8000 \
      >"$LOGS/django.log" 2>&1 < /dev/null & )
  for _ in $(seq 1 30); do backend_running && { echo "Django (8000): iniciado"; return; }; sleep 1; done
  echo "Django: ERROR, revisa $LOGS/django.log"; return 1
}

start_frontend() {
  if frontend_running; then echo "Vite (5173): ya está en marcha"; return; fi
  ( cd "$PROJECT" && setsid nohup npm run dev >"$LOGS/vite.log" 2>&1 < /dev/null & )
  for _ in $(seq 1 40); do frontend_running && { echo "Vite (5173): iniciado"; return; }; sleep 1; done
  echo "Vite: ERROR, revisa $LOGS/vite.log"; return 1
}

stop_all() {
  pkill -f "vite --host 127.0.0.1" >/dev/null 2>&1 && echo "Vite: detenido"
  pkill -f "manage.py runserver 127.0.0.1:8000" >/dev/null 2>&1 && echo "Django: detenido"
  if db_running; then kill "$(cat "$BASE/mysqld.pid")" >/dev/null 2>&1 && echo "MariaDB: detenido"; fi
}

status() {
  db_running && echo "MariaDB (127.0.0.1:3306): ACTIVO" || echo "MariaDB (127.0.0.1:3306): detenido"
  backend_running && echo "Django  (http://127.0.0.1:8000): ACTIVO" || echo "Django  (http://127.0.0.1:8000): detenido"
  frontend_running && echo "Vite    (http://127.0.0.1:5173): ACTIVO" || echo "Vite    (http://127.0.0.1:5173): detenido"
}

case "${1:-status}" in
  start)   start_db; start_backend; start_frontend; status ;;
  stop)    stop_all ;;
  restart) stop_all; sleep 2; start_db; start_backend; start_frontend; status ;;
  status)  status ;;
  *) echo "Uso: $0 {start|stop|restart|status}"; exit 1 ;;
esac
