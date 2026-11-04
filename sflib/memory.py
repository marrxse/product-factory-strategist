"""Память между проектами memory/memory.csv: записи с автором, датой, статусом, основанием; исправление и отзыв.

Запись агента — «наблюдение агента от даты на основании …», а не факт. Исправление создаёт новую запись
и помечает старую «исправлена» со ссылкой; отзыв помечает «отозвана» с причиной. Ничего не удаляется.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, fields, replace
from datetime import date
from pathlib import Path

from . import kb, paths
from .paths import SfError

ACTIVE, CORRECTED, REVOKED = "действует", "исправлена", "отозвана"
KINDS = ("наблюдение агента", "решение человека", "предпочтение человека", "урок процесса")
AUTHORS = ("agent", "human")


@dataclass(frozen=True)
class Entry:
    id: str
    date: str
    author: str
    kind: str
    status: str
    text: str
    basis: str
    replaced_by: str = ""
    reason: str = ""


FIELDS = [f.name for f in fields(Entry)]


def path() -> Path:
    return paths.repo_root() / "memory" / "memory.csv"


def load() -> list[Entry]:
    p = path()
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as handle:
        return [Entry(**{k: (row.get(k) or "").strip() for k in FIELDS}) for row in csv.DictReader(handle)]


def _save(entries: list[Entry]) -> None:
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(asdict(e) for e in entries)


def _next_id(entries: list[Entry]) -> str:
    return f"M{max((int(e.id[1:]) for e in entries if e.id[1:].isdigit()), default=0) + 1}"


def add(text: str, basis: str, author: str = "agent", kind: str = "наблюдение агента") -> Entry:
    if author not in AUTHORS:
        raise SfError(f"author: {', '.join(AUTHORS)}")
    if kind not in KINDS:
        raise SfError(f"kind: {', '.join(KINDS)}")
    if not text.strip():
        raise SfError("Пустая запись.")
    if author == "agent" and not basis.strip():
        raise SfError("Запись агента без основания не принимается: укажите проект и ID (например demo/C2, E5).")
    entries = load()
    entry = Entry(_next_id(entries), date.today().isoformat(), author, kind, ACTIVE, text.strip(), basis.strip())
    _save([*entries, entry])
    return entry


def _find(entries: list[Entry], entry_id: str) -> Entry:
    found = next((e for e in entries if e.id == entry_id), None)
    if found is None:
        raise SfError(f"Нет записи {entry_id}.")
    if found.status != ACTIVE:
        raise SfError(f"{entry_id} уже {found.status}" + (f" (заменена {found.replaced_by})" if found.replaced_by else ""))
    return found


def correct(entry_id: str, new_text: str, reason: str, author: str = "human") -> Entry:
    if not reason.strip():
        raise SfError("Укажите причину исправления.")
    entries = load()
    old = _find(entries, entry_id)
    new = Entry(_next_id(entries), date.today().isoformat(), author, old.kind, ACTIVE, new_text.strip(),
                f"{old.basis}; исправление {old.id}", reason="")
    updated = [replace(e, status=CORRECTED, replaced_by=new.id, reason=reason.strip()) if e.id == old.id else e for e in entries]
    _save([*updated, new])
    return new


def revoke(entry_id: str, reason: str) -> Entry:
    if not reason.strip():
        raise SfError("Укажите причину отзыва.")
    entries = load()
    old = _find(entries, entry_id)
    revoked = replace(old, status=REVOKED, reason=reason.strip())
    _save([revoked if e.id == old.id else e for e in entries])
    return revoked


def describe(entry: Entry) -> str:
    who = "Наблюдение агента" if entry.author == "agent" else "Запись человека"
    head = f"{entry.id} · {who} от {entry.date} · {entry.kind} · {entry.status}"
    tail = f" → заменена {entry.replaced_by}" if entry.replaced_by else ""
    reason = f" (причина: {entry.reason})" if entry.reason else ""
    return f"{head}{tail}{reason}\n  {entry.text}\n  основание: {entry.basis or '—'}"


def search(query: str, include_inactive: bool = False, limit: int = 5) -> list[Entry]:
    """Поиск по основам слов и синонимам базы знаний; действующие записи выше."""
    wanted = kb.stems(query)
    wanted |= kb.expand(wanted, kb.synonym_groups())
    scored = []
    for entry in load():
        if entry.status != ACTIVE and not include_inactive:
            continue
        hits = len(kb.stems(entry.text + " " + entry.kind + " " + entry.basis) & wanted)
        if hits:
            scored.append((hits + (1 if entry.status == ACTIVE else 0), entry))
    return [e for _, e in sorted(scored, key=lambda t: -t[0])[:limit]]
