"""Цена и готовность платить: воспроизводимые расчёты Ван Вестендорпа и Габора — Грейнджера.

Оба метода — заявленная готовность: люди в опросе обычно называют цену выше, чем платят на деле.
Поэтому расчёт даёт диапазон для ценового теста, а не цену. Доказывает цену только реальная оплата (A/B в пилоте).
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

from .paths import SfError

VW_COLUMNS = ("too_cheap", "cheap", "expensive", "too_expensive")
GG_COLUMNS = ("price", "shown", "bought")
MIN_RESPONDENTS = 30   # меньше — диапазон слишком шаткий, отчёт об этом предупреждает
Z95 = 1.96


@dataclass(frozen=True)
class VanWestendorp:
    respondents: int
    dropped: int
    pmc: float | None   # нижняя граница приемлемого: «слишком дёшево» пересекает «не дёшево»
    opp: float | None   # оптимальная точка: «слишком дёшево» пересекает «слишком дорого»
    ipp: float | None   # точка безразличия: «дёшево» пересекает «дорого»
    pme: float | None   # верхняя граница: «слишком дорого» пересекает «не дорого»


@dataclass(frozen=True)
class PricePoint:
    price: float
    shown: int
    bought: int
    rate: float
    low: float
    high: float

    @property
    def revenue_per_100(self) -> float:
        return self.price * self.rate * 100


def _read(path: Path, columns: tuple[str, ...]) -> list[dict[str, float]]:
    if not path.exists():
        raise SfError(f"Нет файла {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(columns) - set(reader.fieldnames or [])
        if missing:
            raise SfError(f"В {path.name} нет колонок: {', '.join(sorted(missing))}. Нужны: {', '.join(columns)}")
        rows = []
        for num, row in enumerate(reader, start=2):
            try:
                rows.append({c: float((row[c] or "").replace(",", ".").replace(" ", "")) for c in columns})
            except ValueError as err:
                raise SfError(f"{path.name}, строка {num}: не число ({err})") from err
    if not rows:
        raise SfError(f"{path.name}: нет строк с данными")
    return rows


def _crossing(grid: list[float], falling: list[float], rising: list[float]) -> float | None:
    """Цена, где убывающая доля впервые становится не больше растущей (линейная интерполяция между узлами)."""
    for i in range(1, len(grid)):
        before, after = falling[i - 1] - rising[i - 1], falling[i] - rising[i]
        if before > 0 >= after:
            share = before / (before - after) if before != after else 0.0
            return round(grid[i - 1] + share * (grid[i] - grid[i - 1]), 2)
    return None


def van_westendorp(rows: list[dict[str, float]]) -> VanWestendorp:
    """Четыре вопроса на респондента: слишком дёшево, дёшево, дорого, слишком дорого. Непоследовательные ответы отбрасываем."""
    valid = [r for r in rows if 0 < r["too_cheap"] <= r["cheap"] <= r["expensive"] <= r["too_expensive"]]
    if len(valid) < 2:
        raise SfError("Меньше двух последовательных ответов (слишком дёшево ≤ дёшево ≤ дорого ≤ слишком дорого).")
    n = len(valid)
    grid = sorted({v for r in valid for v in r.values()})
    too_cheap = [sum(r["too_cheap"] >= p for r in valid) / n for p in grid]
    cheap = [sum(r["cheap"] >= p for r in valid) / n for p in grid]
    expensive = [sum(r["expensive"] <= p for r in valid) / n for p in grid]
    too_expensive = [sum(r["too_expensive"] <= p for r in valid) / n for p in grid]
    return VanWestendorp(
        respondents=n, dropped=len(rows) - n,
        pmc=_crossing(grid, too_cheap, [1 - c for c in cheap]),
        opp=_crossing(grid, too_cheap, too_expensive),
        ipp=_crossing(grid, cheap, expensive),
        pme=_crossing(grid, [1 - e for e in expensive], too_expensive),
    )


def _wilson(bought: int, shown: int) -> tuple[float, float]:
    if shown == 0:
        return 0.0, 0.0
    p = bought / shown
    denom = 1 + Z95 ** 2 / shown
    centre = (p + Z95 ** 2 / (2 * shown)) / denom
    half = Z95 * math.sqrt(p * (1 - p) / shown + Z95 ** 2 / (4 * shown ** 2)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def gabor_granger(rows: list[dict[str, float]]) -> list[PricePoint]:
    """По каждой цене: скольким показали и сколько согласились (или купили в ценовом тесте)."""
    points = []
    for r in sorted(rows, key=lambda r: r["price"]):
        shown, bought = int(r["shown"]), int(r["bought"])
        if shown <= 0 or not 0 <= bought <= shown:
            raise SfError(f"Цена {r['price']:g}: нужно 0 ≤ bought ≤ shown и shown > 0")
        low, high = _wilson(bought, shown)
        points.append(PricePoint(r["price"], shown, bought, bought / shown, low, high))
    return points


def _fmt(value: float | None) -> str:
    return "не найдено" if value is None else f"{value:g}"


def vw_report(path: Path) -> str:
    result = van_westendorp(_read(path, VW_COLUMNS))
    lines = [f"# Ван Вестендорп: {path.name}", "",
             f"Респондентов: {result.respondents} (отброшено непоследовательных: {result.dropped})", "",
             "| Точка | Цена | Смысл |", "|---|---|---|",
             f"| Нижняя граница (PMC) | {_fmt(result.pmc)} | дешевле — цена вызывает сомнение в качестве |",
             f"| Оптимальная (OPP) | {_fmt(result.opp)} | поровну «слишком дёшево» и «слишком дорого» |",
             f"| Безразличия (IPP) | {_fmt(result.ipp)} | поровну «дёшево» и «дорого» — ожидаемая норма |",
             f"| Верхняя граница (PME) | {_fmt(result.pme)} | дороже — большинство считает слишком дорогим |", "",
             f"Приемлемый диапазон: **{_fmt(result.pmc)} — {_fmt(result.pme)}**. "
             "Это заявленная готовность: в опросах люди называют цену выше, чем платят. "
             "Диапазон задаёт цены для ценового теста, а не саму цену."]
    if result.respondents < MIN_RESPONDENTS:
        lines.append(f"\nВнимание: ответов меньше {MIN_RESPONDENTS} — диапазон грубый, выводы только как [ГИП].")
    return "\n".join(lines) + "\n"


def gg_report(path: Path) -> str:
    points = gabor_granger(_read(path, GG_COLUMNS))
    best = max(points, key=lambda p: p.revenue_per_100)
    lines = [f"# Габор — Грейнджер / ценовой тест: {path.name}", "",
             "| Цена | Показали | Согласились | Доля | 95% интервал | Выручка на 100 показов |", "|---|---|---|---|---|---|"]
    for p in points:
        mark = " ←" if p is best else ""
        lines.append(f"| {p.price:g} | {p.shown} | {p.bought} | {p.rate:.1%} | {p.low:.1%}–{p.high:.1%} | "
                     f"{p.revenue_per_100:,.0f}{mark} |".replace(",", " "))
    rivals = [p for p in points if p is not best and p.high * p.price >= best.low * best.price]
    lines += ["", f"Наибольшая выручка на показ — при цене **{best.price:g}**."]
    if rivals:
        lines.append("Но интервалы пересекаются с ценами " + ", ".join(f"{p.price:g}" for p in rivals)
                     + ": по этим данным цены не различимы — нужна бо́льшая выборка или реальный ценовой тест.")
    lines.append("Если это опрос (а не реальная оплата) — доля завышена; решение о цене — только после A/B с оплатой.")
    return "\n".join(lines) + "\n"
