#!/usr/bin/env python3
"""CLI калькулятор оценки выгодности цены Honda CB500F.

Использование (интерактивно):
  python cb500f_calculator.py

Использование (через аргументы):
  python cb500f_calculator.py --year 2019 --mileage 14000 --price 4700 --region NJ --condition good --abs yes --exhaust brand --crashbars yes

Категории вывода: Great Deal / Good Deal / Fair / Overpriced.
Модель описана в analysis/methodology_cb500f.md.
"""

from __future__ import annotations
import argparse
import csv
import pathlib
from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime

DATA_PATH = pathlib.Path(__file__).parent / "data" / "price_reference_cb500f.csv"

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
    "exhaust_brand": 120,  # +30 если сохранён сток (ручной ввод отдельным параметром в будущем)
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


def load_base_prices() -> Dict[int, PriceRow]:
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
    return rows


def clamp(val: float, min_v: float, max_v: float) -> float:
    return max(min_v, min(max_v, val))


def calc_fair_value(year: int, mileage: int, region: str, condition: str, accessories: Dict[str, bool], current_year: int | None = None) -> Dict[str, Any]:
    prices = load_base_prices()
    if year not in prices:
        raise ValueError(f"Год {year} отсутствует в таблице (диапазон {min(prices)}-{max(prices)})")

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

    # Суммируем аксессуары
    accessories_value = 0.0
    for key, present in accessories.items():
        if present:
            accessories_value += ACCESSORY_VALUES[key]
    accessories_cap = 0.18 * base_mid
    accessories_value_capped = min(accessories_value, accessories_cap)

    fair = (base_mid + mileage_adj) * (1 + condition_factor) * (1 + region_factor) + accessories_value_capped

    components = {
        "base_mid": base_mid,
        "mileage_adj": mileage_adj,
        "condition_factor": condition_factor,
        "region_factor": region_factor,
        "accessories_value_raw": accessories_value,
        "accessories_value_capped": accessories_value_capped,
        "expected_mileage": expected_mileage,
    }
    return {"fair_value": fair, "components": components}


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


def fmt_money(v: float) -> str:
    return f"${v:,.0f}"


def build_arg_parser():
    p = argparse.ArgumentParser(description="Оценка Honda CB500F")
    p.add_argument('--year', type=int, help='Год выпуска', required=False)
    p.add_argument('--mileage', type=int, help='Пробег (мили)', required=False)
    p.add_argument('--price', type=float, help='Цена из объявления', required=False)
    p.add_argument('--region', choices=REGION_FACTORS.keys(), help='Регион (штат)', required=False)
    p.add_argument('--condition', choices=CONDITION_FACTORS.keys(), help='Состояние', required=False)
    # Аксессуары (булевы флаги)
    for acc in ACCESSORY_VALUES:
        p.add_argument(f'--{acc}', action='store_true', help=f'Наличие: {acc}')
    return p


def interactive_input():
    year = int(input('Год выпуска: '))
    mileage = int(input('Пробег (мили): '))
    price = float(input('Цена ($): '))
    region = input(f"Регион {list(REGION_FACTORS.keys())}: ").strip().upper()
    if region not in REGION_FACTORS:
        raise SystemExit("Неизвестный регион")
    print("Состояние варианты: excellent / good / fair / needs_work")
    condition = input('Состояние: ').strip().lower()
    if condition not in CONDITION_FACTORS:
        raise SystemExit("Неизвестное состояние")
    accessories = {}
    for acc in ACCESSORY_VALUES:
        ans = input(f"{acc}? (y/N): ").strip().lower()
        accessories[acc] = ans == 'y'
    return year, mileage, price, region, condition, accessories


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.year is None:
        year, mileage, price, region, condition, accessories = interactive_input()
    else:
        accessories = {acc: getattr(args, acc) for acc in ACCESSORY_VALUES}
        year, mileage, price, region, condition = args.year, args.mileage, args.price, args.region, args.condition
        if None in (year, mileage, price, region, condition):
            parser.error("Для неинтерактивного режима укажите все обязательные параметры")

    result = calc_fair_value(year, mileage, region, condition, accessories)
    fair = result['fair_value']
    classification = classify(price, fair)

    print("\n=== Оценка CB500F ===")
    print(f"Год: {year} | Пробег: {mileage} | Регион: {region} | Состояние: {condition}")
    print("Аксессуары:")
    for k,v in accessories.items():
        if v:
            print(f"  - {k}")
    print(f"Справедливая цена: {fmt_money(fair)}")
    print(f"Цена из объявления: {fmt_money(price)}")
    print(f"Классификация: {classification}")
    print("--- Детализация ---")
    for k,v in result['components'].items():
        if isinstance(v, float):
            print(f"{k}: {v:,.2f}")
        else:
            print(f"{k}: {v}")
    target_low = fair * 0.88
    target_high = fair * 0.94
    print(f"Рекомендуемый коридор покупки: {fmt_money(target_low)} - {fmt_money(target_high)}")

if __name__ == '__main__':
    main()
