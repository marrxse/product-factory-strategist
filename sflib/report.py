"""Отчёт для руководителя: один самодостаточный HTML из outputs/ — метки превращаются в сноски и значки.

[E7] → сноска с цитатой, источником и датой; [ГИП]/[ПРОГНОЗ]/[СИНТ] → цветные значки; **C4.** → якорь; [C4] → ссылка.
Реестр доказательств, затраты и качество — приложения. Служебная разметка в тексте руководителю не видна.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from . import cost, evidence as ev
from . import state as stmod
from .markup import TAG_RE, REF

ORDER = ("decision-brief.md", "research.md", "behavior.md", "ux-review.md", "options.md", "product-strategy.md", "comms-strategy.md",
         "validation-plan.md", "quality-report.md")
TITLES = {"decision-brief.md": "Решение", "research.md": "Исследование", "behavior.md": "Поведение клиентов", "ux-review.md": "Анализ интерфейса", "options.md": "Варианты",
          "product-strategy.md": "Продуктовая стратегия", "comms-strategy.md": "Коммуникационная стратегия",
          "validation-plan.md": "План проверки", "quality-report.md": "Отчёт о качестве"}
BADGE = {"ГИП": ("гипотеза", "hyp"), "ПРОГНОЗ": ("прогноз", "fc"), "СИНТ": ("синтетика", "syn"), "ФАКТ": ("факт", "fact")}

CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1f;--muted:#6b6b70;--line:#e3e1db;--card:#fff;--accent:#2f5d8a;
--hyp:#fff1d6;--hyp-fg:#7a4b00;--fc:#e7efff;--fc-fg:#24467a;--syn:#f6e6ff;--syn-fg:#6a2a8a;--fact:#e6f5ea;--fact-fg:#1d6b37}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#161618;--fg:#ececec;--muted:#a0a0a6;--line:#2c2c30;--card:#1e1e21;--accent:#8bb6e6;
--hyp:#3d2f12;--hyp-fg:#f1c46b;--fc:#1a2a44;--fc-fg:#9cc0f5;--syn:#33203d;--syn-fg:#d8a6f2;--fact:#173523;--fact-fg:#8fdaa5;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#161618;--fg:#ececec;--muted:#a0a0a6;--line:#2c2c30;--card:#1e1e21;--accent:#8bb6e6;
--hyp:#3d2f12;--hyp-fg:#f1c46b;--fc:#1a2a44;--fc-fg:#9cc0f5;--syn:#33203d;--syn-fg:#d8a6f2;--fact:#173523;--fact-fg:#8fdaa5;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 -apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 80px}h1{font-size:28px;margin:8px 0 4px}h2{font-size:22px;margin:36px 0 8px;
border-bottom:1px solid var(--line);padding-bottom:6px}h3{font-size:17px;margin:22px 0 6px}p,li{margin:6px 0}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:14px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}th{background:var(--card)}
.meta{color:var(--muted);font-size:14px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:14px 0}
.b{display:inline-block;font-size:11px;font-weight:600;border-radius:6px;padding:1px 6px;margin:0 2px;vertical-align:1px;white-space:nowrap}
.hyp{background:var(--hyp);color:var(--hyp-fg)}.fc{background:var(--fc);color:var(--fc-fg)}.syn{background:var(--syn);color:var(--syn-fg)}
.fact{background:var(--fact);color:var(--fact-fg)}sup a,a.ref{color:var(--accent);text-decoration:none;font-size:12px}
.concl{scroll-margin-top:12px}.rev{text-decoration:line-through;color:var(--muted)}nav a{color:var(--accent);margin-right:12px;font-size:14px}
blockquote{margin:8px 0;padding:4px 12px;border-left:3px solid var(--line);color:var(--muted)}code{font-size:13px}
.legend span{margin-right:10px}.print-only{display:none}
@page{size:A4;margin:16mm 15mm 18mm;@bottom-right{content:counter(page) " / " counter(pages);font:9px -apple-system,Segoe UI,Roboto,sans-serif;color:#6b6b70}
@bottom-left{content:"Отчёт агента «Стратег Фабрики продуктов»";font:9px -apple-system,Segoe UI,Roboto,sans-serif;color:#6b6b70}}
@media print{:root,:root[data-theme="dark"]{--bg:#fff;--fg:#1d1d1f;--muted:#6b6b70;--line:#d9d7d0;--card:#fafaf8;--accent:#2f5d8a;
--hyp:#fff1d6;--hyp-fg:#7a4b00;--fc:#e7efff;--fc-fg:#24467a;--syn:#f6e6ff;--syn-fg:#6a2a8a;--fact:#e6f5ea;--fact-fg:#1d6b37;color-scheme:light}
html,body{background:#fff;-webkit-print-color-adjust:exact;print-color-adjust:exact}body{font-size:10.5pt;line-height:1.45}
main{max-width:none;padding:0}h1{font-size:22pt}h2{font-size:15pt;margin-top:0}h3{font-size:12pt;break-after:avoid}
section{break-before:page}section#decision-brief{break-before:auto}h2#evidence,h2#cost{break-before:page}
table{display:table;font-size:8.6pt;break-inside:auto}thead{display:table-header-group}tr{break-inside:avoid}
td,th{padding:4px 6px;overflow-wrap:anywhere}.card{break-inside:auto;border-radius:6px}
nav{display:block;columns:2;margin:10px 0 0;padding:10px 12px;border:1px solid var(--line);border-radius:6px}nav a{display:block;margin:2px 0;font-size:10pt}
.screen-only{display:none}.print-only{display:inline}p,li{orphans:3;widows:3}
th:first-child,td:first-child{min-width:20mm}
table.ev{table-layout:fixed}table.ev th:nth-child(1){width:11mm}table.ev th:nth-child(3){width:42mm}
table.ev th:nth-child(4){width:20mm}table.ev th:nth-child(5){width:25mm}table.ev td:first-child,table.ev th:first-child{min-width:0}}
"""


def _inline(text: str, records: dict, used: list[str]) -> str:
    """Экранирует текст и превращает метки в сноски/значки, **жирный** и `код` — в HTML."""
    out, pos = [], 0
    for match in TAG_RE.finditer(text):
        out.append(_plain(text[pos:match.start()]))
        out.append(_tag_html(match, records, used))
        pos = match.end()
    out.append(_plain(text[pos:]))
    return "".join(out)


def _plain(text: str) -> str:
    s = html.escape(text)
    s = re.sub(r"\*\*([CС]\d+)\.\*\*", lambda m: f'<b class="concl" id="{m.group(1)}">{m.group(1)}.</b>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def _tag_html(match: re.Match, records: dict, used: list[str]) -> str:
    label = match.group("label") or ""
    refs = re.findall(REF, match.group("refs") or "")
    comment = (match.group("comment") or "").lstrip(" :").strip()
    parts = []
    if label in BADGE and label != "ФАКТ":
        name, cls = BADGE[label]
        title = f' title="{html.escape(comment)}"' if comment else ""
        parts.append(f'<span class="b {cls}"{title}>{name}</span>')
    links = []
    for ref in refs:
        ref = ref.replace("Е", "E").replace("С", "C")
        if ref.startswith("C"):
            links.append(f'<a class="ref" href="#{ref}">{ref}</a>')
            continue
        if ref not in used:
            used.append(ref)
        rec = records.get(ref)
        tip = html.escape(f"«{rec.quote[:200]}» — {rec.source}") if rec else "нет в реестре"
        links.append(f'<a href="#ev-{ref}" title="{tip}">{used.index(ref) + 1}</a>')
    if links:
        parts.append("<sup>[" + ", ".join(links) + "]</sup>")
    return "".join(parts)


def _md(text: str, records: dict, used: list[str]) -> str:
    """Минимальный Markdown: заголовки, списки, таблицы, цитаты, абзацы (комментарии HTML отбрасываются)."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    lines, out, i = text.splitlines(), [], 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(lines[i + 1:j])) + "</code></pre>")
            i = j + 1
            continue
        head = re.match(r"^(#{1,4})\s+(.*)", line)
        if head:
            level = min(len(head.group(1)) + 1, 4)
            out.append(f"<h{level}>{_inline(head.group(2), records, used)}</h{level}>")
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[\s\-:|]+\|?$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            if rows:
                head_row = "".join(f"<th>{_inline(c, records, used)}</th>" for c in rows[0])
                body = "".join("<tr>" + "".join(f"<td>{_inline(c, records, used)}</td>" for c in r) + "</tr>" for r in rows[1:])
                out.append(f"<table><thead><tr>{head_row}</tr></thead><tbody>{body}</tbody></table>")
            continue
        elif re.match(r"^\s*([-*]|\d+\.)\s+", line):
            tag = "ol" if re.match(r"^\s*\d+\.", line) else "ul"
            items = []
            while i < len(lines) and re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
                items.append(re.sub(r"^\s*([-*]|\d+\.)\s+", "", lines[i]))
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{_inline(x, records, used)}</li>" for x in items) + f"</{tag}>")
            continue
        elif line.startswith(">"):
            out.append(f"<blockquote>{_inline(line.lstrip('> '), records, used)}</blockquote>")
        elif line.strip() and not line.strip() == "---":
            out.append(f"<p>{_inline(line, records, used)}</p>")
        i += 1
    return "\n".join(out)


def build(project: Path) -> Path:
    records = ev.by_id(ev.load(project))
    used: list[str] = []
    title = re.sub(r"^#\s*Бриф:\s*", "", (project / "brief.md").read_text(encoding="utf-8").splitlines()[0])
    sections, nav = [], []
    out_dir = project / "outputs"
    names = [n for n in ORDER if (out_dir / n).exists()] + sorted(p.name for p in out_dir.glob("revisit-*.md"))
    for name in names:
        anchor = name.removesuffix(".md")
        label = TITLES.get(name) or ("Пересмотр " + ".".join(reversed(anchor.removeprefix("revisit-").split("-")[1:])))
        nav.append(f'<a href="#{anchor}">{label}</a>')
        body = _md((out_dir / name).read_text(encoding="utf-8"), records, used)
        sections.append(f'<section id="{anchor}"><div class="card">{body}</div></section>' if name == "decision-brief.md"
                        else f'<section id="{anchor}">{body}</section>')
    rows = stmod.parse_rows(stmod.read(project / "state" / "STATE.md"))
    done = sum(1 for r in rows if r.status == "готов")
    stages = f"Этапов пройдено: {done} из {len(rows)}" + ("" if done == len(rows) else
              " · сейчас: " + next(f"{r.num} {r.title} ({r.status})" for r in rows if r.status != "готов"))
    appendix = ["<h2 id='evidence'>Источники</h2><table class='ev'><thead><tr><th>№</th><th>Цитата или расчёт</th><th>Источник</th>"
                "<th>Качество</th><th>Дата публ.</th></tr></thead><tbody>"]
    for n, ref in enumerate(used, start=1):
        rec = records.get(ref)
        if rec is None:
            continue
        src = (f'<a href="{html.escape(rec.source)}">{html.escape(rec.source[:70])}</a>' if rec.source.startswith("http")
               else html.escape(rec.source))
        cls = ' class="rev"' if rec.status == ev.REVOKED else ""
        kind = "<br>синтетика" if rec.kind == "synthetic" else ("<br>расчёт" if rec.kind == "calc" else "")
        appendix.append(f'<tr id="ev-{ref}"{cls}><td>{n}<br><span class="meta">{ref}</span></td><td>«{html.escape(rec.quote)}»'
                        f'<br><span class="meta">{html.escape(rec.locator)}</span></td><td>{src}</td>'
                        f'<td>{rec.quality}{kind}</td><td>{rec.published or "—"}<br><span class="meta">доступ<br>{rec.accessed}</span></td></tr>')
    appendix.append("</tbody></table>")
    cost_md = _md(cost.report(project), records, [])
    page = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head><body><main>
<p class="meta">Отчёт агента «Стратег Фабрики продуктов» · проект {project.name}</p>
<h1>{html.escape(title)}</h1>
<p class="meta">{html.escape(stages)}</p>
<p class="legend meta">Как читать: <sup><a>1</a></sup> — сноска на источник (<span class="screen-only">наведите — цитата</span><span class="print-only">ведёт к цитате в приложении «Источники»</span>) ·
<span class="b hyp">гипотеза</span> не подтверждено · <span class="b fc">прогноз</span> оценка будущего ·
<span class="b syn">синтетика</span> ответ ИИ-персоны, не данные · C4 — номер вывода (ссылка ведёт к нему)</p>
<p class="print-only meta"><b>Содержание</b></p><nav>{''.join(nav)}<a href="#evidence">Источники</a><a href="#cost">Затраты</a></nav>
{''.join(sections)}
{''.join(appendix)}
<h2 id="cost">Затраты и время</h2>{cost_md}
</main></body></html>"""
    target = out_dir / "report.html"
    target.write_text(page, encoding="utf-8")
    return target


def to_pdf(html_path: Path) -> Path:
    """Печать отчёта в PDF через Chrome без окна: правила @media print — светлая тема, разделы с новой страницы, номера страниц."""
    from . import media  # Chrome ищется только при печати
    from .paths import SfError
    chrome = media.find_chrome()
    if not chrome:
        raise SfError("Chrome не найден — откройте report.html в браузере и сохраните как PDF (Файл → Печать → Сохранить как PDF).")
    target = html_path.with_suffix(".pdf")
    import subprocess
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=4000",
                    f"--print-to-pdf={target}", html_path.resolve().as_uri()], check=True, capture_output=True, timeout=180)
    if not target.exists() or target.stat().st_size == 0:
        raise SfError("Chrome не сохранил PDF — сохраните report.html как PDF из браузера вручную.")
    return target
