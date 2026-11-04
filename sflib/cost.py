"""Учёт стоимости и времени: cost.csv с честной пометкой method = факт | оценка | время.

факт   — токены из транскрипта Claude Code (usage каждого ответа модели), в долларах — API-эквивалент;
оценка — токены ≈ символы / chars_per_token (для сред без учёта токенов, например Cursor);
время  — минуты человека (ворота, правки) и длительность этапов по журналу.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path

from . import config, journal
from . import state as stmod
from .paths import SfError

FACT, ESTIMATE, TIME = "факт", "оценка", "время"
METHODS = (FACT, ESTIMATE, TIME)
MTOK = 1_000_000


@dataclass(frozen=True)
class Row:
    ts: str
    stage: str
    step: str
    role: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cache_read: int = 0
    cache_write: int = 0
    usd: float = 0.0
    seconds: int = 0
    method: str = FACT
    note: str = ""


FIELDS = [f.name for f in fields(Row)]


def _path(project: Path) -> Path:
    return project / "state" / "cost.csv"


def load(project: Path) -> list[Row]:
    path = _path(project)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        rows = []
        for raw in csv.DictReader(handle):
            rows.append(Row(
                ts=raw["ts"], stage=raw["stage"], step=raw["step"], role=raw["role"], model=raw["model"],
                tokens_in=int(raw["tokens_in"] or 0), tokens_out=int(raw["tokens_out"] or 0),
                cache_read=int(raw["cache_read"] or 0), cache_write=int(raw["cache_write"] or 0),
                usd=float(raw["usd"] or 0), seconds=int(raw["seconds"] or 0), method=raw["method"], note=raw["note"]))
        return rows


def append(project: Path, row: Row) -> Row:
    if row.method not in METHODS:
        raise SfError(f"method должен быть одним из: {', '.join(METHODS)}")
    path = _path(project)
    new_file = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(asdict(row))
    return row


def usd_for(model: str, tokens_in: int, tokens_out: int, cache_read: int = 0,
            cache_write_5m: int = 0, cache_write_1h: int = 0) -> float:
    p = config.price(model)
    total = (tokens_in * p["input"] + tokens_out * p["output"] + cache_read * p["cache_read"]
             + cache_write_5m * p["cache_write_5m"] + cache_write_1h * p["cache_write_1h"]) / MTOK
    return round(total, 6)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def current_stage(project: Path) -> str:
    row = stmod.current_stage(stmod.parse_rows(stmod.read(project / "state" / "STATE.md")))
    return str(row.num) if row else "8"


def add_estimate(project: Path, stage: str, step: str, role: str, model: str, chars_in: int, chars_out: int) -> Row:
    ratio = float(config.get("estimate", "chars_per_token", 3.0))
    t_in, t_out = round(chars_in / ratio), round(chars_out / ratio)
    usd = usd_for(model, t_in, t_out)
    return append(project, Row(_now(), stage, step, role, model, t_in, t_out, 0, 0, usd, 0, ESTIMATE,
                               f"символы {chars_in}/{chars_out}, коэффициент {ratio}"))


def add_human(project: Path, stage: str, minutes: float, note: str) -> Row:
    return append(project, Row(_now(), stage, "human", "человек", "-", seconds=round(minutes * 60), method=TIME, note=note))


# ---------- факт из транскрипта Claude Code ----------

@dataclass(frozen=True)
class Usage:
    message_id: str
    ts: str
    model: str
    sidechain: bool
    tokens_in: int
    tokens_out: int
    cache_read: int
    cache_write_5m: int
    cache_write_1h: int


def transcript_dir(root: Path) -> Path:
    """Папка транскриптов Claude Code для репозитория: путь, где всё, кроме латиницы и цифр, заменено на «-»."""
    return Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(root))


def read_usages(transcript: Path) -> list[Usage]:
    """Уникальные ответы модели с usage. Один ответ пишется несколькими строками — берём последнюю по id."""
    found: dict[str, Usage] = {}
    from_subagent_file = "subagents" in transcript.parts
    with transcript.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = data.get("message")
            if data.get("type") != "assistant" or not isinstance(message, dict) or not message.get("usage"):
                continue
            usage = message["usage"]
            creation = usage.get("cache_creation") or {}
            write_1h = int(creation.get("ephemeral_1h_input_tokens") or 0)
            write_5m = int(creation.get("ephemeral_5m_input_tokens") or 0)
            if not creation:
                write_5m = int(usage.get("cache_creation_input_tokens") or 0)
            key = message.get("id") or data.get("requestId") or data.get("uuid", "")
            sidechain = from_subagent_file or bool(data.get("isSidechain"))
            found[key] = Usage(key, data.get("timestamp", ""), message.get("model", "unknown"), sidechain,
                               int(usage.get("input_tokens") or 0), int(usage.get("output_tokens") or 0),
                               int(usage.get("cache_read_input_tokens") or 0), write_5m, write_1h)
    return list(found.values())


def _seen_path(project: Path) -> Path:
    return project / "state" / "cost_seen.txt"


def _project_start(project: Path) -> str:
    for entry in journal.read_entries(project / "state" / "log.md"):
        if entry.key == "project:create":
            return datetime.strptime(entry.ts, "%Y-%m-%d %H:%M:%S").astimezone().isoformat()
    return ""


def import_transcripts(project: Path, transcripts: list[Path], stage: str | None = None) -> list[Row]:
    """Добавляет в cost.csv факт по новым (ещё не учтённым) ответам модели, по одной строке на модель и роль."""
    seen_file = _seen_path(project)
    seen = set(seen_file.read_text(encoding="utf-8").split()) if seen_file.exists() else set()
    start = _project_start(project)
    fresh: list[Usage] = []
    for transcript in transcripts:
        for usage in read_usages(transcript):
            if usage.message_id in seen or (start and usage.ts and _iso(usage.ts) < start):
                continue
            fresh.append(usage)
    if not fresh:
        return []
    stage = stage or current_stage(project)
    groups: dict[tuple[str, str], list[Usage]] = {}
    for usage in fresh:
        role = "subagent" if usage.sidechain else "orchestrator"
        groups.setdefault((usage.model, role), []).append(usage)
    rows = []
    for (model, role), items in sorted(groups.items()):
        t_in, t_out = sum(u.tokens_in for u in items), sum(u.tokens_out for u in items)
        c_read = sum(u.cache_read for u in items)
        w5, w1 = sum(u.cache_write_5m for u in items), sum(u.cache_write_1h for u in items)
        try:
            usd = usd_for(model, t_in, t_out, c_read, w5, w1)
            note = f"{len(items)} ответов модели; API-эквивалент"
        except SfError:
            usd, note = 0.0, f"{len(items)} ответов; нет цены для {model} в config.toml"
        rows.append(append(project, Row(_now(), stage, "transcript", role, model, t_in, t_out, c_read, w5 + w1, usd, 0, FACT, note)))
    with seen_file.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(u.message_id for u in fresh) + "\n")
    return rows


def _iso(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().isoformat()
    except ValueError:
        return ts


# ---------- отчёт ----------

def stage_durations(project: Path) -> dict[str, int]:
    """Секунды работы агента по этапам: от STAGE start до STAGE done (суммируются повторные заходы)."""
    starts: dict[str, datetime] = {}
    totals: dict[str, int] = {}
    for entry in journal.read_entries(project / "state" / "log.md"):
        if entry.kind != "STAGE":
            continue
        parts = entry.key.split(":")
        if len(parts) != 3:
            continue
        _, num, action = parts
        moment = datetime.strptime(entry.ts, "%Y-%m-%d %H:%M:%S")
        if action == "start":
            starts.setdefault(num, moment)  # повторный start без done (доработка) не затирает начало
        elif action == "done" and num in starts:
            totals[num] = totals.get(num, 0) + int((moment - starts.pop(num)).total_seconds())
    return totals


def report(project: Path) -> str:
    rows = load(project)
    durations = stage_durations(project)
    stages = sorted({r.stage for r in rows} | set(durations), key=lambda s: int(s) if s.isdigit() else 99)
    head = "| Этап | Факт, $ (API-экв.) | Оценка, $ | Токены факт (вх/вых/кэш) | Агент, мин | Человек, мин |"
    lines = [head, "|---|---|---|---|---|---|"]
    tot = {"fact": 0.0, "est": 0.0, "agent": 0, "human": 0}
    for stage in stages:
        mine = [r for r in rows if r.stage == stage]
        fact = sum(r.usd for r in mine if r.method == FACT)
        est = sum(r.usd for r in mine if r.method == ESTIMATE)
        tok = (sum(r.tokens_in for r in mine if r.method == FACT), sum(r.tokens_out for r in mine if r.method == FACT),
               sum(r.cache_read + r.cache_write for r in mine if r.method == FACT))
        human = sum(r.seconds for r in mine if r.method == TIME)
        agent = durations.get(stage, 0)
        tot = {"fact": tot["fact"] + fact, "est": tot["est"] + est,
               "agent": tot["agent"] + agent, "human": tot["human"] + human}
        tokens = f"{tok[0]:,}/{tok[1]:,}/{tok[2]:,}".replace(",", " ")
        lines.append(f"| {stage} | {fact:.2f} | {est:.2f} | {tokens} | {agent / 60:.0f} | {human / 60:.0f} |")
    lines.append(f"| **Итого** | **{tot['fact']:.2f}** | **{tot['est']:.2f}** | | **{tot['agent'] / 60:.0f}** | **{tot['human'] / 60:.0f}** |")
    lines.append("")
    lines.append("Факт и оценка не складываются. Факт — по usage из транскрипта Claude Code в ценах API "
                 f"(config.toml, цены на {config.get('prices', 'checked', '?')}); при подписке реальные списания иные.")
    return "\n".join(lines)


def calibrate(chars: int, fact_tokens: int) -> float:
    """Коэффициент символов на токен по одному измерению с фактом."""
    if fact_tokens <= 0:
        raise SfError("Нужно положительное число фактических токенов.")
    return round(chars / fact_tokens, 3)
