"""Проверка формы результатов: ссылки, обязательные разделы, варианты, синтетика, обещания, секреты.

Проверяет форму, а не ум: смысл оценивают quality-review, verifier и человек (docs/LIMITATIONS.md).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import config, graph, scan
from . import evidence as ev
from . import state as stmod
from .markup import Line, parse_text, sections

ERROR, WARN = "ОШИБКА", "внимание"
NUMBER_RE = re.compile(
    r"\d[\d\s]*(?:[.,]\d+)?\s*(?:%|процент|млн|млрд|тыс|₽|руб|\$|долл|раз(?:а)?\b|п\.\s?п\.|пп\b|"
    r"пользовател|абонент|клиент|человек|чел\.)", re.IGNORECASE)
SKIP_MARK = "<!-- sf:ok -->"
# «без спроса» (= не спросив) — не про спрос на продукт
DEMAND_RE = re.compile(r"(?<!без )\bспрос\w*|готов\w* платить|большинство|распространен|доля рынка|все пользователи|купят|купил\w* бы|"
                       r"процент\w* покуп|вердикт",
                       re.IGNORECASE)

STAGE_FILES = {
    2: ("research-plan.md",),
    3: ("research.md",),
    4: ("options.md", "quality-report.md"),
    5: ("product-strategy.md", "comms-strategy.md", "quality-report.md"),
    6: ("validation-plan.md", "decision-brief.md"),
}
REQUIRED_SECTIONS = {
    "research.md": ("Чего мы не знаем",),
    "product-strategy.md": ("Аудитори", "Альтернатив", "Выбранное направление", "Отказ", "Экономик", "Цена"),
    "comms-strategy.md": ("Аудитори", "Барьер", "Ключевое сообщение", "Подтвержд", "Канал", "Обещани"),
    "validation-plan.md": ("Ожидаемое изменение", "С чем сравниваем", "Срок", "Нежелательн", "Порог"),
    "decision-brief.md": ("Рекомендац", "Чего мы не знаем"),
    "ux-review.md": ("Что анализировали", "Путь пользователя", "Находки", "Чего не видно"),
    "behavior.md": ("Участники", "Что люди делают", "Карта поведения", "Следствия", "Чего мы не знаем"),
}


@dataclass(frozen=True)
class Issue:
    level: str
    where: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level}] {self.where}: {self.message}"


def run(project: Path, final: bool = False, repo_root: Path | None = None) -> list[Issue]:
    out_dir = project / "outputs"
    files = {p.name: parse_text(p.read_text(encoding="utf-8"), p.name) for p in sorted(out_dir.glob("*.md"))}
    issues: list[Issue] = []
    issues += _evidence_format(project)
    issues += _references(project, files)
    issues += _untagged_numbers(files)
    issues += _malformed_tags(files)
    issues += _synthetic_misuse(files)
    issues += _required_files(project, files, final)
    issues += _required_sections(files)
    issues += _options(files.get("options.md"))
    issues += _promises(files)
    if repo_root is not None:
        issues += [Issue(ERROR, f"{f}:{n}", f"похоже на секрет ({kind}) — удалите и перевыпустите ключ")
                   for f, n, kind in scan.secrets(repo_root)]
    return issues


def _evidence_format(project: Path) -> list[Issue]:
    return [Issue(ERROR, "evidence.csv", msg) for msg in ev.check(project)]


def _references(project: Path, files: dict[str, list[Line]]) -> list[Issue]:
    records = ev.by_id(ev.load(project))
    all_lines = [line for lines in files.values() for line in lines]
    declared: dict[str, Line] = {}
    issues = []
    for line in all_lines:
        if line.conclusion:
            if line.conclusion in declared:
                first = declared[line.conclusion]
                issues.append(Issue(ERROR, f"{line.file}:{line.num}", f"вывод {line.conclusion} уже объявлен в {first.file}:{first.num}"))
            else:
                declared[line.conclusion] = line
            if not line.refs and "ГИП" not in line.labels:
                issues.append(Issue(ERROR, f"{line.file}:{line.num}", f"вывод {line.conclusion} без оснований — добавьте [E…]/[C…] или пометьте [ГИП]"))
    for line in all_lines:
        for ref in line.refs:
            where = f"{line.file}:{line.num}"
            if ref.startswith("C"):
                if ref not in declared:
                    issues.append(Issue(ERROR, where, f"ссылка на необъявленный вывод {ref}"))
            elif ref not in records:
                issues.append(Issue(ERROR, where, f"{ref} нет в evidence.csv"))
            elif records[ref].status == ev.REVOKED:
                issues.append(Issue(ERROR, where, f"{ref} отозвана ({records[ref].revoked_reason}) — пересмотрите вывод: sf.py revisit {ref}"))
    cycle = graph.find_cycle(graph.Graph(tuple(all_lines), declared, {c: tuple(r for r in l.refs if r != c) for c, l in declared.items()}))
    if cycle:
        issues.append(Issue(ERROR, "outputs", "циклическая опора выводов: " + " → ".join(cycle)))
    return issues


def _untagged_numbers(files: dict[str, list[Line]]) -> list[Issue]:
    skip = set(config.get("validate", "skip_number_check", []))
    skip_sections = tuple(s.lower() for s in config.get("validate", "skip_number_sections", []))
    issues = []
    for name, lines in files.items():
        if name in skip:
            continue
        for line in lines:
            text = line.text.strip()
            if not text or text.startswith(("#", "|---", "|--", ">")) or SKIP_MARK in text:
                continue
            if line.heading.lower().startswith(skip_sections):
                continue
            if NUMBER_RE.search(text) and not line.is_tagged:
                issues.append(Issue(ERROR, f"{name}:{line.num}", f"число без метки источника: «{text[:90]}» — добавьте [E…], [ПРОГНОЗ …] или [ГИП]"))
    return issues


LABEL_IN_BRACKETS_RE = re.compile(r"\[[^\]\n]*\b(ФАКТ|ГИП|ПРОГНОЗ|СИНТ)\b[^\]\n]*\]")


def _malformed_tags(files: dict[str, list[Line]]) -> list[Issue]:
    """Метка, которую нельзя разобрать (например [ГИП; СИНТ S1]), прячет ссылки от проверок."""
    issues = []
    for name, lines in files.items():
        for line in lines:
            parsed = {tag.label for tag in line.tags}
            for match in LABEL_IN_BRACKETS_RE.finditer(line.text):
                if match.group(1) not in parsed or match.group(0).count("[") > 1:
                    issues.append(Issue(ERROR, f"{name}:{line.num}", f"непонятная метка «{match.group(0)}» — "
                                        "по одной метке в скобках: [ГИП] [СИНТ S1], пояснение через двоеточие: [ГИП: …]"))
                    break
    return issues


def _synthetic_misuse(files: dict[str, list[Line]]) -> list[Issue]:
    issues = []
    for name, lines in files.items():
        for line in lines:
            synthetic_refs = [r for r in line.refs if r.startswith("S")]
            if not synthetic_refs:
                continue
            where = f"{name}:{line.num}"
            if "СИНТ" not in line.labels:
                issues.append(Issue(ERROR, where, f"синтетика {', '.join(synthetic_refs)} без метки [СИНТ …]"))
            if line.conclusion and "ГИП" not in line.labels:
                issues.append(Issue(ERROR, where, f"вывод {line.conclusion} опирается на синтетику — это может быть только [ГИП]"))
            if DEMAND_RE.search(line.text):
                issues.append(Issue(ERROR, where, "синтетика использована как доказательство спроса/распространённости — запрещено"))
    return issues


def _required_files(project: Path, files: dict[str, list[Line]], final: bool) -> list[Issue]:
    rows = stmod.parse_rows(stmod.read(project / "state" / "STATE.md"))
    reached = {r.num for r in rows if r.status in ("ждёт решения", "готов")}
    issues = []
    for stage, names in STAGE_FILES.items():
        if final or stage in reached:
            for name in names:
                if name not in files:
                    issues.append(Issue(ERROR, f"outputs/{name}", f"нет файла (нужен для этапа {stage})"))
    return issues


def _required_sections(files: dict[str, list[Line]]) -> list[Issue]:
    issues = []
    for name, needed in REQUIRED_SECTIONS.items():
        if name not in files:
            continue
        found = sections(files[name], r"^#{2,3}\s")
        for key in needed:
            match = next((title for title in found if key.lower() in title.lower()), None)
            if match is None:
                issues.append(Issue(ERROR, name, f"нет раздела «{key}…»"))
            elif not any(l.text.strip() and not l.text.strip().startswith("_") for l in found[match]):
                issues.append(Issue(ERROR, name, f"раздел «{match}» пустой"))
    return issues


def _options(lines: list[Line] | None) -> list[Issue]:
    if lines is None:
        return []
    variants = {t: body for t, body in sections(lines, r"^#{2,3}\s").items() if t.lower().startswith("вариант")}
    issues = []
    if len(variants) < 3:
        issues.append(Issue(ERROR, "options.md", f"вариантов {len(variants)}, нужно не меньше 3 (заголовки «## Вариант …»)"))
    titles = " | ".join(variants).lower()
    if not re.search(r"оставить как есть|статус[- ]кво|ничего не менять", titles):
        issues.append(Issue(ERROR, "options.md", "нет варианта «оставить как есть»"))
    if "закры" not in titles:
        issues.append(Issue(ERROR, "options.md", "нет варианта «закрыть направление»"))
    for title, body in variants.items():
        objection = [l for l in body if "возражени" in l.text.lower()]
        if not objection:
            issues.append(Issue(ERROR, "options.md", f"у «{title}» нет сильнейшего возражения"))
        if not any("истинн" in l.text.lower() for l in body):
            issues.append(Issue(WARN, "options.md", f"у «{title}» нет блока «что должно оказаться истинным»"))
    return issues


def _promises(files: dict[str, list[Line]]) -> list[Issue]:
    comms, product = files.get("comms-strategy.md"), files.get("product-strategy.md")
    if comms is None:
        return []
    capabilities = {l.capability for l in (product or []) if l.capability}
    promises = [l for l in comms if l.promise]
    issues = []
    if not promises:
        issues.append(Issue(ERROR, "comms-strategy.md", "нет пронумерованных обещаний (**О1.** … (опора: П1))"))
    for line in promises:
        where = f"comms-strategy.md:{line.num}"
        if not line.supports:
            issues.append(Issue(ERROR, where, f"обещание {line.promise} без опоры на возможность продукта (опора: П…)"))
        for cap in line.supports:
            if cap not in capabilities:
                issues.append(Issue(ERROR, where, f"обещание {line.promise} опирается на {cap}, которого нет в product-strategy.md"))
    return issues


def summarize(issues: list[Issue]) -> tuple[int, int]:
    errors = sum(1 for i in issues if i.level == ERROR)
    return errors, len(issues) - errors
