#!/usr/bin/env bash
# Guarda la conexión a MongoDB en el archivo .env (solo tú puedes leerlo) y prueba que funcione.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "1) Pega la cadena de conexión de Atlas y pulsa Enter:"
read -r URI
echo
echo "2) Escribe la contraseña de adaptared_app (no se verá en pantalla) y pulsa Enter:"
read -r -s PW
echo
export URI PW

.venv/bin/python -W ignore - <<'PYEND'
import os, re, sys, urllib.parse as up

raw = os.environ["URI"]
pw = os.environ["PW"]
found = re.search(r"mongodb(?:\+srv)?://[^\s\"'`]+", raw)
if not found:
    sys.exit("ERROR: no encontré una cadena mongodb+srv:// en lo que pegaste (recibí %d caracteres).\n"
             "Copia de nuevo la cadena desde Atlas (Connect > Drivers) y vuelve a ejecutar el programa." % len(raw.strip()))
uri = found.group(0)
m = re.search(r"<[^>]*password[^>]*>", uri)
if m:
    uri = uri.replace(m.group(0), up.quote(pw, safe=""))
else:
    print("Aviso: no encontré <db_password> en la cadena; la uso tal como la pegaste.")

with open(".env", "w") as f:
    f.write("MONGODB_URI='%s'\nMONGODB_DB=adaptared\n" % uri)
os.chmod(".env", 0o600)
print("Guardado en .env (no se muestra la clave).")

from pymongo import MongoClient
try:
    MongoClient(uri, serverSelectionTimeoutMS=12000).admin.command("ping")
    print("CONEXION OK: MongoDB Atlas respondió. Ya puedes arrancar con ./run.sh")
except Exception as e:
    print("NO CONECTÓ:", type(e).__name__)
    print(str(e)[:300])
    print("Revisa: contraseña, usuario adaptared_app, y que tu IP esté en IP Access List.")
    sys.exit(1)
PYEND
