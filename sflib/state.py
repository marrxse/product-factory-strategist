"""STATE.md: машинно-управляемая таблица этапов + свободные разделы, которые ведёт агент."""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from . import stages as st

BEGIN = "<!-- sf:stages -->"
END = "<!-- /sf:stages -->"
ROW_RE = re.compile(r"^\| (\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$")
HEADER = "| № | Этап | Статус | Ворота | Обновлено |\n|---|------|--------|--------|-----------|"


@dataclass(frozen=True)
class Row:
    num: int
    title: str
    status: str
    gate: str
    updated: str


def initial_rows() -> list[Row]:
    today = date.today().isoformat()
    return [
        Row(s.num, s.title, st.NOT_STARTED, st.GATE_PENDING if s.has_gate else st.NO_GATE, today)
        for s in st.STAGES
    ]


def render_block(rows: list[Row]) -> str:
    body = "\n".join(f"| {r.num} | {r.title} | {r.status} | {r.gate} | {r.updated} |" for r in rows)
    return f"{BEGIN}\n{HEADER}\n{body}\n{END}"


def parse_rows(text: str) -> list[Row]:
    if BEGIN not in text or END not in text:
        raise ValueError("В STATE.md нет блока этапов (<!-- sf:stages -->). Восстановите из templates/project/state/STATE.md.")
    block = text.split(BEGIN, 1)[1].split(END, 1)[0]
    rows = []
    for line in block.strip().splitlines():
        match = ROW_RE.match(line.strip())
        if match:
            num, title, status, gate, updated = (part.strip() for part in match.groups())
            rows.append(Row(int(num), title, status, gate, updated))
    return rows


def replace_block(text: str, rows: list[Row]) -> str:
    head, rest = text.split(BEGIN, 1)
    tail = rest.split(END, 1)[1]
    return head + render_block(rows) + tail


def update_row(rows: list[Row], num: int, **changes: str) -> list[Row]:
    if not any(r.num == num for r in rows):
        raise ValueError(f"В таблице этапов нет этапа {num}.")
    stamp = {"updated": date.today().isoformat()}
    return [replace(r, **changes, **stamp) if r.num == num else r for r in rows]


def current_stage(rows: list[Row]) -> Row | None:
    """Первый этап (кроме пересмотра), который ещё не готов."""
    for row in rows:
        if row.num != 8 and row.status != st.DONE:
            return row
    return None


def section(text: str, heading: str) -> str:
    """Содержимое раздела `## heading` до следующего `## `."""
    pattern = re.compile(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_rows(path: Path, rows: list[Row]) -> None:
    path.write_text(replace_block(read(path), rows), encoding="utf-8")
