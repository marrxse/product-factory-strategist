"""Поиск попыток инъекций в источниках и секретов в репозитории."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

TEXT_SUFFIXES = {".md", ".txt", ".html", ".htm", ".csv", ".json", ".xml", ".yaml", ".yml", ".toml", ".py", ".mdc", ".tsv"}

INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+)?(the\s+)?(previous|prior|above)\s+(instructions|rules)", "ignore previous instructions"),
    (r"игнорир\w*\s+(все\s+)?(предыдущ|прежн|вышеуказанн)\w*\s+(инструкц|правил)", "игнорируй инструкции"),
    (r"(disregard|forget)\s+(your|all)\s+(instructions|rules)", "disregard instructions"),
    (r"\byou\s+are\s+now\b", "you are now"),
    (r"\bты\s+теперь\b", "ты теперь"),
    (r"<\s*/?\s*system\s*>|\[system\]|system\s+prompt", "системный промпт"),
    (r"(do\s+not|don't)\s+tell\s+the\s+user|не\s+сообщай\s+пользовател", "скрыть от пользователя"),
    (r"(выполни|запусти|execute|run)\s+(команд|the\s+command|this\s+command)", "выполнить команду"),
    (r"rm\s+-rf|curl\s+[^\n|]*\|\s*(ba)?sh|wget\s+[^\n|]*\|\s*(ba)?sh", "опасная команда"),
    (r"(отправь|перешли|send|email)\s[^\n]{0,40}(ключ|пароль|token|api\s*key|password|secret)", "вывод секретов"),
    (r"(new|новые)\s+(instructions|инструкции)\s*:", "новые инструкции"),
    (r"(as\s+an?\s+ai|как\s+ии)[^\n]{0,30}(must|должен)", "указание ИИ"),
]
INJECTION_RES = [(re.compile(p, re.IGNORECASE), name) for p, name in INJECTION_PATTERNS]

SECRET_PATTERNS = [
    (r"sk-ant-[A-Za-z0-9_\-]{20,}", "ключ Anthropic"),
    (r"\bsk-[A-Za-z0-9]{32,}", "ключ OpenAI-подобный"),
    (r"\bghp_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}", "токен GitHub"),
    (r"\bAKIA[0-9A-Z]{16}\b", "ключ AWS"),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "приватный ключ"),
    (r"\bxox[baprs]-[A-Za-z0-9-]{10,}", "токен Slack"),
    (r"(api[_-]?key|secret|token|password|пароль)\s*[:=]\s*['\"][^'\"\s]{12,}['\"]", "секрет в присваивании"),
]
SECRET_RES = [(re.compile(p, re.IGNORECASE), name) for p, name in SECRET_PATTERNS]


def injections_in_text(text: str) -> list[tuple[int, str, str]]:
    found = []
    for num, line in enumerate(text.splitlines(), start=1):
        for regex, name in INJECTION_RES:
            if regex.search(line):
                found.append((num, name, line.strip()[:160]))
                break
    return found


def injections(folder: Path) -> list[tuple[str, int, str, str]]:
    """(файл относительно folder, строка, тип, цитата) для всех текстовых файлов папки."""
    result = []
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="replace")
            result.extend((str(path.relative_to(folder)), n, name, quote) for n, name, quote in injections_in_text(text))
    return result


def _candidate_files(root: Path) -> list[Path]:
    """Файлы, которые попадут в git: отслеживаемые и неигнорируемые. Без git — все, кроме .git."""
    try:
        out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=root,
                             capture_output=True, text=True, check=True, timeout=20).stdout
        return [root / rel for rel in out.splitlines() if rel]
    except (OSError, subprocess.SubprocessError):
        return [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]


def secrets(root: Path) -> list[tuple[str, int, str]]:
    found = []
    for path in _candidate_files(root):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES | {".env", ""}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for num, line in enumerate(text.splitlines(), start=1):
            for regex, name in SECRET_RES:
                if regex.search(line):
                    found.append((str(path.relative_to(root)), num, name))
                    break
    return found
