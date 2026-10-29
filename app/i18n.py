"""Idioma de la interfaz (español / inglés).

El idioma se elige así: 1) la cookie "lang" si existe (la fija el botón ES/EN),
2) la variable de entorno APP_DEFAULT_LANG (es, en o auto), 3) el idioma del navegador.
Las páginas en inglés viven en app/templates/en/. Aquí están los textos del lado del servidor.
"""
from __future__ import annotations

import os

LANGS = ("es", "en")

HAZARDS = {
    "es": {"calor": "Calor extremo", "inundacion": "Inundación", "sequia": "Sequía"},
    "en": {"calor": "Extreme heat", "inundacion": "Flooding", "sequia": "Drought"},
}

LEVEL_LABELS = {
    "es": {"bajo": "Bajo", "moderado": "Moderado", "alto": "Alto", "critico": "Crítico"},
    "en": {"bajo": "Low", "moderado": "Moderate", "alto": "High", "critico": "Critical"},
}

_NAV = [
    ("dashboard", "/", "panel"),
    ("mapa", "/mapa", "mapa"),
    ("comunidades", "/comunidades", "comunidades"),
    ("alertas", "/alertas", "alertas"),
    ("agro", "/agro", "agro"),
    ("reportes", "/reportes", "reportes"),
    ("impacto", "/impacto", "impacto"),
    ("metodologia", "/metodologia", "metodo"),
]
_NAV_LABELS = {
    "es": ["Panel", "Mapa de riesgo", "Comunidades", "Alertas", "Agricultura", "Reportes locales", "Impacto", "Cómo funciona"],
    "en": ["Dashboard", "Risk map", "Communities", "Alerts", "Agriculture", "Local reports", "Impact", "How it works"],
}
NAV = {lang: [(k, href, _NAV_LABELS[lang][i], ico) for i, (k, href, ico) in enumerate(_NAV)] for lang in LANGS}

MONTHS = {
    "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}

CROP_NAMES = {
    "papa": ("Papa", "Potato"),
    "maiz": ("Maíz amiláceo", "Floury maize"),
    "cafe": ("Café", "Coffee"),
    "cacao": ("Cacao", "Cocoa"),
    "frijol": ("Frijol", "Beans"),
}
MEASURE_NAMES = {
    "riego": ("Riego por goteo", "Drip irrigation"),
    "sombra": ("Sombra y agroforestería", "Shade and agroforestry"),
    "variedades": ("Variedades tolerantes", "Tolerant varieties"),
    "cosecha_agua": ("Cosecha de agua de lluvia", "Rainwater harvesting"),
    "mulch": ("Cobertura del suelo (mulch)", "Soil cover (mulch)"),
}
COST_NAMES = {"Bajo": "Low", "Medio": "Medium", "Alto": "High"}

# Cultivos que aparecen en el texto de cada comunidad (la base guarda el texto en español).
CROP_WORDS_EN = {
    "papa": "potato", "maíz": "maize", "café": "coffee", "cacao": "cocoa", "plátano": "plantain",
    "frijol": "beans", "haba": "fava beans", "frutales": "fruit trees", "hortalizas": "vegetables",
    "cebada": "barley", "ganadería": "livestock",
}


def crops_en(text: str) -> str:
    parts = [p.strip() for p in (text or "").split(",")]
    return ", ".join(CROP_WORDS_EN.get(p.lower(), p) for p in parts if p)


# Acciones recomendadas en inglés: misma estructura y orden que risk.ACTIONS.
ACTIONS_EN = {
    "calor": [
        ("moderado", "Announce the hottest hours of the day by radio and WhatsApp", "Risk management committee", "Today"),
        ("alto", "Reschedule fieldwork to before 10 a.m. and after 4 p.m.", "Farmers' associations", "24 hours"),
        ("alto", "Set up safe drinking water points and shade for children and older adults", "Municipality and schools", "48 hours"),
        ("critico", "Alert the health post to watch for heat stroke and dehydration", "Health network", "Immediate"),
        ("critico", "Protect crops with shade netting and irrigate during the cooler hours", "Producers", "Immediate"),
    ],
    "inundacion": [
        ("moderado", "Check riverbeds and clear streams and drains", "Municipality", "48 hours"),
        ("alto", "Move animals, seeds and supplies to higher ground", "Farming families", "24 hours"),
        ("alto", "Check evacuation routes and meeting points with the community", "Local civil defense", "24 hours"),
        ("critico", "Evacuate families in low-lying areas and close roads that can flood", "Civil defense and community patrols", "Immediate"),
        ("critico", "Secure drinking water: chlorinate and store it before it turns muddy", "Water committee and health post", "Immediate"),
    ],
    "sequia": [
        ("moderado", "Measure soil moisture every week in reference plots", "Agricultural promoters", "This week"),
        ("alto", "Prioritize irrigation of sensitive crops and use mulch to hold moisture", "Producers", "72 hours"),
        ("alto", "Organize water turns among users of the canal or spring", "Irrigators' board", "72 hours"),
        ("critico", "Activate water reserves for people and livestock", "Municipality", "Immediate"),
        ("critico", "Arrange drought-tolerant seed and crop insurance for losses", "Agricultural agency", "2 weeks"),
    ],
}

# Datos de demostración en inglés (clave = texto original en español).
SEED_ALERTS_EN = {
    "Déficit de lluvia de más de tres semanas. Priorizar el riego de la papa en floración y coordinar turnos de agua.":
        "Rain deficit for more than three weeks. Prioritize irrigation of flowering potatoes and coordinate water turns.",
    "Se esperan tardes con calor por encima de lo normal. Reprogramar el trabajo de campo a la mañana.":
        "Afternoons hotter than normal are expected. Move fieldwork to the morning.",
    "Lluvias intensas en la parte alta. Revisar quebradas y mover animales a zonas altas.":
        "Heavy rain in the upper area. Check streams and move animals to higher ground.",
}
SEED_REPORTS_EN = {
    "El manantial del barrio alto bajó casi a la mitad. Hay turnos de agua desde el lunes.":
        ("The spring in the upper neighborhood dropped by almost half. Water turns have been in place since Monday.", "Panao irrigators' board"),
    "La quebrada de la zona baja ya llega a la carretera después de la lluvia de anoche.":
        ("The stream in the lower area now reaches the road after last night's rain.", "Resident of Tingo María"),
    "Las hortalizas bajo malla se queman al mediodía. Pedimos asesoría para sombra.":
        ("Vegetables under netting burn at midday. We are asking for advice on shade.", "Horticulturists' association"),
    "Las parcelas de papa sin riego muestran hojas enrolladas desde hace dos semanas.":
        ("Unirrigated potato plots have shown curled leaves for two weeks.", "Agricultural promoter"),
}
DEFAULT_REPORTER = {"es": "Vecino o vecina", "en": "Neighbor"}

# Mensajes de confirmación y error (clave -> (español, inglés)).
MSG = {
    "alert_check": ("Revisa la comunidad, la amenaza y el nivel.", "Check the community, the hazard and the level."),
    "alert_len": ("El mensaje debe tener entre 10 y 400 caracteres.", "The message must be between 10 and 400 characters."),
    "alert_ok": ("Alerta publicada para {name}.", "Alert published for {name}."),
    "gen_none": ("No hay amenazas nuevas en nivel alto o crítico.", "There are no new hazards at high or critical level."),
    "gen_ok": ("Se crearon {n} alertas a partir del pronóstico.", "{n} alerts were created from the forecast."),
    "state_bad": ("Estado no válido.", "Invalid status."),
    "state_resolved": ("Alerta marcada como resuelta.", "Alert marked as resolved."),
    "state_reactivated": ("Alerta reactivada.", "Alert reactivated."),
    "rep_check": ("Elige una comunidad y un tipo de evento.", "Choose a community and an event type."),
    "rep_len": ("Cuéntanos qué pasó en 10 a 500 caracteres.", "Tell us what happened in 10 to 500 characters."),
    "rep_ok": (
        "Gracias. Tu reporte quedó registrado y un técnico lo revisará.",
        "Thank you. Your report was recorded and a technician will review it.",
    ),
    "rep_verified": ("Reporte verificado.", "Report verified."),
    "nf_community": ("Comunidad no encontrada", "Community not found"),
    "nf_alert": ("Alerta no encontrada", "Alert not found"),
    "nf_report": ("Reporte no encontrado", "Report not found"),
}


def tr(lang: str, key: str, **kw) -> str:
    es, en = MSG[key]
    return (en if lang == "en" else es).format(**kw)


IMPACT = {
    "es": {
        "years": ["Año 1", "Año 2", "Año 3"],
        "revenue": ["Suscripciones municipales", "Programas de cooperación", "Alianzas con seguros y agroindustria", "Subvenciones"],
    },
    "en": {
        "years": ["Year 1", "Year 2", "Year 3"],
        "revenue": ["Municipal subscriptions", "Cooperation programs", "Partnerships with insurers and agribusiness", "Grants"],
    },
}


def detect(request) -> str:
    """Idioma de esta petición: cookie, luego APP_DEFAULT_LANG, luego el navegador."""
    cookie = request.cookies.get("lang")
    if cookie in LANGS:
        return cookie
    forced = os.environ.get("APP_DEFAULT_LANG", "auto").strip().lower()
    if forced in LANGS:
        return forced
    first = request.headers.get("accept-language", "").split(",")[0].strip().lower()
    return "en" if first and not first.startswith("es") else "es"


def crops_for(lang: str, crops: dict) -> dict:
    i = 1 if lang == "en" else 0
    return {k: {**v, "name": CROP_NAMES[k][i]} for k, v in crops.items()}


def measures_for(lang: str, measures: dict) -> dict:
    i = 1 if lang == "en" else 0
    return {
        k: {**v, "name": MEASURE_NAMES[k][i], "cost": COST_NAMES.get(v["cost"], v["cost"]) if lang == "en" else v["cost"]}
        for k, v in measures.items()
    }
