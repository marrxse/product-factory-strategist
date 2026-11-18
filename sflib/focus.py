"""Синтетическая фокус-группа: карта возражений на десятках ИИ-персон — без прогноза спроса.

Персоны создаёт код (воспроизводимо, по сегментам и зерну), а не модель: так разнообразие не зависит от того,
что модель «считает типичным». Отвечают субагенты respondent, которые не знают наших гипотез.
Итог — частоты стоп-факторов «×N из M персон» и их формулировки: это список того, что проверить на реальных людях.
Доли «купят / не купят» не считаются намеренно: синтетика не доказывает спрос (задание, AGENTS.md §4).
"""
from __future__ import annotations

import csv
import json
import random
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .paths import SfError

BATCH = 10                       # персон в одном вызове субагента
MIN_PERSONAS, MAX_PERSONAS = 10, 200
OTHER = "другое"
ATTRS = ("age", "income", "phone_skill", "habit", "attitude", "situation")
ATTR_TITLES = {"age": "возраст", "income": "доход", "phone_skill": "уверенность с телефоном", "habit": "привычка",
               "attitude": "отношение", "situation": "ситуация"}


@dataclass(frozen=True)
class Persona:
    id: str
    segment: str
    age: int
    income: str
    phone_skill: str
    habit: str
    attitude: str
    situation: str


def load_spec(path: Path) -> dict:
    if not path.exists():
        raise SfError(f"Нет файла {path} — образец: knowledge/synthetic-focus-group.md, раздел «Спецификация»")
    spec = tomllib.loads(path.read_text(encoding="utf-8"))
    focus = spec.get("focus", {})
    for key in ("stimulus", "concerns"):
        if not focus.get(key):
            raise SfError(f"В [focus] нет «{key}»")
    segments = spec.get("segments", [])
    if not segments:
        raise SfError("Нет ни одного [[segments]]")
    for seg in segments:
        missing = [k for k in ("name", "share", "age", *ATTRS[1:]) if k not in seg]
        if missing:
            raise SfError(f"Сегмент «{seg.get('name', '?')}»: нет полей {', '.join(missing)}")
    total = sum(float(s["share"]) for s in segments)
    if abs(total - 1) > 0.01:
        raise SfError(f"Доли сегментов в сумме {total:.2f}, а нужно 1")
    n = int(focus.get("n", 60))
    if not MIN_PERSONAS <= n <= MAX_PERSONAS:
        raise SfError(f"n = {n}: допустимо {MIN_PERSONAS}–{MAX_PERSONAS}")
    return spec


def personas(spec: dict) -> list[Persona]:
    """Детерминированно: то же зерно — те же персоны. Число в сегменте пропорционально доле."""
    focus, segments = spec["focus"], spec["segments"]
    n, rng = int(focus.get("n", 60)), random.Random(int(focus.get("seed", 1)))
    counts = [round(n * float(s["share"])) for s in segments]
    counts[-1] += n - sum(counts)
    result = []
    for seg, count in zip(segments, counts):
        low, high = seg["age"]
        for _ in range(count):
            result.append(Persona(f"P{len(result) + 1:03d}", seg["name"], rng.randint(int(low), int(high)),
                                  *(rng.choice(seg[a]) for a in ATTRS[1:])))
    return result


def card(p: Persona) -> str:
    return (f"{p.id} · {p.segment}: {p.age} лет; доход — {p.income}; с телефоном — {p.phone_skill}; "
            f"привычка — {p.habit}; отношение — {p.attitude}; ситуация — {p.situation}")


def batch_prompts(spec: dict, people: list[Persona]) -> list[str]:
    """Задания для субагента respondent: без наших гипотез и вариантов — только предложение, которое увидит человек."""
    focus = spec["focus"]
    codes = "; ".join(focus["concerns"]) + f"; {OTHER}"
    head = ("Ты отвечаешь по очереди за каждого человека из списка — каждый раз заново, как будто других не было. "
            "Ты не знаешь, чего хотят авторы предложения, и не пытаешься им угодить. Люди разные: многим всё равно, "
            "многие не поняли, кто-то против. Не придумывай статистику.\n\n"
            f"Предложение, которое человек увидел:\n«{focus['stimulus']}»\n\n"
            "Для каждого человека выведи ровно одну строку JSON без пояснений:\n"
            '{"id": "P…", "retell": "как он пересказал бы предложение своими словами", '
            '"stop": ["до двух кодов из списка"], "stop_text": "что его смущает или остановит, его словами", '
            '"condition": "что должно быть правдой, чтобы он попробовал (или «ничего»)"}\n'
            f"Коды стоп-факторов: {codes}. Если ничего не смущает — \"stop\": [].\n\nЛюди:\n")
    return [head + "\n".join(card(p) for p in people[i:i + BATCH]) for i in range(0, len(people), BATCH)]


def write_setup(project: Path, spec_path: Path) -> tuple[Path, list[Path]]:
    spec = load_spec(spec_path)
    people = personas(spec)
    out = project / "state" / "focus"
    out.mkdir(parents=True, exist_ok=True)
    table = out / "personas.csv"
    with table.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "segment", *ATTRS])
        for p in people:
            writer.writerow([p.id, p.segment, p.age, p.income, p.phone_skill, p.habit, p.attitude, p.situation])
    prompts = []
    for i, text in enumerate(batch_prompts(spec, people), start=1):
        path = out / f"batch-{i:02d}.md"
        path.write_text(f"<!-- СИНТЕТИКА: задание для субагента respondent -->\n{text}\n", encoding="utf-8")
        prompts.append(path)
    return table, prompts


def read_responses(path: Path, known_ids: set[str], codes: list[str]) -> tuple[list[dict], list[str]]:
    """Строки JSON из ответов субагентов. Неразборчивые и чужие строки не теряются молча — возвращаются как проблемы."""
    if not path.exists():
        raise SfError(f"Нет файла ответов {path}")
    allowed, rows, problems, seen = set(codes) | {OTHER}, [], [], set()
    for num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip().strip(",")
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            problems.append(f"строка {num}: не JSON")
            continue
        pid = row.get("id", "")
        if pid not in known_ids:
            problems.append(f"строка {num}: неизвестная персона «{pid}»")
            continue
        if pid in seen:
            problems.append(f"строка {num}: повтор {pid} — берём первый ответ")
            continue
        seen.add(pid)
        stop = [c.strip().lower() for c in row.get("stop", []) if str(c).strip()][:2]
        row["stop"] = [c if c in allowed else OTHER for c in stop]
        rows.append(row)
    missing = sorted(known_ids - seen)
    if missing:
        problems.append(f"нет ответов: {', '.join(missing[:10])}" + (" …" if len(missing) > 10 else ""))
    return rows, problems


def objection_map(project: Path, spec_path: Path, responses: Path) -> str:
    spec = load_spec(spec_path)
    people = {p.id: p for p in personas(spec)}
    codes = [c.lower() for c in spec["focus"]["concerns"]]
    rows, problems = read_responses(responses, set(people), codes)
    if not rows:
        raise SfError("Нет ни одного разборчивого ответа — карту строить не из чего.")
    m = len(rows)
    segments = sorted({p.segment for p in people.values()})
    lines = ["<!-- СИНТЕТИКА — не данные о реальных людях. Карта показывает, ЧТО проверить, а не СКОЛЬКО людей так думает. -->",
             "# Синтетическая фокус-группа: карта возражений", "",
             f"Персон с ответом: {m} из {len(people)} (сегменты: {', '.join(segments)}; зерно {spec['focus'].get('seed', 1)}).",
             "Частота — среди ИИ-персон, а не людей: она ранжирует возражения для проверки, но не измеряет спрос "
             "и не переносится на рынок.", "",
             "## Стоп-факторы", "",
             "| Стоп-фактор | Персон | " + " | ".join(segments) + " | Как сказали |",
             "|---|---|" + "---|" * len(segments) + "---|"]
    ranked = sorted({c for r in rows for c in r["stop"]}, key=lambda c: -sum(c in r["stop"] for r in rows))
    for code in ranked:
        hit = [r for r in rows if code in r["stop"]]
        by_seg = [str(sum(people[r["id"]].segment == s for r in hit)) for s in segments]
        quotes = " / ".join(f"«{r.get('stop_text', '')[:90]}»" for r in hit[:2])
        lines.append(f"| {code} | ×{len(hit)} из {m} | " + " | ".join(by_seg) + f" | {quotes} |")
    calm = sum(1 for r in rows if not r["stop"])
    lines += ["", f"Без стоп-факторов: {calm} из {m} персон — они не назвали возражений; это не прогноз покупок.", "",
              "## Условия, при которых персоны готовы попробовать (выборка)", ""]
    lines += [f"- {r['id']} ({people[r['id']].segment}): {r.get('condition', '')[:160]}" for r in rows[:8]]
    lines += ["", "## Как поняли предложение (выборка пересказов — искать неверное понимание)", ""]
    lines += [f"- {r['id']}: «{r.get('retell', '')[:160]}»" for r in rows[:: max(1, m // 8)][:8]]
    if problems:
        lines += ["", "## Проблемы с ответами", ""] + [f"- {p}" for p in problems]
    lines += ["", "## Что делать дальше",
              "Три самых частых стоп-фактора — в гайд реальных интервью и тест понимания на 5–8 людях; "
              "в стратегии — только с меткой [СИНТ S…] и как гипотеза."]
    return "\n".join(lines) + "\n"
