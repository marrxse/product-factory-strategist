"""Расчёты для документа по брифу: проверяемость B против E, сбор разрешений, чувствительность пилота к исходной
доле, правило решения, прибыль по месяцам и кварталам против вложений, цена закрытия разрывов, ориентир на 2029 год,
каналы. Воспроизводимо. Факты — таблица брифа (E9–E13), ставка 500 руб. (E16); остальное — допущения агента [ГИП].
Запуск: python3 state/analysis/plan_calcs.py
"""
from __future__ import annotations

import math

Z_A2, Z_A1, Z_B = 1.96, 1.645, 0.8416
RATE = 500
CONN_EST, CONN_BAU = 6500, 8000
COMPATIBLE, PERMISSION_CEIL = 0.60, 0.50      # [ГИП]
PARTICIPANTS, LOW_EVENT = 2.0, 0.25           # [ГИП]
EFFECT = 0.04                                  # [ГИП] снижение доли ограничений
CHURN_AFTER_RESTRICT, ADDON_BUY, ADDON_MARGIN = 0.05, 0.25, 120
SMS_COST, DISPUTE_SHARE, DISPUTE_COST = 1.0, 0.01, 150  # руб. за СМС; доля спорных операций; руб. за разбор [ГИП]
ACT_ON_SIGNAL = 0.40
PEOPLE_PM = {"аналитик 0,5 × 9 мес.": 4.5, "дизайнер 0,5 × 6 мес.": 3.0, "разработка II кв.": 1.5, "тестирование": 1.0}
PM_COST = 0.3                                  # млн руб. за человеко-месяц [ГИП]


def fmt(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")


def per_arm(p1: float, p2: float, z_a: float = Z_A2) -> int:
    v = p1 * (1 - p1) + p2 * (1 - p2)
    return math.ceil((z_a + Z_B) ** 2 * v / (p1 - p2) ** 2)


def testability() -> None:
    """Почему первым проверяем B: на 1 000 владельцах эффект E не различить."""
    owners = 1000
    for stop in (0.04, 0.07, 0.10):
        n = per_arm(stop, stop * 0.7)
        print(f"пилот E: остановок {stop:.0%} → {stop * 0.7:.1%} (−30%): нужно {fmt(n)} владельцев в ветке, есть {owners} всего")
    b_pool = CONN_EST * COMPATIBLE * PERMISSION_CEIL
    print(f"пилот B: пул ≈{fmt(b_pool)} групп, нужно 1 760 (12% → 8%) — проверяем; соотношение пулов ≈{b_pool / (owners / 2):.0f}:1 к ветке E")


def permissions() -> None:
    """Разрешения ещё нет: сколько групп в пуле через N недель после запуска запроса (10% откликов в неделю до потолка)."""
    pool_max = CONN_EST * COMPATIBLE * PERMISSION_CEIL
    for weeks in (2, 4, 6, 8):
        share = 1 - 0.9 ** weeks
        print(f"сбор разрешений: через {weeks} нед. ≈{fmt(pool_max * share)} групп в пуле ({share:.0%} потолка) [ГИП]")


def baseline_sensitivity() -> None:
    for base in (0.06, 0.09, 0.12):
        target = base * 2 / 3
        n = per_arm(base, target)
        print(f"исходная доля {base:.0%} → {target:.0%} (−1/3): {fmt(n)} групп в ветке, {fmt(2 * n)} всего")


def decision_rule() -> None:
    se = math.sqrt(2 * 0.12 * 0.88 / 880)
    print(f"правило: стандартная ошибка разницы {se * 100:.2f} п. п.; односторонний 5%-й порог = {Z_A1 * se * 100:.1f} п. п."
          f" = {Z_A1 * se / 0.12:.0%} относительного снижения от 12%")


def monthly_profit() -> None:
    """Раскатка с октября на совместимые группы с разрешением; удержанные месяцы, допакеты, СМС, споры — по месяцам и кварталам."""
    groups = CONN_BAU * COMPATIBLE * PERMISSION_CEIL
    numbers = groups * PARTICIPANTS
    prevented = numbers * LOW_EVENT * EFFECT
    signals = groups * (1 - (1 - LOW_EVENT) ** PARTICIPANTS)
    kept, cum = 0.0, 0.0
    invest = sum(PEOPLE_PM.values()) * PM_COST
    print(f"раскатка: {fmt(groups)} групп, {fmt(numbers)} номеров, ограничений меньше на {prevented:.0f} в месяц, сигналов {fmt(signals)} в месяц")
    for month in range(1, 13):
        kept = kept * 0.98 + prevented * CHURN_AFTER_RESTRICT
        gain = kept * RATE
        costs = prevented * ADDON_BUY * ADDON_MARGIN + signals * SMS_COST + signals * ACT_ON_SIGNAL * DISPUTE_SHARE * DISPUTE_COST
        cum += gain - costs
        if month in (3, 6, 9, 12):
            print(f"   месяц {month:2d}: удержано номеров {kept:.1f}, прибыль месяца {(gain - costs) / 1e3:+.1f} тыс. руб.,"
                  f" накоплено {cum / 1e6:+.3f} млн против вложений {invest:.2f} млн")
    unit = prevented * CHURN_AFTER_RESTRICT * RATE
    print(f"граница B: накопленная прибыль покрывает вложения, только если ограничений меньше на ≈"
          f"{fmt(prevented * invest * 1e6 / max(cum, 1))} в месяц — вне доступной базы [ГИП]")
    print(f"вложения: {sum(PEOPLE_PM.values()):.1f} человеко-месяца × {PM_COST} = {invest:.2f} млн руб.")


def gap_prices() -> None:
    cost_group = 3000          # руб. за дополнительную группу (пример E56)
    bonus = 300                # руб. бонус за новый номер в F [ГИП]
    print(f"цена закрытия разрывов (при допущениях): подключённые 3 900 групп × {fmt(cost_group)} руб. = {3900 * cost_group / 1e6:.1f} млн;"
          f" владельцы 950 × {fmt(cost_group)} = {950 * cost_group / 1e6:.1f} млн;"
          f" прибыль: 6 000 новых номеров × бонус {bonus} руб. = {6000 * bonus / 1e6:.1f} млн расходов"
          f" на +6 млн валовой прибыли [ГИП]")


def target_2029() -> None:
    bau_growth = 1500          # нетто в год без изменений (6 500 → 8 000, E11)
    f_growth = (0, 800, 1500)  # [ГИП] дополнительные группы в год от F и меньшего распада
    for f in f_growth:
        end = 8100 + 2 * (bau_growth + f)
        print(f"ориентир конца 2029: 8 100 + 2 × ({fmt(bau_growth)} + {fmt(f)}) = {fmt(end)} групп = {end / 100_000:.1%} доступных домохозяйств")


def channels() -> None:
    rows = [("приложение: экран создания группы", 4667, 0.60, "A/B экрана на 2 неделях"),
            ("поддержка: обращение «нет интернета у близкого»", 1200, 0.15, "скрипт оператора на 1 смене"),
            ("продажи: подключение семейного тарифа", 900, 0.25, "одна сеть салонов, 4 недели")]
    for name, reach, conv, test in rows:
        print(f"канал {name}: увидят ≈{fmt(reach)} подходящих в год [ГИП], подключатся {conv:.0%} [ГИП] ≈{fmt(reach * conv)}; проверка — {test}")


if __name__ == "__main__":
    testability()
    permissions()
    baseline_sensitivity()
    decision_rule()
    monthly_profit()
    gap_prices()
    target_2029()
    channels()
