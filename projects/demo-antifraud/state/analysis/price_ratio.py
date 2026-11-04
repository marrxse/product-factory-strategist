"""Сравнение цены операторских подписок с премиум-версиями приложений (воспроизводимо, без внешних данных)."""
KASPERSKY_YEAR = (1071, 1399)      # ₽/год: E21 (выдача), E27 (t-j.ru, 2026)
OPERATOR_MONTH = (149, 249)        # ₽/мес: E23 «Защитник+», E17 «Защитник+ для семьи»
kasp_month = tuple(round(y / 12) for y in KASPERSKY_YEAR)
ratio_low = OPERATOR_MONTH[0] / kasp_month[1]
ratio_high = OPERATOR_MONTH[1] / kasp_month[0]
print(f"kaspersky_month = {kasp_month[0]}–{kasp_month[1]} ₽; operator/kaspersky = {ratio_low:.1f}–{ratio_high:.1f}x")
