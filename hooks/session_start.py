#!/usr/bin/env python3
"""SessionStart: показать агенту состояние активного проекта, чтобы новый чат продолжил с места, а не начал заново."""
from __future__ import annotations

import sys

from _common import read_input  # noqa: E402  (добавляет корень репозитория в sys.path)

from sflib import paths, project, sync  # noqa: E402


def main() -> int:
    read_input()
    lines = []
    stale = sync.check(paths.repo_root())
    if stale:
        lines.append("Навыки/субагенты в .claude/ расходятся с источниками — выполни: python3 sf.py sync")
    active = paths.get_active()
    if not active:
        names = project.list_projects()
        lines.append("Активного проекта нет. " + (f"Есть проекты: {', '.join(names)} (python3 sf.py use <имя>)."
                                                   if names else "Предложи человеку «начни <тема>»."))
    else:
        try:
            lines.append(project.summary(paths.project_dir(active)))
            lines.append("\nПродолжай по skills/resume/SKILL.md: покажи человеку, где остановились, и не повторяй выполненные шаги.")
        except (paths.SfError, ValueError) as err:
            lines.append(f"Не удалось прочитать состояние проекта {active}: {err}")
    print("[Стратег] Состояние при старте сессии:\n" + "\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as err:  # хук не должен мешать старту сессии
        print(f"[Стратег] session_start: внутренняя ошибка хука: {err}", file=sys.stderr)
        sys.exit(0)
