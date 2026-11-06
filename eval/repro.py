"""Проверка воспроизводимости агента: детерминированная часть и разброс модели на этапе «Варианты».

1. Расчёты: каждый скрипт-источник записи calc запускается дважды — вывод должен совпасть, а числа записи
   должны найтись в выводе (с допуском на округление).
2. Варианты: независимые прогоны этапа 4 на одном входе (eval/reproducibility/run-*/options.md) сравниваются
   с исходным результатом: рекомендация, набор типов вариантов, обязательные элементы, опора на реестр, проверка формы.

Запуск из корня репозитория: python3 eval/repro.py  → eval/reproducibility/README.md (раздел «Результаты»)
"""
from __future__ import annotations

import csv
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sflib import validate  # noqa: E402

PROJECT = ROOT / "projects" / "demo-antifraud"
RUNS = ROOT / "eval" / "reproducibility"
NUM_RE = re.compile(r"\d[\d  ]*(?:[.,]\d+)?")
TOLERANCE = 0.02
TYPES = {  # тип варианта → слова в заголовке или строке теста различия
    "оставить": ("оставить", "как есть", "сохранить без"),
    "закрыть": ("закрыть", "закрытие", "свернуть"),
    "бесплатно в тарифе": ("бесплатн", "в тариф", "включить в"),
    "семейная защита": ("семей", "близк", "родител"),
    "компенсация потерь": ("компенсац", "страхов", "возмещ"),
    "B2B": ("b2b", "бизнес", "компани", "юрлиц"),
    "переупаковка / новая платная ценность": ("переупак", "премиум", "расширенн", "ии-", "анализ разговора", "дипфейк"),
    "цена": ("снизить цену", "дешевле", "скидк", "цену"),
}


def numbers(text: str) -> list[float]:
    out = []
    for raw in NUM_RE.findall(text):
        cleaned = raw.replace(" ", "").replace(" ", "").replace(",", ".")
        try:
            out.append(float(cleaned))
        except ValueError:
            continue
    return out


def calc_checks() -> list[tuple[str, str, bool, int, int]]:
    """(id, скрипт, вывод одинаков при двух запусках, найдено чисел, всего чисел записи вне скобок)."""
    rows = []
    with (PROJECT / "evidence.csv").open(encoding="utf-8") as handle:
        for rec in csv.DictReader(handle):
            if rec["kind"] != "calc" or rec["status"] != "active" or not rec["source"].endswith(".py"):
                continue
            script = PROJECT / rec["source"]
            runs = [subprocess.run([sys.executable, "-I", str(script)], capture_output=True, text=True, cwd=PROJECT).stdout
                    for _ in range(2)]
            claimed = numbers(re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", rec["quote"]))  # без входов в скобках и ссылок
            produced = numbers(runs[0])
            found = sum(any(abs(c - p) <= TOLERANCE * max(abs(c), 1) for p in produced) for c in claimed)
            rows.append((rec["id"], rec["source"], runs[0] == runs[1], found, len(claimed)))
    return rows + _report_checks()


def _report_checks() -> list[tuple[str, str, bool, int, int]]:
    """Отчёты sf.py behavior: пересчитать той же командой и сравнить с сохранённым файлом целиком."""
    from sflib import behavior
    rows = []
    with (PROJECT / "evidence.csv").open(encoding="utf-8") as handle:
        records = [r for r in csv.DictReader(handle) if r["kind"] == "calc" and r["status"] == "active" and r["source"].endswith("-churn.md")]
    for source in sorted({r["source"] for r in records}):
        saved = (PROJECT / source).read_text(encoding="utf-8")
        command = re.search(r"Расчёт: `sf.py behavior churn (\S+) --target (\S+) --positive (\S+)(?: --skip (\S+))?(?: --within (\S+))?(?: --where \"([^\"]+)\")?`", saved)
        data, target, positive, skip, within, where = command.groups()
        fresh = behavior.churn_report(PROJECT / "sources" / data, target, positive, (skip or "").split(",") if skip else [], within, where)
        ids = ", ".join(r["id"] for r in records if r["source"] == source)
        claimed = sum(1 for r in records if r["source"] == source for _ in [0])
        found = sum(1 for r in records if r["source"] == source and all(n in fresh for n in re.findall(r"\d+\.\d+%|\d+\.\d+ п", r["quote"])))
        rows.append((ids, source, fresh == saved, found, claimed))
    return rows


def _variant_blocks(text: str) -> list[str]:
    return [line for line in text.splitlines() if re.match(r"^#{2,3}\s*Вариант", line)]


def _types(text: str) -> set[str]:
    heads = " ".join(_variant_blocks(text)).lower()
    return {name for name, words in TYPES.items() if any(w in heads for w in words)}


def _recommended(text: str) -> str:
    """Явная строка «Рекомендуемый вариант: …» или первый вариант, названный в разделе рекомендации."""
    match = re.search(r"Рекомендуемый вариант:\s*(.+)", text)
    if match:
        return match.group(1).strip()
    section = re.search(r"^#{2,3}\s*Рекомендац[^\n]*\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    letter = re.search(r"вариант\s+([A-F])\b", section.group(1)) if section else None
    if not letter:
        return "не найдено"
    head = re.search(rf"^#{{2,3}}\s*Вариант\s+{letter.group(1)}\s*[—-]\s*(.+)$", text, re.MULTILINE)
    return f"{letter.group(1)} — {head.group(1).strip()}" if head else letter.group(1)


def _recommended_type(rec: str) -> set[str]:
    low = rec.lower()
    return {name for name, words in TYPES.items() if any(w in low for w in words)}


def _form_issues(options_text: str) -> list[str]:
    """validate на копии проекта, где вместо исходных вариантов — вариант прогона."""
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "p"
        shutil.copytree(PROJECT, copy, ignore=shutil.ignore_patterns("outputs"))
        (copy / "outputs").mkdir()
        shutil.copy2(PROJECT / "outputs" / "research.md", copy / "outputs" / "research.md")
        (copy / "outputs" / "options.md").write_text(options_text, encoding="utf-8")
        issues = validate.run(copy, final=False)
    return [str(i) for i in issues if i.level == validate.ERROR and "options.md" in i.where]


def _cited(text: str) -> set[str]:
    return set(re.findall(r"\bE\d+\b", text))


def compare() -> list[dict]:
    sources = {"исходный (этап 4 демо)": PROJECT / "outputs" / "options.md"}
    sources.update({p.parent.name: p for p in sorted(RUNS.glob("run-*/options.md"))})
    base_cited = _cited(sources["исходный (этап 4 демо)"].read_text(encoding="utf-8"))
    result = []
    for name, path in sources.items():
        text = path.read_text(encoding="utf-8")
        rec = _recommended(text)
        cited = _cited(text)
        result.append({
            "name": name, "variants": len(_variant_blocks(text)), "types": _types(text), "rec": rec,
            "rec_types": _recommended_type(rec), "keep": "оставить" in _types(text), "close": "закрыть" in _types(text),
            "errors": _form_issues(text), "cited": len(cited),
            "overlap": len(cited & base_cited) / len(cited | base_cited) if cited | base_cited else 0.0,
        })
    return result


def report() -> str:
    out = ["## Результаты", "", "### 1. Расчёты (детерминированная часть)", "",
           "| Запись | Скрипт или отчёт | Повтор дал тот же вывод | Числа записи найдены в выводе |", "|---|---|---|---|"]
    for rid, script, same, found, total in calc_checks():
        out.append(f"| {rid} | `{script}` | {'да' if same else 'НЕТ'} | {found} из {total} |")
    rows = compare()
    out += ["", "### 2. Этап «Варианты»: исходный результат и независимые прогоны", "",
            "| Прогон | Вариантов | «Оставить» и «закрыть» | Ошибок формы | Рекомендация | Совпадает с исходной | Ссылок на реестр | Общих ссылок с исходным |",
            "|---|---|---|---|---|---|---|---|"]
    base_types = rows[0]["rec_types"]
    for r in rows:
        same = "—" if r is rows[0] else ("да" if r["rec_types"] & base_types else "НЕТ")
        out.append(f"| {r['name']} | {r['variants']} | {'да' if r['keep'] and r['close'] else 'НЕТ'} | {len(r['errors'])} | "
                   f"{r['rec']} | {same} | {r['cited']} | {r['overlap']:.0%} |")
    agree = sum(1 for r in rows[1:] if r["rec_types"] & base_types)
    out += ["", f"**Рекомендация совпала с исходной в {agree} из {len(rows) - 1} независимых прогонов.**"]
    all_types = sorted(set().union(*(r["types"] for r in rows)))
    out += ["", "Типы вариантов (по заголовкам):", "", "| Тип | " + " | ".join(r["name"] for r in rows) + " |",
            "|---|" + "---|" * len(rows)]
    for kind in all_types:
        out.append(f"| {kind} | " + " | ".join("●" if kind in r["types"] else "" for r in rows) + " |")
    kinds = (("синтетика как довод спроса или основа вывода", ("синтетик",)), ("число без источника", ("число без метки",)),
             ("вывод без оснований", ("без оснований",)), ("неправильно оформленная метка", ("непонятная метка",)))
    out += ["", "Ошибки, которые поймала проверка формы (в обычной работе агент исправляет их до закрытия этапа — хук после записи):", "",
            "| Тип ошибки | " + " | ".join(r["name"] for r in rows) + " |", "|---|" + "---|" * len(rows)]
    for title, keys in kinds:
        out.append(f"| {title} | " + " | ".join(str(sum(any(k in e for k in keys) for e in r["errors"])) for r in rows) + " |")
    errors = [f"- {r['name']}: {e}" for r in rows for e in r["errors"]]
    if errors:
        out += ["", "<details><summary>Все ошибки</summary>", "", *errors, "", "</details>"]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    readme = RUNS / "README.md"
    head = readme.read_text(encoding="utf-8").split("## Результаты")[0] if readme.exists() else "# Воспроизводимость\n\n"
    readme.write_text(head.rstrip() + "\n\n" + report(), encoding="utf-8")
    print(report())
