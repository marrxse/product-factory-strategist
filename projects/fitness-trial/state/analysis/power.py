"""Мощность A/B-теста по учебной таблице (воспроизводимо). Основная метрика брифа — платящие во 2-м месяце на старт пробного периода."""
import csv, math
from pathlib import Path
rows = list({tuple(r.items()): r for r in csv.DictReader(open(Path(__file__).parents[2] / "sources" / "cohorts.csv", encoding="utf-8"))}.values())
mature = [r for r in rows if r["active_paid_month2_check"]]
base = sum(int(r["active_paid_month2"]) for r in mature) / sum(int(r["trial_starts"]) for r in mature)
trials_per_month = sum(int(r["trial_starts"]) for r in rows) / len(rows)
Z = 1.96 + 0.84  # α=0.05 (двусторонний), мощность 80%
def mde(n):  # минимальный обнаружимый эффект при n на группу (приближение)
    return Z * math.sqrt(2 * base * (1 - base) / n)
quarter = trials_per_month * 3
for groups in (3, 2):
    n = quarter / groups
    print(f"groups={groups}: n≈{n:.0f}/группу за квартал → MDE ≈ +{mde(n)*100:.1f} п.п. от базы {base*100:.1f}%")
