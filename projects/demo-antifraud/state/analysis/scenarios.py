"""Итог первого года семейной защиты в трёх сценариях и чувствительность к каждому допущению (воспроизводимо).

Склеивает две готовые модели: объём рынка (market_size.py, E80) и окупаемость (breakeven.py, E49) —
в одно число «итог года = маржинальный доход от новых пар − инвестиции». Привлечение — только собственные
каналы (стоимость привлечения 0, как в стратегии). Факт — только численность пожилых (E79); остальное — допущения
агента [ГИП] из тех же скриптов и плана проверки. Каждое допущение задано тремя значениями:
(неблагоприятное, базовое, благоприятное). Чувствительность: меняем одно допущение от неблагоприятного
к благоприятному при остальных базовых и смотрим, насколько меняется итог года.
"""
from __future__ import annotations

OLDER = 35_100_000  # старше трудоспособного возраста, начало 2025 (E79)
HORIZON = 12
PRICE = 149  # ₽ в месяц за пару — цена пилота

ASSUMPTIONS: dict[str, tuple[str, tuple[float, float, float]]] = {
    "has_protector": ("есть взрослый близкий-защитник", (0.6, 0.7, 0.8)),
    "net_share": ("доля нашей сети среди пожилых", (0.15, 0.25, 0.30)),
    "same_net": ("защитник в той же сети", (0.25, 0.375, 0.50)),
    "reach": ("охват приглашением за год", (0.05, 0.10, 0.15)),
    "consent": ("согласие близкого", (0.20, 0.40, 0.50)),
    "first_pay": ("первая оплата среди согласившихся", (0.03, 0.10, 0.15)),
    "churn": ("отток платящих пар в месяц", (0.20, 0.15, 0.10)),
    "margin": ("маржа", (0.70, 0.80, 0.85)),
    "cannibalization": ("переход с текущей подписки", (0.30, 0.20, 0.10)),
    "investment": ("инвестиции, ₽", (10_000_000, 6_000_000, 3_000_000)),
}


def paid_months(churn: float) -> float:
    """Средние оплаченные месяцы пары за год при равномерном наборе (как в breakeven.py)."""
    return sum((1 - churn) ** t for t in range(HORIZON)) / 2


def payers(v: dict[str, float]) -> float:
    return OLDER * v["has_protector"] * v["net_share"] * v["same_net"] * v["reach"] * v["consent"] * v["first_pay"]


def value_per_payer(v: dict[str, float]) -> float:
    return PRICE * v["margin"] * paid_months(v["churn"]) * (1 - v["cannibalization"])


def year_result(v: dict[str, float]) -> float:
    return payers(v) * value_per_payer(v) - v["investment"]


def cohort_result(v: dict[str, float]) -> float:
    """Итог за всю жизнь пар, набранных в первый год: они платят и после 12-го месяца, пока не уйдут."""
    lifetime_months = 1 / v["churn"]
    return payers(v) * PRICE * v["margin"] * lifetime_months * (1 - v["cannibalization"]) - v["investment"]


def scenario(index: int) -> dict[str, float]:
    return {key: values[index] for key, (_, values) in ASSUMPTIONS.items()}


def mln(x: float) -> str:
    return f"{x / 1e6:+.1f}".replace(".", ",").replace("-", "−")


def fmt(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")


if __name__ == "__main__":
    base = scenario(1)
    for name, idx in (("неблагоприятный", 0), ("базовый", 1), ("благоприятный", 2)):
        v = scenario(idx)
        print(f"сценарий {name}: платящих пар за год {fmt(payers(v))}; итог года {mln(year_result(v))} млн ₽; "
              f"за всю жизнь когорты первого года {mln(cohort_result(v))} млн ₽")

    swings = []
    for key, (label, (low, _, high)) in ASSUMPTIONS.items():
        lo = year_result({**base, key: low})
        hi = year_result({**base, key: high})
        swings.append((hi - lo, label, lo, hi))
    print("чувствительность (итог года при неблагоприятном … благоприятном значении, остальное базовое):")
    for swing, label, lo, hi in sorted(swings, reverse=True):
        print(f"  {label}: {mln(lo)} … {mln(hi)} млн ₽ (размах {swing / 1e6:.1f} млн)".replace(".", ","))

    unit = payers({**base, "reach": 1.0}) * value_per_payer(base)
    need_reach = base["investment"] / unit
    need_pay = base["investment"] / (payers({**base, "first_pay": 1.0}) * value_per_payer(base))
    max_invest = year_result({**base, "investment": 0})
    print(f"безубыточность при остальных базовых: инвестиции ≤ {max_invest / 1e6:.1f} млн ₽".replace(".", ","))
    print(f"безубыточность при остальных базовых: охват за год ≥ {need_reach:.1%}; "
          f"или первая оплата ≥ {need_pay:.1%} согласившихся пар".replace(".", ","))
