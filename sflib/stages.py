"""Этапы рабочего процесса и ворота (точки, где решает человек)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stage:
    num: int
    code: str
    title: str
    skill: str
    has_gate: bool


STAGES: tuple[Stage, ...] = (
    Stage(0, "intake", "Постановка задачи", "intake", True),
    Stage(1, "collect", "Сбор материалов", "collect", False),
    Stage(2, "plan", "План исследования", "research-plan", True),
    Stage(3, "research", "Исследование", "research", False),
    Stage(4, "options", "Варианты", "options", True),
    Stage(5, "strategy", "Стратегии", "product-strategy + comms-strategy", True),
    Stage(6, "validation", "План проверки", "validation-plan", True),
    Stage(7, "decision", "Поддержка решения", "decision-support", False),
    Stage(8, "revisit", "Пересмотр по новым данным", "decision-support", True),
)

# Статусы этапа
NOT_STARTED = "не начат"
IN_PROGRESS = "в работе"
AWAITING = "ждёт решения"
DONE = "готов"
STAGE_STATUSES = (NOT_STARTED, IN_PROGRESS, AWAITING, DONE)

# Статусы ворот
NO_GATE = "—"
GATE_PENDING = "ждёт"
GATE_OK = "одобрено"
GATE_FIX = "правки"


def get_stage(num: int) -> Stage:
    for stage in STAGES:
        if stage.num == num:
            return stage
    raise ValueError(f"Нет этапа {num}. Допустимо: 0–{len(STAGES) - 1}.")
