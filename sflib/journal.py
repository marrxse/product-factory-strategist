"""Журнал действий log.md с ключами шагов: защита от незаметного повтора выполненных действий.

Формат строки: `- 2026-11-04 22:10:03 | DONE | collect:fetch:example.com | текст`
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

KINDS = ("START", "DONE", "FAIL", "SKIP", "NOTE", "STAGE", "GATE", "CORRECTION", "INJECTION", "REPEAT", "ROUTE")
LINE_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| ([A-Z]+) \| ([^|]*) \| (.*)$")
KEY_RE = re.compile(r"^[\w:./\-]+$", re.UNICODE)


@dataclass(frozen=True)
class Entry:
    ts: str
    kind: str
    key: str
    text: str


def normalize_key(key: str) -> str:
    norm = re.sub(r"\s+", "-", key.strip().lower())
    if not norm or not KEY_RE.match(norm):
        raise ValueError(f"Недопустимый ключ шага «{key}»: буквы, цифры и символы : . / - _")
    return norm


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def read_entries(log_path: Path) -> list[Entry]:
    if not log_path.exists():
        return []
    entries = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        match = LINE_RE.match(line)
        if match:
            entries.append(Entry(*(part.strip() for part in match.groups())))
    return entries


def append(log_path: Path, kind: str, key: str, text: str) -> Entry:
    if kind not in KINDS:
        raise ValueError(f"Неизвестный тип записи {kind}.")
    clean_text = " ".join(text.split()).replace("|", "/")
    entry = Entry(now(), kind, key, clean_text)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"- {entry.ts} | {entry.kind} | {entry.key} | {entry.text}\n")
    return entry


def last_status(entries: list[Entry], key: str) -> str | None:
    """Последний статус шага (START/DONE/FAIL/SKIP) или None, если шага не было."""
    step_kinds = {"START", "DONE", "FAIL", "SKIP", "REPEAT"}
    status = None
    for entry in entries:
        if entry.key == key and entry.kind in step_kinds:
            status = entry.kind
    return status


def unfinished(entries: list[Entry]) -> list[Entry]:
    """Шаги, начатые, но не завершённые (START/REPEAT/FAIL без последующего DONE/SKIP)."""
    latest: dict[str, Entry] = {}
    for entry in entries:
        if entry.kind in {"START", "DONE", "FAIL", "SKIP", "REPEAT"}:
            latest[entry.key] = entry
    return [entry for entry in latest.values() if entry.kind in {"START", "FAIL", "REPEAT"}]
