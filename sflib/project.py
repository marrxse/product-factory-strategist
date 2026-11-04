"""Создание проекта из шаблона, переключение, сводка состояния."""
from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from . import journal, paths
from . import state as stmod

TEMPLATE_TOKENS = ("{{TITLE}}", "{{SLUG}}", "{{DATE}}")


def _fill(text: str, title: str, slug: str) -> str:
    return text.replace("{{TITLE}}", title).replace("{{SLUG}}", slug).replace("{{DATE}}", date.today().isoformat())


def create(slug: str, title: str, source_example: Path | None = None) -> Path:
    """Копирует шаблон проекта; при --from берёт brief.md и sources/ из примера."""
    paths.validate_slug(slug)
    target = paths.projects_dir() / slug
    if target.exists():
        raise paths.SfError(f"Проект «{slug}» уже существует. Продолжить его: python3 sf.py use {slug}")
    template = paths.templates_dir()
    if not template.is_dir():
        raise paths.SfError("Не найден шаблон templates/project/. Репозиторий повреждён.")
    if source_example is not None and not source_example.is_dir():
        raise paths.SfError(f"Папка примера не найдена: {source_example}")

    shutil.copytree(template, target)
    for file in target.rglob("*"):
        if file.is_file() and file.suffix in {".md", ".csv"}:
            file.write_text(_fill(file.read_text(encoding="utf-8"), title, slug), encoding="utf-8")

    state_path = target / "state" / "STATE.md"
    stmod.write_rows(state_path, stmod.initial_rows())

    if source_example is not None:
        _import_example(source_example, target)

    log = target / "state" / "log.md"
    origin = f" из {source_example.name}" if source_example else ""
    journal.append(log, "NOTE", "project:create", f"Проект создан{origin}")
    paths.set_active(slug)
    return target


def _import_example(example: Path, target: Path) -> None:
    brief = example / "brief.md"
    if brief.exists():
        shutil.copy2(brief, target / "brief.md")
    sources = example / "sources"
    if sources.is_dir():
        shutil.copytree(sources, target / "sources", dirs_exist_ok=True)


def list_projects() -> list[str]:
    root = paths.projects_dir()
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and (p / "state" / "STATE.md").exists())


def summary(project: Path, log_lines: int = 5) -> str:
    """Короткая сводка для человека и для начала новой сессии."""
    state_path = project / "state" / "STATE.md"
    text = stmod.read(state_path)
    rows = stmod.parse_rows(text)
    entries = journal.read_entries(project / "state" / "log.md")
    current = stmod.current_stage(rows)

    out = [f"Проект: {project.name}"]
    if current is None:
        out.append("Все этапы до поддержки решения завершены. Доступен пересмотр (этап 8).")
    else:
        out.append(f"Текущий этап: {current.num} — {current.title} ({current.status}; ворота: {current.gate})")
    out.append("")
    out.append("Этапы: " + " · ".join(f"{r.num}:{_mark(r)}" for r in rows))

    pending = [r for r in rows if r.gate == "ждёт" and r.status == "ждёт решения"]
    if pending:
        out.append("Ждёт решения человека: " + ", ".join(f"этап {r.num} ({r.title})" for r in pending))

    open_steps = journal.unfinished(entries)
    if open_steps:
        out.append("Незавершённые шаги (проверить перед повтором):")
        out.extend(f"  - [{e.kind}] {e.key} — {e.text} ({e.ts})" for e in open_steps)

    for heading in ("Дальше", "Открытые вопросы к человеку", "Действующие допущения"):
        body = stmod.section(text, heading)
        if body and not body.startswith("_"):
            out.append(f"\n{heading}:\n{body}")

    if entries:
        out.append("\nПоследние действия:")
        out.extend(f"  {e.ts} {e.kind} {e.key} — {e.text}" for e in entries[-log_lines:])
    return "\n".join(out)


def _mark(row: stmod.Row) -> str:
    marks = {"не начат": "·", "в работе": "▶", "ждёт решения": "?", "готов": "✓"}
    return marks.get(row.status, row.status)
