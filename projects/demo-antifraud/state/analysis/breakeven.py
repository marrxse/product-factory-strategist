"""Точка окупаемости семейной защиты (воспроизводимо). ВСЕ входы — допущения агента, не данные
(внутренних данных о затратах, оттоке и привлечении нет — ограничение брифа).

Условия расчёта: цены без НДС; бесплатный период не учитывается (первая оплата — в месяц подключения);
маржа — доля выручки после платёжных и операционных расходов; каннибализация текущей подписки — доля
новых пар, которые просто перешли с текущей подписки и не приносят дополнительной выручки.
Набор равномерный в течение 12 месяцев: в среднем пара платит половину горизонта (приближение)."""
PRICES = (149, 199)                 # ₽/мес за пару
MONTHLY_CHURN = (0.10, 0.20)        # отток платящих пар в месяц
MARGIN = 0.8
CAC = (0, 300, 600)                 # ₽ на привлечение одной платящей пары
CANNIBALIZATION = 0.2               # доля пар, перешедших с текущей подписки
INVESTMENT = (3_000_000, 6_000_000, 10_000_000)
HORIZON = 12

def paid_months(churn: float) -> float:
    return sum((1 - churn) ** t for t in range(HORIZON)) / 2

print("инвестиции | цена | CAC | новых платящих пар в месяц при оттоке 10% … 20% (каннибализация 20%)")
for inv in INVESTMENT:
    for price in PRICES:
        for cac in CAC:
            per_month = []
            for churn in MONTHLY_CHURN:
                value = price * MARGIN * paid_months(churn) * (1 - CANNIBALIZATION) - cac
                per_month.append("не окупается" if value <= 0 else f"≈{inv / value / HORIZON:,.0f}".replace(",", " "))
            print(f"{inv/1e6:.0f} млн ₽ | {price} ₽ | {cac} ₽ | {per_month[0]} … {per_month[1]}")

# Сводка для реестра (E49): все числа записи выводятся этим скриптом.
need = [inv / (price * MARGIN * paid_months(ch) * (1 - CANNIBALIZATION)) / HORIZON
        for inv in INVESTMENT for price in (199,) for ch in MONTHLY_CHURN]
print(f"сводка: окупаемость за {HORIZON} мес.; при 199 ₽ и бесплатном привлечении нужно ≈{min(need):,.0f}–{max(need):,.0f} новых платящих пар в месяц".replace(",", " "))
for price in PRICES:
    limits = [price * MARGIN * paid_months(ch) * (1 - CANNIBALIZATION) for ch in MONTHLY_CHURN]
    print(f"сводка: предельная стоимость привлечения при {price} ₽ ≈{min(limits):.0f}–{max(limits):.0f} ₽ (дороже — не окупается при любом наборе)")
