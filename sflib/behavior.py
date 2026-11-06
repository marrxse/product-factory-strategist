"""Анализ поведения клиентов: воспроизводимые расчёты по журналу событий и по таблице оттока.

events: проверка данных, удержание по когортам, активация, поведенческие сегменты (RFM), путь к целевому действию.
churn:  доля ушедших по каждому признаку с 95% интервалом Уилсона и признаки с наибольшим разрывом.
Только стандартная библиотека; выводы делает агент со ссылкой на отчёт (это корреляции, а не причины).
"""
from __future__ import annotations

import csv
import hashlib
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .paths import SfError

Z95 = 1.96
MIN_GROUP = 30            # меньше — доля слишком шумная, в рейтинг признаков не идёт
NUMERIC_LEVELS = 12       # больше разных чисел — признак режется на квартили
TOP_PATHS = 5
MISSING = {"", "na", "n/a", "null", "none", "nan", "-", "—"}


@dataclass(frozen=True)
class Event:
    user: str
    day: date
    name: str
    value: float


def wilson(successes: int, total: int) -> tuple[float, float]:
    """95% интервал доли (метод Уилсона) — корректен и для маленьких групп и долей у 0 или 1."""
    if total == 0:
        return 0.0, 0.0
    p = successes / total
    denom = 1 + Z95 ** 2 / total
    centre = (p + Z95 ** 2 / (2 * total)) / denom
    half = Z95 * math.sqrt(p * (1 - p) / total + Z95 ** 2 / (4 * total ** 2)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def _read(path: Path) -> tuple[list[dict], list[str], str]:
    if not path.is_file():
        raise SfError(f"Нет файла {path}")
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig", errors="replace")
    sample = text[:4096]
    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t") if sample.strip() else csv.excel
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    rows = [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in reader]
    return rows, [c.strip() for c in reader.fieldnames or []], hashlib.sha1(raw).hexdigest()[:10]


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _ci(succ: int, total: int) -> str:
    low, high = wilson(succ, total)
    return f"{_pct(succ / total) if total else '—'} [{_pct(low)}–{_pct(high)}]"


def _header(title: str, path: Path, sha: str, command: str) -> list[str]:
    return [f"# {title}", "", f"- Данные: `{path.name}` (sha1 {sha})", f"- Расчёт: `{command}` — повторный запуск даёт те же числа",
            f"- Дата расчёта: {date.today().isoformat()}", ""]


# ---------- журнал событий ----------

def parse_events(rows: list[dict], columns: list[str]) -> tuple[list[Event], dict[str, int]]:
    need = {"user_id", "date", "event"}
    if not need <= set(columns):
        raise SfError(f"Нужны колонки user_id, date, event (есть: {', '.join(columns)})")
    problems = Counter()
    events, seen = [], set()
    for row in rows:
        if any(row.get(c, "").lower() in MISSING for c in need):
            problems["пропуск в user_id/date/event"] += 1
            continue
        try:
            day = date.fromisoformat(row["date"][:10])
        except ValueError:
            problems["дата не в формате ГГГГ-ММ-ДД"] += 1
            continue
        key = (row["user_id"], row["date"], row["event"], row.get("value", ""))
        if key in seen:
            problems["полный дубль строки"] += 1
            continue
        seen.add(key)
        try:
            value = float(row.get("value", "") or 0)
        except ValueError:
            problems["value не число"] += 1
            value = 0.0
        events.append(Event(row["user_id"], day, row["event"], value))
    if not events:
        raise SfError("После проверки не осталось ни одного события.")
    return sorted(events, key=lambda e: (e.user, e.day)), dict(problems)


def _month(d: date) -> tuple[int, int]:
    return d.year, d.month


def _months_between(a: tuple[int, int], b: tuple[int, int]) -> int:
    return (b[0] - a[0]) * 12 + b[1] - a[1]


def cohort_retention(events: list[Event]) -> tuple[dict[tuple[int, int], dict[int, float | None]], dict[tuple[int, int], int], bool]:
    """Доля когорты (месяц первого события), активной в месяц k. None — месяц ещё не наблюдали целиком."""
    first: dict[str, date] = {}
    active: dict[str, set[tuple[int, int]]] = defaultdict(set)
    for e in events:
        first.setdefault(e.user, e.day)
        active[e.user].add(_month(e.day))
    last_day = max(e.day for e in events)
    last_month = _month(last_day)
    next_day = date.fromordinal(last_day.toordinal() + 1)
    last_month_complete = next_day.month != last_day.month
    cohorts: dict[tuple[int, int], list[str]] = defaultdict(list)
    for user, day in first.items():
        cohorts[_month(day)].append(user)
    table: dict[tuple[int, int], dict[int, float | None]] = {}
    for cohort, users in sorted(cohorts.items()):
        horizon = _months_between(cohort, last_month)
        row: dict[int, float | None] = {}
        for k in range(horizon + 1):
            month = ((cohort[0] * 12 + cohort[1] - 1 + k) // 12, (cohort[1] - 1 + k) % 12 + 1)
            incomplete = month == last_month and not last_month_complete
            share = sum(month in active[u] for u in users) / len(users)
            row[k] = None if incomplete else share
        table[cohort] = row
    return table, {c: len(u) for c, u in cohorts.items()}, last_month_complete


def activation(events: list[Event], name: str, window: int) -> tuple[int, int]:
    first: dict[str, date] = {}
    done: set[str] = set()
    for e in events:
        first.setdefault(e.user, e.day)
        if e.name == name and (e.day - first[e.user]).days <= window:
            done.add(e.user)
    return len(done), len(first)


def segments(events: list[Event], risk_days: int) -> dict[str, list[tuple[int, int, float]]]:
    """Сегменты по действиям на дату конца данных: (давность, частота дней, сумма) для каждого клиента."""
    end = max(e.day for e in events)
    days: dict[str, set[date]] = defaultdict(set)
    money: dict[str, float] = defaultdict(float)
    first: dict[str, date] = {}
    for e in events:
        days[e.user].add(e.day)
        money[e.user] += e.value
        first.setdefault(e.user, e.day)
    result: dict[str, list[tuple[int, int, float]]] = defaultdict(list)
    for user, active_days in days.items():
        recency = (end - max(active_days)).days
        frequency = len(active_days)
        age = (end - first[user]).days
        if age <= risk_days:
            name = "новые"
        elif recency > 3 * risk_days:
            name = "спящие"
        elif recency > risk_days:
            name = "под риском ухода" if frequency >= 2 else "разовые"
        else:
            name = "активные" if frequency >= 2 else "разовые"
        result[name].append((recency, frequency, money[user]))
    return result


def target_path(events: list[Event], target: str) -> tuple[int, int, float | None, Counter]:
    by_user: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        by_user[e.user].append(e)
    reached, lags, before = 0, [], Counter()
    for user_events in by_user.values():
        idx = next((i for i, e in enumerate(user_events) if e.name == target), None)
        if idx is None:
            continue
        reached += 1
        lags.append((user_events[idx].day - user_events[0].day).days)
        if idx > 0:
            before[user_events[idx - 1].name] += 1
    median = statistics.median(lags) if lags else None
    return reached, len(by_user), median, before


def events_report(path: Path, activation_event: str | None, target: str | None, window: int, risk_days: int) -> str:
    rows, columns, sha = _read(path)
    events, problems = parse_events(rows, columns)
    users = {e.user for e in events}
    command = f"sf.py behavior events {path.name}" + (f" --activation {activation_event}" if activation_event else "") + \
              (f" --target {target}" if target else "") + f" --window {window} --risk-days {risk_days}"
    out = _header("Поведение клиентов: журнал событий", path, sha, command)
    out += ["## Проверка данных", f"- Строк: {len(rows)}; принято событий: {len(events)}; клиентов: {len(users)}",
            f"- Период: {min(e.day for e in events)} — {max(e.day for e in events)}",
            "- Виды событий: " + ", ".join(f"{n} ({c})" for n, c in Counter(e.name for e in events).most_common())]
    out += [f"- Отброшено: {name} — {count}" for name, count in problems.items()] or ["- Отброшенных строк нет"]
    table, sizes, complete = cohort_retention(events)
    horizon = max((len(r) for r in table.values()), default=0)
    out += ["", "## Удержание по когортам", "Доля когорты (месяц первого события), активной в месяц k. «…» — месяц наблюдался не целиком; такие ячейки не сравнивать.",
            "", "| Когорта | Размер | " + " | ".join(f"M{k}" for k in range(horizon)) + " |", "|---|---|" + "---|" * horizon]
    for cohort, row in table.items():
        cells = ["…" if row.get(k) is None and k in row else (_pct(row[k]) if k in row else "") for k in range(horizon)]
        out.append(f"| {cohort[0]}-{cohort[1]:02d} | {sizes[cohort]} | " + " | ".join(cells) + " |")
    if not complete:
        out.append("\nПоследний месяц данных неполный — его доли занижены и помечены «…».")
    small = [f"{c[0]}-{c[1]:02d}" for c, n in sizes.items() if n < MIN_GROUP]
    if small:
        out.append(f"\nКогорты меньше {MIN_GROUP} клиентов ({', '.join(small)}) — доли шумные, выводы по ним не делать.")
    if activation_event:
        done, total = activation(events, activation_event, window)
        out += ["", "## Активация", f"Совершили «{activation_event}» в первые {window} дней: {done} из {total} — {_ci(done, total)} (95% интервал)."]
    segs = segments(events, risk_days)
    out += ["", "## Поведенческие сегменты (на дату конца данных)",
            f"Правила: новые — первое событие не раньше {risk_days} дней назад; активные — действовали за последние {risk_days} дней не меньше двух дней; "
            f"под риском ухода — были активны, но молчат {risk_days}–{3 * risk_days} дней; спящие — молчат дольше {3 * risk_days} дней; разовые — один день активности.",
            "", "| Сегмент | Клиентов | Доля | Медиана давности, дн | Медиана частоты, дн | Сумма value |", "|---|---|---|---|---|---|"]
    for name in ("новые", "активные", "под риском ухода", "разовые", "спящие"):
        members = segs.get(name, [])
        if members:
            out.append(f"| {name} | {len(members)} | {_pct(len(members) / len(users))} | {statistics.median(m[0] for m in members):g} | "
                       f"{statistics.median(m[1] for m in members):g} | {sum(m[2] for m in members):g} |")
    if target:
        reached, total, median, before = target_path(events, target)
        out += ["", "## Путь к целевому действию", f"Дошли до «{target}»: {reached} из {total} — {_ci(reached, total)}."]
        if median is not None:
            out.append(f"Медиана дней от первого события до цели: {median:g}.")
        if before:
            out.append("Чаще всего непосредственно перед целью: " + ", ".join(f"{n} ({c})" for n, c in before.most_common(TOP_PATHS)) +
                       ". Это последовательность, а не причина.")
    out += ["", "## Как читать", "- Доли с интервалами: пересекающиеся интервалы — различие может быть случайным.",
            "- Это наблюдаемое поведение; почему люди так действуют — гипотеза (навык behavior-analysis), проверяется экспериментом или интервью."]
    return "\n".join(out) + "\n"


# ---------- таблица оттока ----------

def _numeric(values: list[str]) -> list[float] | None:
    try:
        return [float(v.replace(",", ".")) for v in values]
    except ValueError:
        return None


def _levels(column: str, rows: list[dict]) -> tuple[list[str], str] | None:
    """Значение уровня для каждой строки: категория или квартиль числа. None — признак-идентификатор."""
    values = [r.get(column, "") for r in rows]
    present = [v for v in values if v.lower() not in MISSING]
    distinct = set(present)
    numbers = _numeric(present)
    if numbers is not None and len(distinct) > NUMERIC_LEVELS:
        cuts = statistics.quantiles(numbers, n=4)
        def label(v: str) -> str:
            if v.lower() in MISSING:
                return "пропуск"
            x = float(v.replace(",", "."))
            q = sum(x > c for c in cuts)
            bounds = [min(numbers), *cuts, max(numbers)]
            return f"Q{q + 1}: {bounds[q]:g}–{bounds[q + 1]:g}"
        return [label(v) for v in values], "квартили"
    if len(distinct) > max(NUMERIC_LEVELS * 4, len(rows) // 2):
        return None
    return [v if v.lower() not in MISSING else "пропуск" for v in values], "категории"


def filter_rows(rows: list[dict], where: str | None) -> list[dict]:
    """Одно условие «колонка=значение» или «колонка!=значение» — сравнивать сопоставимых клиентов."""
    if not where:
        return rows
    negate = "!=" in where
    column, _, value = where.partition("!=" if negate else "=")
    column, value = column.strip(), value.strip()
    if not column or column not in rows[0]:
        raise SfError(f"Условие --where «{where}»: нет такой колонки.")
    kept = [r for r in rows if (r[column] != value) == negate]
    if not kept:
        raise SfError(f"Условию «{where}» не соответствует ни одна строка.")
    return kept


def churn_report(path: Path, target: str, positive: str, skip: list[str], within: str | None = None,
                 where: str | None = None) -> str:
    rows, columns, sha = _read(path)
    total_rows = len(rows)
    rows = filter_rows(rows, where)
    if target not in columns:
        raise SfError(f"Нет колонки «{target}» (есть: {', '.join(columns)})")
    flags = [r[target] == positive for r in rows]
    if not any(flags):
        raise SfError(f"Ни одной строки со значением «{positive}» в «{target}».")
    base, n = sum(flags), len(rows)
    command = f"sf.py behavior churn {path.name} --target {target} --positive {positive}" + (f" --skip {','.join(skip)}" if skip else "") + \
              (f" --within {within}" if within else "") + (f' --where "{where}"' if where else "")
    if within and within not in columns:
        raise SfError(f"Нет колонки «{within}» для --within.")
    out = _header("Поведение клиентов: кто уходит", path, sha, command)
    out += ["## Проверка данных", f"- Клиентов: {n}" + (f" из {total_rows} (условие: {where})" if where else "") + f"; признаков: {len(columns) - 1}",
            f"- Ушли («{target}» = {positive}): {base} — {_ci(base, n)} (95% интервал)"]
    features, tables, skipped = [], [], []
    for column in columns:
        if column == target or column in skip:
            continue
        parsed = _levels(column, rows)
        if parsed is None:
            skipped.append(column)
            continue
        labels, kind = parsed
        groups: dict[str, list[bool]] = defaultdict(list)
        for label, flag in zip(labels, flags):
            groups[label].append(flag)
        stats = sorted(((lvl, len(g), sum(g)) for lvl, g in groups.items()), key=lambda x: -x[2] / x[1])
        solid = [(lvl, size, churned) for lvl, size, churned in stats if size >= MIN_GROUP]
        if len(solid) >= 2:
            hi, lo = solid[0], solid[-1]
            features.append((hi[2] / hi[1] - lo[2] / lo[1], column, hi, lo))
        missing = sum(1 for lvl in labels if lvl == "пропуск")
        block = [f"### {column} ({kind}{f', пропусков {missing}' if missing else ''})", "| Значение | Клиентов | Доля ушедших [95% интервал] | К среднему |", "|---|---|---|---|"]
        block += [f"| {lvl} | {size} | {_ci(churned, size)} | {(churned / size) / (base / n):.2f}× |" for lvl, size, churned in stats]
        tables.append("\n".join(block))
    if skipped:
        out.append(f"- Пропущены как идентификаторы (почти все значения разные): {', '.join(skipped)}")
    out += ["", "## Признаки с наибольшим разрывом в оттоке",
            f"Разрыв = доля ушедших в худшей группе минус в лучшей (только группы от {MIN_GROUP} клиентов).", "",
            "| Признак | Разрыв | Где уходят чаще | Где реже |", "|---|---|---|---|"]
    for gap, column, hi, lo in sorted(features, reverse=True):
        out.append(f"| {column} | {gap * 100:.1f} п. п. | {hi[0]}: {_ci(hi[2], hi[1])} | {lo[0]}: {_ci(lo[2], lo[1])} |")
    if within:
        out += _stratified(rows, flags, columns, target, skip, within)
    out += ["", "## Доли по каждому признаку", *tables, "", "## Как читать",
            "- Это связь признака с уходом, а не причина: признаки связаны между собой (например, срок жизни и тип договора).",
            "- Причину проверяет эксперимент; механизм (почему уходят) — гипотеза навыка behavior-analysis."]
    return "\n".join(out) + "\n"


def _stratified(rows: list[dict], flags: list[bool], columns: list[str], target: str, skip: list[str], within: str) -> list[str]:
    """Сохраняется ли разрыв внутри групп контрольного признака — грубая проверка на смешение факторов."""
    control = _levels(within, rows)
    if control is None:
        raise SfError(f"«{within}» похож на идентификатор — по нему нельзя разбить на группы.")
    strata = control[0]
    out = ["", f"## Разрыв внутри групп «{within}»",
           f"Если разрыв признака держится внутри каждой группы «{within}», он не объясняется только этим признаком. "
           f"Пусто — в группе меньше двух значений по {MIN_GROUP}+ клиентов.", ""]
    names = sorted(set(strata))
    out += ["| Признак | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for column in columns:
        if column in (target, within, *skip):
            continue
        parsed = _levels(column, rows)
        if parsed is None:
            continue
        cells = []
        for stratum in names:
            groups: dict[str, list[bool]] = defaultdict(list)
            for label, flag, st in zip(parsed[0], flags, strata):
                if st == stratum:
                    groups[label].append(flag)
            rates = sorted((sum(g) / len(g), lvl) for lvl, g in groups.items() if len(g) >= MIN_GROUP)
            cells.append(f"{(rates[-1][0] - rates[0][0]) * 100:.1f} п. п. ({rates[-1][1]} > {rates[0][1]})" if len(rates) >= 2 else "")
        out.append(f"| {column} | " + " | ".join(cells) + " |")
    return out
