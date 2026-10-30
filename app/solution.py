"""Hoja de solución: acciones concretas para una comunidad, armadas con sus propios datos.

Toma las acciones del modelo (risk.ACTIONS) y las vuelve específicas: con fechas límite reales,
cultivos, hogares, personas sin agua segura, servicios disponibles y los días de mayor peligro
del pronóstico. No inventa datos: todo sale de la comunidad y de su pronóstico.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from . import i18n, risk

WEEKDAYS = {
    "es": ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"],
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
}

# Plazo (en el idioma original del modelo) -> días desde hoy
_DEADLINE_DAYS = {"Hoy": 0, "Inmediato": 0, "24 horas": 1, "48 horas": 2, "72 horas": 3, "Esta semana": 6, "2 semanas": 14}

_WORDS = {
    "es": {
        "today": "Hoy, {d}", "now": "Inmediato (hoy, {d})", "by": "Hasta el {d}",
        "on": "el {d}", "from_to": "del {a} al {b}", "days_list": "los días {x}",
        "contact_default": "el comité de gestión de riesgo",
        "meet_school": "la escuela (punto de encuentro)", "meet_other": "el punto de encuentro acordado con Defensa civil",
        "meet_school_short": "la escuela", "meet_other_short": "el punto acordado con Defensa civil",
        "place_school": "en la escuela", "place_other": "en el local comunal o la plaza",
        "crops_default": "los cultivos",
    },
    "en": {
        "today": "Today, {d}", "now": "Immediate (today, {d})", "by": "By {d}",
        "on": "on {d}", "from_to": "from {a} to {b}", "days_list": "on {x}",
        "contact_default": "the risk management committee",
        "meet_school": "the school (meeting point)", "meet_other": "the meeting point agreed with civil defense",
        "meet_school_short": "the school", "meet_other_short": "the point agreed with civil defense",
        "place_school": "at the school", "place_other": "at the community hall or the square",
        "crops_default": "the crops",
    },
}

# Acciones específicas, en el mismo orden que risk.ACTIONS. Los campos {…} salen de los datos.
SPECIFIC = {
    "es": {
        "calor": [
            "Difundir el aviso de arriba por radio local y WhatsApp a los {hh} hogares ({pop} personas). Repetirlo cada mañana mientras dure el calor ({days}).",
            "Trabajar en el campo solo antes de las 10 a. m. y después de las 4 p. m. ({days}).",
            "Habilitar agua segura y sombra {place}, con prioridad para niñas, niños y personas mayores. Hoy unas {no_water} personas dependen de agua sin tratar: hervirla o clorarla antes de repartirla.",
            "{health_action}",
            "Proteger {crops} con mallas de sombra y regar solo en horas frescas (antes de las 10 a. m. o después de las 4 p. m.).",
        ],
        "inundacion": [
            "Limpiar quebradas, cauces y alcantarillas antes de la lluvia más fuerte: se esperan hasta {rmax} mm {rmax_day}.",
            "Mover animales, semillas e insumos ({crops}) a zonas altas antes de que empiece la lluvia fuerte.",
            "Recorrer con la comunidad la ruta de evacuación hasta {meet} y confirmar que los {hh} hogares la conocen.",
            "Evacuar a las familias de las zonas más bajas, cercanas a ríos y quebradas, y cerrar los caminos que se inundan.",
            "Clorar y guardar agua potable antes de que se enturbie. Unas {no_water} personas ({nw_pct} % de los hogares) no tienen agua segura en casa: atenderlas primero.",
        ],
        "sequia": [
            "Medir la humedad del suelo cada semana en parcelas de referencia de {crops}. Último dato: {soil} % de humedad del suelo.",
            "Priorizar el riego de {crops} y cubrir el suelo con paja para retener la humedad.",
            "Organizar turnos de agua entre los usuarios del canal o manantial, empezando por el consumo humano de los {hh} hogares.",
            "Activar las reservas de agua para las {pop} personas y para los animales.",
            "Gestionar semilla tolerante a sequía para {crops} y revisar el seguro agrícola ante pérdidas.",
        ],
    },
    "en": {
        "calor": [
            "Share the notice above by local radio and WhatsApp with the {hh} households ({pop} people). Repeat it every morning while the heat lasts ({days}).",
            "Do fieldwork only before 10 a.m. and after 4 p.m. ({days}).",
            "Set up safe water and shade {place}, with priority for children and older adults. Today about {no_water} people depend on untreated water: boil or chlorinate it before handing it out.",
            "{health_action}",
            "Protect {crops} with shade netting and irrigate only during cooler hours (before 10 a.m. or after 4 p.m.).",
        ],
        "inundacion": [
            "Clear streams, riverbeds and drains before the heaviest rain: up to {rmax} mm expected {rmax_day}.",
            "Move animals, seeds and supplies ({crops}) to higher ground before the heavy rain starts.",
            "Walk the evacuation route to {meet} with the community and confirm that the {hh} households know it.",
            "Evacuate families in the lowest areas, near rivers and streams, and close the roads that flood.",
            "Chlorinate and store drinking water before it turns muddy. About {no_water} people ({nw_pct}% of households) have no safe water at home: serve them first.",
        ],
        "sequia": [
            "Measure soil moisture every week in reference plots of {crops}. Latest reading: {soil}% soil moisture.",
            "Prioritize irrigation of {crops} and cover the soil with straw to hold moisture.",
            "Organize water turns among users of the canal or spring, starting with drinking water for the {hh} households.",
            "Activate water reserves for the {pop} people and for livestock.",
            "Arrange drought-tolerant seed for {crops} and check crop insurance for losses.",
        ],
    },
}

HEALTH = {
    "es": {
        "yes": "El puesto de salud de {name} debe vigilar golpe de calor y deshidratación durante el calor ({days}), con prioridad para niños pequeños y personas mayores.",
        "no": "{name} no tiene puesto de salud: acordar hoy con la red de salud a dónde llevar a una persona con golpe de calor y cómo trasladarla.",
    },
    "en": {
        "yes": "The health post in {name} should watch for heat stroke and dehydration during the heat ({days}), with priority for young children and older adults.",
        "no": "{name} has no health post: agree today with the health network on where to take someone with heat stroke and how to get them there.",
    },
}

MESSAGES = {
    "es": {
        "calor": "AVISO DE CALOR - {name}. Se esperan hasta {peak} °C ({days}), {anom} °C más de lo normal. No trabaje al sol de 10 a. m. a 4 p. m. Tome agua segura, busque sombra y cuide a niñas, niños y personas mayores. Si alguien tiene mareos, vómitos o fiebre alta, {help}.",
        "inundacion": "AVISO DE LLUVIA INTENSA - {name}. Se esperan {r3} mm de lluvia en 3 días (hasta {rmax} mm {rmax_day}). Aléjese de quebradas y zonas bajas, no cruce ríos crecidos y tenga lista una mochila con agua, documentos y linterna. Punto de encuentro: {meet_short}.",
        "sequia": "AVISO DE SEQUÍA - {name}. En los últimos 30 días solo han caído {rain30} mm de lluvia (lo normal son {rain30_clim} mm). Use el agua primero para beber y cocinar, riegue en horas frescas y cubra el suelo con paja. Los turnos de agua se coordinan con {contact}.",
    },
    "en": {
        "calor": "HEAT WARNING - {name}. Up to {peak} °C is expected ({days}), {anom} °C above normal. Do not work in the sun from 10 a.m. to 4 p.m. Drink safe water, find shade and look after children and older adults. If someone has dizziness, vomiting or a high fever, {help}.",
        "inundacion": "HEAVY RAIN WARNING - {name}. {r3} mm of rain is expected in 3 days (up to {rmax} mm {rmax_day}). Stay away from streams and low ground, do not cross swollen rivers and keep a bag ready with water, documents and a flashlight. Meeting point: {meet_short}.",
        "sequia": "DROUGHT WARNING - {name}. Only {rain30} mm of rain has fallen in the last 30 days (normal is {rain30_clim} mm). Use water first for drinking and cooking, irrigate in cooler hours and cover the soil with straw. Water turns are coordinated with {contact}.",
    },
}

HELP = {
    "es": {"yes": "llévelo al puesto de salud", "no": "avise de inmediato a {contact}"},
    "en": {"yes": "take them to the health post", "no": "tell {contact} immediately"},
}

WHY = {
    "es": {
        "calor": "Hasta {peak} °C {peak_day}, {anom} °C sobre lo normal de la zona ({clim} °C).",
        "inundacion": "{r3} mm de lluvia pronosticada en 3 días, con un máximo de {rmax} mm {rmax_day}.",
        "sequia": "{rain30} mm de lluvia en 30 días; lo normal en la zona son {rain30_clim} mm.",
    },
    "en": {
        "calor": "Up to {peak} °C {peak_day}, {anom} °C above the area's normal ({clim} °C).",
        "inundacion": "{r3} mm of forecast rain in 3 days, with a maximum of {rmax} mm {rmax_day}.",
        "sequia": "{rain30} mm of rain in 30 days; normal for the area is {rain30_clim} mm.",
    },
}


def lima_today() -> date:
    return datetime.now(timezone(timedelta(hours=-5))).date()


def fmt_day(d: date, lang: str) -> str:
    return f"{WEEKDAYS[lang][d.weekday()]} {d.day} {i18n.MONTHS[lang][d.month - 1]}"


def deadline(spanish_when: str, today: date, lang: str) -> str:
    """Convierte un plazo como '24 horas' en una fecha concreta."""
    w = _WORDS[lang]
    n = _DEADLINE_DAYS.get(spanish_when, 0)
    d = fmt_day(today + timedelta(days=n), lang)
    if spanish_when == "Hoy":
        return w["today"].format(d=d)
    if spanish_when == "Inmediato":
        return w["now"].format(d=d)
    return w["by"].format(d=d)


def _span(days: list[date], lang: str) -> str:
    """Escribe una lista de días como 'el jue 5 nov', 'del jue 5 nov al sáb 7 nov' o 'los días …'."""
    w = _WORDS[lang]
    days = sorted(days)
    if len(days) == 1:
        return w["on"].format(d=fmt_day(days[0], lang))
    contiguous = all((b - a).days == 1 for a, b in zip(days, days[1:]))
    if contiguous and len(days) >= 3:
        return w["from_to"].format(a=fmt_day(days[0], lang), b=fmt_day(days[-1], lang))
    return w["days_list"].format(x=", ".join(fmt_day(d, lang) for d in days))


def _facts(c: dict, hazards_by_key: dict, obs: list[dict], lang: str) -> dict:
    """Reúne los datos concretos que se insertan en los textos."""
    w = _WORDS[lang]
    fut = [o for o in obs if o["is_forecast"]]
    past = [o for o in obs if not o["is_forecast"]]
    clim = c["tmax_clim"]

    hot = [date.fromisoformat(o["day"]) for o in fut if o["tmax"] >= clim + 3.0]
    peak_obs = max(fut, key=lambda o: o["tmax"]) if fut else None
    if not hot and peak_obs:
        hot = [date.fromisoformat(peak_obs["day"])]
    rain_obs = max(fut, key=lambda o: o["rain"]) if fut else None

    pct = round(c["water_access"] * 100)
    crops = (i18n.crops_en(c.get("main_crops") or "") if lang == "en" else (c.get("main_crops") or "")).lower() or w["crops_default"]
    school = bool(c.get("has_school"))
    contact = (c.get("contact") if lang == "es" else None) or w["contact_default"]
    peak = peak_obs["tmax"] if peak_obs else clim
    return {
        "name": c["name"],
        "hh": f"{c['households']:,}",
        "pop": f"{c['population']:,}",
        "crops": crops,
        "days": _span(hot, lang) if hot else "",
        "peak": peak,
        "peak_day": w["on"].format(d=fmt_day(date.fromisoformat(peak_obs["day"]), lang)) if peak_obs else "",
        "clim": clim,
        "anom": round(peak - clim, 1),
        "r3": round(hazards_by_key["inundacion"]["driver"]) if "inundacion" in hazards_by_key else 0,
        "rmax": round(rain_obs["rain"]) if rain_obs else 0,
        "rmax_day": w["on"].format(d=fmt_day(date.fromisoformat(rain_obs["day"]), lang)) if rain_obs else "",
        "rain30": round(hazards_by_key["sequia"]["driver"]) if "sequia" in hazards_by_key else 0,
        "rain30_clim": c.get("rain30_clim", ""),
        "soil": round(past[-1]["soil"]) if past else "-",
        "no_water": f"{round(c['population'] * (1 - c['water_access'])):,}",
        "nw_pct": 100 - pct,
        "place": w["place_school"] if school else w["place_other"],
        "meet": w["meet_school"] if school else w["meet_other"],
        "meet_short": w["meet_school_short"] if school else w["meet_other_short"],
        "contact": contact,
    }


def build_solution(c: dict, hazards: list[dict], plans: list[dict], obs: list[dict], lang: str = "es", today: date | None = None) -> dict:
    """Arma la hoja de solución: un bloque por amenaza con aviso listo para enviar y acciones concretas."""
    lang = lang if lang in SPECIFIC else "es"
    today = today or lima_today()
    by_key = {h["key"]: h for h in hazards}
    f = _facts(c, by_key, obs, lang)
    has_health = bool(c.get("has_health_post"))
    f["help"] = HELP[lang]["yes" if has_health else "no"].format(contact=f["contact"])
    f["health_action"] = HEALTH[lang]["yes" if has_health else "no"].format(name=c["name"], days=f["days"])

    blocks = []
    for p in plans:
        h = p["hazard"]
        key = h["key"]
        actions = []
        for i, a in enumerate(p["actions"]):
            actions.append({
                "text": SPECIFIC[lang][key][i].format(**f),
                "who": a["who"],
                "when": deadline(risk.ACTIONS[key][i][3], today, lang),
            })
        blocks.append({
            "key": key,
            "name": h["name"],
            "level": h["level"],
            "why": WHY[lang][key].format(**f),
            "message": MESSAGES[lang][key].format(**f),
            "actions": actions,
        })
    return {"blocks": blocks, "contact": f["contact"], "today": today}
