"""Воспроизводимый первичный анализ таблицы (CSV): структура, пропуски, дубли, единицы, периоды, сводка.

Только проверки и описательная статистика — выводы делает агент со ссылкой на этот отчёт.
"""
from __future__ import annotations

import csv
import hashlib
import re
import statistics
from datetime import date
from pathlib import Path

from .paths import SfError

DATE_PATTERNS = (
    (re.compile(r"^\d{4}-\d{2}-\d{2}$"), "%Y-%m-%d"),
    (re.compile(r"^\d{2}\.\d{2}\.\d{4}$"), "%d.%m.%Y"),
    (re.compile(r"^\d{4}-\d{2}$"), "%Y-%m"),
)
UNIT_HINTS = {
    "%": "проценты", "pct": "проценты", "percent": "проценты", "доля": "доля (0–1 или %?)", "share": "доля (0–1 или %?)",
    "rub": "рубли", "руб": "рубли", "₽": "рубли", "usd": "доллары", "$": "доллары",
    "тыс": "тысячи", "thous": "тысячи", "млн": "миллионы", "mln": "миллионы",
}
MISSING = {"", "na", "n/a", "null", "none", "-", "—", "nan"}


def _number(value: str) -> float | None:
    cleaned = value.replace(" ", "").replace(" ", "").replace("%", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _date(value: str) -> str | None:
    from datetime import datetime
    for regex, fmt in DATE_PATTERNS:
        if regex.match(value):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                return None
    return None


def _read(path: Path) -> tuple[list[str], list[list[str]]]:
    if not path.exists():
        raise SfError(f"Файл не найден: {path}")
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(text.splitlines(), dialect))
    if not rows:
        raise SfError("Таблица пустая.")
    return rows[0], rows[1:]


def profile(path: Path) -> str:
    header, rows = _read(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    out = [f"# Профиль таблицы {path.name}", "",
           f"- Файл: `{path}` · sha256: {digest} · строк данных: {len(rows)} · колонок: {len(header)}",
           f"- Сформировано: sf.py analyze, {date.today().isoformat()} (повторный запуск даёт тот же результат на том же файле)", ""]
    issues = []
    ragged = sum(1 for r in rows if len(r) != len(header))
    if ragged:
        issues.append(f"{ragged} строк с числом ячеек, отличным от заголовка")
    duplicates = len(rows) - len({tuple(r) for r in rows})
    if duplicates:
        issues.append(f"{duplicates} полностью повторяющихся строк")
    out += ["| Колонка | Тип | Пропуски | Единицы (по названию) | Сводка |", "|---|---|---|---|---|"]
    for index, name in enumerate(header):
        values = [r[index].strip() if index < len(r) else "" for r in rows]
        present = [v for v in values if v.lower() not in MISSING]
        missing = len(values) - len(present)
        numbers = [n for n in (_number(v) for v in present) if n is not None]
        dates = [d for d in (_date(v) for v in present) if d is not None]
        unit = next((label for key, label in UNIT_HINTS.items() if key in name.lower()), "—")
        if present and len(dates) == len(present):
            kind, summary = "дата", _period(dates)
            gaps = _month_gaps(dates)
            if gaps:
                issues.append(f"«{name}»: пропущенные месяцы {', '.join(gaps[:6])}{'…' if len(gaps) > 6 else ''}")
        elif present and len(numbers) == len(present):
            kind = "число"
            summary = (f"мин {min(numbers):g} · медиана {statistics.median(numbers):g} · макс {max(numbers):g} · "
                       f"сумма {sum(numbers):g}")
            if unit.startswith("доля") and max(numbers) > 1 and min(numbers) >= 0:
                issues.append(f"«{name}»: доля больше 1 — проценты или доли? уточнить единицы")
            if any(n < 0 for n in numbers) and unit in ("рубли", "доллары", "тысячи", "миллионы"):
                issues.append(f"«{name}»: отрицательные значения в денежной колонке")
        else:
            kind = "текст" if not numbers else f"смешанный ({len(numbers)} чисел из {len(present)})"
            summary = f"уникальных {len(set(present))}"
            if numbers:
                issues.append(f"«{name}»: смешаны числа и текст — проверить формат")
        if missing:
            share = missing / len(values) if values else 0
            if share > 0.05:
                issues.append(f"«{name}»: пропуски {missing} из {len(values)} ({share:.0%})")
        out.append(f"| {name} | {kind} | {missing} | {unit} | {summary} |")
    out += ["", "## Что проверить перед выводами"]
    out += [f"- {i}" for i in issues] or ["- Явных проблем не найдено. Единицы и определения показателей всё равно сверить с источником."]
    return "\n".join(out)


def _period(dates: list[str]) -> str:
    return f"с {min(dates)} по {max(dates)} ({len(set(dates))} уникальных)"


def _month_gaps(dates: list[str]) -> list[str]:
    months = sorted({d[:7] for d in dates})
    if len(months) < 3:
        return []
    year, month = map(int, months[0].split("-"))
    gaps = []
    while f"{year:04d}-{month:02d}" <= months[-1]:
        key = f"{year:04d}-{month:02d}"
        if key not in months:
            gaps.append(key)
        month += 1
        if month > 12:
            year, month = year + 1, 1
    return gaps
