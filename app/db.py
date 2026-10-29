"""Conexión a MongoDB (local o MongoDB Atlas).

Variables de entorno:
  MONGODB_URI  cadena de conexión. Por defecto: mongodb://localhost:27017
               Con Atlas: mongodb+srv://usuario:clave@cluster.xxxxx.mongodb.net
               Para pruebas sin servidor: mongomock://
  MONGODB_DB   nombre de la base. Por defecto: adaptared
"""
from __future__ import annotations

import os

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.environ.get("MONGODB_DB", "adaptared")

_client = None


def is_mock() -> bool:
    return MONGODB_URI.startswith("mongomock://")


def get_client():
    global _client
    if _client is None:
        if is_mock():
            import mongomock

            _client = mongomock.MongoClient()
        else:
            _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    return _client


def get_db() -> Database:
    return get_client()[MONGODB_DB]


def init_db() -> None:
    """Comprueba la conexión y crea los índices."""
    if not is_mock():
        try:
            get_client().admin.command("ping")
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "No se pudo conectar a MongoDB. Revisa que el servidor esté encendido "
                "y que MONGODB_URI sea correcta."
            ) from exc
    db = get_db()
    db.communities.create_index("slug", unique=True)
    db.observations.create_index([("community_id", ASCENDING), ("day", ASCENDING)], unique=True)
    db.alerts.create_index([("status", ASCENDING), ("created_at", DESCENDING)])
    db.reports.create_index([("created_at", DESCENDING)])
