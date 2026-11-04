"""Разбор разметки в outputs/*.md: метки доказательств, ключевые выводы, опоры обещаний.

Метки: [E3], [E3; E7], [ГИП], [ПРОГНОЗ E3], [СИНТ S2], [ФАКТ E3]
Выводы: **C4.** текст [E1; C2]   Возможности продукта: **П2.**   Обещания: **О1.** … (опора: П2)
Кириллические двойники латинских букв (Е, С) нормализуются.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

LOOKALIKE = str.maketrans({"Е": "E", "С": "C", "е": "E", "с": "C"})
REF = r"[EЕSCС]\d+"
TAG_RE = re.compile(rf"\[(?P<label>ФАКТ|ГИП|ПРОГНОЗ|СИНТ)?\s*(?P<refs>{REF}(?:\s*[;,]\s*{REF})*)?\s*\](?!\()")
CONCLUSION_RE = re.compile(r"\*\*([CС]\d+)\.\*\*")
CAPABILITY_RE = re.compile(r"\*\*П(\d+)\.\*\*")
PROMISE_RE = re.compile(r"\*\*[ОO](\d+)\.\*\*")
SUPPORT_RE = re.compile(r"опора:\s*((?:П\d+\s*[,;]?\s*)+)", re.IGNORECASE)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass(frozen=True)
class Tag:
    label: str          # ФАКТ / ГИП / ПРОГНОЗ / СИНТ или "" (= ФАКТ)
    refs: tuple[str, ...]


@dataclass(frozen=True)
class Line:
    file: str
    num: int
    text: str
    heading: str        # ближайший заголовок
    tags: tuple[Tag, ...]
    conclusion: str     # C-id, если строка объявляет вывод
    capability: str     # П-id
    promise: str        # О-id
    supports: tuple[str, ...]  # П-id, на которые опирается обещание

    @property
    def refs(self) -> tuple[str, ...]:
        return tuple(ref for tag in self.tags for ref in tag.refs)

    @property
    def labels(self) -> set[str]:
        return {tag.label or "ФАКТ" for tag in self.tags}

    @property
    def is_tagged(self) -> bool:
        return bool(self.tags)


def _norm(ref: str) -> str:
    return ref.translate(LOOKALIKE)


def parse_tags(text: str) -> tuple[Tag, ...]:
    tags = []
    for match in TAG_RE.finditer(text):
        label, refs = match.group("label") or "", match.group("refs") or ""
        if not label and not refs:
            continue
        ids = tuple(_norm(r) for r in re.findall(REF, refs))
        tags.append(Tag(label, ids))
    return tuple(tags)


def parse_text(text: str, file: str) -> list[Line]:
    lines, heading, in_code = [], "", False
    for num, raw in enumerate(text.splitlines(), start=1):
        if raw.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        head = HEADING_RE.match(raw)
        if head:
            heading = head.group(2).strip()
        conclusion = CONCLUSION_RE.search(raw)
        capability = CAPABILITY_RE.search(raw)
        promise = PROMISE_RE.search(raw)
        support = SUPPORT_RE.search(raw)
        lines.append(Line(
            file=file, num=num, text=raw, heading=heading, tags=parse_tags(raw),
            conclusion=_norm(conclusion.group(1)) if conclusion else "",
            capability=f"П{capability.group(1)}" if capability else "",
            promise=f"О{promise.group(1)}" if promise else "",
            supports=tuple(re.findall(r"П\d+", support.group(1))) if support else (),
        ))
    return lines


def parse_outputs(project: Path) -> list[Line]:
    out_dir = project / "outputs"
    result: list[Line] = []
    for path in sorted(out_dir.glob("*.md")):
        result.extend(parse_text(path.read_text(encoding="utf-8"), path.name))
    return result


def sections(lines: list[Line], level_re: str) -> dict[str, list[Line]]:
    """Разбивает строки файла на разделы по заголовкам, подходящим под level_re (например r'^#{2,3}\\s')."""
    pattern = re.compile(level_re)
    result: dict[str, list[Line]] = {}
    current = None
    for line in lines:
        if pattern.match(line.text):
            current = HEADING_RE.match(line.text).group(2).strip()
            result[current] = []
        elif current is not None:
            result[current].append(line)
    return result
