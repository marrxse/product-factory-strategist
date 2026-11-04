"""Воспроизводимая выборка утверждений для проверки субагентом verifier."""
from __future__ import annotations

import random
from pathlib import Path

from . import evidence as ev
from .markup import parse_outputs

KEY_FILES = ("decision-brief.md", "options.md", "product-strategy.md", "comms-strategy.md")


def build(project: Path, size: int, seed: int) -> str:
    """Все строки ключевых файлов с числами/цитатами-ссылками + случайная выборка остальных утверждений с E-ссылками."""
    records = ev.by_id(ev.load(project))
    lines = [l for l in parse_outputs(project) if any(r.startswith("E") for r in l.refs)]
    key = [l for l in lines if l.file in KEY_FILES and any(ch.isdigit() for ch in l.text.split("[")[0])]
    rest = [l for l in lines if l not in key]
    rng = random.Random(seed)
    picked = key + rng.sample(rest, min(size, len(rest)))
    out = [f"# Выборка утверждений для проверки (seed={seed}, ключевых с числами: {len(key)}, случайных: {len(picked) - len(key)})",
           "", "Для каждого: цитата есть в источнике? число совпадает? вывод следует из цитаты? Ответ: да / частично / нет + пояснение.", ""]
    for index, line in enumerate(picked, start=1):
        out.append(f"## {index}. {line.file}:{line.num}")
        out.append(f"Утверждение: {line.text.strip()}")
        for ref in line.refs:
            record = records.get(ref)
            if record is not None and ref.startswith("E"):
                out.append(f"- {ref}: «{record.quote}» — {record.source} ({record.locator or '—'})")
        out.append("- Вердикт: ")
        out.append("")
    return "\n".join(out)
