"""Datos de demostración (sintéticos).

Los nombres de lugares son reales para dar contexto, pero las ubicaciones y
altitudes son aproximadas y TODAS las cifras son simuladas. Para un piloto real,
reemplaza estos datos por los de SENAMHI, estaciones locales y el INEI.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from .db import get_db
from .i18n import SEED_ALERTS_EN, SEED_REPORTS_EN

# slug, nombre, distrito, provincia, lat, lon, altitud, población, hogares, cultivos,
# vulnerabilidad, exp. calor, exp. inundación, exp. sequía, acceso a agua segura,
# puesto de salud, escuela, lluvia normal 30 días (mm), escenario de la semana
COMMUNITIES = [
    ("tingo-maria", "Tingo María", "Rupa-Rupa", "Leoncio Prado", -9.296, -75.998, 660, 3400, 780, "Café, cacao", 0.55, 0.80, 0.85, 0.35, 0.62, 1, 1, 290, "flood"),
    ("castillo-grande", "Castillo Grande", "Castillo Grande", "Leoncio Prado", -9.345, -76.020, 690, 1900, 420, "Cacao, plátano", 0.62, 0.78, 0.70, 0.30, 0.48, 1, 1, 270, "heat"),
    ("aucayacu", "Aucayacu", "José Crespo y Castillo", "Leoncio Prado", -8.925, -76.108, 580, 2600, 610, "Cacao, maíz", 0.66, 0.78, 0.72, 0.30, 0.40, 1, 1, 300, "mixed"),
    ("panao", "Panao", "Panao", "Pachitea", -9.895, -75.995, 2150, 3100, 700, "Papa, maíz", 0.70, 0.35, 0.45, 0.65, 0.45, 1, 1, 110, "drought"),
    ("chinchao", "Chinchao", "Chinchao", "Huánuco", -9.760, -76.080, 1700, 2400, 540, "Café, frijol", 0.58, 0.55, 0.60, 0.45, 0.55, 1, 1, 150, "mixed"),
    ("churubamba", "Churubamba", "Churubamba", "Huánuco", -9.870, -76.120, 2000, 2800, 650, "Maíz, papa", 0.50, 0.40, 0.40, 0.55, 0.60, 1, 1, 90, "drought"),
    ("santa-maria-del-valle", "Santa María del Valle", "Santa María del Valle", "Huánuco", -9.840, -76.160, 1900, 2300, 560, "Frutales, maíz", 0.42, 0.50, 0.35, 0.50, 0.72, 1, 1, 80, "calm"),
    ("amarilis", "Amarilis", "Amarilis", "Huánuco", -9.930, -76.240, 1900, 4200, 1050, "Hortalizas, maíz", 0.38, 0.55, 0.30, 0.40, 0.80, 1, 1, 70, "heat"),
    ("margos", "Margos", "Margos", "Huánuco", -10.030, -76.590, 3250, 1500, 360, "Papa, haba", 0.74, 0.20, 0.35, 0.70, 0.35, 1, 1, 100, "drought"),
    ("chavinillo", "Chavinillo", "Chavinillo", "Yarowilca", -9.820, -76.620, 3400, 1700, 410, "Papa, cebada", 0.72, 0.18, 0.40, 0.62, 0.38, 1, 1, 95, "calm"),
    ("jesus", "Jesús", "Jesús", "Lauricocha", -10.000, -76.620, 3500, 1300, 320, "Papa, ganadería", 0.68, 0.15, 0.50, 0.55, 0.42, 0, 1, 105, "flood"),
    ("molino", "Molino", "Molino", "Pachitea", -9.950, -75.930, 2600, 1800, 430, "Maíz, frijol", 0.64, 0.40, 0.55, 0.55, 0.44, 0, 1, 100, "mixed"),
]

SEED_ALERTS = [
    ("panao", "sequia", "alto", "Déficit de lluvia de más de tres semanas. Priorizar el riego de la papa en floración y coordinar turnos de agua.", "activa", "manual", -2),
    ("castillo-grande", "calor", "moderado", "Se esperan tardes con calor por encima de lo normal. Reprogramar el trabajo de campo a la mañana.", "activa", "manual", -1),
    ("jesus", "inundacion", "moderado", "Lluvias intensas en la parte alta. Revisar quebradas y mover animales a zonas altas.", "resuelta", "manual", -6),
]

SEED_REPORTS = [
    ("panao", "sequia", "El manantial del barrio alto bajó casi a la mitad. Hay turnos de agua desde el lunes.", "Junta de regantes de Panao", 0, -3),
    ("tingo-maria", "inundacion", "La quebrada de la zona baja ya llega a la carretera después de la lluvia de anoche.", "Vecina de Tingo María", 1, -2),
    ("amarilis", "calor", "Las hortalizas bajo malla se queman al mediodía. Pedimos asesoría para sombra.", "Asociación de horticultores", 1, -1),
    ("margos", "sequia", "Las parcelas de papa sin riego muestran hojas enrolladas desde hace dos semanas.", "Promotor agrario", 0, 0),
]


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def generate_observations(community_id: int, tmax_clim: float, rain30: float, scenario: str, today: date) -> list[tuple]:
    """Serie diaria: 30 días observados (hasta hoy) y 7 de pronóstico."""
    rng = random.Random(community_id * 100000 + today.toordinal())
    mean_rain = rain30 / 30.0
    soil = 30.0 if scenario == "drought" else 45.0
    rows = []
    for offset in range(-29, 8):
        day = today + timedelta(days=offset)
        forecast = offset >= 1
        tmax = tmax_clim + 0.8 * _sin(offset + community_id) + rng.gauss(0, 0.7)
        if scenario == "heat" and 1 <= offset <= 6:
            tmax += 3.0 + 0.8 * offset
        elif scenario == "mixed" and 1 <= offset <= 5:
            tmax += 2.0 + 0.4 * offset
        tmin = tmax - rng.uniform(7, 12) - (2 if tmax_clim < 20 else 0)

        rain = rng.expovariate(1 / (mean_rain / 0.35)) if rng.random() < 0.35 else 0.0
        if scenario == "drought":
            rain *= 0.06 if not forecast else 0.1
        elif scenario == "flood":
            if -6 <= offset <= 0:
                rain += rng.uniform(5, 18)
            elif 1 <= offset <= 4:
                rain = rng.uniform(22, 48)
        elif scenario == "mixed" and 2 <= offset <= 3:
            rain = rng.uniform(20, 38)
        soil = _clamp(soil * 0.94 + rain * 0.8 + 1.0, 4, 100)
        rows.append((day.isoformat(), round(tmax, 1), round(tmin, 1), round(rain, 1), round(soil, 1), int(forecast)))
    return rows


def _sin(x: float) -> float:
    import math

    return math.sin(x / 5.0)


def refresh_observations(db, today: date | None = None) -> None:
    today = today or date.today()
    docs = []
    for c in db.communities.find({}, {"_id": 0, "id": 1, "tmax_clim": 1, "rain30_clim": 1, "scenario": 1}):
        for day, tmax, tmin, rain, soil, fc in generate_observations(
            c["id"], c["tmax_clim"], c["rain30_clim"], c["scenario"], today
        ):
            docs.append(
                {"community_id": c["id"], "day": day, "tmax": tmax, "tmin": tmin, "rain": rain, "soil": soil, "is_forecast": bool(fc)}
            )
    db.observations.delete_many({})
    if docs:
        db.observations.insert_many(docs)
    db.meta.update_one({"_id": "obs_day"}, {"$set": {"value": today.isoformat()}}, upsert=True)


def backfill_translations(db) -> None:
    """Agrega la versión en inglés a los datos de demostración que se cargaron antes de existir el botón ES/EN."""
    for es, en in SEED_ALERTS_EN.items():
        db.alerts.update_many({"message": es, "message_en": {"$exists": False}}, {"$set": {"message_en": en}})
    for es, (en, who_en) in SEED_REPORTS_EN.items():
        db.reports.update_many(
            {"description": es, "description_en": {"$exists": False}},
            {"$set": {"description_en": en, "reporter_en": who_en}},
        )


def seed_if_needed() -> None:
    today = date.today()
    db = get_db()
    count = db.communities.count_documents({})
    if count == 0:
        ids = {}
        for idx, c in enumerate(COMMUNITIES, start=1):
            (slug, name, district, province, lat, lon, elev, pop, hh, crops, vuln, hx, fx, dx, water, hp, sch, rain30, scen) = c
            ids[slug] = idx
            db.communities.insert_one(
                {
                    "id": idx,
                    "slug": slug,
                    "name": name,
                    "district": district,
                    "province": province,
                    "lat": lat,
                    "lon": lon,
                    "elevation": elev,
                    "population": pop,
                    "households": hh,
                    "main_crops": crops,
                    "vulnerability": vuln,
                    "heat_exposure": hx,
                    "flood_exposure": fx,
                    "drought_exposure": dx,
                    "water_access": water,
                    "has_health_post": hp,
                    "has_school": sch,
                    "tmax_clim": round(35 - 0.0065 * elev, 1),
                    "rain30_clim": rain30,
                    "scenario": scen,
                    "contact": "Comité local de gestión de riesgo",
                }
            )
        now = datetime.now()
        for slug, hazard, level, msg, status, source, days in SEED_ALERTS:
            db.alerts.insert_one(
                {
                    "community_id": ids[slug],
                    "hazard": hazard,
                    "level": level,
                    "message": msg,
                    "message_en": SEED_ALERTS_EN.get(msg, msg),
                    "status": status,
                    "source": source,
                    "created_at": (now + timedelta(days=days)).isoformat(timespec="minutes"),
                }
            )
        for slug, hazard, desc, who, verified, days in SEED_REPORTS:
            db.reports.insert_one(
                {
                    "community_id": ids[slug],
                    "hazard": hazard,
                    "description": desc,
                    "description_en": SEED_REPORTS_EN.get(desc, (desc, who))[0],
                    "reporter": who,
                    "reporter_en": SEED_REPORTS_EN.get(desc, (desc, who))[1],
                    "verified": bool(verified),
                    "created_at": (now + timedelta(days=days)).isoformat(timespec="minutes"),
                }
            )
    backfill_translations(db)
    stored = db.meta.find_one({"_id": "obs_day"})
    if count == 0 or stored is None or stored.get("value") != today.isoformat():
        refresh_observations(db, today)
