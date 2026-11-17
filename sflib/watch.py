"""Сторож оснований: заново открывает веб-источники записей реестра и проверяет, на месте ли цитата.

Решение держится на цитатах. Если страница изменилась так, что цитаты больше нет, решение могло потерять основание —
агент узнаёт об этом сам, а не когда кто-то случайно заметит. Сторож ничего не отзывает: он показывает,
какие выводы затронуты, а правку «было → стало» подтверждает человек (этап 8).
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from . import evidence as ev
from . import fetch
from . import graph as graph_mod
from .paths import SfError

SAME, CHANGED, UNAVAILABLE, NOT_COMPARABLE = "на месте", "ИЗМЕНИЛОСЬ", "недоступен", "не сравнить"
MIN_FRAGMENT = 12          # короче — слишком частые совпадения, такие куски не проверяем
MIN_PAGE_TEXT = 200        # меньше — страница собирается скриптами или пуста: это «недоступен», а не «изменилось»
URL_RE = re.compile(r"^- URL:\s*(https?://\S+)", re.MULTILINE)

Fetcher = Callable[[str], tuple[str, str]]   # url → (заголовок, текст); ошибки — SfError


@dataclass(frozen=True)
class Result:
    record_id: str
    url: str
    status: str
    detail: str
    conclusions: tuple[str, ...] = ()


def normalize(text: str) -> str:
    """Сравниваем смысл строки, а не типографику: HTML-коды (&nbsp;), разметку Markdown, регистр, ё, кавычки, тире, пробелы."""
    text = html.unescape(text)
    text = re.sub(r"[*_`]+", "", text)
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[«»“”„\"']", "", text)
    text = re.sub(r"[‐‑‒–—−]", "-", text)
    text = text.replace(" ", " ").replace("​", "")
    return re.sub(r"\s+", " ", text).strip()


def fragments(quote: str) -> list[str]:
    """Цитату с пропусками «…» проверяем по частям: каждая часть должна остаться на странице."""
    parts = re.split(r"…|\.\.\.|\[[^\]]*\]", normalize(quote))
    return [p.strip(" .,;:-") for p in parts if len(p.strip(" .,;:-")) >= MIN_FRAGMENT]


def quote_in(quote: str, text: str) -> bool | None:
    """True — все части цитаты есть в тексте; False — какой-то нет; None — цитата слишком короткая для проверки."""
    parts = fragments(quote)
    if not parts:
        return None
    haystack = normalize(text)
    return all(part in haystack for part in parts)


def url_for(project: Path, record: ev.Record) -> tuple[str, Path | None]:
    """URL записи и её сохранённый снимок: либо адрес прямо в источнике, либо строка «- URL:» в снимке."""
    if record.source.startswith(("http://", "https://")):
        named = re.search(r"sources/\S+\.md", record.locator)
        if named:
            return record.source, project / named.group(0)
        saved = sorted((project / "sources").glob(f"web-{fetch.slug_for(record.source)}-*.md"))
        return record.source, saved[-1] if saved else None
    path = project / record.source
    if path.suffix != ".md" or not path.exists():
        return "", None
    found = URL_RE.search(path.read_text(encoding="utf-8")[:2000])
    return (found.group(1), path) if found else ("", None)


def check(project: Path, fetcher: Fetcher, ids: list[str] | None = None) -> list[Result]:
    """Проверить действующие записи с веб-источником. Каждая страница загружается один раз."""
    records = [r for r in ev.load(project) if r.status == ev.ACTIVE and r.kind != "synthetic"]
    if ids:
        unknown = set(ids) - {r.id for r in records}
        if unknown:
            raise SfError(f"Нет действующих записей: {', '.join(sorted(unknown))}")
        records = [r for r in records if r.id in ids]
    graph = graph_mod.build(project)
    pages: dict[str, str | SfError] = {}
    results = []
    for record in records:
        url, snapshot = url_for(project, record)
        if not url:
            continue
        if url not in pages:
            try:
                text = fetcher(url)[1]
                pages[url] = text if len(text.strip()) >= MIN_PAGE_TEXT else SfError(
                    "страница без текста (собирается скриптами или пуста) — сравнить нельзя, проверьте вручную")
            except SfError as err:
                pages[url] = err
        page = pages[url]
        deps = tuple(graph.dependents_of(record.id))
        if isinstance(page, SfError):
            results.append(Result(record.id, url, UNAVAILABLE, str(page), deps))
            continue
        # Сравнивать есть смысл, только если цитата дословно была в нашем снимке: иначе это пересказ или выдержка,
        # и её отсутствие на живой странице ничего не говорит об изменении.
        baseline = quote_in(record.quote, snapshot.read_text(encoding="utf-8")) if snapshot and snapshot.exists() else None
        now = quote_in(record.quote, page)
        if now is None or baseline is False:
            why = "цитата слишком короткая" if now is None else "цитаты не было дословно и в нашем снимке"
            results.append(Result(record.id, url, NOT_COMPARABLE, why, deps))
        elif now:
            results.append(Result(record.id, url, SAME, "цитата найдена на живой странице", deps))
        else:
            results.append(Result(record.id, url, CHANGED, "цитаты больше нет на странице", deps))
    return results


def report(results: list[Result], today: date | None = None) -> str:
    """Отчёт для state/: что изменилось — первым, затем недоступное, затем остальное."""
    today = today or date.today()
    order = {CHANGED: 0, UNAVAILABLE: 1, NOT_COMPARABLE: 2, SAME: 3}
    counts = {s: sum(1 for r in results if r.status == s) for s in order}
    lines = [f"# Сторож оснований — {today.isoformat()}", "",
             f"Проверено записей: {len(results)} · изменилось: {counts[CHANGED]} · недоступно: {counts[UNAVAILABLE]} · "
             f"не сравнить: {counts[NOT_COMPARABLE]} · на месте: {counts[SAME]}", "",
             "| Запись | Статус | Затронутые выводы | Подробно |", "|---|---|---|---|"]
    for r in sorted(results, key=lambda r: (order[r.status], r.record_id)):
        lines.append(f"| {r.record_id} | {r.status} | {', '.join(r.conclusions) or '—'} | {r.detail[:120]} · {r.url} |")
    changed = [r.record_id for r in results if r.status == CHANGED]
    lines += ["", "## Что делать",
              f"Изменились: {', '.join(changed)}. Посмотреть затронутое: `sf.py revisit {' '.join(changed)}`; "
              "новые данные — этап 8 (навык decision-support), правки подтверждает человек." if changed
              else "Изменений в цитатах не найдено. Недоступные страницы проверьте позже — это не изменение."]
    return "\n".join(lines) + "\n"
