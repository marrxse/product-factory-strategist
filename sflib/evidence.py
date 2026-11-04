"""Реестр доказательств evidence.csv: добавить, показать, отозвать, проверить формат."""
from __future__ import annotations

import csv
import re
from dataclasses import asdict, dataclass, fields, replace
from datetime import date
from pathlib import Path

from .paths import SfError

KINDS = ("web", "doc", "table", "calc", "interview", "synthetic")
QUALITY = ("A", "B", "C")  # A — первичный/официальный, B — надёжный вторичный, C — слабый/пересказ
ACTIVE, REVOKED = "active", "revoked"
ID_RE = re.compile(r"^[ES]\d+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class Record:
    id: str
    status: str
    kind: str
    source: str
    locator: str
    accessed: str
    quote: str
    quality: str
    note: str = ""
    added_by: str = "agent"
    revoked_reason: str = ""


FIELDS = [f.name for f in fields(Record)]


def path_for(project: Path) -> Path:
    return project / "evidence.csv"


def load(project: Path) -> list[Record]:
    path = path_for(project)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise SfError(f"В evidence.csv нет колонок: {', '.join(sorted(missing))}")
        return [Record(**{k: (row.get(k) or "").strip() for k in FIELDS}) for row in reader]


def save(project: Path, records: list[Record]) -> None:
    with path_for(project).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(asdict(r) for r in records)


def by_id(records: list[Record]) -> dict[str, Record]:
    return {r.id: r for r in records}


def next_id(records: list[Record], kind: str) -> str:
    prefix = "S" if kind == "synthetic" else "E"
    nums = [int(r.id[1:]) for r in records if r.id.startswith(prefix) and r.id[1:].isdigit()]
    return f"{prefix}{max(nums, default=0) + 1}"


def add(project: Path, kind: str, source: str, locator: str, quote: str, quality: str,
        note: str = "", added_by: str = "agent", accessed: str | None = None) -> Record:
    records = load(project)
    candidate = Record("", ACTIVE, kind, source.strip(), locator.strip(), accessed or date.today().isoformat(),
                       quote.strip(), quality.strip().upper(), note.strip(), added_by)
    problems = record_problems(candidate, project, check_id=False)
    if problems:
        raise SfError("Запись не добавлена: " + "; ".join(problems))
    duplicate = next((r for r in records if (r.source, r.locator, r.quote) == (candidate.source, candidate.locator, candidate.quote)), None)
    if duplicate:
        raise SfError(f"Такая запись уже есть: {duplicate.id}. Используйте её.")
    record = replace(candidate, id=next_id(records, kind))
    save(project, [*records, record])
    return record


def revoke(project: Path, record_id: str, reason: str) -> Record:
    if not reason.strip():
        raise SfError("Укажите причину отзыва.")
    records = load(project)
    index = by_id(records)
    if record_id not in index:
        raise SfError(f"Нет записи {record_id}.")
    updated = replace(index[record_id], status=REVOKED, revoked_reason=reason.strip())
    save(project, [updated if r.id == record_id else r for r in records])
    return updated


def record_problems(record: Record, project: Path, check_id: bool = True) -> list[str]:
    problems = []
    if check_id and not ID_RE.match(record.id):
        problems.append(f"неверный id «{record.id}»")
    if record.status not in (ACTIVE, REVOKED):
        problems.append(f"статус «{record.status}» (нужно active/revoked)")
    if record.kind not in KINDS:
        problems.append(f"вид «{record.kind}» (допустимо: {', '.join(KINDS)})")
    if record.quality not in QUALITY:
        problems.append(f"качество «{record.quality}» (A/B/C)")
    if not DATE_RE.match(record.accessed):
        problems.append(f"дата «{record.accessed}» (ГГГГ-ММ-ДД)")
    if not record.source:
        problems.append("нет источника")
    if not record.quote:
        problems.append("нет цитаты или расчёта")
    if record.kind in ("doc", "table", "interview") and record.source and not record.source.startswith("http"):
        if not (project / record.source).exists():
            problems.append(f"файл источника не найден: {record.source}")
    if record.kind == "web" and not record.source.startswith(("http://", "https://")):
        problems.append("для web нужен URL")
    if record.status == REVOKED and not record.revoked_reason:
        problems.append("отозвана без причины")
    if record.kind == "synthetic" and check_id and not record.id.startswith("S"):
        problems.append("синтетика должна иметь id S…")
    return problems


def check(project: Path) -> list[str]:
    """Проблемы формата всего реестра (для validate)."""
    records = load(project)
    issues = []
    seen: set[str] = set()
    for record in records:
        if record.id in seen:
            issues.append(f"{record.id}: повторяющийся id")
        seen.add(record.id)
        issues.extend(f"{record.id}: {p}" for p in record_problems(record, project))
    return issues


def describe(record: Record) -> str:
    status = "ОТОЗВАНА: " + record.revoked_reason if record.status == REVOKED else "действует"
    return (f"{record.id} [{record.kind}, качество {record.quality}, {record.accessed}, {status}]\n"
            f"  источник: {record.source}\n  место: {record.locator or '—'}\n  цитата/расчёт: «{record.quote}»"
            + (f"\n  заметка: {record.note}" if record.note else ""))
