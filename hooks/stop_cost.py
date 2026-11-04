#!/usr/bin/env python3
"""Stop / SubagentStop: перенести фактическое использование токенов из транскрипта в cost.csv активного проекта.

Учитываются только новые ответы модели после создания проекта (повторный запуск ничего не дублирует).
"""
from __future__ import annotations

import sys
from pathlib import Path

from _common import read_input  # noqa: E402

from sflib import cost, journal, paths  # noqa: E402


def transcripts_for(transcript_path: str) -> list[Path]:
    main_file = Path(transcript_path)
    if not main_file.exists():
        return []
    sub_dir = main_file.with_suffix("")  # <session>/subagents/*.jsonl
    return [main_file, *sorted(sub_dir.rglob("*.jsonl"))] if sub_dir.is_dir() else [main_file]


def main() -> int:
    data = read_input()
    active = paths.get_active()
    if not active or not data.get("transcript_path"):
        return 0
    project = paths.project_dir(active)
    files = transcripts_for(data["transcript_path"])
    if not files:
        return 0
    try:
        cost.import_transcripts(project, files)
    except (paths.SfError, OSError, ValueError) as err:
        journal.append(project / "state" / "log.md", "FAIL", "cost:transcript", f"учёт стоимости не выполнен: {err}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as err:
        print(f"[Стратег] stop_cost: внутренняя ошибка хука: {err}", file=sys.stderr)
        sys.exit(0)
