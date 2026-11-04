"""Синхронизация .claude/ из единых источников skills/ и agents/ (переносимость Claude Code ↔ Cursor).

Модель субагента берётся из config.toml [models] по роли: в agents/*.md пишется `model: {{role:critic}}`.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from . import config, paths

ROLE_RE = re.compile(r"\{\{role:([a-z_]+)\}\}")


def _render_agent(text: str) -> str:
    def repl(match: re.Match) -> str:
        role = match.group(1)
        model = config.get("models", role)
        if not model:
            raise paths.SfError(f"В config.toml [models] нет роли «{role}».")
        return model
    return ROLE_RE.sub(repl, text)


def planned(root: Path) -> dict[Path, str]:
    """Что должно лежать в .claude/: путь → содержимое."""
    result: dict[Path, str] = {}
    for skill in sorted((root / "skills").glob("*/SKILL.md")):
        result[root / ".claude" / "skills" / skill.parent.name / "SKILL.md"] = skill.read_text(encoding="utf-8")
    for agent in sorted((root / "agents").glob("*.md")):
        result[root / ".claude" / "agents" / agent.name] = _render_agent(agent.read_text(encoding="utf-8"))
    settings = root / "hooks" / "settings.json"
    if settings.exists():
        result[root / ".claude" / "settings.json"] = settings.read_text(encoding="utf-8")
    return result


def check(root: Path) -> list[str]:
    """Расхождения .claude/ с источниками."""
    problems = []
    plan = planned(root)
    for target, content in plan.items():
        if not target.exists():
            problems.append(f"нет {target.relative_to(root)}")
        elif target.read_text(encoding="utf-8") != content:
            problems.append(f"устарел {target.relative_to(root)}")
    for folder in (root / ".claude" / "skills", root / ".claude" / "agents"):
        if folder.exists():
            for extra in folder.rglob("*.md"):
                if extra not in plan:
                    problems.append(f"лишний {extra.relative_to(root)} (нет источника)")
    return problems


def apply(root: Path) -> int:
    for folder in (root / ".claude" / "skills", root / ".claude" / "agents"):
        if folder.exists():
            shutil.rmtree(folder)
    plan = planned(root)
    for target, content in plan.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return len(plan)
