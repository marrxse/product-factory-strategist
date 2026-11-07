"""Сборка docs/DESCRIPTION.pdf из свёрстанного документа docs/description/index.html (альбомный А4) через Chrome без окна.

Запуск: python3 docs/build_pdf.py   (нужен Chrome или Chromium; без него откройте index.html и сохраните как PDF)
Текстовая версия того же содержания — docs/DESCRIPTION.md.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sflib import media  # noqa: E402

SOURCE = ROOT / "docs" / "description" / "index.html"
TARGET = ROOT / "docs" / "DESCRIPTION.pdf"


def build() -> Path:
    chrome = media.find_chrome()
    if not chrome:
        print(f"Chrome не найден — откройте {SOURCE.relative_to(ROOT)} в браузере и сохраните как PDF (альбомная ориентация, без полей).")
        return SOURCE
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=4000",
                    f"--print-to-pdf={TARGET}", SOURCE.as_uri()], check=True, capture_output=True, timeout=180)
    print(f"Готово: {TARGET.relative_to(ROOT)}")
    return TARGET


if __name__ == "__main__":
    build()
