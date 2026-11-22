"""График окупаемости напоминания владельцам (E): накопленная чистая прибыль после раскатки против вложений.
Числа — из того же цикла, что owners_access.py (E65, E67): уход номеров после остановки 10% и 5%. Выход — outputs/img/payback.svg.
Запуск: python3 state/analysis/payback_chart.py
"""
from __future__ import annotations

from pathlib import Path

ACCESSIBLE, IDENTIFIED, STOP, PREVENTED, LOST, RATE = 40_000, 0.50, 0.07, 0.30, 0.10, 500
INVEST = 3.15
MONTHS = 36


def series(churn: float) -> list[float]:
    reach = ACCESSIBLE * IDENTIFIED
    prevented = reach * STOP * PREVENTED
    kept, cum, out = 0.0, 0.0, []
    for _ in range(MONTHS):
        kept = kept * 0.98 + prevented * churn
        cum += (prevented * LOST + kept) * RATE - reach * 2 * 1.0
        out.append(cum / 1e6)
    return out


def svg() -> str:
    w, h, left, right, top, bottom = 760, 380, 70, 30, 40, 60
    ymax = 12.0
    x = lambda m: left + (m - 1) * (w - left - right) / (MONTHS - 1)
    y = lambda v: top + (ymax - v) * (h - top - bottom) / ymax
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="Helvetica, Arial, sans-serif" font-size="13">',
             f'<rect width="{w}" height="{h}" fill="#fff"/>']
    for v in range(0, 13, 3):
        parts.append(f'<line x1="{left}" x2="{w - right}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#e5e5e5"/>'
                     f'<text x="{left - 8}" y="{y(v) + 4:.1f}" text-anchor="end" fill="#666">{v}</text>')
    for m in (1, 6, 12, 18, 24, 30, 36):
        parts.append(f'<text x="{x(m):.1f}" y="{h - bottom + 20}" text-anchor="middle" fill="#666">{m}</text>')
    parts.append(f'<text x="{(left + w - right) / 2}" y="{h - 12}" text-anchor="middle" fill="#444">месяцев после раскатки</text>')
    parts.append(f'<text x="{left - 8}" y="{top - 16}" text-anchor="end" fill="#444">млн руб.</text>')
    parts.append(f'<line x1="{left}" x2="{w - right}" y1="{y(INVEST):.1f}" y2="{y(INVEST):.1f}" stroke="#c62828" stroke-dasharray="6 4" stroke-width="2"/>'
                 f'<text x="{left + 8}" y="{y(INVEST) - 6:.1f}" fill="#c62828">вложения в пилоты 3,15 млн</text>')
    for churn, color, label in ((0.10, "#00a650", "уход после остановки 10%"), (0.05, "#7b1fa2", "уход после остановки 5%")):
        s = series(churn)
        pts = " ".join(f"{x(m + 1):.1f},{y(min(v, ymax)):.1f}" for m, v in enumerate(s))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="3"/>')
        pay = next((m + 1 for m, v in enumerate(s) if v >= INVEST), None)
        if pay:
            parts.append(f'<circle cx="{x(pay):.1f}" cy="{y(INVEST):.1f}" r="5" fill="{color}"/>'
                         f'<text x="{x(pay) + 8:.1f}" y="{y(INVEST) + 18:.1f}" fill="{color}" font-weight="bold">{pay} мес.</text>')
        ly = top + 4 + (0 if churn == 0.10 else 20)
        parts.append(f'<line x1="{left + 300}" x2="{left + 324}" y1="{ly}" y2="{ly}" stroke="{color}" stroke-width="3"/>'
                     f'<text x="{left + 330}" y="{ly + 4}" fill="#333">{label}</text>')
    parts.append("</svg>")
    return "".join(parts)


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[2] / "outputs" / "img" / "payback.svg"
    out.parent.mkdir(exist_ok=True)
    out.write_text(svg(), encoding="utf-8")
    for churn in (0.10, 0.05):
        s = series(churn)
        print(f"уход {churn:.0%}: 12 мес. {s[11]:+.2f}, 24 мес. {s[23]:+.2f}, 36 мес. {s[35]:+.2f} млн;"
              f" окупаемость {next((m + 1 for m, v in enumerate(s) if v >= INVEST), '>36')} мес.")
    print(f"график: {out}")
