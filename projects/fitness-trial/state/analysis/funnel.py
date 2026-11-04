"""Воронка по учебной таблице cohorts.csv (воспроизводимо). Правила очистки:
- дубль строки 2026-03 удаляется (профиль: «1 полностью повторяющаяся строка»);
- конверсия установка→пробный период: без апреля (пропуск installs);
- удержание ко 2-му месяцу: без июня (когорта не завершена: active_paid_month2_check пуст)."""
import csv
from pathlib import Path

rows = list(csv.DictReader(open(Path(__file__).parents[2] / "sources" / "cohorts.csv", encoding="utf-8")))
unique = list({tuple(r.items()): r for r in rows}.values())
num = lambda r, k: int(r[k]) if r[k] else None

inst = [r for r in unique if num(r, "installs")]
install_to_trial = sum(num(r, "trial_starts") for r in inst) / sum(num(r, "installs") for r in inst)
trial_to_paid = sum(num(r, "paid_after_trial") for r in unique) / sum(num(r, "trial_starts") for r in unique)
mature = [r for r in unique if r["active_paid_month2_check"]]
paid_to_m2 = sum(num(r, "active_paid_month2") for r in mature) / sum(num(r, "paid_after_trial") for r in mature)
print(f"cohorts={len(unique)} (дубль удалён); install_to_trial={install_to_trial:.1%} (без апреля); "
      f"trial_to_paid={trial_to_paid:.1%}; paid_to_month2={paid_to_m2:.1%} (без июня)")
