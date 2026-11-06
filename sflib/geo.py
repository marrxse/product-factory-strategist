"""Канал «ответы нейросетей» (GEO): что ИИ-ассистенты отвечают на вопросы покупателей о категории.

Вход — файлы sources/geo/<ассистент>-<ГГГГ-ММ-ДД>.md с разделами «## Q<n>: <вопрос>» и текстом ответа под ними
(ответы сохраняет человек или агент; ассистент и дата — в имени файла). Расчёт детерминированный:
доля ответов с упоминанием бренда, порядок первого упоминания, на какие сайты ссылаются, рискованные утверждения.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .paths import SfError

QUESTION_RE = re.compile(r"^##\s*(Q\d+)\s*[:.]\s*(.+)$", re.MULTILINE)
URL_RE = re.compile(r"https?://[^\s)\]>»\"']+")
FILE_RE = re.compile(r"^(?P<assistant>.+)-(?P<date>\d{4}-\d{2}-\d{2})\.md$")


@dataclass(frozen=True)
class Answer:
    assistant: str
    day: str
    qid: str
    question: str
    text: str


def parse_brands(spec: str) -> dict[str, tuple[str, ...]]:
    """«МТС=МТС|MTS; МегаФон=МегаФон|Мегафон» → {бренд: (варианты написания)}."""
    brands = {}
    for part in (p.strip() for p in spec.split(";") if p.strip()):
        name, _, aliases = part.partition("=")
        variants = tuple(a.strip() for a in (aliases or name).split("|") if a.strip())
        if not name.strip() or not variants:
            raise SfError(f"Не понял бренд «{part}». Формат: Бренд=вариант1|вариант2; Другой=…")
        brands[name.strip()] = variants
    if not brands:
        raise SfError("Укажите бренды: --brands \"МТС=МТС|MTS; МегаФон=МегаФон|Мегафон\"")
    return brands


def load(folder: Path) -> list[Answer]:
    if not folder.is_dir():
        raise SfError(f"Нет папки {folder} — сохраните ответы ассистентов в sources/geo/<ассистент>-<ГГГГ-ММ-ДД>.md")
    answers = []
    for path in sorted(folder.glob("*.md")):
        match = FILE_RE.match(path.name)
        if not match or path.name.startswith("questions"):
            continue
        text = path.read_text(encoding="utf-8")
        heads = list(QUESTION_RE.finditer(text))
        for i, head in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            answers.append(Answer(match["assistant"], match["date"], head.group(1), head.group(2).strip(),
                                  text[head.end():end].strip()))
    if not answers:
        raise SfError(f"В {folder} нет ответов в формате «## Q1: вопрос» в файлах <ассистент>-<дата>.md")
    return answers


def _first_position(text: str, variants: tuple[str, ...]) -> int | None:
    low = text.lower()
    hits = [low.find(v.lower()) for v in variants if v.lower() in low]
    return min(hits) if hits else None


def analyze(answers: list[Answer], brands: dict[str, tuple[str, ...]], risky: list[str]) -> str:
    assistants = sorted({a.assistant for a in answers})
    out = ["# Ответы нейросетей: что видит покупатель", "",
           f"- Ассистенты: {', '.join(assistants)}; ответов: {len(answers)}; вопросов: {len({a.qid for a in answers})}",
           f"- Даты сбора: {', '.join(sorted({a.day for a in answers}))} — ответы ассистентов меняются, вывод действует на эти даты", "",
           "## Упоминания брендов", "Доля ответов, где бренд упомянут, и как часто он назван первым среди упомянутых.", "",
           "| Бренд | " + " | ".join(assistants) + " | Всего | Назван первым |", "|---|" + "---|" * (len(assistants) + 2)]
    first_counter: Counter = Counter()
    per_answer: dict[tuple[str, str], list[str]] = {}
    for a in answers:
        plain = URL_RE.sub(" ", a.text)  # бренд в адресе ссылки — не упоминание в ответе
        positions = {b: p for b, v in brands.items() if (p := _first_position(plain, v)) is not None}
        ordered = sorted(positions, key=positions.get)
        per_answer[(a.assistant, a.qid)] = ordered
        if ordered:
            first_counter[ordered[0]] += 1
    for brand in brands:
        cells = []
        for name in assistants:
            own = [a for a in answers if a.assistant == name]
            hit = sum(brand in per_answer[(a.assistant, a.qid)] for a in own)
            cells.append(f"{hit} из {len(own)}")
        total = sum(brand in v for v in per_answer.values())
        out.append(f"| {brand} | " + " | ".join(cells) + f" | {total} из {len(answers)} | {first_counter[brand]} |")
    domains: Counter = Counter()
    for a in answers:
        for url in set(URL_RE.findall(a.text)):
            domains[urlparse(url).netloc.removeprefix("www.")] += 1
    out += ["", "## На какие сайты ссылаются ответы", "Здесь работает GEO: ассистенты пересказывают эти источники, а не только сайт бренда.", ""]
    out += [f"- {d} — в {n} ответах" for d, n in domains.most_common(15)] or ["- ссылок в ответах нет — ассистент не показал источники"]
    out += ["", "## Рискованные утверждения", "Фразы-маркеры, которые нужно сверить с фактами (неверное в ответах ИИ — повод для работы с источниками).", ""]
    flagged = []
    for a in answers:
        for marker in risky:
            for m in re.finditer(re.escape(marker), a.text, re.IGNORECASE):
                start = a.text.rfind(".", 0, m.start()) + 1
                end = a.text.find(".", m.end())
                flagged.append(f"- {a.assistant} {a.qid} «{marker}»: «{a.text[start:end if end > 0 else None].strip()[:220]}»")
                break
    out += flagged or ["- не найдено"]
    out += ["", "## Ответы по вопросам", "", "| Вопрос | " + " | ".join(assistants) + " |", "|---|" + "---|" * len(assistants)]
    questions: dict[str, str] = {}
    for a in answers:
        questions.setdefault(a.qid, a.question)
    for qid, question in sorted(questions.items(), key=lambda x: int(x[0][1:])):
        cells = [", ".join(per_answer.get((n, qid), [])) or "—" for n in assistants]
        out.append(f"| {qid}: {question} | " + " | ".join(cells) + " |")
    out += ["", "## Как читать", "- Это снимок ответов на дату сбора, не доля рынка и не мнение покупателей.",
            "- Нет упоминания — не значит «нас не знают»: значит, ассистент не нашёл нас в источниках, которые он читает."]
    return "\n".join(out) + "\n"
