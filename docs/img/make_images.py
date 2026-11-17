"""Картинки README (запуск: python3 docs/img/make_images.py docs/img): тёмный стиль, акценты зелёный и фиолетовый."""
import sys
from pathlib import Path
OUT = Path(sys.argv[1])
FONT = "-apple-system,BlinkMacSystemFont,'SF Pro Display','Segoe UI',Roboto,Helvetica,Arial,sans-serif"
BG, FG, MUT, LINE, CARD = "#ffffff", "#1d1d1f", "#6e6e73", "#e3e3e8", "#f5f5f7"
GREEN, PURPLE, PURPLE_T = "#00a650", "#731982", "#731982"

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def svg(w, h, label, body, glows=True):
    g = ""
    if glows:
        g = f"""<defs>
<radialGradient id="g1" cx="0.92" cy="-0.05" r="0.55"><stop offset="0" stop-color="{GREEN}" stop-opacity="0.13"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></radialGradient>
<radialGradient id="g2" cx="0.02" cy="1.08" r="0.6"><stop offset="0" stop-color="{PURPLE}" stop-opacity="0.10"/><stop offset="1" stop-color="{PURPLE}" stop-opacity="0"/></radialGradient>
</defs>"""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{esc(label)}">\n'
            f'<style>text{{font-family:{FONT}}}</style>\n{g}\n'
            f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="28" fill="{BG}" stroke="{LINE}" stroke-width="2"/>\n'
            + (f'<rect width="{w}" height="{h}" rx="28" fill="url(#g1)"/><rect width="{w}" height="{h}" rx="28" fill="url(#g2)"/>\n' if glows else "")
            + "\n".join(body) + "\n</svg>\n")

def t(x, y, s, size, fill=FG, weight=400, ls=0, anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'letter-spacing="{ls}" text-anchor="{anchor}"{extra}>{s}</text>')

# ---------- hero ----------
b = [t(80, 108, "ИИ-агент · Стратег Фабрики продуктов", 20, GREEN, 600, 0.2),
     t(80, 188, "Решение, под каждой цифрой", 64, FG, 700, -1.8),
     t(80, 262, f'которого — <tspan fill="{GREEN}">цитата.</tspan>', 64, FG, 700, -1.8),
     t(80, 320, "От размытого вопроса — к исследованию, вариантам, стратегии и плану проверки.", 22, MUT, 400, -0.2),
     t(80, 350, "А после решения — честный пересмотр, когда меняются данные.", 22, MUT, 400, -0.2),
     f'<rect x="80" y="400" width="1040" height="1" fill="{LINE}"/>']
stats = [("93%", "утверждений подтвердила", "независимая проверка"),
         ("0", "выдуманных цитат", "и чисел во всех проверках"),
         ("12 из 14", "оценка моделью по рубрике —", "у обычного ИИ-чата 6")]
for i, (big, a, c) in enumerate(stats):
    x = 80 + i * 360
    b += [t(x, 482, big, 58, FG, 700, -1.6), t(x, 518, a, 18, MUT), t(x, 542, c, 18, MUT)]
(OUT / "hero.svg").write_text(svg(1200, 600, "Стратег Фабрики продуктов — решение, под каждой цифрой которого цитата. 93% утверждений подтвердила проверка, 0 выдуманных цитат, 12 из 14 по слепой рубрике против 6 у обычного чата", b), encoding="utf-8")

# ---------- evidence chain ----------
rows = [  # level, kind, id, line1, line2 — настоящая цепочка «основания C15» (фрагмент без ветки о конкурентах)
    (0, "C", "C15", "Продавать не «защиту себя», а помощь близкому в момент звонка", "Вывод о поведении клиентов · behavior.md"),
    (1, "E", "E71", "«…58% уверены, что смогли бы … распознать признаки…»", "ФОМ, апрель 2025, 1500 человек (по Интерфаксу) · качество B"),
    (1, "E", "E74", "«45% респондентов продолжают беседу…»", "исследование Народного фронта · качество B"),
    (1, "E", "E73", "«…избежать материальных потерь удалось лишь 6%»", "опрос «Сравни», январь 2026 · качество C"),
    (1, "C", "C11", "Проверить «семейную защиту» в I квартале 2027 года", "Рекомендация · утверждена человеком на воротах 4"),
    (2, "C", "C10", "Базовую блокировку не нужно делать бесплатной — она уже бесплатна", "Вывод · options.md"),
    (3, "E", "E36", "«Базовая блокировка спама и мошеннических звонков у нашего оператора уже бесплатна…»", "Бриф, уточнение руководителя · 04.11.2026 · качество A"),
]
top, rh, ind, x0 = 250, 86, 52, 80
h = top + len(rows) * rh + 150
b = [t(80, 98, "Доказательность", 20, GREEN, 600, 0.2),
     t(80, 160, "Каждый вывод доходит до цитаты.", 48, FG, 700, -1.3),
     t(80, 202, "Настоящая цепочка из демо — так агент отвечает на «основания C15».", 21, MUT, 400, -0.2)]
ys = [top + i * rh for i in range(len(rows))]
for i, (lv, *_) in enumerate(rows):
    if lv == 0:
        continue
    p = max(j for j in range(i) if rows[j][0] == lv - 1)
    px, cy = x0 + (lv - 1) * ind + 30, ys[i] + 8
    b.append(f'<path d="M{px} {ys[p] + 26} V{cy - 14} Q{px} {cy} {px + 14} {cy} H{x0 + lv * ind - 10}" '
             f'fill="none" stroke="#c7c7cc" stroke-width="2" stroke-linecap="round"/>')
for i, (lv, kind, cid, l1, l2) in enumerate(rows):
    x, y = x0 + lv * ind, ys[i]
    fill, tc = (PURPLE, PURPLE_T) if kind == "C" else (GREEN, GREEN)
    op = "0.12" if kind == "C" else "0.12"
    b.append(f'<rect x="{x}" y="{y - 8}" width="62" height="32" rx="16" fill="{fill}" fill-opacity="{op}"/>')
    b.append(t(x + 31, y + 14, cid, 16, tc, 700, 0.3, "middle"))
    b.append(t(x + 80, y + 14, esc(l1), 20 if kind == "C" else 18, FG, 600 if kind == "C" else 400, -0.2))
    b.append(t(x + 80, y + 42, esc(l2), 15, MUT))
fy = top + len(rows) * rh + 10
b += [f'<rect x="80" y="{fy}" width="1040" height="96" rx="20" fill="{CARD}" stroke="{LINE}"/>',
      f'<circle cx="122" cy="{fy + 48}" r="16" fill="{GREEN}"/>',
      f'<path d="M114 {fy + 48} l6 6 l11 -12" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>',
      t(160, fy + 42, "Отзовите один источник — агент сам найдёт, что пересмотреть.", 21, FG, 600, -0.2),
      t(160, fy + 70, "Для E36 это 12 зависимых выводов и 47 мест в 7 документах. В демо так прошли пять пересмотров.", 16, MUT)]
(OUT / "evidence-chain.svg").write_text(svg(1200, h, "Цепочка оснований вывода C15 до дословных цитат источников; отзыв записи E36 затрагивает 12 выводов и 47 мест в 7 документах", b, glows=False), encoding="utf-8")

# ---------- check: анимация настоящих выводов sf.py ----------
# Строки — дословный вывод команд на копии демо, куда добавлена строка без источника.
MONO = "'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
RED, YELLOW = "#d70015", "#b25000"
lines = [  # (цвет, текст, пауза перед строкой в долях цикла)
    (MUT, "# в research.md попала строка: «Рынок защиты от мошенников вырос на 37% за год.»", 0.04),
    (FG, "$ python3 sf.py validate", 0.10),
    (RED, "[ОШИБКА] research.md:67: число без метки источника", 0.16),
    (RED, "         добавьте [E…], [ПРОГНОЗ …] или [ГИП]", 0.18),
    (FG, "$ python3 sf.py stage 3 done", 0.28),
    (RED, "Этап 3 не закрыт: validate нашёл ошибок 1.", 0.34),
    (MUT, " ", 0.40),
    (FG, "$ python3 sf.py revisit E11", 0.46),
    (YELLOW, "Изменилось: E11", 0.52),
    (YELLOW, "  Затронутые выводы (транзитивно): C1, C3, C9, C11", 0.55),
    (MUT, "  - decision-brief.md:11: I квартал 2027 года — проверить «семейную защиту»…", 0.60),
    (MUT, "  - product-strategy.md:41: Не продаём блокировку: она бесплатна у нас…", 0.63),
    (MUT, "  # … и ещё 18 мест — всего 20 в 5 документах", 0.66),
]
CYCLE = 22
css = [f"text{{font-family:{FONT}}}", f".m{{font-family:{MONO}}}"]
for i, (_, _, start) in enumerate(lines):
    # первый кадр — полный (его видят превью и браузеры без анимации), затем строки появляются по очереди
    a = round(28 + start * 70, 1)
    b2 = round(a + 1.2, 1)
    css.append(f"@keyframes k{i}{{0%,20%{{opacity:1}}23%,{a}%{{opacity:0}}{b2}%,100%{{opacity:1}}}}"
               f".l{i}{{animation:k{i} {CYCLE}s linear infinite}}")
css.append("@media (prefers-reduced-motion:reduce){" + "".join(f".l{i}" + ("," if i < len(lines) - 1 else "") for i in range(len(lines))) + "{animation:none}}")
H2, ty = 790, 300
b = [t(80, 98, "Проверка кодом, а не просьбой", 20, GREEN, 600, 0.2),
     t(80, 160, "Число без источника не пройдёт.", 48, FG, 700, -1.3),
     t(80, 202, "Настоящий вывод команд агента: этап не закрыть, пока проверка красная.", 21, MUT, 400, -0.2),
     f'<rect x="80" y="236" width="1040" height="{H2 - 236 - 60}" rx="16" fill="{CARD}" stroke="{LINE}"/>',
     f'<rect x="80" y="236" width="1040" height="40" rx="16" fill="#ececf0"/><rect x="80" y="260" width="1040" height="16" fill="#ececf0"/>',
     '<circle cx="106" cy="256" r="6.5" fill="#ff5f57"/><circle cx="128" cy="256" r="6.5" fill="#febc2e"/><circle cx="150" cy="256" r="6.5" fill="#28c840"/>',
     t(600, 261, "demo-antifraud", 14, MUT, 500, 0, "middle")]
for i, (color, text, _) in enumerate(lines):
    b.append(f'<text class="m l{i}" x="108" y="{ty + 18 + i * 31}" font-size="16.5" fill="{color}" xml:space="preserve">{esc(text)}</text>')
out = svg(1200, H2, "Анимация: агент дописал число без источника, validate выдал ошибку, этап не закрылся; revisit E11 нашёл 4 зависимых вывода и 20 мест в 5 документах", b, glows=False)
out = out.replace(f"<style>text{{font-family:{FONT}}}</style>", "<style>" + "\n".join(css) + "</style>")
(OUT / "check.svg").write_text(out, encoding="utf-8")

# ---------- pipeline: цепочка промптов (источник правды — docs/PIPELINE.md) ----------
rows_p = [  # этап, промпт, результат, проверка, ворота
    ("0", "Постановка задачи", "intake", "brief.md", "≤3 вопроса с вариантом по умолчанию", True),
    ("1", "Сбор материалов", "collect", "evidence.csv", "цитата, место, дата · классификатор", False),
    ("2", "План исследования", "research-plan", "research-plan.md", "цена ошибки × неопределённость", True),
    ("3", "Исследование", "research + 4 навыка", "research.md · behavior.md", "раздел «Чего мы не знаем»", False),
    ("4", "Варианты", "options + quality-review", "options.md", "≥3 варианта · критик вслепую", True),
    ("5", "Стратегии", "product- + comms-strategy", "2 стратегии", "обещание → возможность продукта", True),
    ("6", "План проверки", "validation-plan", "decision-brief.md", "пороги «продолжить / остановить»", True),
    ("7", "Поддержка решения", "decision-support", "decisions.md", "сроки и условия пересмотра", False),
    ("8", "Пересмотр", "decision-support", "revisit-<дата>.md", "граф затронутых выводов", True),
]
cols = [(80, "Этап"), (320, "Промпт (навык)"), (560, "Результат"), (790, "Проверка"), (1105, "")]
top_p, rh_p = 262, 64
H3 = top_p + len(rows_p) * rh_p + 90
b = [t(80, 98, "Цепочка промптов", 20, GREEN, 600, 0.2),
     t(80, 160, "Один шаг — один промпт, результат и проверка.", 48, FG, 700, -1.3),
     t(80, 202, "Полная таблица собирается из кода командой sf.py pipeline — docs/PIPELINE.md.", 21, MUT, 400, -0.2)]
b += [t(x, top_p - 18, name, 14, MUT, 600, 0.4) for x, name in cols[:4]]
b.append(t(1120, top_p - 18, "ворота", 14, MUT, 600, 0.4, "end"))
for i, (num, stage, skill, result, check, gate) in enumerate(rows_p):
    y = top_p + i * rh_p
    b.append(f'<rect x="64" y="{y}" width="1072" height="{rh_p - 8}" rx="14" fill="{CARD if i % 2 == 0 else BG}"/>')
    b.append(t(84, y + 36, num, 18, GREEN, 700, 0, "start"))
    b.append(t(112, y + 36, esc(stage), 17, FG, 600, -0.2))
    b.append(f'<text class="m" x="320" y="{y + 35}" font-size="14.5" fill="{PURPLE_T}" font-family="{MONO}">{esc(skill)}</text>')
    b.append(f'<text class="m" x="560" y="{y + 35}" font-size="14.5" fill="{FG}" font-family="{MONO}">{esc(result)}</text>')
    b.append(t(790, y + 35, esc(check), 14.5, MUT))
    if gate:
        b.append(f'<circle cx="1108" cy="{y + 28}" r="11" fill="{BG}" stroke="{GREEN}" stroke-width="2.2"/><circle cx="1108" cy="{y + 28}" r="5" fill="{GREEN}"/>')
fy3 = top_p + len(rows_p) * rh_p + 30
b.append(t(80, fy3 + 10, "Каждый шаг: хук после записи проверяет метки и ссылки · этап не закрывается, пока проверка красная · на воротах решает человек.", 16, MUT))
(OUT / "pipeline.svg").write_text(svg(1200, H3, "Цепочка промптов агента: девять шагов, у каждого промпт-навык, результат, проверка и ворота человека", b, glows=False), encoding="utf-8")
