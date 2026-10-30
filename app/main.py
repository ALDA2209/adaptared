"""AdaptaRed: alerta temprana y adaptación climática para comunidades de Huánuco."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import i18n, pdfexport, risk, services
from .db import get_db, init_db
from .seed import seed_if_needed
from .weather import fetch_open_meteo

APP_DIR = Path(__file__).resolve().parent
MONTHS = i18n.MONTHS["es"]
MONTHS_EN = i18n.MONTHS["en"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    seed_if_needed()
    yield


app = FastAPI(title="AdaptaRed", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


def fmt_dt(value: str) -> str:
    try:
        d = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return value or ""
    return f"{d.day} {MONTHS[d.month - 1]}, {d:%H:%M}"


def fmt_day(value: str) -> str:
    d = datetime.fromisoformat(value)
    return f"{d.day} {MONTHS[d.month - 1]}"


def fmt_dt_en(value: str) -> str:
    try:
        d = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return value or ""
    return f"{MONTHS_EN[d.month - 1]} {d.day}, {d:%H:%M}"


def fmt_day_en(value: str) -> str:
    d = datetime.fromisoformat(value)
    return f"{MONTHS_EN[d.month - 1]} {d.day}"


templates.env.filters["miles"] = lambda n: f"{int(round(n)):,}"
templates.env.filters["fecha"] = fmt_dt
templates.env.filters["dia"] = fmt_day
templates.env.filters["fecha_en"] = fmt_dt_en
templates.env.filters["dia_en"] = fmt_day_en
templates.env.filters["crops_en"] = i18n.crops_en
templates.env.globals.update(
    HAZARDS=risk.HAZARDS,
    LEVELS=risk.LEVELS,
    LEVEL_LABELS=risk.LEVEL_LABELS,
    CROPS=risk.CROPS,
    MEASURES=risk.MEASURES,
    HAZARDS_EN=i18n.HAZARDS["en"],
    LEVEL_LABELS_EN=i18n.LEVEL_LABELS["en"],
    CROPS_EN=i18n.crops_for("en", risk.CROPS),
    MEASURES_EN=i18n.measures_for("en", risk.MEASURES),
)


def get_database():
    yield get_db()


def current_lang(request: Request) -> str:
    return i18n.detect(request)


def render(request: Request, name: str, active: str, **ctx):
    lang = current_lang(request)
    keep = [(k, v) for k, v in request.query_params.multi_items() if k not in ("msg", "kind")]
    next_url = request.url.path + ("?" + "&".join(f"{quote(k)}={quote(v)}" for k, v in keep) if keep else "")
    ctx.update(
        nav=i18n.NAV[lang],
        active=active,
        flash=request.query_params.get("msg"),
        flash_kind=request.query_params.get("kind", "ok"),
        lang=lang,
        next_url=quote(next_url, safe=""),
    )
    return templates.TemplateResponse(request, name if lang == "es" else f"en/{name}", ctx)


@app.get("/idioma/{code}")
def set_language(code: str, next: str = "/"):
    if code not in i18n.LANGS:
        raise HTTPException(404, "Language not supported")
    target = next if next.startswith("/") and not next.startswith("//") and "\\" not in next else "/"
    resp = RedirectResponse(target, status_code=303)
    resp.set_cookie("lang", code, max_age=60 * 60 * 24 * 365, samesite="lax", path="/")
    return resp


def back(path: str, msg: str, kind: str = "ok") -> RedirectResponse:
    sep = "&" if "?" in path else "?"
    return RedirectResponse(f"{path}{sep}msg={quote(msg)}&kind={kind}", status_code=303)


def series_payload(obs: list[dict]) -> dict:
    return {
        "days": [o["day"] for o in obs],
        "tmax": [o["tmax"] for o in obs],
        "tmin": [o["tmin"] for o in obs],
        "rain": [o["rain"] for o in obs],
        "soil": [o["soil"] for o in obs],
        "forecast": [bool(o["is_forecast"]) for o in obs],
    }


def slim(c: dict) -> dict:
    r = c["risk"]
    return {
        "slug": c["slug"],
        "name": c["name"],
        "district": c["district"],
        "province": c["province"],
        "lat": c["lat"],
        "lon": c["lon"],
        "elevation": c["elevation"],
        "population": c["population"],
        "score": r["score"],
        "level": r["level"],
        "dominant": r["dominant"],
        "dominant_name": r["dominant_name"],
        "by_hazard": {k: {"score": v["score"], "level": v["level"]} for k, v in r["by_hazard"].items()},
    }


# ----------------------------------------------------------------------------- páginas
@app.get("/")
def dashboard(request: Request, db=Depends(get_database)):
    lang = current_lang(request)
    items = services.overview(db, lang)
    summary = services.summarize(items)
    top = items[0]
    obs = services.get_observations(db, top["id"])
    ridge = sorted(items, key=lambda c: c["elevation"])
    return render(
        request,
        "dashboard.html",
        "dashboard",
        items=items,
        summary=summary,
        headline=services.headline(summary, lang),
        top=top,
        top5=items[:5],
        alerts=services.get_alerts(db, "activa", lang)[:4],
        ridge=[{"name": c["name"], "slug": c["slug"], "elevation": c["elevation"], "score": c["risk"]["score"], "level": c["risk"]["level"]} for c in ridge],
        series=series_payload(obs),
        hazard_counts=summary["hazards_high"],
    )


@app.get("/mapa")
def mapa(request: Request, db=Depends(get_database)):
    items = services.overview(db, current_lang(request))
    return render(request, "mapa.html", "mapa", items=items, points=[slim(c) for c in items])


@app.get("/comunidades")
def comunidades(request: Request, q: str = "", nivel: str = "", amenaza: str = "", orden: str = "riesgo", db=Depends(get_database)):
    items = services.overview(db, current_lang(request))
    if q:
        ql = q.lower()
        items = [c for c in items if ql in c["name"].lower() or ql in c["province"].lower() or ql in c["district"].lower()]
    if nivel in risk.LEVELS:
        items = [c for c in items if c["risk"]["level"] == nivel]
    if amenaza in risk.HAZARDS:
        items = [c for c in items if risk.level_rank(c["risk"]["by_hazard"][amenaza]["level"]) >= 1]
        items.sort(key=lambda c: c["risk"]["by_hazard"][amenaza]["score"], reverse=True)
    elif orden == "nombre":
        items.sort(key=lambda c: c["name"])
    elif orden == "poblacion":
        items.sort(key=lambda c: c["population"], reverse=True)
    return render(request, "comunidades.html", "comunidades", items=items, q=q, nivel=nivel, amenaza=amenaza, orden=orden)


def community_context(db, slug: str, lang: str) -> dict:
    """Datos de una comunidad que comparten la página y el PDF del plan."""
    c = services.get_community(db, slug)
    if not c:
        raise HTTPException(404, i18n.tr(lang, "nf_community"))
    obs = services.get_observations(db, c["id"])
    c["risk"] = risk.assess(c, obs, i18n.HAZARDS[lang])
    order = sorted(c["risk"]["by_hazard"].values(), key=lambda h: h["score"], reverse=True)
    plans = [
        {"hazard": h, "actions": risk.recommend(h["key"], h["level"], lang)}
        for h in order
        if risk.level_rank(h["level"]) >= 1
    ]
    alerts = [a for a in services.get_alerts(db, None, lang) if a["community_id"] == c["id"]]
    reports = [r for r in services.get_reports(db, lang) if r["community_id"] == c["id"]]
    fut = [o for o in obs if o["is_forecast"]]
    return {
        "c": c,
        "obs": obs,
        "hazards": order,
        "plans": plans,
        "alerts": alerts,
        "reports": reports,
        "series": series_payload(obs),
        "people_no_water": round(c["population"] * (1 - c["water_access"])),
        "peak_tmax": max((o["tmax"] for o in fut), default=None),
        "total_rain": round(sum(o["rain"] for o in fut), 1),
    }


@app.get("/comunidades/{slug}")
def comunidad(request: Request, slug: str, db=Depends(get_database)):
    ctx = community_context(db, slug, current_lang(request))
    return render(request, "comunidad.html", "comunidades", **ctx)


@app.get("/comunidades/{slug}/solucion.pdf")
def solucion_pdf(request: Request, slug: str, db=Depends(get_database)):
    """Descarga la hoja de solución de la comunidad (acciones concretas) como PDF, en el idioma activo."""
    lang = current_lang(request)
    ctx = community_context(db, slug, lang)
    data = pdfexport.build_solution_pdf(ctx["c"], ctx["hazards"], ctx["plans"], ctx["obs"], lang)
    name = "solucion" if lang == "es" else "solution"
    return Response(
        data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{name}-{slug}.pdf"'},
    )


# ----------------------------------------------------------------------------- alertas
@app.get("/alertas")
def alertas(request: Request, estado: str = "", db=Depends(get_database)):
    alerts = services.get_alerts(db, None, current_lang(request))
    if estado in ("activa", "resuelta"):
        alerts = [a for a in alerts if a["status"] == estado]
    comms = services.get_communities(db)
    return render(request, "alertas.html", "alertas", alerts=alerts, communities=comms, estado=estado)


@app.post("/alertas")
def crear_alerta(
    request: Request,
    comunidad: str = Form(...),
    amenaza: str = Form(...),
    nivel: str = Form(...),
    mensaje: str = Form(...),
    db=Depends(get_database),
):
    lang = current_lang(request)
    c = services.get_community(db, comunidad)
    mensaje = mensaje.strip()
    if not c or amenaza not in risk.HAZARDS or nivel not in risk.LEVELS:
        return back("/alertas", i18n.tr(lang, "alert_check"), "err")
    if not 10 <= len(mensaje) <= 400:
        return back("/alertas", i18n.tr(lang, "alert_len"), "err")
    services.create_alert(db, c["id"], amenaza, nivel, mensaje)
    return back("/alertas", i18n.tr(lang, "alert_ok", name=c["name"]))


@app.post("/alertas/generar")
def generar_alertas(request: Request, db=Depends(get_database)):
    """Crea alertas para cada amenaza en nivel alto o crítico que aún no tenga una alerta activa."""
    lang = current_lang(request)
    created = 0
    active = {(a["community_id"], a["hazard"]) for a in services.get_alerts(db, "activa")}
    for c in services.overview(db):
        for hz in c["risk"]["by_hazard"].values():
            if risk.level_rank(hz["level"]) >= 2 and (c["id"], hz["key"]) not in active:
                services.create_alert(
                    db, c["id"], hz["key"], hz["level"], services.alert_text(c, hz, "es"), "automatica",
                    message_en=services.alert_text(c, hz, "en"),
                )
                created += 1
    if created == 0:
        return back("/alertas", i18n.tr(lang, "gen_none"))
    return back("/alertas", i18n.tr(lang, "gen_ok", n=created))


@app.post("/alertas/{alert_id}/estado")
def cambiar_estado(request: Request, alert_id: str, estado: str = Form(...), db=Depends(get_database)):
    lang = current_lang(request)
    if estado not in ("activa", "resuelta"):
        return back("/alertas", i18n.tr(lang, "state_bad"), "err")
    if not services.set_alert_status(db, alert_id, estado):
        raise HTTPException(404, i18n.tr(lang, "nf_alert"))
    return back("/alertas", i18n.tr(lang, "state_resolved" if estado == "resuelta" else "state_reactivated"))


# ----------------------------------------------------------------------------- agricultura
@app.get("/agro")
def agro(request: Request, db=Depends(get_database)):
    comms = services.get_communities(db)
    return render(request, "agro.html", "agro", communities=comms)


CROP_WORDS = {"papa": "papa", "maíz": "maiz", "café": "cafe", "cacao": "cacao", "frijol": "frijol"}


def local_crops(text: str) -> set[str]:
    words = {w.strip().lower() for w in text.split(",")}
    return {CROP_WORDS[w] for w in words if w in CROP_WORDS}


@app.get("/api/agro/simular")
def simular(request: Request, comunidad: str, dtemp: float = 0.0, dlluvia: float = 0.0, medidas: str = "", db=Depends(get_database)):
    lang = current_lang(request)
    crop_info = i18n.crops_for(lang, risk.CROPS)
    measure_info = i18n.measures_for(lang, risk.MEASURES)
    c = services.get_community(db, comunidad)
    if not c:
        raise HTTPException(404, i18n.tr(lang, "nf_community"))
    dtemp = max(-2.0, min(6.0, dtemp))
    dlluvia = max(-60.0, min(40.0, dlluvia))
    chosen = [m for m in medidas.split(",") if m in risk.MEASURES]
    tmax = c["tmax_clim"] + dtemp
    rain30 = c["rain30_clim"] * (1 + dlluvia / 100)
    mine = local_crops(c["main_crops"])
    crops = []
    for key, info in crop_info.items():
        base = risk.yield_index(key, c["tmax_clim"], c["rain30_clim"])
        scen = risk.yield_index(key, tmax, rain30)
        with_m = risk.yield_index(key, tmax, rain30, chosen)
        crops.append(
            {
                "key": key,
                "name": info["name"],
                "local": key in mine,
                "baseline": base["index"],
                "scenario": scen["index"],
                "with_measures": with_m["index"],
                "heat_stress": scen["heat_stress"],
                "water_stress": scen["water_stress"],
            }
        )
    pool = [x for x in crops if x["local"]] or crops
    focus = min(pool, key=lambda x: x["scenario"] - x["baseline"])
    measures = []
    for key, m in measure_info.items():
        gain = risk.yield_index(focus["key"], tmax, rain30, [key])["index"] - focus["scenario"]
        measures.append({"key": key, "name": m["name"], "cost": m["cost"], "gain": round(gain, 1)})
    measures.sort(key=lambda m: m["gain"], reverse=True)
    return {
        "community": {"slug": c["slug"], "name": c["name"], "tmax": round(tmax, 1), "rain30": round(rain30)},
        "scenario": {"dtemp": dtemp, "dlluvia": dlluvia, "measures": chosen},
        "crops": crops,
        "focus": {"key": focus["key"], "name": focus["name"], "drop": round(focus["baseline"] - focus["scenario"], 1)},
        "measures": measures,
    }


# ----------------------------------------------------------------------------- reportes
@app.get("/reportes")
def reportes(request: Request, db=Depends(get_database)):
    return render(
        request,
        "reportes.html",
        "reportes",
        reports=services.get_reports(db, current_lang(request)),
        communities=services.get_communities(db),
    )


@app.post("/reportes")
def crear_reporte(
    request: Request,
    comunidad: str = Form(...),
    amenaza: str = Form(...),
    descripcion: str = Form(...),
    quien: str = Form(""),
    db=Depends(get_database),
):
    lang = current_lang(request)
    c = services.get_community(db, comunidad)
    descripcion = descripcion.strip()
    if not c or amenaza not in risk.HAZARDS:
        return back("/reportes", i18n.tr(lang, "rep_check"), "err")
    if not 10 <= len(descripcion) <= 500:
        return back("/reportes", i18n.tr(lang, "rep_len"), "err")
    services.create_report(db, c["id"], amenaza, descripcion, quien.strip()[:80] or i18n.DEFAULT_REPORTER[lang])
    return back("/reportes", i18n.tr(lang, "rep_ok"))


@app.post("/reportes/{report_id}/verificar")
def verificar_reporte(request: Request, report_id: str, db=Depends(get_database)):
    lang = current_lang(request)
    if not services.verify_report(db, report_id):
        raise HTTPException(404, i18n.tr(lang, "nf_report"))
    return back("/reportes", i18n.tr(lang, "rep_verified"))


# ----------------------------------------------------------------------------- impacto y método
IMPACT = {
    "years": ["Año 1", "Año 2", "Año 3"],
    "communities": [12, 60, 180],
    "people": [29000, 140000, 420000],
    "cost_per_person": [3.2, 1.5, 0.9],
    "revenue": {
        "Suscripciones municipales": [10, 55, 160],
        "Programas de cooperación": [40, 70, 110],
        "Alianzas con seguros y agroindustria": [0, 25, 90],
        "Subvenciones": [60, 40, 20],
    },
    "costs": [95, 150, 260],
}


@app.get("/impacto")
def impacto(request: Request):
    lang = current_lang(request)
    net = [sum(v[i] for v in IMPACT["revenue"].values()) - IMPACT["costs"][i] for i in range(3)]
    text = i18n.IMPACT[lang]
    impact = {
        **IMPACT,
        "years": text["years"],
        "revenue": dict(zip(text["revenue"], IMPACT["revenue"].values())),
    }
    return render(request, "impacto.html", "impacto", impact=impact, net=net)


@app.get("/metodologia")
def metodologia(request: Request):
    return render(
        request,
        "metodologia.html",
        "metodologia",
        thresholds=risk.LEVEL_THRESHOLDS,
        crops=i18n.crops_for(current_lang(request), risk.CROPS),
        measures=i18n.measures_for(current_lang(request), risk.MEASURES),
    )


# ----------------------------------------------------------------------------- API JSON
@app.get("/api/comunidades")
def api_comunidades(request: Request, db=Depends(get_database)):
    items = services.overview(db, current_lang(request))
    return {"summary": services.summarize(items), "communities": [slim(c) for c in items]}


@app.get("/api/comunidades/{slug}")
def api_comunidad(request: Request, slug: str, db=Depends(get_database)):
    lang = current_lang(request)
    c = services.get_community(db, slug)
    if not c:
        raise HTTPException(404, i18n.tr(lang, "nf_community"))
    obs = services.get_observations(db, c["id"])
    c["risk"] = risk.assess(c, obs, i18n.HAZARDS[lang])
    return {"community": c, "series": series_payload(obs)}


@app.get("/api/clima-en-vivo/{slug}")
def clima_en_vivo(request: Request, slug: str, db=Depends(get_database)):
    c = services.get_community(db, slug)
    if not c:
        raise HTTPException(404, i18n.tr(current_lang(request), "nf_community"))
    live = fetch_open_meteo(c["lat"], c["lon"])
    if live:
        today = datetime.now().date().isoformat()
        return {
            "source": "open-meteo",
            "days": [d["day"] for d in live],
            "tmax": [d["tmax"] for d in live],
            "tmin": [d["tmin"] for d in live],
            "rain": [d["rain"] for d in live],
            "forecast": [d["day"] > today for d in live],
        }
    obs = services.get_observations(db, c["id"])
    data = series_payload(obs)
    return JSONResponse({"source": "simulado", **{k: data[k] for k in ("days", "tmax", "tmin", "rain", "forecast")}})


@app.get("/healthz")
def healthz():
    return {"ok": True}
