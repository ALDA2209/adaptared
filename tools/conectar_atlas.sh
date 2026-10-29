#!/usr/bin/env bash
# Uso: ./tools/conectar_atlas.sh cluster0.ab1cd.mongodb.net
# Guarda la conexión en .env y prueba que funcione. La contraseña se escribe a mano.
set -euo pipefail
cd "$(dirname "$0")/.."

HOST="${1:-}"
if [ -z "$HOST" ]; then
  echo "Falta el nombre del cluster. Ejemplo:"
  echo "  ./tools/conectar_atlas.sh cluster0.ab1cd.mongodb.net"
  exit 1
fi
HOST="${HOST#mongodb+srv://}"
HOST="${HOST%%/*}"

echo "Escribe la contraseña de adaptared_app (se verá lo que escribas) y pulsa Enter:"
read -r PW
echo
if [ -z "$PW" ]; then echo "No recibí contraseña. Vuelve a ejecutar y ESCRÍBELA a mano."; exit 1; fi
export HOST PW

.venv/bin/python -W ignore - <<'PYEND'
import os, sys, urllib.parse as up

host, pw = os.environ["HOST"], os.environ["PW"]
uri = "mongodb+srv://adaptared_app:%s@%s/?retryWrites=true&w=majority&appName=Cluster0" % (up.quote(pw, safe=""), host)
with open(".env", "w") as f:
    f.write("MONGODB_URI='%s'\nMONGODB_DB=adaptared\n" % uri)
os.chmod(".env", 0o600)
print("Guardado en .env para el cluster:", host)

from pymongo import MongoClient
try:
    MongoClient(uri, serverSelectionTimeoutMS=12000).admin.command("ping")
    print("CONEXION OK: MongoDB Atlas respondió. Ya puedes arrancar con ./run.sh")
except Exception as e:
    print("NO CONECTÓ:", type(e).__name__)
    print(str(e)[:300])
    print("Revisa: nombre del cluster, contraseña, y que tu IP esté en IP Access List.")
    sys.exit(1)
PYEND
