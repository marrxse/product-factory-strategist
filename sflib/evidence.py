"""Реестр доказательств evidence.csv: добавить, показать, отозвать, проверить формат."""
from __future__ import annotations

import csv
import re
from dataclasses import asdict, dataclass, fields, replace
from datetime import date
from pathlib import Path

from .paths import SfError

KINDS = ("web", "doc", "table", "calc", "interview", "synthetic", "image", "audio", "video")
QUALITY = ("A", "B", "C")  # A — первичный/официальный, B — надёжный вторичный, C — слабый/пересказ
ACTIVE, REVOKED = "active", "revoked"
ID_RE = re.compile(r"^[ES]\d+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PUBLISHED_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")  # год, год-месяц или точная дата
OPTIONAL_FIELDS = ("published",)  # старые реестры без этих колонок читаются как есть


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
    published: str = ""  # когда опубликованы данные (или период, к которому они относятся) — не путать с датой доступа


FIELDS = [f.name for f in fields(Record)]


def path_for(project: Path) -> Path:
    return project / "evidence.csv"


def load(project: Path) -> list[Record]:
    path = path_for(project)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(FIELDS) - set(OPTIONAL_FIELDS) - set(reader.fieldnames or [])
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
        note: str = "", added_by: str = "agent", accessed: str | None = None, published: str = "") -> Record:
    records = load(project)
    candidate = Record("", ACTIVE, kind, source.strip(), locator.strip(), accessed or date.today().isoformat(),
                       quote.strip(), quality.strip().upper(), note.strip(), added_by, published=published.strip())
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


def set_quality(project: Path, record_id: str, quality: str, reason: str) -> Record:
    """Исправить оценку качества по решению проверки: старая оценка и причина остаются в заметке."""
    quality = quality.strip().upper()
    if quality not in QUALITY:
        raise SfError(f"Качество «{quality}»: допустимо A, B, C.")
    if not reason.strip():
        raise SfError("Укажите причину изменения оценки.")
    records = load(project)
    index = by_id(records)
    if record_id not in index:
        raise SfError(f"Нет записи {record_id}.")
    old = index[record_id]
    if old.quality == quality:
        raise SfError(f"У {record_id} уже качество {quality}.")
    trail = f"качество {old.quality} → {quality}: {reason.strip()}"
    updated = replace(old, quality=quality, note=f"{old.note}; {trail}" if old.note else trail)
    save(project, [updated if r.id == record_id else r for r in records])
    return updated


def set_published(project: Path, record_id: str, published: str) -> Record:
    """Указать дату публикации данных записи: год, год-месяц или ГГГГ-ММ-ДД."""
    published = published.strip()
    if not PUBLISHED_RE.match(published):
        raise SfError(f"Дата публикации «{published}»: нужно ГГГГ, ГГГГ-ММ или ГГГГ-ММ-ДД.")
    records = load(project)
    index = by_id(records)
    if record_id not in index:
        raise SfError(f"Нет записи {record_id}.")
    updated = replace(index[record_id], published=published)
    save(project, [updated if r.id == record_id else r for r in records])
    return updated


def published_end(value: str) -> date | None:
    """Последний день периода публикации: «2021» → 31.12.2021, «2025-03» → 28.03.2025 (с запасом), дата — как есть."""
    if not value or not PUBLISHED_RE.match(value):
        return None
    parts = [int(p) for p in value.split("-")]
    if len(parts) == 1:
        return date(parts[0], 12, 31)
    if len(parts) == 2:
        return date(parts[0], parts[1], 28)
    return date(parts[0], parts[1], parts[2])


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
    if record.published and not PUBLISHED_RE.match(record.published):
        problems.append(f"дата публикации «{record.published}» (ГГГГ, ГГГГ-ММ или ГГГГ-ММ-ДД)")
    if not record.source:
        problems.append("нет источника")
    if not record.quote:
        problems.append("нет цитаты или расчёта")
    if record.kind in ("doc", "table", "interview", "image", "audio", "video") and record.source and not record.source.startswith("http"):
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
    dated = f"опубликовано {record.published}, " if record.published else ""
    return (f"{record.id} [{record.kind}, качество {record.quality}, {dated}доступ {record.accessed}, {status}]\n"
            f"  источник: {record.source}\n  место: {record.locator or '—'}\n  цитата/расчёт: «{record.quote}»"
            + (f"\n  заметка: {record.note}" if record.note else ""))
