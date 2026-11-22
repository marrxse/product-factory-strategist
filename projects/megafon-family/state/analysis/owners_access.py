"""Вариант E на доступной базе владельцев: напоминание до дня списания по второму номеру не требует объединения
номеров в кабинете — оператор видит номера одного владельца и остановки за неоплату. Воспроизводимо.
Факт — 40 тыс. доступных владельцев (E8), ставка 500 руб. (E16). Остальное — допущения агента [ГИП].
"""
from __future__ import annotations

import math

ACCESSIBLE = 40_000
IDENTIFIED = (0.30, 0.50, 0.70)       # доля доступных владельцев, у которых оператор видит второй номер с отдельной оплатой
STOP_RATE = (0.04, 0.07, 0.10)        # остановок за неоплату по второму номеру в месяц
PREVENTED = (0.20, 0.30, 0.40)        # доля остановок, которые снимает напоминание
LOST_MONTH = (0.0, 0.1, 0.2)          # потерянного оплаченного месяца на остановку: 0 — платёж только переносится; 0,1 ≈ 3 дня простоя
CHURN_AFTER_STOP = (0.05, 0.10, 0.15) # уход номера после остановки
RATE = 500
GAP = 6_000_000
Z_A, Z_B = 1.96, 0.8416


def paid_months(i: int, months: int, lost=None, churn=None, effect=None) -> tuple[float, float]:
    reach = ACCESSIBLE * IDENTIFIED[i]
    prevented = reach * STOP_RATE[i] * (PREVENTED[i] if effect is None else effect)
    lost = LOST_MONTH[i] if lost is None else lost
    churn = CHURN_AFTER_STOP[i] if churn is None else churn
    total, kept = 0.0, 0.0
    for _ in range(months):
        kept = kept * 0.98 + prevented * churn
        total += prevented * lost + kept
    return prevented, total


def per_arm(p1: float, p2: float) -> int:
    v = p1 * (1 - p1) + p2 * (1 - p2)
    return math.ceil((Z_A + Z_B) ** 2 * v / (p1 - p2) ** 2)


if __name__ == "__main__":
    for name, i in (("неблагоприятный", 0), ("базовый", 1), ("благоприятный", 2)):
        prev, m6 = paid_months(i, 6)
        _, m12 = paid_months(i, 12)
        reach = f"{ACCESSIBLE * IDENTIFIED[i]:,.0f}".replace(",", " ")
        print(f"E на доступной базе, {name}: в охвате {reach} владельцев, остановок меньше на {prev:.0f} в месяц;"
              f" с июля (6 мес.) {m6 * RATE / 1e6:+.2f} млн руб.; за 12 мес. {m12 * RATE / 1e6:+.2f} млн руб."
              f" ({m12 * RATE / GAP:.0%} годового разрыва)")
    n = per_arm(0.07, 0.049)
    print(f"пилот E: 7% → 4,9% остановок — {n} владельцев в ветке, {2 * n} всего; доступно {ACCESSIBLE} — набор сразу, исход за 1–2 цикла списания")
    for i in (0, 1, 2):
        cost = ACCESSIBLE * IDENTIFIED[i] * 2 * 1.0   # два напоминания в месяц по 1 руб. [ГИП]
        print(f"   расходы на напоминания, сценарий {i}: ≈{cost * 12 / 1e6:.2f} млн руб. в год")
    se = math.sqrt(2 * 0.07 * 0.93 / n)
    print(f"правило E: стандартная ошибка разницы {se * 100:.2f} п. п.; односторонний 5%-й порог {1.645 * se * 100:.1f} п. п."
          f" = {1.645 * se / 0.07:.0%} относительного снижения от 7%")
    _, days_only = paid_months(1, 12, churn=0.0)
    _, churn_only = paid_months(1, 12, lost=0.0)
    print(f"разложение базового за 12 мес.: простой {days_only * RATE / 1e6:.2f} млн, уход после остановки {churn_only * RATE / 1e6:.2f} млн")
    _, moved = paid_months(1, 12, lost=0.0, churn=0.0)
    print(f"если платёж только переносится и никто не уходит: {moved * RATE / 1e6:.2f} млн — E не окупается")
    cost_year = ACCESSIBLE * IDENTIFIED[1] * 2 * 12 / 1e6
    for churn in (0.02, 0.05, 0.10):
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            _, m = paid_months(1, 12, churn=churn, effect=mid)
            lo, hi = (mid, hi) if m * RATE / 1e6 < cost_year else (lo, mid)
        print(f"безубыточность по расходам на напоминания ({cost_year:.2f} млн в год) при уходе после остановки {churn:.0%}: эффект ≥ {hi:.0%} остановок")
    invest, cum = 3.15, 0.0
    reach = ACCESSIBLE * IDENTIFIED[1]
    prevented = reach * STOP_RATE[1] * PREVENTED[1]
    kept = 0.0
    for month in range(1, 19):
        kept = kept * 0.98 + prevented * CHURN_AFTER_STOP[1]
        cum += (prevented * LOST_MONTH[1] + kept) * RATE - reach * 2 * 1.0
        if month % 3 == 0:
            print(f"   E, месяц {month:2d} после раскатки: накоплено {cum / 1e6:+.2f} млн руб. против вложений {invest} млн")
    # второй год из того же цикла и окупаемость при уходе 5%
    for churn in (0.10, 0.05):
        reach = ACCESSIBLE * IDENTIFIED[1]
        prevented = reach * STOP_RATE[1] * PREVENTED[1]
        kept, cum, y1, y2, pay = 0.0, 0.0, 0.0, 0.0, None
        for month in range(1, 37):
            kept = kept * 0.98 + prevented * churn
            net = (prevented * LOST_MONTH[1] + kept) * RATE - reach * 2 * 1.0
            cum += net
            if month <= 12:
                y1 += net
            elif month <= 24:
                y2 += net
            if pay is None and cum >= invest * 1e6:
                pay = month
        print(f"уход после остановки {churn:.0%}: чистыми год 1 {y1 / 1e6:+.2f} млн, год 2 {y2 / 1e6:+.2f} млн; окупаемость {pay} мес.")
