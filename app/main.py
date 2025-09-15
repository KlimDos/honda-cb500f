from __future__ import annotations
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pathlib
from .market_model import (
    REGION_FACTORS, CONDITION_FACTORS, ACCESSORY_VALUES,
    calc_fair_value, classify, recommended_band, ACCESSORY_LABELS_RU
)
import mistune

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "analysis"
GUIDES_DIR = BASE_DIR / "guides"

app = FastAPI(title="CB500F Market Tool")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

markdown = mistune.create_markdown()

def load_markdown_html(path: pathlib.Path) -> str:
    if not path.exists():
        return "<p>Not found</p>"
    return markdown(path.read_text(encoding='utf-8'))

@app.get("/", response_class=HTMLResponse)
async def form_page(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "regions": REGION_FACTORS.keys(),
        "conditions": CONDITION_FACTORS.keys(),
        "accessories": ACCESSORY_VALUES,
        "accessories_ru": ACCESSORY_LABELS_RU,
        "result": None,
    })

@app.post("/", response_class=HTMLResponse)
async def calc(request: Request,
               year: int = Form(...),
               mileage: int = Form(...),
               price: float = Form(...),
               region: str = Form(...),
               condition: str = Form(...)):
    # Собираем остальные checkbox поля вручную (FastAPI не поддерживает произвольный **kwargs для формы)
    form = await request.form()
    accessories = {acc: (form.get(acc) == 'on') for acc in ACCESSORY_VALUES}
    data = calc_fair_value(year, mileage, region, condition, accessories)
    fair = data['fair_value']
    classification = classify(price, fair)
    band_low, band_high = recommended_band(fair)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "regions": REGION_FACTORS.keys(),
        "conditions": CONDITION_FACTORS.keys(),
        "accessories": ACCESSORY_VALUES,
        "accessories_ru": ACCESSORY_LABELS_RU,
        "result": {
            "fair": fair,
            "classification": classification,
            "components": data['components'],
            "asking": price,
            "band": (band_low, band_high),
            "year": year,
            "mileage": mileage,
            "region": region,
            "condition": condition,
            "selected_accessories": accessories,
        }
    })

@app.post("/api/evaluate")
async def api_evaluate(payload: dict):
    required = {"year", "mileage", "price", "region", "condition"}
    missing = required - payload.keys()
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing fields: {', '.join(sorted(missing))}")
    try:
        accessories = {acc: bool(payload.get(acc, False)) for acc in ACCESSORY_VALUES}
        data = calc_fair_value(int(payload['year']), int(payload['mileage']), payload['region'], payload['condition'], accessories)
        fair = data['fair_value']
        classification = classify(float(payload['price']), fair)
        band_low, band_high = recommended_band(fair)
        return {
            "fair_value": round(fair, 2),
            "classification": classification,
            "offer_band": [round(band_low,2), round(band_high,2)],
            "components": data['components'],
            "accessories": {k:v for k,v in accessories.items() if v},
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/healthz")
async def healthz():
    try:
        # Простая проверка доступа к данным
        _ = list(REGION_FACTORS.keys())
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})

@app.get("/methodology", response_class=HTMLResponse)
async def methodology(request: Request):
    html = load_markdown_html(CONTENT_DIR / "methodology_cb500f.md")
    return templates.TemplateResponse("content.html", {"request": request, "title": "Methodology", "html_content": html})

@app.get("/strategy", response_class=HTMLResponse)
async def strategy(request: Request):
    html = load_markdown_html(GUIDES_DIR / "fb_marketplace_strategy.md")
    return templates.TemplateResponse("content.html", {"request": request, "title": "FB Marketplace Strategy", "html_content": html})
