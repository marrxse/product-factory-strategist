"""Пути репозитория и активного проекта."""
from __future__ import annotations

import os
import re
from pathlib import Path

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")


class SfError(Exception):
    """Понятная пользователю ошибка: печатается без трассировки."""


def repo_root() -> Path:
    env = os.environ.get("SF_ROOT")
    return Path(env).resolve() if env else Path(__file__).resolve().parent.parent


def projects_dir() -> Path:
    return repo_root() / "projects"


def templates_dir() -> Path:
    return repo_root() / "templates" / "project"


def active_file() -> Path:
    return projects_dir() / ".active"


def validate_slug(slug: str) -> str:
    if not SLUG_RE.match(slug):
        raise SfError(
            f"Имя проекта «{slug}» не подходит: латиница в нижнем регистре, цифры и дефис, 2–41 символ."
        )
    return slug


def get_active() -> str | None:
    path = active_file()
    if not path.exists():
        return None
    slug = path.read_text(encoding="utf-8").strip()
    return slug or None


def set_active(slug: str) -> None:
    validate_slug(slug)
    if not (projects_dir() / slug).is_dir():
        raise SfError(f"Проект «{slug}» не найден в projects/.")
    projects_dir().mkdir(parents=True, exist_ok=True)
    active_file().write_text(slug + "\n", encoding="utf-8")


def project_dir(slug: str | None = None) -> Path:
    """Папка проекта: явно заданного или активного."""
    name = slug or get_active()
    if not name:
        raise SfError("Нет активного проекта. Создайте: python3 sf.py new <имя> или выберите: python3 sf.py use <имя>.")
    path = projects_dir() / validate_slug(name)
    if not path.is_dir():
        raise SfError(f"Проект «{name}» не найден в projects/.")
    return path
