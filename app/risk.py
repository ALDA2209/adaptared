"""Modelo de riesgo climático de AdaptaRed.

Riesgo = Amenaza x Exposición x Vulnerabilidad (marco del IPCC), con una
fórmula simple y explicable que cualquier técnico municipal pueda revisar.
Todos los parámetros están a la vista para calibrarlos con datos reales.
"""
from __future__ import annotations

HAZARDS = {
    "calor": "Calor extremo",
    "inundacion": "Inundación",
    "sequia": "Sequía",
}

LEVELS = ["bajo", "moderado", "alto", "critico"]
LEVEL_LABELS = {"bajo": "Bajo", "moderado": "Moderado", "alto": "Alto", "critico": "Crítico"}
LEVEL_THRESHOLDS = {"moderado": 20, "alto": 40, "critico": 60}


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def level_for(score: float) -> str:
    if score >= LEVEL_THRESHOLDS["critico"]:
        return "critico"
    if score >= LEVEL_THRESHOLDS["alto"]:
        return "alto"
    if score >= LEVEL_THRESHOLDS["moderado"]:
        return "moderado"
    return "bajo"


def level_rank(level: str) -> int:
    return LEVELS.index(level)


def _best_window(values: list[float], size: int, fn) -> float:
    if not values:
        return 0.0
    if len(values) < size:
        return fn(values)
    return max(fn(values[i : i + size]) for i in range(len(values) - size + 1))


def compute_hazards(community: dict, obs: list[dict]) -> dict:
    """Calcula amenaza (0-1) para calor, inundación y sequía."""
    past = [o for o in obs if not o["is_forecast"]]
    fut = [o for o in obs if o["is_forecast"]]

    # Calor: mayor anomalía media de 3 días en el pronóstico.
    anomalies = [o["tmax"] - community["tmax_clim"] for o in fut]
    a3 = _best_window(anomalies, 3, lambda w: sum(w) / len(w))
    heat = clamp((a3 - 1.5) / 5.0)

    # Inundación: lluvia máxima en 3 días, ponderada por el suelo ya saturado.
    r3 = _best_window([o["rain"] for o in fut], 3, sum)
    sat = (sum(o["soil"] for o in past[-3:]) / max(1, len(past[-3:]))) / 100.0
    flood = clamp(r3 / 90.0 * (0.6 + 0.4 * sat))

    # Sequía: déficit de lluvia de 30 días y humedad actual del suelo.
    rain30 = sum(o["rain"] for o in past[-30:])
    deficit = clamp(1 - rain30 / community["rain30_clim"]) if community["rain30_clim"] else 0.0
    soil_now = past[-1]["soil"] if past else 50.0
    drought = clamp(0.6 * deficit + 0.4 * clamp(1 - soil_now / 55.0))

    return {
        "calor": {"hazard": heat, "driver": a3, "unit": "°C sobre lo normal (3 días)"},
        "inundacion": {"hazard": flood, "driver": r3, "unit": "mm en 3 días"},
        "sequia": {"hazard": drought, "driver": rain30, "unit": "mm en 30 días"},
    }


def assess(community: dict, obs: list[dict], names: dict | None = None) -> dict:
    """Devuelve el riesgo por amenaza y el riesgo global de una comunidad.

    `names` permite devolver los nombres de las amenazas en otro idioma.
    """
    names = names or HAZARDS
    hz = compute_hazards(community, obs)
    exposure = {
        "calor": community["heat_exposure"],
        "inundacion": community["flood_exposure"],
        "sequia": community["drought_exposure"],
    }
    vuln = community["vulnerability"]
    result = {}
    for key, h in hz.items():
        score = 100 * h["hazard"] * (0.4 + 0.6 * exposure[key]) * (0.4 + 0.6 * vuln)
        result[key] = {
            "key": key,
            "name": names[key],
            "hazard": round(h["hazard"], 3),
            "exposure": exposure[key],
            "vulnerability": vuln,
            "score": round(score, 1),
            "level": level_for(score),
            "driver": round(h["driver"], 1),
            "unit": h["unit"],
        }
    dominant = max(result.values(), key=lambda r: r["score"])
    return {
        "by_hazard": result,
        "score": dominant["score"],
        "level": dominant["level"],
        "dominant": dominant["key"],
        "dominant_name": dominant["name"],
    }


# Acciones recomendadas: (nivel mínimo, qué hacer, quién, plazo)
ACTIONS = {
    "calor": [
        ("moderado", "Avisar por radio y WhatsApp las horas más calurosas del día", "Comité de gestión de riesgo", "Hoy"),
        ("alto", "Reprogramar el trabajo de campo para antes de las 10 a. m. y después de las 4 p. m.", "Juntas de agricultores", "24 horas"),
        ("alto", "Habilitar puntos de agua segura y sombra para niñas, niños y personas mayores", "Municipalidad y escuelas", "48 horas"),
        ("critico", "Activar al puesto de salud para vigilancia de golpe de calor y deshidratación", "Red de salud", "Inmediato"),
        ("critico", "Proteger la cosecha con mallas de sombra y riego en horas frescas", "Productores", "Inmediato"),
    ],
    "inundacion": [
        ("moderado", "Revisar cauces y limpiar quebradas y alcantarillas", "Municipalidad", "48 horas"),
        ("alto", "Mover animales, semillas e insumos a zonas altas", "Familias productoras", "24 horas"),
        ("alto", "Verificar rutas de evacuación y puntos de encuentro con la comunidad", "Defensa civil local", "24 horas"),
        ("critico", "Evacuar familias en zonas bajas y cerrar caminos inundables", "Defensa civil y rondas", "Inmediato"),
        ("critico", "Asegurar el agua potable: clorar y guardar agua antes de que se turbie", "JASS y puesto de salud", "Inmediato"),
    ],
    "sequia": [
        ("moderado", "Medir la humedad del suelo cada semana en parcelas de referencia", "Promotores agrarios", "Esta semana"),
        ("alto", "Priorizar riego de cultivos sensibles y usar mulch para retener humedad", "Productores", "72 horas"),
        ("alto", "Organizar turnos de agua entre usuarios del canal o manantial", "Junta de regantes", "72 horas"),
        ("critico", "Activar reservas de agua para consumo humano y para animales", "Municipalidad", "Inmediato"),
        ("critico", "Gestionar semilla tolerante a sequía y seguro agrícola ante pérdidas", "Agencia agraria", "2 semanas"),
    ],
}


def recommend(hazard: str, level: str, lang: str = "es") -> list[dict]:
    from .i18n import ACTIONS_EN

    rank = level_rank(level)
    out = []
    for min_level, what, who, when in (ACTIONS_EN if lang == "en" else ACTIONS)[hazard]:
        if level_rank(min_level) <= rank:
            out.append({"what": what, "who": who, "when": when, "min_level": min_level})
    return out


# --- Cultivos y simulador agrícola -------------------------------------------------
CROPS = {
    "papa": {"name": "Papa", "t_crit": 23.0, "water_need": 110.0, "t_span": 5.0},
    "maiz": {"name": "Maíz amiláceo", "t_crit": 27.0, "water_need": 90.0, "t_span": 6.0},
    "cafe": {"name": "Café", "t_crit": 27.5, "water_need": 140.0, "t_span": 5.0},
    "cacao": {"name": "Cacao", "t_crit": 32.0, "water_need": 160.0, "t_span": 5.0},
    "frijol": {"name": "Frijol", "t_crit": 29.0, "water_need": 80.0, "t_span": 6.0},
}

# Cada medida reduce parte del estrés por calor y/o por falta de agua.
MEASURES = {
    "riego": {"name": "Riego por goteo", "heat": 0.0, "water": 0.55, "cost": "Medio"},
    "sombra": {"name": "Sombra y agroforestería", "heat": 0.45, "water": 0.15, "cost": "Bajo"},
    "variedades": {"name": "Variedades tolerantes", "heat": 0.30, "water": 0.30, "cost": "Bajo"},
    "cosecha_agua": {"name": "Cosecha de agua de lluvia", "heat": 0.0, "water": 0.35, "cost": "Medio"},
    "mulch": {"name": "Cobertura del suelo (mulch)", "heat": 0.10, "water": 0.20, "cost": "Bajo"},
}


def yield_index(crop_key: str, tmax: float, rain30: float, measures: list[str] | None = None) -> dict:
    crop = CROPS[crop_key]
    heat_stress = clamp((tmax - crop["t_crit"]) / crop["t_span"])
    water_stress = clamp((crop["water_need"] - rain30) / crop["water_need"])
    for m in measures or []:
        if m in MEASURES:
            heat_stress *= 1 - MEASURES[m]["heat"]
            water_stress *= 1 - MEASURES[m]["water"]
    index = 100 * (1 - 0.55 * heat_stress - 0.45 * water_stress)
    return {
        "index": round(index, 1),
        "heat_stress": round(heat_stress, 3),
        "water_stress": round(water_stress, 3),
    }
