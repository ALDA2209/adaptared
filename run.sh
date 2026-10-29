#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Si existe un archivo .env, se cargan sus variables (por ejemplo MONGODB_URI).
if [ -f .env ]; then set -a; . ./.env; set +a; fi
[ -f .venv/bin/activate ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
echo "AdaptaRed en http://${HOST:-127.0.0.1}:${PORT:-8000}"
case "${MONGODB_URI:-mongodb://localhost:27017}" in
  mongodb+srv://*) echo "Base de datos: MongoDB Atlas (nube)" ;;
  mongomock://*)   echo "Base de datos: simulada, solo para pruebas" ;;
  *)               echo "Base de datos: MongoDB en un servidor propio o local" ;;
esac
exec uvicorn app.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
