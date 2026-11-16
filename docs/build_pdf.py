"""Сборка docs/DESCRIPTION.pdf из свёрстанного документа docs/description/index.html (альбомный А4) через Chrome без окна.

Запуск: python3 docs/build_pdf.py   (нужен Chrome или Chromium; без него откройте index.html и сохраните как PDF)
Перед сборкой проверяется, что на каждой странице содержимое не выходит за нижний колонтитул.
Текстовая версия того же содержания — docs/DESCRIPTION.md.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sflib import media  # noqa: E402

SOURCE = ROOT / "docs" / "description" / "index.html"
TARGET = ROOT / "docs" / "DESCRIPTION.pdf"
VIEWPORT = "--window-size=1123,794"   # альбомный А4 при 96 точках на дюйм
OVERFLOW_JS = """
var out=[];document.querySelectorAll('.page').forEach(function(pg,i){var f=pg.querySelector('.foot');
var lim=f?f.getBoundingClientRect().top-2:pg.getBoundingClientRect().bottom;var max=0;
pg.querySelectorAll('*').forEach(function(el){if(f&&(el===f||f.contains(el)))return;var r=el.getBoundingClientRect();
if(r.height>0&&r.bottom>max)max=r.bottom;});if(max>lim)out.push((i+1)+':+'+Math.round(max-lim)+'px');});
var p=document.createElement('pre');p.id='ovf';p.textContent=out.join(' ')||'OK';document.body.appendChild(p);
"""


def overflow(chrome: str) -> str:
    """«OK» или список «страница:+лишние пиксели» — содержимое зашло на колонтитул."""
    probe = SOURCE.with_name("_check.html")
    probe.write_text(SOURCE.read_text(encoding="utf-8").replace("</body>", f"<script>{OVERFLOW_JS}</script></body>"), encoding="utf-8")
    try:
        dom = subprocess.run([chrome, "--headless", "--disable-gpu", VIEWPORT, "--dump-dom", probe.as_uri()],
                             capture_output=True, text=True, timeout=120).stdout
    finally:
        probe.unlink(missing_ok=True)
    found = re.search(r'<pre id="ovf">([^<]*)', dom)
    return found.group(1) if found else "проверка не выполнилась"


def build() -> int:
    chrome = media.find_chrome()
    if not chrome:
        print(f"Chrome не найден — откройте {SOURCE.relative_to(ROOT)} в браузере и сохраните как PDF (альбомная ориентация, без полей).")
        return 1
    result = overflow(chrome)
    if result != "OK":
        print(f"Содержимое не помещается на страницах: {result}. Сократите текст и повторите.")
        return 1
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=4000",
                    f"--print-to-pdf={TARGET}", SOURCE.as_uri()], check=True, capture_output=True, timeout=180)
    print(f"Готово: {TARGET.relative_to(ROOT)} (вёрстка проверена: ничего не выходит за страницу)")
    return 0


if __name__ == "__main__":
    sys.exit(build())
