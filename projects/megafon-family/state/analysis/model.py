"""Расчёты по брифу МегаФона «Связь для близких и собственных устройств» (воспроизводимо). Версия 2.

Версия 2 — по замечаниям критика и проверяющего:
- активность B считается только по группам, которые без сигнала были бы неактивны;
- вычитается замещение платных допакетов;
- вариант E (владельцы, остановка за неоплату) считается той же моделью;
- набор пилота — с фильтрами «совместимый тариф», «разрешение участника», «впервые подходящая группа»;
  единица — группа.

Факты — таблица и ставки брифа (E7–E17). Всё прочее — допущения агента [ГИП]: (неблагоприятное, базовое, благоприятное).
Запуск: python3 state/analysis/model.py
"""
from __future__ import annotations

import math

# --- Факты брифа (учебные числа) ---
GP = {"plan": 282, "est": 275, "bau": 279, "target": 285}          # млн руб. (E9)
ACTIVE = {"plan": 5000, "est": 4000, "bau": 5000, "target": 8000}  # (E10)
CONN = {"plan": 7500, "est": 6500, "bau": 8000, "target": 12000}   # (E11)
OWNERS = {"plan": 1000, "est": 800, "bau": 1000, "target": 2000}   # (E12)
ACTIV14 = {"plan": 0.50, "est": 0.42, "bau": 0.45, "target": 0.60}  # (E13)
HH_ACCESSIBLE, OWNERS_ACCESSIBLE = 100_000, 40_000                  # (E8)
RATE = 500                                                          # руб. за доп. оплаченный месяц номера (E16)
ROLLOUT = 5                                                         # месяцев работы в плановом году (с августа)

# --- Допущения [ГИП]: (неблагоприятное, базовое, благоприятное) ---
PARTICIPANTS = (1.5, 2.0, 2.5)          # участников на группу
LOW_EVENT = (0.15, 0.25, 0.35)          # доля участников с низким остатком хотя бы раз в месяц
COMPATIBLE = (0.45, 0.60, 0.75)         # группы на тарифах, где можно выделять из остатка
PERMISSION = (0.30, 0.50, 0.70)         # участник разрешил показывать остаток
RESTRICT = 0.12                         # ограничены за 7 дней (учебный пример брифа, E18)
EFFECT = (0.02, 0.04, 0.06)             # снижение доли ограничений, п. п.
CHURN_AFTER_RESTRICT = (0.03, 0.05, 0.08)
ACT_ON_SIGNAL = (0.25, 0.40, 0.55)      # организатор действует по сигналу
INACTIVE = 1 - ACTIVE["bau"] / CONN["bau"]   # 37,5% групп без изменений неактивны
ADDON_BUY = (0.40, 0.25, 0.10)          # после ограничения участник покупает платный допакет
ADDON_MARGIN = 120                      # руб. валовой прибыли с допакета

# Вариант E: владельцы, номер роутера
STOP_RATE = (0.04, 0.07, 0.10)          # номеров роутера с остановкой за неоплату в месяц
PREVENTED = (0.20, 0.30, 0.40)          # доля остановок, которые снимает напоминание
LOST_MONTH_PER_STOP = (0.2, 0.3, 0.4)   # оплаченного месяца теряется за остановку (дни простоя)
CHURN_AFTER_STOP = (0.05, 0.10, 0.15)   # уход номера после остановки
OWNERS_IN_SERVICE = (1000, 1300, 1600)  # владельцев в услуге (без изменений 1 000; напоминание — повод объединить)
Z_A, Z_B = 1.96, 0.8416


def fmt(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")


def gap_decomposition() -> None:
    share_plan = ACTIVE["plan"] / CONN["plan"]
    share_est = ACTIVE["est"] / CONN["est"]
    print(f"Q1 активные {ACTIVE['est']} против плана {ACTIVE['plan']}: доля {share_est:.1%} против {share_plan:.1%};"
          f" из-за меньшего числа групп {(CONN['est'] - CONN['plan']) * share_plan:+.0f},"
          f" из-за меньшей доли {CONN['est'] * (share_est - share_plan):+.0f}")
    print(f"   прибыль −{GP['plan'] - GP['est']} млн = {fmt((GP['plan'] - GP['est']) * 1e6 / RATE)} мес.; активация"
          f" {ACTIV14['est']:.0%} против {ACTIV14['plan']:.0%}")
    print(f"   цели: разрыв {CONN['target'] - CONN['bau']} подключённых, {ACTIVE['target'] - ACTIVE['bau']} активных,"
          f" {OWNERS['target'] - OWNERS['bau']} владельцев, {ACTIV14['target'] - ACTIV14['bau']:.0%} активации,"
          f" {GP['target'] - GP['bau']} млн = {fmt((GP['target'] - GP['bau']) * 1e6 / RATE)} мес.;"
          f" охват {CONN['bau'] / HH_ACCESSIBLE:.0%} → {CONN['target'] / HH_ACCESSIBLE:.0%}")


def accumulate(prevented_per_month: float, churn: float, months: int) -> float:
    total, kept = 0.0, 0.0
    for _ in range(months):
        kept = kept * 0.98 + prevented_per_month * churn
        total += kept
    return total


def option_b(i: int, months: int = ROLLOUT) -> dict[str, float]:
    groups = CONN["bau"] * COMPATIBLE[i] * PERMISSION[i]
    numbers = groups * PARTICIPANTS[i]
    prevented = numbers * LOW_EVENT[i] * EFFECT[i]                       # ограничений меньше в месяц
    retained = accumulate(prevented, CHURN_AFTER_RESTRICT[i], months)
    substitution = prevented * ADDON_BUY[i] * ADDON_MARGIN * months / 1e6  # потерянные допакеты, млн
    event_groups = groups * (1 - (1 - LOW_EVENT[i]) ** PARTICIPANTS[i])
    new_active = event_groups * ACT_ON_SIGNAL[i] * INACTIVE
    return {"groups": groups, "prevented": prevented, "money": retained * RATE / 1e6 - substitution,
            "retained": retained, "substitution": substitution, "new_active": new_active}


def option_e(i: int, months: int = ROLLOUT) -> dict[str, float]:
    prevented = OWNERS_IN_SERVICE[i] * STOP_RATE[i] * PREVENTED[i]
    paid = prevented * LOST_MONTH_PER_STOP[i] * months + accumulate(prevented, CHURN_AFTER_STOP[i], months)
    return {"prevented": prevented, "money": paid * RATE / 1e6, "paid": paid}


def compare() -> None:
    need = (GP["target"] - GP["bau"]) * 1e6 / RATE
    for name, i in (("неблагоприятный", 0), ("базовый", 1), ("благоприятный", 2)):
        b, e = option_b(i), option_e(i)
        print(f"Q3 {name}: B — групп в услуге {fmt(b['groups'])}, ограничений меньше на {b['prevented']:.0f}/мес.,"
              f" новых активных {b['new_active']:.0f}, деньги {b['money']:+.2f} млн (удержание {b['retained'] * RATE / 1e6:.2f},"
              f" замещение допакетов −{b['substitution']:.2f}); E — остановок меньше на {e['prevented']:.0f}/мес.,"
              f" деньги {e['money']:+.2f} млн")
    b12, e12 = option_b(1, 12), option_e(1, 12)
    print(f"   первые 12 месяцев работы (базовый): B {b12['money']:+.2f} млн, E {e12['money']:+.2f} млн;"
          f" нужно {fmt(need)} мес. = 6 млн руб.")
    print(f"   потребность другого пути (F): ≈{fmt(need / 3)} новых номеров с августа, если каждый даёт {RATE} руб./мес. [ГИП]")


def per_arm(p1: float, p2: float) -> int:
    v = p1 * (1 - p1) + p2 * (1 - p2)
    return math.ceil((Z_A + Z_B) ** 2 * v / (p1 - p2) ** 2)


def pilot() -> None:
    """Набор: единица — группа; исход — «у кого-то в группе ограничение за 7 дней после первого случая»."""
    pool = CONN["est"] * COMPATIBLE[1] * PERMISSION[1]
    first = 1 - (1 - LOW_EVENT[1]) ** PARTICIPANTS[1]
    for p2 in (0.08, 0.09):
        need, have, month, left = 2 * per_arm(RESTRICT, p2), 0.0, 0, pool
        while have < need and month < 12:
            month += 1
            new = left * first
            have, left = have + new, left - new
        print(f"Q4 12% → {p2:.0%}: нужно {need} групп; пул {fmt(pool)}; набрано {fmt(have)} за {month} мес."
              + ("" if have >= need else " — пула не хватает"))
    sms_pool = CONN["est"] * COMPATIBLE[1]
    print(f"   I квартал: СМС со ссылкой на существующую операцию (E36) на тех же {fmt(pool)} группах — проверка понятности и исполнения")
    print(f"   владельцы (E): пул {fmt(OWNERS['est'])} подключённых, согласие другого человека не нужно; совместимых групп {fmt(sms_pool)}")


if __name__ == "__main__":
    gap_decomposition()
    compare()
    pilot()
