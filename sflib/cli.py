"""Командная строка `python3 sf.py <команда>`. Каждая команда — маленькая функция."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import cli_extra, cli_research, journal, media, paths, project, validate
from . import stages as st
from . import state as stmod

EXIT_ALREADY_DONE = 3


def cmd_new(args: argparse.Namespace) -> int:
    example = Path(args.source).resolve() if args.source else None
    target = project.create(args.slug, args.title or args.slug, example)
    print(f"Создан проект {target.relative_to(paths.repo_root()).as_posix()} и сделан активным.")
    print("Дальше: этап 0 — постановка задачи (skills/intake/SKILL.md).")
    return 0


def cmd_use(args: argparse.Namespace) -> int:
    paths.set_active(args.slug)
    print(f"Активный проект: {args.slug}")
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    active = paths.get_active()
    names = project.list_projects()
    if not names:
        print("Проектов нет. Создайте: python3 sf.py new <имя> --title \"...\"")
    for name in names:
        print(("* " if name == active else "  ") + name)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    if not args.project and not paths.get_active():
        # Первый запуск свежей копии — это не ошибка, а начало: подсказываем, с чего начать
        existing = sorted(p.name for p in paths.projects_dir().iterdir() if p.is_dir()) if paths.projects_dir().is_dir() else []
        lines = ["Активного проекта пока нет — это нормально для первого запуска.",
                 "Начать новую задачу: напишите агенту «начни <тема>» (или python3 sf.py new <имя> --title \"<тема>\")."]
        if existing:
            lines.append(f"Посмотреть готовый пример: python3 sf.py use {existing[0]} — затем «покажи состояние» "
                         f"(есть: {', '.join(existing)}).")
        print("\n".join(lines))
        return 0
    print(project.summary(paths.project_dir(args.project)))
    return 0


def cmd_stage(args: argparse.Namespace) -> int:
    proj = paths.project_dir(args.project)
    stage = st.get_stage(args.num)
    state_path = proj / "state" / "STATE.md"
    rows = stmod.parse_rows(stmod.read(state_path))
    if args.action == "start":
        rows = stmod.update_row(rows, stage.num, status=st.IN_PROGRESS)
    else:
        errors = [i for i in validate.run(proj) if i.level == validate.ERROR]
        if errors and not args.force:
            print(f"Этап {stage.num} не закрыт: validate нашёл ошибок {len(errors)} (первая: {errors[0]}). "
                  "Исправьте или закройте осознанно: --force \"причина\".")
            return 1
        if errors:
            journal.append(proj / "state" / "log.md", "NOTE", f"stage:{stage.num}:force", f"закрыт с ошибками: {args.force}")
        new_status = st.AWAITING if stage.has_gate else st.DONE
        new_gate = st.GATE_PENDING if stage.has_gate else st.NO_GATE
        rows = stmod.update_row(rows, stage.num, status=new_status, gate=new_gate)
    stmod.write_rows(state_path, rows)
    journal.append(proj / "state" / "log.md", "STAGE", f"stage:{stage.num}:{args.action}", f"{stage.title}: {args.action}")
    tail = " — покажите результат человеку и ждите решения." if args.action == "done" and stage.has_gate else ""
    print(f"Этап {stage.num} ({stage.title}): {args.action}{tail}")
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    proj = paths.project_dir(args.project)
    stage = st.get_stage(args.num)
    if not stage.has_gate:
        raise paths.SfError(f"У этапа {stage.num} нет ворот.")
    state_path = proj / "state" / "STATE.md"
    rows = stmod.parse_rows(stmod.read(state_path))
    if args.decision == "ok":
        rows = stmod.update_row(rows, stage.num, status=st.DONE, gate=st.GATE_OK)
    else:
        rows = stmod.update_row(rows, stage.num, status=st.IN_PROGRESS, gate=st.GATE_FIX)
    stmod.write_rows(state_path, rows)
    note = args.note or ""
    journal.append(proj / "state" / "log.md", "GATE", f"gate:{stage.num}", f"{args.decision} {note}".strip())
    print(f"Ворота этапа {stage.num}: {'одобрено' if args.decision == 'ok' else 'нужны правки'}")
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    proj = paths.project_dir(args.project)
    log_path = proj / "state" / "log.md"
    key = journal.normalize_key(args.key)
    entries = journal.read_entries(log_path)
    status = journal.last_status(entries, key)

    if args.action == "check":
        print(status or "нет")
        return 0
    if args.action == "start":
        if status == "DONE" and not args.repeat:
            print(f"Шаг «{key}» уже выполнен. Не повторяйте его; если повтор нужен — добавьте --repeat \"причина\".")
            return EXIT_ALREADY_DONE
        kind = "REPEAT" if status == "DONE" else "START"
        text = f"{args.text} (повтор: {args.repeat})" if kind == "REPEAT" else args.text
        journal.append(log_path, kind, key, text)
    else:
        journal.append(log_path, args.action.upper(), key, args.text)
    print(f"log: {args.action} {key}")
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    root = paths.repo_root()
    problems = []
    if sys.version_info < (3, 11):
        problems.append("Нужен Python 3.11+ (используется tomllib).")
    for rel in ("AGENTS.md", "config.toml", "templates/project/state/STATE.md", ".gitignore"):
        if not (root / rel).exists():
            problems.append(f"Нет файла {rel}")
    gitignore = (root / ".gitignore").read_text(encoding="utf-8") if (root / ".gitignore").exists() else ""
    if ".env" not in gitignore:
        problems.append(".env не указан в .gitignore")
    if problems:
        print("Найдены проблемы:\n" + "\n".join(f"  - {p}" for p in problems))
        return 1
    print(f"OK: Python {sys.version.split()[0]}, структура репозитория на месте. Активный проект: {paths.get_active() or 'нет'}")
    optional = ", ".join(f"{name} {'есть' if ok else 'нет'}" for name, ok in media.tools().items())
    print(f"Необязательные программы для медиа: {optional}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sf.py", description="Стратег Фабрики продуктов — служебные команды агента")
    parser.add_argument("--project", "-p", help="имя проекта (по умолчанию активный)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new", help="создать проект из шаблона")
    p.add_argument("slug")
    p.add_argument("--title", help="человекочитаемое название")
    p.add_argument("--from", dest="source", help="папка примера с brief.md и sources/")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("use", help="сделать проект активным")
    p.add_argument("slug")
    p.set_defaults(func=cmd_use)

    sub.add_parser("list", help="список проектов").set_defaults(func=cmd_list)
    sub.add_parser("status", help="сводка: этап, ворота, незавершённые шаги").set_defaults(func=cmd_status)
    sub.add_parser("doctor", help="проверить окружение").set_defaults(func=cmd_doctor)

    p = sub.add_parser("stage", help="отметить начало/конец этапа")
    p.add_argument("num", type=int)
    p.add_argument("action", choices=("start", "done"))
    p.add_argument("--force", help="закрыть этап, несмотря на ошибки validate (причина пишется в журнал)")
    p.set_defaults(func=cmd_stage)

    p = sub.add_parser("gate", help="решение человека на воротах")
    p.add_argument("num", type=int)
    p.add_argument("decision", choices=("ok", "fix"))
    p.add_argument("note", nargs="?", default="")
    p.set_defaults(func=cmd_gate)

    p = sub.add_parser("log", help="журнал шагов с ключами")
    p.add_argument("action", choices=("start", "done", "fail", "skip", "note", "check", "correction", "injection", "route"))
    p.add_argument("key")
    p.add_argument("text", nargs="?", default="")
    p.add_argument("--repeat", help="причина осознанного повтора выполненного шага")
    p.set_defaults(func=cmd_log)

    cli_research.register(sub)
    cli_extra.register(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (paths.SfError, ValueError) as err:
        print(f"Ошибка: {err}", file=sys.stderr)
        return 1
