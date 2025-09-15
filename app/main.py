from __future__ import annotations
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pathlib
from .market_model import (
    REGION_FACTORS, CONDITION_FACTORS, ACCESSORY_VALUES,
    calc_fair_value, classify, recommended_band
)

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "analysis"
GUIDES_DIR = BASE_DIR / "guides"

app = FastAPI(title="CB500F Market Tool")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

def load_text(path: pathlib.Path) -> str:
    if not path.exists():
        return "Not found"
    return path.read_text(encoding='utf-8')

@app.get("/", response_class=HTMLResponse)
async def form_page(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "regions": REGION_FACTORS.keys(),
        "conditions": CONDITION_FACTORS.keys(),
        "accessories": ACCESSORY_VALUES,
        "result": None,
    })

@app.post("/", response_class=HTMLResponse)
async def calc(request: Request,
               year: int = Form(...),
               mileage: int = Form(...),
               price: float = Form(...),
               region: str = Form(...),
               condition: str = Form(...),
               **kwargs):
    accessories = {}
    for acc in ACCESSORY_VALUES:
        accessories[acc] = kwargs.get(acc) == 'on'
    data = calc_fair_value(year, mileage, region, condition, accessories)
    fair = data['fair_value']
    classification = classify(price, fair)
    band_low, band_high = recommended_band(fair)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "regions": REGION_FACTORS.keys(),
        "conditions": CONDITION_FACTORS.keys(),
        "accessories": ACCESSORY_VALUES,
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

@app.get("/methodology", response_class=HTMLResponse)
async def methodology(request: Request):
    text = load_text(CONTENT_DIR / "methodology_cb500f.md")
    return templates.TemplateResponse("content.html", {"request": request, "title": "Methodology", "content": text})

@app.get("/strategy", response_class=HTMLResponse)
async def strategy(request: Request):
    text = load_text(GUIDES_DIR / "fb_marketplace_strategy.md")
    return templates.TemplateResponse("content.html", {"request": request, "title": "FB Marketplace Strategy", "content": text})
