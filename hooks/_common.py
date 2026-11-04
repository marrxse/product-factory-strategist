"""Общее для хуков: корень репозитория, чтение входа хука, безопасный запуск.

Хуки не должны ломать работу: внутренняя ошибка хука печатается в stderr и не блокирует агента
(кроме осознанной блокировки кодом 2 в post_write_validate).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BLOCK = 2  # код Claude Code: показать stderr агенту, чтобы он исправил


def read_input() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        return {}
