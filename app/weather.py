"""Conector opcional con Open-Meteo (gratuito, sin llave).

Si no hay internet o el servicio falla, devuelve None y la app sigue
funcionando con la serie guardada en la base de datos.
"""
from __future__ import annotations

import httpx

URL = "https://api.open-meteo.com/v1/forecast"


def fetch_open_meteo(lat: float, lon: float, timeout: float = 6.0) -> list[dict] | None:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "past_days": 7,
        "forecast_days": 7,
        "timezone": "America/Lima",
    }
    try:
        r = httpx.get(URL, params=params, timeout=timeout)
        r.raise_for_status()
        d = r.json()["daily"]
        out = []
        for day, tmax, tmin, rain in zip(
            d["time"], d["temperature_2m_max"], d["temperature_2m_min"], d["precipitation_sum"]
        ):
            if tmax is None or tmin is None:
                continue
            out.append({"day": day, "tmax": tmax, "tmin": tmin, "rain": rain or 0.0})
        return out or None
    except Exception:
        return None
