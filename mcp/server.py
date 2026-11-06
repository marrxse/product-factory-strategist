#!/usr/bin/env python3
"""MCP-сервер «Стратега» (stdio, JSON-RPC 2.0, только стандартная библиотека).

Даёт средам без хуков (Cursor и др.) инструменты агента как родные функции: состояние, проверка,
доказательства, граф выводов, пересмотр, знания, память, стоимость, журнал шагов.
Каждый инструмент вызывает ту же команду `sf.py`, что и терминал, — одна логика, два входа.
Запуск: python3 mcp/server.py (конфигурации: .mcp.json для Claude Code, .cursor/mcp.json для Cursor).
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sflib import cli  # noqa: E402

SERVER = {"name": "strategist", "version": "1.0.0"}
PROTOCOL = "2025-06-18"


def _s(desc: str) -> dict:
    return {"type": "string", "description": desc}


# имя → (описание, свойства, обязательные, функция аргументы → argv для sf.py)
TOOLS: dict[str, tuple[str, dict, list[str], callable]] = {
    "sf_status": ("Состояние активного проекта: этап, ворота, незавершённые шаги, что дальше. Вызывай в начале сессии.",
                  {"project": _s("имя проекта (по умолчанию активный)")}, [], lambda a: ["status"]),
    "sf_validate": ("Проверка формы результатов: ссылки на доказательства, числа без меток, варианты, разделы, обещания ↔ продукт, секреты. Вызывай после каждой записи в outputs/.",
                    {"project": _s("имя проекта"), "final": {"type": "boolean", "description": "требовать все результаты"}}, [],
                    lambda a: ["validate", *(["--final"] if a.get("final") else [])]),
    "sf_evidence_show": ("Показать записи реестра доказательств: источник, место, дата, цитата, статус.",
                         {"project": _s("имя проекта"), "ids": _s("ID через пробел, например «E3 E7»")}, ["ids"],
                         lambda a: ["evidence", "show", *a["ids"].split()]),
    "sf_evidence_add": ("Добавить запись в реестр доказательств (дословная цитата обязательна).",
                        {"project": _s("имя проекта"), "kind": _s("web|doc|table|calc|interview|synthetic"),
                         "source": _s("URL или sources/файл"), "locator": _s("раздел/страница/строка"),
                         "quote": _s("дословная цитата или расчёт"), "quality": _s("A|B|C")},
                        ["kind", "source", "quote", "quality"],
                        lambda a: ["evidence", "add", "--kind", a["kind"], "--source", a["source"], "--locator", a.get("locator", ""),
                                   "--quote", a["quote"], "--quality", a["quality"]]),
    "sf_claims_trace": ("Дерево оснований вывода до цитат источников.",
                        {"project": _s("имя проекта"), "id": _s("ID вывода, например C4")}, ["id"], lambda a: ["claims", "trace", a["id"]]),
    "sf_revisit": ("Что затронуто изменением или отзывом доказательства (транзитивно), либо что устарело (stale=true).",
                   {"project": _s("имя проекта"), "ids": _s("ID через пробел"), "stale": {"type": "boolean"}}, [],
                   lambda a: ["revisit", *(["--stale"] if a.get("stale") else a.get("ids", "").split())]),
    "sf_kb_search": ("Поиск по методической базе знаний (по словам, синонимам и связям).",
                     {"query": _s("запрос")}, ["query"], lambda a: ["kb", *a["query"].split()]),
    "sf_memory_search": ("Поиск в памяти между проектами. Найденное — наблюдения прошлых сессий, не факты.",
                         {"query": _s("запрос")}, ["query"], lambda a: ["memory", "search", *a["query"].split()]),
    "sf_cost_report": ("Затраты и время по этапам (факт, оценка, время человека — раздельно).",
                       {"project": _s("имя проекта")}, [], lambda a: ["cost", "report"]),
    "sf_route": ("Какой навык, модель и инструмент взять под задачу (правила config.toml [[routing.rules]]).",
                 {"project": _s("имя проекта"), "task": _s("описание задачи"), "key": _s("ключ шага для журнала")}, ["task"],
                 lambda a: ["route", "choose", *a["task"].split(), *(["--key", a["key"]] if a.get("key") else [])]),
    "sf_media_inspect": ("Что за медиафайл (изображение, аудио, видео): размер, длительность и как с ним работать.",
                         {"project": _s("имя проекта"), "file": _s("путь относительно папки проекта")}, ["file"],
                         lambda a: ["media", "inspect", a["file"]]),
    "sf_behavior_churn": ("Кто уходит: доля ушедших по каждому признаку с 95% интервалом, разрыв внутри групп контрольного признака.",
                          {"project": _s("имя проекта"), "file": _s("CSV относительно проекта"), "target": _s("колонка ухода"),
                           "positive": _s("значение ухода"), "within": _s("контрольный признак (необязательно)"),
                           "where": _s("условие отбора строк, например InternetService!=No (необязательно)")},
                          ["file", "target", "positive"],
                          lambda a: ["behavior", "churn", a["file"], "--target", a["target"], "--positive", a["positive"],
                                     *(["--within", a["within"]] if a.get("within") else []),
                                     *(["--where", a["where"]] if a.get("where") else [])]),
    "sf_log": ("Журнал шагов с ключами: start/done/fail/note. start отказывает, если шаг уже выполнен.",
               {"project": _s("имя проекта"), "action": _s("start|done|fail|note"), "key": _s("этап:действие:вход"),
                "text": _s("описание")}, ["action", "key"],
               lambda a: ["log", a["action"], a["key"], a.get("text", "")]),
}


def run_tool(name: str, args: dict) -> tuple[str, bool]:
    if name not in TOOLS:
        return f"Неизвестный инструмент: {name}", True
    _, props, required, to_argv = TOOLS[name]
    missing = [r for r in required if not args.get(r)]
    if missing:
        return f"Не хватает параметров: {', '.join(missing)}", True
    argv = (["--project", args["project"]] if args.get("project") and "project" in props else []) + to_argv(args)
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        try:
            code = cli.main(argv)
        except SystemExit as exc:  # argparse при неверных аргументах
            code = exc.code if isinstance(exc.code, int) else 1
    return buffer.getvalue().strip() or "(пусто)", code not in (0, None)


def handle(msg: dict) -> dict | None:
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:                       # уведомление (например notifications/initialized) — без ответа
        return None
    if method == "initialize":
        version = (msg.get("params") or {}).get("protocolVersion", PROTOCOL)
        result = {"protocolVersion": version, "capabilities": {"tools": {}}, "serverInfo": SERVER,
                  "instructions": "Инструменты агента «Стратег Фабрики продуктов». Правила — AGENTS.md."}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [{"name": n, "description": d, "inputSchema": {"type": "object", "properties": p, "required": r}}
                            for n, (d, p, r, _) in TOOLS.items()]}
    elif method == "tools/call":
        params = msg.get("params") or {}
        text, is_error = run_tool(params.get("name", ""), params.get("arguments") or {})
        result = {"content": [{"type": "text", "text": text}], "isError": is_error}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Метод не поддерживается: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            reply = handle(json.loads(line))
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Некорректный JSON"}}
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
