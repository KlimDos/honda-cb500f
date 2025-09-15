from __future__ import annotations
from dataclasses import dataclass
import csv
import pathlib
from datetime import datetime
from typing import Dict, Any

DATA_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "price_reference_cb500f.csv"

REGION_FACTORS = {
    "NY": 0.03,
    "NJ": 0.03,
    "PA": 0.00,
    "MD": 0.01,
    "VA": 0.02,
}

CONDITION_FACTORS = {
    "excellent": 0.07,
    "good": 0.00,
    "fair": -0.08,
    "needs_work": -0.15,
}

ACCESSORY_VALUES = {
    "abs": 150,
    "exhaust_brand": 120,
    "crashbars": 50,
    "windscreen": 40,
    "heated_grips": 60,
    "luggage_quality": 250,
    "luggage_basic": 120,
    "new_tires": 180,
    "fresh_chainkit": 120,
}

@dataclass
class PriceRow:
    year: int
    base_mid_usd: float
    range_low_usd: float
    range_high_usd: float


_CACHE: Dict[int, PriceRow] | None = None


def load_base_prices(force: bool = False) -> Dict[int, PriceRow]:
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE
    rows: Dict[int, PriceRow] = {}
    with DATA_PATH.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            year = int(r['year'])
            rows[year] = PriceRow(
                year=year,
                base_mid_usd=float(r['base_mid_usd']),
                range_low_usd=float(r['range_low_usd']),
                range_high_usd=float(r['range_high_usd']),
            )
    _CACHE = rows
    return rows


def calc_fair_value(year: int, mileage: int, region: str, condition: str, accessories: Dict[str, bool], current_year: int | None = None) -> Dict[str, Any]:
    prices = load_base_prices()
    if year not in prices:
        raise ValueError(f"Год {year} отсутствует в таблице (диапазон {min(prices)}-{max(prices)})")
    if region not in REGION_FACTORS:
        raise ValueError("Неизвестный регион")
    if condition not in CONDITION_FACTORS:
        raise ValueError("Неизвестное состояние")
    if current_year is None:
        current_year = datetime.now().year
    base_mid = prices[year].base_mid_usd
    expected_miles_per_year = 2500
    years_old = max(0, current_year - year)
    expected_mileage = years_old * expected_miles_per_year
    delta_miles = mileage - expected_mileage
    if delta_miles > 0:
        mileage_adj = - min(delta_miles, 20000) * 0.10
    else:
        mileage_adj = + min(-delta_miles, 15000) * 0.06
    condition_factor = CONDITION_FACTORS[condition]
    region_factor = REGION_FACTORS[region]
    accessories_value = 0.0
    for key, present in accessories.items():
        if present and key in ACCESSORY_VALUES:
            accessories_value += ACCESSORY_VALUES[key]
    accessories_cap = 0.18 * base_mid
    accessories_value_capped = min(accessories_value, accessories_cap)
    fair = (base_mid + mileage_adj) * (1 + condition_factor) * (1 + region_factor) + accessories_value_capped
    return {
        "fair_value": fair,
        "components": {
            "base_mid": base_mid,
            "mileage_adj": mileage_adj,
            "condition_factor": condition_factor,
            "region_factor": region_factor,
            "accessories_value_raw": accessories_value,
            "accessories_value_capped": accessories_value_capped,
            "expected_mileage": expected_mileage,
        }
    }


def classify(asking_price: float, fair_value: float, fair_break: float = 4000) -> str:
    ratio = asking_price / fair_value
    delta = asking_price - fair_value
    if ratio <= 0.90 or (fair_value < fair_break and delta <= -300) or (fair_value >= fair_break and delta <= -400):
        return "Great Deal"
    if ratio <= 0.97:
        return "Good Deal"
    if ratio <= 1.07:
        return "Fair"
    return "Overpriced"


def recommended_band(fair_value: float) -> tuple[float, float]:
    return fair_value * 0.88, fair_value * 0.94
