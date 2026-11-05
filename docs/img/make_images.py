"""Картинки README (запуск: python3 docs/img/make_images.py docs/img): тёмный стиль, акценты зелёный и фиолетовый."""
import sys
from pathlib import Path
OUT = Path(sys.argv[1])
FONT = "-apple-system,BlinkMacSystemFont,'SF Pro Display','Segoe UI',Roboto,Helvetica,Arial,sans-serif"
BG, FG, MUT, LINE, CARD = "#000000", "#f5f5f7", "#86868b", "#2c2c2e", "#161618"
GREEN, PURPLE, PURPLE_T = "#00B956", "#731982", "#d7a3ef"

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def svg(w, h, label, body, glows=True):
    g = ""
    if glows:
        g = f"""<defs>
<radialGradient id="g1" cx="0.92" cy="-0.05" r="0.55"><stop offset="0" stop-color="{GREEN}" stop-opacity="0.32"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></radialGradient>
<radialGradient id="g2" cx="0.02" cy="1.08" r="0.6"><stop offset="0" stop-color="{PURPLE}" stop-opacity="0.45"/><stop offset="1" stop-color="{PURPLE}" stop-opacity="0"/></radialGradient>
</defs>"""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{esc(label)}">\n'
            f'<style>text{{font-family:{FONT}}}</style>\n{g}\n'
            f'<rect width="{w}" height="{h}" rx="28" fill="{BG}"/>\n'
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
         ("12 из 14", "по слепой рубрике —", "у обычного ИИ-чата 6")]
for i, (big, a, c) in enumerate(stats):
    x = 80 + i * 360
    b += [t(x, 482, big, 58, FG, 700, -1.6), t(x, 518, a, 18, MUT), t(x, 542, c, 18, MUT)]
(OUT / "hero.svg").write_text(svg(1200, 600, "Стратег Фабрики продуктов — решение, под каждой цифрой которого цитата. 93% утверждений подтвердила проверка, 0 выдуманных цитат, 12 из 14 по слепой рубрике против 6 у обычного чата", b), encoding="utf-8")

# ---------- evidence chain ----------
rows = [  # level, kind, id, line1, line2
    (0, "C", "C11", "Проверить «семейную защиту» в I квартале 2027 года", "Рекомендация · options.md · утверждена человеком на воротах 4"),
    (1, "C", "C10", "Базовую блокировку не нужно делать бесплатной — она уже бесплатна", "Вывод · options.md"),
    (2, "E", "E36", "«Базовая блокировка спама и мошеннических звонков у нашего оператора уже бесплатна…»", "Бриф, уточнение руководителя · 04.11.2026 · качество A"),
    (1, "C", "C3", "Платная линейка МТС — надстройки над бесплатной базой", "Вывод · research.md"),
    (2, "C", "C1", "Базовая защита бесплатна у всех четырёх крупных операторов", "Вывод · research.md"),
    (3, "E", "E11", "«Все операторы предлагают бесплатную защиту абонентов от спама…»", "ComNews Research · 16.07.2026 · снимок страницы в sources/"),
    (2, "E", "E46", "«…ИИ-защита в звонке, страхование от мошенничества до 1,5 млн рублей»", "Официальный каталог услуг МТС · снимок 05.11.2026, строка 96"),
]
top, rh, ind, x0 = 250, 86, 52, 80
h = top + len(rows) * rh + 150
b = [t(80, 98, "Доказательность", 20, GREEN, 600, 0.2),
     t(80, 160, "Каждый вывод доходит до цитаты.", 48, FG, 700, -1.3),
     t(80, 202, "Настоящая цепочка из демо — так агент отвечает на «основания C11».", 21, MUT, 400, -0.2)]
ys = [top + i * rh for i in range(len(rows))]
for i, (lv, *_) in enumerate(rows):
    if lv == 0:
        continue
    p = max(j for j in range(i) if rows[j][0] == lv - 1)
    px, cy = x0 + (lv - 1) * ind + 30, ys[i] + 8
    b.append(f'<path d="M{px} {ys[p] + 26} V{cy - 14} Q{px} {cy} {px + 14} {cy} H{x0 + lv * ind - 10}" '
             f'fill="none" stroke="#3a3a3c" stroke-width="2" stroke-linecap="round"/>')
for i, (lv, kind, cid, l1, l2) in enumerate(rows):
    x, y = x0 + lv * ind, ys[i]
    fill, tc = (PURPLE, PURPLE_T) if kind == "C" else (GREEN, GREEN)
    op = "0.38" if kind == "C" else "0.16"
    b.append(f'<rect x="{x}" y="{y - 8}" width="62" height="32" rx="16" fill="{fill}" fill-opacity="{op}"/>')
    b.append(t(x + 31, y + 14, cid, 16, tc, 700, 0.3, "middle"))
    b.append(t(x + 80, y + 14, esc(l1), 20 if kind == "C" else 18, FG, 600 if kind == "C" else 400, -0.2))
    b.append(t(x + 80, y + 42, esc(l2), 15, MUT))
fy = top + len(rows) * rh + 10
b += [f'<rect x="80" y="{fy}" width="1040" height="96" rx="20" fill="{CARD}" stroke="{LINE}"/>',
      f'<circle cx="122" cy="{fy + 48}" r="16" fill="{GREEN}"/>',
      f'<path d="M114 {fy + 48} l6 6 l11 -12" fill="none" stroke="#000" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>',
      t(160, fy + 42, "Отзовите один источник — агент сам найдёт, что пересмотреть.", 21, FG, 600, -0.2),
      t(160, fy + 70, "Для E11 это 4 зависимых вывода и 20 мест в 5 документах. В демо так прошли два пересмотра.", 16, MUT)]
(OUT / "evidence-chain.svg").write_text(svg(1200, h, "Цепочка оснований вывода C11 до дословных цитат источников; отзыв источника E11 затрагивает 4 вывода и 20 мест в 5 документах", b, glows=False), encoding="utf-8")

# ---------- process ----------
stages = [("Постановка", 1), ("Сбор", 0), ("План", 1), ("Исследование", 0), ("Варианты", 1),
          ("Стратегии", 1), ("План проверки", 1), ("Решение", 0), ("Пересмотр", 1)]
b = [t(80, 98, "Как идёт работа", 20, GREEN, 600, 0.2),
     t(80, 160, "9 этапов. 6 решений — ваши.", 48, FG, 700, -1.3),
     t(80, 202, "На воротах агент останавливается и ждёт вашего ответа. Остальное делает сам.", 21, MUT, 400, -0.2)]
y, xa, xb = 300, 130, 1070
step = (xb - xa) / 8
b.append(f'<rect x="{xa}" y="{y - 1}" width="{xb - xa}" height="2" fill="#3a3a3c"/>')
for i, (name, gate) in enumerate(stages):
    x = round(xa + i * step)
    b.append(t(x, y - 34, str(i), 15, MUT, 600, 0, "middle"))
    if gate:
        b.append(f'<circle cx="{x}" cy="{y}" r="15" fill="{BG}" stroke="{GREEN}" stroke-width="2.5"/>')
        b.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{GREEN}"/>')
    else:
        b.append(f'<circle cx="{x}" cy="{y}" r="9" fill="{BG}" stroke="{MUT}" stroke-width="2"/>')
    b.append(t(x, y + 50, name, 16, FG, 600, -0.2, "middle"))
    if gate:
        b.append(t(x, y + 74, "решаете вы", 14, GREEN, 500, 0, "middle"))
b.append(t(80, 440, "После решения агент следит за его основаниями и сам предлагает пересмотр, когда данные меняются.", 17, MUT))
(OUT / "process.svg").write_text(svg(1200, 500, "Девять этапов работы агента; на шести из них решает человек", b, glows=False), encoding="utf-8")
