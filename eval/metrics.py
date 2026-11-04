"""Автоматические метрики для сравнения результата агента и обычного чата (одинаковые правила для обоих).

Запуск: python3 eval/metrics.py <файл.md> [<файл.md> ...]   — файлы одного результата склеиваются.
Метрики — эвристики по тексту: они считают форму доказательности, а не правильность выводов.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sflib.validate import NUMBER_RE  # noqa: E402

SOURCE_RE = re.compile(r"\[(?:ФАКТ\s*)?[EЕ]\d+|https?://|\]\(https?://")
LABEL_RE = re.compile(r"\[(ГИП|ПРОГНОЗ|СИНТ)|гипотез|оценк[аи] агента|предполож", re.IGNORECASE)
OPTION_RE = re.compile(r"^#{2,4}\s*(вариант|опция|сценарий|option)\b|^\|\s*[A-EА-Е]\s*[—-]", re.IGNORECASE | re.MULTILINE)
KEYS = {
    "вариант «оставить как есть»": r"оставить как есть|статус[- ]кво|ничего не менять|без изменений",
    "вариант «закрыть»": r"закры\w*\s+(направлени|подписк|продукт|бесплатн)|закрыть\b",
    "раздел о пробелах": r"чего мы не знаем|не знаем|неизвестн|пробел",
    "сильнейшие возражения": r"возражени",
    "противоречия источников": r"противоречи",
    "план: база сравнения": r"контрольн|база сравнения|с чем сравниваем|сравниваем с",
    "план: срок": r"срок наблюдения|недел[ьи]\s|\d+\s*недел",
    "план: пороги решения": r"порог|остановить|продолжить",
    "план: нежелательные последствия": r"нежелательн|сторож|guardrail",
}


def sentences(text: str) -> list[str]:
    lines = [l for l in text.splitlines() if l.strip() and not l.strip().startswith(("#", "|---", "```"))]
    out = []
    for line in lines:
        out.extend(s for s in re.split(r"(?<=[.!?])\s+", line) if s.strip())
    return out


def measure(text: str) -> dict:
    numeric = [s for s in sentences(text) if NUMBER_RE.search(s)]
    sourced = [s for s in numeric if SOURCE_RE.search(s)]
    labeled = [s for s in numeric if not SOURCE_RE.search(s) and LABEL_RE.search(s)]
    bare = len(numeric) - len(sourced) - len(labeled)
    result = {
        "символов": len(text),
        "утверждений с числами": len(numeric),
        "из них с источником": len(sourced),
        "из них помечены как гипотеза/прогноз": len(labeled),
        "из них без источника и метки": bare,
        "доля чисел с источником или меткой": round((len(sourced) + len(labeled)) / len(numeric), 2) if numeric else None,
        "уникальных ссылок на источники": len(set(re.findall(r"\[[EЕ]\d+|https?://[^\s)\]]+", text))),
        "вариантов (заголовки/строки)": len(OPTION_RE.findall(text)),
    }
    result.update({k: bool(re.search(v, text, re.IGNORECASE)) for k, v in KEYS.items()})
    return result


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    text = "\n\n".join(Path(p).read_text(encoding="utf-8") for p in sys.argv[1:])
    print(json.dumps(measure(text), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
