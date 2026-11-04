"""Граф выводов: вывод C → доказательства E/S и другие выводы C. Основа пересмотра при новых данных."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from . import evidence as ev
from .markup import Line, parse_outputs


@dataclass(frozen=True)
class Graph:
    lines: tuple[Line, ...]
    conclusions: dict[str, Line]            # C-id → строка объявления
    depends: dict[str, tuple[str, ...]]     # C-id → на что опирается

    def dependents_of(self, node_id: str) -> list[str]:
        """Все выводы, прямо или транзитивно опирающиеся на node_id (порядок обхода в ширину)."""
        found: list[str] = []
        frontier = [node_id]
        while frontier:
            current = frontier.pop(0)
            for cid, refs in self.depends.items():
                if current in refs and cid not in found and cid != node_id:
                    found.append(cid)
                    frontier.append(cid)
        return found

    def lines_citing(self, ids: set[str]) -> list[Line]:
        return [line for line in self.lines if ids & set(line.refs) and not line.conclusion]


def build(project: Path) -> Graph:
    lines = tuple(parse_outputs(project))
    conclusions: dict[str, Line] = {}
    depends: dict[str, tuple[str, ...]] = {}
    for line in lines:
        if line.conclusion and line.conclusion not in conclusions:
            conclusions[line.conclusion] = line
            depends[line.conclusion] = tuple(r for r in line.refs if r != line.conclusion)
    return Graph(lines, conclusions, depends)


def find_cycle(graph: Graph) -> list[str]:
    """Возвращает цикл зависимостей между выводами, если он есть."""
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> list[str]:
        state[node] = 1
        stack.append(node)
        for ref in graph.depends.get(node, ()):
            if not ref.startswith("C"):
                continue
            if state.get(ref) == 1:
                return stack[stack.index(ref):] + [ref]
            if ref not in state:
                cycle = visit(ref)
                if cycle:
                    return cycle
        stack.pop()
        state[node] = 2
        return []

    for node in graph.depends:
        if node not in state:
            cycle = visit(node)
            if cycle:
                return cycle
    return []


def trace(project: Path, node_id: str, depth: int = 0, seen: set[str] | None = None) -> list[str]:
    """Дерево оснований вывода до цитат источников."""
    graph = build(project)
    records = ev.by_id(ev.load(project))
    return _trace(graph, records, node_id, depth, seen or set())


def _trace(graph: Graph, records: dict, node_id: str, depth: int, seen: set[str]) -> list[str]:
    pad = "  " * depth
    if node_id in seen:
        return [f"{pad}{node_id} (уже показан выше)"]
    seen.add(node_id)
    if node_id.startswith(("E", "S")):
        record = records.get(node_id)
        if record is None:
            return [f"{pad}{node_id} — НЕТ В РЕЕСТРЕ"]
        mark = " [ОТОЗВАНА]" if record.status == ev.REVOKED else ""
        return [f"{pad}{node_id}{mark}: «{record.quote[:160]}» — {record.source} ({record.locator or '—'})"]
    line = graph.conclusions.get(node_id)
    if line is None:
        return [f"{pad}{node_id} — вывод не найден в outputs/"]
    out = [f"{pad}{node_id} ({line.file}:{line.num}): {line.text.strip()[:200]}"]
    for ref in graph.depends.get(node_id, ()):
        out.extend(_trace(graph, records, ref, depth + 1, seen))
    return out


@dataclass(frozen=True)
class Impact:
    changed: str
    conclusions: list[str]
    lines: list[Line]


def impact(project: Path, changed_ids: list[str]) -> list[Impact]:
    """Что затронуто изменением/отзывом доказательств или выводов."""
    graph = build(project)
    result = []
    for changed in changed_ids:
        affected = graph.dependents_of(changed)
        cited = graph.lines_citing({changed, *affected})
        result.append(Impact(changed, affected, cited))
    return result


DUE_RE = re.compile(r"Пересмотреть\s*(?:до|не позже)?\s*:?\s*\**\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)


def decisions_due(project: Path, today: date | None = None) -> list[str]:
    """Решения из state/decisions.md, у которых наступил срок пересмотра."""
    today = today or date.today()
    path = project / "state" / "decisions.md"
    if not path.exists():
        return []
    heading, due = "", []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
        match = DUE_RE.search(line)
        if match and date.fromisoformat(match.group(1)) <= today:
            due.append(f"решение «{heading}»: срок пересмотра {match.group(1)} наступил")
    return due


def stale(project: Path, max_age_days: int, today: date | None = None) -> list[str]:
    """Устаревшие основания: отозванные, но используемые; слишком старые; несуществующие."""
    today = today or date.today()
    graph = build(project)
    records = ev.by_id(ev.load(project))
    used = {ref for line in graph.lines for ref in line.refs}
    issues = []
    for ref in sorted(used):
        if ref.startswith("C"):
            if ref not in graph.conclusions:
                issues.append(f"{ref}: ссылка на несуществующий вывод")
            continue
        record = records.get(ref)
        if record is None:
            issues.append(f"{ref}: нет в реестре доказательств")
        elif record.status == ev.REVOKED:
            deps = ", ".join(graph.dependents_of(ref)) or "—"
            issues.append(f"{ref}: ОТОЗВАНА ({record.revoked_reason}), но используется; затронутые выводы: {deps}")
        elif record.accessed and date.fromisoformat(record.accessed) < today - timedelta(days=max_age_days):
            issues.append(f"{ref}: данные от {record.accessed} старше {max_age_days} дней — проверить актуальность")
    return issues
