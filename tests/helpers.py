"""Общие помощники тестов: временная копия репозитория через SF_ROOT."""
from __future__ import annotations

import io
import os
import shutil
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from sflib import cli

REPO = Path(__file__).resolve().parent.parent


class TempRepo:
    """Временный корень с шаблонами; SF_ROOT указывает на него на время теста."""

    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        shutil.copytree(REPO / "templates", root / "templates")
        for name in ("AGENTS.md", "config.toml", ".gitignore"):
            shutil.copy2(REPO / name, root / name)
        (root / "projects").mkdir()
        self._old = os.environ.get("SF_ROOT")
        os.environ["SF_ROOT"] = str(root)
        return root

    def __exit__(self, *exc: object) -> None:
        if self._old is None:
            os.environ.pop("SF_ROOT", None)
        else:
            os.environ["SF_ROOT"] = self._old
        self._tmp.cleanup()


def run(*argv: str) -> tuple[int, str]:
    """Запускает CLI и возвращает (код выхода, stdout+stderr)."""
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        code = cli.main(list(argv))
    return code, buffer.getvalue()
