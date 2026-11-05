"""Маршрутизация: какой навык, модель и инструмент взять под задачу — и как исправить ошибочный выбор.

Правила — в config.toml [[routing.rules]]: слова задачи → навык, роль (модель из [models]), инструмент.
Выбор детерминированный и бесплатный (без вызова модели); исправление — эскалация по config.toml [models].escalation.
Сверка классификатора: дешёвая модель ставит качество источникам вслепую, расхождения уходят модели сильнее.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from . import config
from . import evidence as ev
from .paths import SfError

WORD_RE = re.compile(r"[a-zа-яё0-9-]+", re.IGNORECASE)
CLASSIFY_FIELDS = ("id", "kind", "source", "locator", "quote")


@dataclass(frozen=True)
class Rule:
    name: str
    words: tuple[str, ...]
    skill: str
    role: str
    tool: str
    why: str


@dataclass(frozen=True)
class Choice:
    rule: Rule
    model: str
    matched: tuple[str, ...]
    runner_up: str


@dataclass(frozen=True)
class Disagreement:
    id: str
    ours: str
    theirs: str
    reason: str


def rules() -> list[Rule]:
    raw = config.load().get("routing", {}).get("rules", [])
    if not raw:
        raise SfError("В config.toml нет правил [[routing.rules]].")
    return [Rule(r["name"], tuple(w.lower() for w in r["words"]), r["skill"], r["role"], r.get("tool", "—"), r.get("why", ""))
            for r in raw]


def words_of(text: str) -> set[str]:
    return {w.lower().replace("ё", "е") for w in WORD_RE.findall(text)}


def _matches(task_words: set[str], prefix: str) -> bool:
    prefix = prefix.replace("ё", "е")
    return any(w.startswith(prefix) for w in task_words)


def model_for(role: str) -> str:
    model = config.get("models", role)
    if not model:
        raise SfError(f"В config.toml [models] нет роли «{role}».")
    return model


def choose(task: str) -> Choice:
    """Правило с наибольшим числом совпавших слов; при равенстве — первое в config (оно дешевле или частнее)."""
    task_words = words_of(task)
    scored = []
    for rule in rules():
        hit = tuple(w for w in rule.words if _matches(task_words, w))
        scored.append((len(hit), rule, hit))
    ranked = sorted(scored, key=lambda item: -item[0])
    best_score, best, hit = ranked[0]
    if best_score == 0:
        default = Rule("общая работа", (), "по этапу", "orchestrator", "—", "задача не похожа ни на одно правило")
        return Choice(default, model_for("orchestrator"), (), "")
    runner = next((r.name for s, r, _ in ranked[1:] if s > 0), "")
    return Choice(best, model_for(best.role), hit, runner)


def escalate(model: str) -> str:
    ladder = config.get("models", "escalation", [])
    if model not in ladder:
        raise SfError(f"Модели «{model}» нет в лестнице эскалации: {', '.join(ladder)}")
    index = ladder.index(model)
    if index == len(ladder) - 1:
        raise SfError(f"{model} — уже самая сильная модель. Дальше — человек.")
    return ladder[index + 1]


def price_note(model: str) -> str:
    try:
        price = config.price(model)
    except SfError:
        return ""
    return f"${price['input']:g} / ${price['output']:g} за 1 млн токенов (вход / выход)"


def write_classify_input(project: Path) -> Path:
    """Действующие записи реестра без поля качества — чтобы классификатор не видел оценку агента."""
    target = project / "state" / "routing" / "classify-input.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    records = [r for r in ev.load(project) if r.status == ev.ACTIVE and r.kind != "synthetic"]
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CLASSIFY_FIELDS)
        writer.writerows([r.id, r.kind, r.source, r.locator, r.quote] for r in records)
    return target


def compare(project: Path, classified: Path) -> tuple[int, list[Disagreement]]:
    """Сколько записей классификатор оценил так же, как реестр, и где разошёлся."""
    if not classified.is_file():
        raise SfError(f"Нет файла {classified}")
    ours = {r.id: r.quality for r in ev.load(project) if r.status == ev.ACTIVE}
    with classified.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or not {"id", "quality"} <= set(rows[0]):
        raise SfError("Нужны колонки id и quality (и reason).")
    checked = [r for r in rows if r["id"].strip() in ours]
    disagreements = [Disagreement(r["id"].strip(), ours[r["id"].strip()], r["quality"].strip().upper(), (r.get("reason") or "").strip())
                     for r in checked if r["quality"].strip().upper() != ours[r["id"].strip()]]
    return len(checked), disagreements
