"""Поиск по базе знаний и памяти без внешних сервисов: по формулировке, по смыслу (теги и синонимы), по связям.

- формулировка: совпадение основ слов в заголовке, тегах и тексте;
- смысл: запрос расширяется группами синонимов из knowledge/INDEX.md («удержание» → «отток», «retention», «churn»);
- связи: к найденным темам добавляются связанные (поле related), с меньшим весом и пометкой «по связи».
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from . import paths

STEM_LEN = 5
WORD_RE = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)
FRONT_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
W_TITLE, W_TAG, W_BODY_CAP, W_RELATED, W_SYNONYM = 4, 3, 3, 0.4, 0.5


@dataclass(frozen=True)
class Doc:
    file: str
    title: str
    tags: tuple[str, ...]
    related: tuple[str, ...]
    body: str


@dataclass(frozen=True)
class Hit:
    doc: Doc
    score: float
    via: str          # «текст» | «смысл» | «связь с <тема>»
    snippet: str


def stem(word: str) -> str:
    return word.lower().replace("ё", "е")[:STEM_LEN]


def stems(text: str) -> set[str]:
    return {stem(w) for w in WORD_RE.findall(text) if len(w) > 2}


def _list(value: str) -> tuple[str, ...]:
    return tuple(v.strip() for v in value.strip().strip("[]").split(",") if v.strip())


def parse_doc(path: Path, root: Path) -> Doc:
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    match = FRONT_RE.match(text)
    body = text
    if match:
        body = text[match.end():]
        for line in match.group(1).splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip()
    title = meta.get("title") or next((l.lstrip("# ").strip() for l in body.splitlines() if l.startswith("#")), path.stem)
    return Doc(path.relative_to(root).as_posix(), title, _list(meta.get("tags", "")), _list(meta.get("related", "")), body)


def load_docs(root: Path | None = None) -> list[Doc]:
    root = root or paths.repo_root()
    folder = root / "knowledge"
    return [parse_doc(p, root) for p in sorted(folder.glob("*.md")) if p.name != "INDEX.md"]


def synonym_groups(root: Path | None = None) -> list[set[str]]:
    """Строки INDEX.md вида `- синонимы: удержание, отток, retention, churn`."""
    index = (root or paths.repo_root()) / "knowledge" / "INDEX.md"
    if not index.exists():
        return []
    groups = []
    for line in index.read_text(encoding="utf-8").splitlines():
        if line.strip().lower().startswith("- синонимы:"):
            words = line.split(":", 1)[1]
            groups.append({stem(w) for w in WORD_RE.findall(words)})
    return groups


def expand(query_stems: set[str], groups: list[set[str]]) -> set[str]:
    extra: set[str] = set()
    for group in groups:
        if query_stems & group:
            extra |= group
    return extra - query_stems


def _snippet(body: str, wanted: set[str]) -> str:
    for line in body.splitlines():
        clean = line.strip()
        if clean and not clean.startswith("#") and stems(clean) & wanted:
            return clean[:160]
    return next((l.strip()[:160] for l in body.splitlines() if l.strip() and not l.startswith("#")), "")


def idf_weights(docs: list[Doc]) -> dict[str, float]:
    """Редкое слово весит больше частого: log(1 + N / число тем со словом)."""
    counts: dict[str, int] = {}
    for doc in docs:
        for s in stems(doc.title + " " + " ".join(doc.tags) + " " + doc.body):
            counts[s] = counts.get(s, 0) + 1
    total = max(len(docs), 1)
    return {s: math.log(1 + total / c) for s, c in counts.items()}


def score(doc: Doc, wanted: set[str], idf: dict[str, float]) -> float:
    title, tags = stems(doc.title), stems(" ".join(doc.tags))
    body_counts: dict[str, int] = {}
    for word in WORD_RE.findall(doc.body):
        s = stem(word)
        if s in wanted:
            body_counts[s] = body_counts.get(s, 0) + 1
    total = 0.0
    for s in wanted:
        hit = W_TITLE * (s in title) + W_TAG * (s in tags) + min(body_counts.get(s, 0), W_BODY_CAP)
        total += hit * idf.get(s, 0.0)
    return total


def search(query: str, docs: list[Doc], groups: list[set[str]], limit: int = 5) -> list[Hit]:
    """Каждое слово запроса — понятие (само слово + синонимы). Итог умножается на долю покрытых понятий,
    чтобы тема, отвечающая на весь запрос, была выше темы, где много одного общего слова."""
    direct = stems(query)
    if not direct:
        return []
    idf = idf_weights(docs)
    concepts = [(s, expand({s}, groups)) for s in direct if idf.get(s) or expand({s}, groups)]
    concepts = concepts or [(s, set()) for s in direct]
    synonyms = set().union(*(syn for _, syn in concepts))
    hits: dict[str, Hit] = {}
    for doc in docs:
        s_direct = s_meaning = 0.0
        covered = 0
        for word, syn in concepts:
            part_direct = score(doc, {word}, idf)
            part_meaning = score(doc, syn, idf) * W_SYNONYM if syn else 0.0
            covered += (part_direct + part_meaning) > 0
            s_direct, s_meaning = s_direct + part_direct, s_meaning + part_meaning
        total = (s_direct + s_meaning) * covered / len(concepts)
        if total > 0:
            via = "текст" if s_direct >= s_meaning else "смысл"
            hits[doc.file] = Hit(doc, total, via, _snippet(doc.body, direct | synonyms))
    by_stem = {Path(d.file).stem: d for d in docs}
    for hit in sorted(hits.values(), key=lambda h: -h.score)[:limit]:
        for rel in hit.doc.related:
            target = by_stem.get(rel)
            if target and target.file not in hits:
                hits[target.file] = Hit(target, hit.score * W_RELATED, f"связь с «{hit.doc.title}»", _snippet(target.body, set()))
    return sorted(hits.values(), key=lambda h: -h.score)[:limit]


def broken_links(docs: list[Doc]) -> list[str]:
    names = {Path(d.file).stem for d in docs}
    return [f"{d.file}: связь «{r}» ведёт в никуда" for d in docs for r in d.related if r not in names]
