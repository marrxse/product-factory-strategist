"""Насколько надёжны правила решения пилота: вероятность каждого решения при разной истинной доле (воспроизводимо).

Пилот: 1 000 приглашённых пар, около 400 согласившихся, около 40 платящих (validation-plan.md).
Правило «продолжить, если доля ≥ цели» при истинной доле, равной цели, срабатывает примерно в половине случаев —
решение превращается в подбрасывание монеты. Скрипт считает точные биномиальные вероятности для старых
и новых порогов и выборку, нужную, чтобы увидеть эффект удержания (C18). Входы — допущения агента [ГИП].
"""
from __future__ import annotations

import math

INVITES, CONSENTED, PAYING = 1_000, 400, 40
TRUE_PAY = (0.03, 0.05, 0.07, 0.10, 0.12)
TRUE_CONSENT = (0.20, 0.30, 0.35, 0.40, 0.45)
Z_ALPHA, Z_BETA = 1.96, 0.8416


def p_at_least(share: float, n: int, p: float) -> float:
    """Вероятность увидеть долю не меньше share в n испытаниях при истинной доле p."""
    k = math.ceil(share * n - 1e-9)
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def decisions(go: float, stop: float, n: int, p: float) -> tuple[float, float, float]:
    """(продолжить, пересмотреть, остановить): продолжить при доле ≥ go, остановить при доле < stop."""
    p_go = p_at_least(go, n, p)
    p_stop = max(0.0, 1 - p_at_least(stop, n, p))
    return p_go, max(0.0, 1 - p_go - p_stop), p_stop


def wilson(x: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = x / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def per_group(p1: float, p2: float) -> int:
    variance = p1 * (1 - p1) + p2 * (1 - p2)
    return math.ceil((Z_ALPHA + Z_BETA) ** 2 * variance / (p1 - p2) ** 2)


def table(title: str, go: float, stop: float, n: int, truths: tuple[float, ...]) -> None:
    print(f"{title}: продолжить при ≥{go:.0%}, остановить при <{stop:.0%}, n={n}")
    for p in truths:
        g, r, s = decisions(go, stop, n, p)
        print(f"  истинная доля {p:.0%}: продолжить {g:.0%} · пересмотреть {r:.0%} · остановить {s:.0%}")


if __name__ == "__main__":
    table("первая оплата, старые пороги", 0.10, 0.03, CONSENTED, TRUE_PAY)
    table("первая оплата, новые пороги", 0.08, 0.05, CONSENTED, TRUE_PAY)
    table("согласие, старые пороги", 0.40, 0.20, INVITES, TRUE_CONSENT)
    table("согласие, новые пороги", 0.37, 0.30, INVITES, TRUE_CONSENT)
    lo, hi = wilson(round(0.10 * CONSENTED), CONSENTED)
    print(f"точность: при 40 платящих из 400 истинная доля где-то в {lo:.1%}–{hi:.1%}")
    lo, hi = wilson(round(0.20 * PAYING), PAYING)
    print(f"отток после первой оплаты 20% на {PAYING} платящих: истинный где-то в {lo:.0%}–{hi:.0%} — порог «≤20%» не различим")
    for base, effect in ((0.06, 0.25), (0.06, 0.50)):
        n = per_group(base, base * (1 - effect))
        print(f"удержание (C18): отток основного тарифа за 3 месяца {base:.0%} против {base * (1 - effect):.1%} — "
              f"нужно {n} пилотных пар и столько же сопоставимых; в пилоте {CONSENTED}")
