"""Сборка docs/DESCRIPTION.pdf из docs/DESCRIPTION.md: HTML со стилем и картинками → PDF через Chrome без окна.

Запуск: python3 docs/build_pdf.py   (нужен Chrome или Chromium; без них остаётся docs/DESCRIPTION.html)
"""
from __future__ import annotations

import base64
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sflib import media  # noqa: E402
from sflib.report import _md  # noqa: E402

DOCS = ROOT / "docs"
REPO_URL = "https://github.com/marrxse/product-factory-strategist/blob/main/"
IMAGE_RE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)\s*$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
MIME = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}

CSS = """
@page { size: A4; margin: 16mm 15mm 18mm; }
:root { --ink:#1d1d1f; --muted:#6e6e73; --line:#d2d2d7; --green:#00a04b; --purple:#731982; --tint:#f5f5f7; }
* { box-sizing: border-box; }
body { margin:0; color:var(--ink); background:#fff;
  font: 10.5pt/1.5 -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
h2 { font-size: 30pt; letter-spacing: -0.02em; line-height: 1.1; margin: 0 0 6pt; }
h3 { font-size: 15pt; letter-spacing: -0.01em; margin: 20pt 0 6pt; padding-top: 10pt; border-top: 1px solid var(--line);
  break-after: avoid; }
h4 { font-size: 11.5pt; margin: 12pt 0 4pt; break-after: avoid; }
p, li { margin: 4pt 0; }
a { color: var(--purple); text-decoration: none; }
b { font-weight: 650; }
code { font: 9pt "SF Mono", Menlo, Consolas, monospace; background: var(--tint); padding: 1px 4px; border-radius: 4px; }
pre { background: var(--tint); padding: 8pt 10pt; border-radius: 8px; white-space: pre-wrap; }
table { width: 100%; border-collapse: collapse; margin: 6pt 0 10pt; font-size: 9pt; break-inside: auto; }
th { text-align: left; font-weight: 650; color: var(--muted); border-bottom: 1.5px solid var(--ink); padding: 4pt 6pt; }
td { border-bottom: 1px solid var(--line); padding: 4pt 6pt; vertical-align: top; }
tr { break-inside: avoid; }
figure { margin: 10pt 0 14pt; break-inside: avoid; }
figure img { display: block; max-width: 100%; max-height: 215mm; width: auto; height: auto; margin: 0 auto;
  border-radius: 10px; border: 1px solid var(--line); }
figure { page-break-inside: avoid; }
figcaption { color: var(--muted); font-size: 8.5pt; margin-top: 4pt; }
.cover { break-after: page; }
.cover .eyebrow { color: var(--green); font-weight: 650; font-size: 11pt; margin: 0 0 8pt; }
.cover .lead { font-size: 13pt; color: var(--muted); max-width: 150mm; }
.cover dl { display: grid; grid-template-columns: 34mm 1fr; gap: 4pt 10pt; margin-top: 16pt; font-size: 10pt; }
.cover dt { color: var(--muted); }
.cover dd { margin: 0; }
"""


def _data_uri(src: str) -> str:
    path = (DOCS / src).resolve()
    return f"data:{MIME.get(path.suffix.lower(), 'application/octet-stream')};base64," + base64.b64encode(path.read_bytes()).decode()


def _links(html_text: str) -> str:
    def repl(match: re.Match) -> str:
        label, href = match.group(1), match.group(2)
        if not href.startswith(("http://", "https://", "#")):
            href = REPO_URL + str((DOCS / href).resolve().relative_to(ROOT)).replace("\\", "/")
        return f'<a href="{href}">{label}</a>'
    return LINK_RE.sub(repl, html_text)


def body_html(markdown: str) -> str:
    """Markdown → HTML; строки-картинки `![подпись](путь)` становятся встроенными рисунками."""
    parts, chunk = [], []
    for line in markdown.splitlines():
        image = IMAGE_RE.match(line)
        if not image:
            chunk.append(line)
            continue
        parts.append(_links(_md("\n".join(chunk), {}, [])))
        chunk = []
        parts.append(f'<figure><img src="{_data_uri(image["src"])}" alt="{image["alt"]}">'
                     f'<figcaption>{image["alt"]}</figcaption></figure>')
    parts.append(_links(_md("\n".join(chunk), {}, [])))
    return "\n".join(parts)


def build() -> Path:
    text = (DOCS / "DESCRIPTION.md").read_text(encoding="utf-8")
    cover, _, rest = text.partition("\n<!-- cover-end -->\n")
    html_doc = (f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Стратег Фабрики продуктов</title>'
                f"<style>{CSS}</style></head><body><section class=\"cover\">{body_html(cover)}</section>"
                f"{body_html(rest)}</body></html>")
    html_doc = html_doc.replace("<p>@eyebrow ", '<p class="eyebrow">').replace("<p>@lead ", '<p class="lead">')
    out_html = DOCS / "DESCRIPTION.html"
    out_html.write_text(html_doc, encoding="utf-8")
    chrome = media.find_chrome()
    if not chrome:
        print(f"Chrome не найден — собран только {out_html.relative_to(ROOT)}; откройте и сохраните как PDF.")
        return out_html
    out_pdf = DOCS / "DESCRIPTION.pdf"
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={out_pdf}",
                    out_html.as_uri()], check=True, capture_output=True, timeout=180)
    out_html.unlink()
    print(f"Готово: {out_pdf.relative_to(ROOT)}")
    return out_pdf


if __name__ == "__main__":
    build()
