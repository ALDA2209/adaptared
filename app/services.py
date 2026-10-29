"""Consultas y resúmenes que usan las páginas y la API."""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from bson import ObjectId

from . import i18n, risk


def get_communities(db) -> list[dict]:
    return list(db.communities.find({}, {"_id": 0}).sort("name", 1))


def get_community(db, slug: str) -> dict | None:
    return db.communities.find_one({"slug": slug}, {"_id": 0})


def get_observations(db, community_id: int) -> list[dict]:
    return list(db.observations.find({"community_id": community_id}, {"_id": 0}).sort("day", 1))


def overview(db, lang: str = "es") -> list[dict]:
    """Todas las comunidades con su riesgo calculado, de mayor a menor."""
    out = []
    names = i18n.HAZARDS[lang]
    for c in get_communities(db):
        obs = get_observations(db, c["id"])
        c["risk"] = risk.assess(c, obs, names)
        out.append(c)
    out.sort(key=lambda c: c["risk"]["score"], reverse=True)
    return out


def summarize(items: list[dict]) -> dict:
    levels = Counter(c["risk"]["level"] for c in items)
    hazards = Counter(c["risk"]["dominant"] for c in items if c["risk"]["level"] in ("alto", "critico"))
    people_high = sum(c["population"] for c in items if c["risk"]["level"] in ("alto", "critico"))
    total_people = sum(c["population"] for c in items)
    n_high = levels["alto"] + levels["critico"]
    return {
        "levels": {k: levels.get(k, 0) for k in risk.LEVELS},
        "n": len(items),
        "n_high": n_high,
        "people_high": people_high,
        "people_total": total_people,
        "hazards_high": {k: hazards.get(k, 0) for k in risk.HAZARDS},
        "no_water": sum(c["population"] * (1 - c["water_access"]) for c in items if c["risk"]["level"] in ("alto", "critico")),
    }


def headline(summary: dict, lang: str = "es") -> str:
    n, hi = summary["n"], summary["n_high"]
    if lang == "en":
        if hi == 0:
            return f"None of the {n} communities is at high risk this week."
        top = max(summary["hazards_high"], key=summary["hazards_high"].get)
        word = {"calor": "extreme heat", "inundacion": "flooding", "sequia": "drought"}[top]
        verb = "community faces" if hi == 1 else "communities face"
        return f"{hi} of {n} {verb} high or critical risk this week, mostly from {word}."
    if hi == 0:
        return f"Ninguna de las {n} comunidades tiene riesgo alto esta semana."
    top = max(summary["hazards_high"], key=summary["hazards_high"].get)
    word = {"calor": "calor extremo", "inundacion": "inundación", "sequia": "sequía"}[top]
    plural = "comunidad enfrenta" if hi == 1 else "comunidades enfrentan"
    return f"{hi} de {n} {plural} riesgo alto o crítico esta semana, sobre todo por {word}."


def _with_community(docs: list[dict], db, lang: str = "es") -> list[dict]:
    names = {c["id"]: c for c in get_communities(db)}
    out = []
    for d in docs:
        item = {k: v for k, v in d.items() if k != "_id"}
        item["id"] = str(d["_id"])
        if lang == "en":
            # Los datos de demostración y las alertas automáticas guardan también su versión en inglés.
            for field in ("message", "description", "reporter"):
                if d.get(field + "_en"):
                    item[field] = d[field + "_en"]
        c = names.get(d["community_id"], {})
        item["community_name"] = c.get("name", "")
        item["community_slug"] = c.get("slug", "")
        out.append(item)
    return out


def get_alerts(db, status: str | None = None, lang: str = "es") -> list[dict]:
    docs = list(db.alerts.find({"status": status} if status else {}))
    items = _with_community(docs, db, lang)
    items.sort(key=lambda a: a["created_at"], reverse=True)
    items.sort(key=lambda a: a["status"] != "activa")
    return items


def get_reports(db, lang: str = "es") -> list[dict]:
    items = _with_community(list(db.reports.find({})), db, lang)
    items.sort(key=lambda r: r["created_at"], reverse=True)
    return items


def create_alert(
    db, community_id: int, hazard: str, level: str, message: str, source: str = "manual", message_en: str | None = None
) -> None:
    doc = {
        "community_id": community_id,
        "hazard": hazard,
        "level": level,
        "message": message,
        "status": "activa",
        "source": source,
        "created_at": datetime.now().isoformat(timespec="minutes"),
    }
    if message_en:
        doc["message_en"] = message_en
    db.alerts.insert_one(doc)


def set_alert_status(db, alert_id: str, status: str) -> bool:
    if not ObjectId.is_valid(alert_id):
        return False
    return db.alerts.update_one({"_id": ObjectId(alert_id)}, {"$set": {"status": status}}).matched_count == 1


def create_report(db, community_id: int, hazard: str, description: str, reporter: str) -> None:
    db.reports.insert_one(
        {
            "community_id": community_id,
            "hazard": hazard,
            "description": description,
            "reporter": reporter,
            "verified": False,
            "created_at": datetime.now().isoformat(timespec="minutes"),
        }
    )


def verify_report(db, report_id: str) -> bool:
    if not ObjectId.is_valid(report_id):
        return False
    return db.reports.update_one({"_id": ObjectId(report_id)}, {"$set": {"verified": True}}).matched_count == 1


def alert_text(community: dict, hz: dict, lang: str = "es") -> str:
    name = i18n.HAZARDS[lang][hz["key"]].lower()
    level = i18n.LEVEL_LABELS[lang][hz["level"]].lower()
    if lang == "en":
        driver = {
            "calor": f"Up to {hz['driver']:+.1f} °C above normal is expected for three days in a row.",
            "inundacion": f"Up to {hz['driver']:.0f} mm of rain is forecast over three days.",
            "sequia": f"Only {hz['driver']:.0f} mm fell in the last 30 days.",
        }[hz["key"]]
        return f"{community['name']}: {level} risk from {name}. {driver}"
    driver = {
        "calor": f"Se esperan hasta {hz['driver']:+.1f} °C sobre lo normal durante tres días seguidos.",
        "inundacion": f"Se pronostica hasta {hz['driver']:.0f} mm de lluvia en tres días.",
        "sequia": f"Cayeron solo {hz['driver']:.0f} mm en los últimos 30 días.",
    }[hz["key"]]
    return f"{community['name']}: riesgo {level} por {name}. {driver}"
