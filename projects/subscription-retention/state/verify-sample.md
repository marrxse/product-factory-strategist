# Выборка утверждений для проверки (seed=42, ключевых с числами: 15, случайных: 10)

Для каждого: цитата есть в источнике? число совпадает? вывод следует из цитаты? Ответ: да / частично / нет + пояснение.

## 1. options.md:3
Утверждение: > Версия 3 (цикл доработки 1: учтены отчёт критика 5/12, проверка утверждений 14 из 23 и совет взглядов). Основа — `research.md` (C1–C10). Внутренних данных нет: экономика вариантов — масштаб на условных шагах [E52; E53], а не прогноз эффекта.
- E52: «+5 п.п. к конверсии пробного периода = +50 платящих на 1000 стартов; 30 324–35 511 ₽ выручки первых двух месяцев (условный шаг, не прогноз)» — projects/subscription-retention/state/analysis/options-sensitivity.md (раздел B)
- E53: «каждые 10% iOS-подписчиков с несостоявшимся списанием = 22–25 человек и 8 778–9 975 ₽ в месяц на 1000 платящих» — projects/subscription-retention/state/analysis/options-sensitivity.md (раздел C)
- Вердикт: 

## 2. options.md:11
Утверждение: | A — оставить как есть | всем | ничего | пользователь, 399 ₽/мес [E54] | полная |
- E54: «399 ₽ (бриф) против двух месячных тарифов «Просто» 379 и 499 ₽ (снимок, строки 351 и 361): 399/379 = 1,05; 399/499 = 0,80 → наша цена внутри диапазона 379–499 ₽» — projects/subscription-retention/brief.md (цена брифа vs оба месячных тарифа «Просто»)
- Вердикт: 

## 3. options.md:30
Утверждение: Что получаем / цена: масштаб — каждые +5 п.п. к конверсии пробного периода дают +50 платящих и 30 324–35 511 ₽ выручки первых двух месяцев на 1000 стартов [E52] (условный шаг, не прогноз). Цена: дизайн и разработка онбординга и напоминаний, A/B-тест на 4–8 недель [ГИП: оценка агента, оценка команды не получена].
- E52: «+5 п.п. к конверсии пробного периода = +50 платящих на 1000 стартов; 30 324–35 511 ₽ выручки первых двух месяцев (условный шаг, не прогноз)» — projects/subscription-retention/state/analysis/options-sensitivity.md (раздел B)
- Вердикт: 

## 4. options.md:37
Утверждение: Ставка: платящим на iPhone — способ продлить подписку вне App Store (оплата на сайте, СБП, российские карты) и честное предупреждение до списания. Зачем: с 01.04.2026 пополнение Apple ID со счёта телефона не работает у крупнейших операторов [E26; E28], российские карты не работают с 2022 года [E24]; остались подарочные и иностранные карты [E27] — то есть способ оплаты есть, но неудобный, и «массовым» его назвать нельзя [C5]. Это единственная найденная внешняя причина, которая изменилась в 2026 году.
- E26: «крупнейших операторов связи в России пропала возможность» — https://zona.media/news/2026/04/01/apple-id (текст новости, абзац 1)
- E28: «перестало работать пополнение баланса в» — https://istories.media/news/2026/04/01/oplata-apple-id-s-mobilnogo-telefona-perestala-rabotat-u-abonentov-krupneyshih-operatorov-svyazi/ (текст новости, абзац 1)
- E24: «с 1 апреля 2026 Apple отключила последний рабочий у россиян канал автосписания, оплату со счёта мобильного оператора (карты РФ отвалились ещё в марте 2022).» — https://vc.ru/services/3028056-avtoprodlenie-podpisok-app-store (строка 69; вводная часть)
- E27: «Без пополнения со счета мобильного телефона осталась возможность оплатить Apple ID через цифровые подарочные карты и иностранные банковские карты.» — https://zona.media/news/2026/04/01/apple-id (абзац о способах оплаты)
- Вердикт: 

## 5. options.md:38
Утверждение: Что получаем / цена: каждые 10% iOS-подписчиков с несостоявшимся списанием — 22–25 человек и 8 778–9 975 ₽ в месяц на 1000 платящих [E53]; реальная доля неизвестна. Расчёт переносит долю iPhone среди абонентов (22–25% [E31; E32; E33]) на наших платящих — это допущение; платящая аудитория обычно смещена к iOS, поэтому масштаб, вероятно, занижен [ГИП]. Цена: платёжный провайдер, веб-страница оплаты, юридическая проверка правил App Store о внешней оплате [ГИП: правила не проверены], 4–8 недель [ГИП: оценка агента].
- E53: «каждые 10% iOS-подписчиков с несостоявшимся списанием = 22–25 человек и 8 778–9 975 ₽ в месяц на 1000 платящих» — projects/subscription-retention/state/analysis/options-sensitivity.md (раздел C)
- E31: «Доля iPhone среди смартфонов россиян достигла почти 25%» — https://rg.ru/2026/04/23/operatory-v-rossii-kazhdyj-chetvertyj-abonent-polzuetsia-iphone.html (лид статьи)
- E32: «В пресс-службе МТС рассказали, что доля устройств Apple в сети достигла 22%» — https://rg.ru/2026/04/23/operatory-v-rossii-kazhdyj-chetvertyj-abonent-polzuetsia-iphone.html (абзац с пресс-службой МТС)
- E33: «доля пользователей Apple среди клиентов составляет 22,36%» — https://rg.ru/2026/04/23/operatory-v-rossii-kazhdyj-chetvertyj-abonent-polzuetsia-iphone.html (абзац с пресс-службой Билайна)
- Вердикт: 

## 6. options.md:46
Утверждение: Что получаем / цена: прямого свидетельства для полугодового плана нет. Ближайшее — дешёвые годовые планы удерживают через год до 36% против 6,7% у дорогих месячных, по всем категориям [E2]; это корреляция между разными приложениями с отбором (годовой план выбирают более мотивированные) [ГИП]. Цена: пересмотр пейвола и условий, риск каннибализации месячной подписки, уведомление текущих подписчиков [ГИП].
- E2: «Most apps with cheap annual plans retain up to 36% of users after a year, while high-priced monthly plans retain just 6.7%.» — https://www.revenuecat.com/blog/company/the-state-of-subscription-apps-2025-launch.md (строка 80; «Low prices keep users locked in»)
- Вердикт: 

## 7. options.md:47
Утверждение: Риски: длинный план переносит проблему продления на конец периода — ~30% годовых подписок отменяют в первый месяц [E1], а продление годовой подписки основатель «Мо» называет главным вызовом [E25]; пауза может снизить выручку, не изменив привычку [ГИП]; пауза не должна стать скрытым препятствием к отмене.
- E1: «Nearly 30% of annual subscriptions are canceled in the first month.» — https://www.revenuecat.com/blog/company/the-state-of-subscription-apps-2025-launch.md (строка 64; «Retention starts on day one»)
- E25: «Главным вызовом бизнес-модели Александр Горный называет продление пользователями годовой подписки.» — https://sberbusiness.live/publications/khoteli-povtorit-uspekh-headspace-kak-vykhodtsy-iz-mail-ru-sozdali-prilozhenie-dlia-meditatsii-s-1-6-mln-polzovatelei (строка 33; «Как зарабатывает «Мо»…»)
- Вердикт: 

## 8. options.md:48
Утверждение: Сильнейшее возражение (критик, дословно): D — это три разных изменения: бесплатный курс, пауза и план на 6 месяцев. Их эффекты не удастся разделить. Единственный количественный довод — 36% против 6,7% [E2] — это корреляция между разными приложениями [E6], причём про дешёвые годовые планы, а не полугодовые. Меняя цены текущим подписчикам, мы рискуем выручкой, пока даже не знаем, падает ли у нас первое продление.
- E2: «Most apps with cheap annual plans retain up to 36% of users after a year, while high-priced monthly plans retain just 6.7%.» — https://www.revenuecat.com/blog/company/the-state-of-subscription-apps-2025-launch.md (строка 80; «Low prices keep users locked in»)
- E6: «there is a correlational pattern, and a flattering one.» — https://www.revenuecat.com/blog/growth/free-trial-length.md (строка 80; оговорка под графиком)
- Вердикт: 

## 9. options.md:56
Утверждение: Сильнейшее возражение (критик, дословно): Вопрос был о том, почему уходят частные подписчики, а E предлагает строить B2B-продажи с долгим циклом сделки без единой цифры о российском рынке корпоративных программ благополучия. В квартал уложится только разведка. А низкая вовлечённость [E17; E18] даёт работодателю тот же повод не продлевать договор, что и подписчику.
- E17: «The medians of app 15-day and 30-day retention rates were 3.9% (IQR 10.3%) and 3.3% (IQR 6.2%), respectively.» — https://pmc.ncbi.nlm.nih.gov/articles/PMC6785720 (Abstract, Results; строка 131)
- E18: «On day 30, peer support (median 8.9%, n=2), mindfulness/meditation (median 4.7%, IQR 6.2%)» — https://pmc.ncbi.nlm.nih.gov/articles/PMC6785720 (Abstract, Results; строка 131)
- Вердикт: 

## 10. options.md:61
Утверждение: Ставка: прекратить развитие приложения: перевести в режим поддержки без новых функций и маркетинга либо искать покупателя. Зачем: интерес к категории после пандемии снижался — по оценкам Apptopia, сессии топ-10 приложений медитации в США упали на 48% от пика II кв. 2020 года к 2022 году [E20], у Calm и Headspace — на 26,4% и 60,3% за год [E21]; это сессии, а не выручка, данные без методики, уверенность низкая [C8]; для России 2026 года данных нет [ГИП]. Через 30 дней приложениями медитации пользуются 4,7% установивших (данные 2019 года по всем установкам) [E18].
- E20: «Combined User Sessions of the top 10 meditation apps have fallen 48% from their height in Q2 2020.» — https://apptopia.com/en/insights/calm-and-headspace-losing-app-engagement/ (строка 22)
- E21: «User sessions of Calm and Headspace are down 26.4% and 60.3% YoY in July, respectively.» — https://apptopia.com/en/insights/calm-and-headspace-losing-app-engagement/ (строка 24)
- E18: «On day 30, peer support (median 8.9%, n=2), mindfulness/meditation (median 4.7%, IQR 6.2%)» — https://pmc.ncbi.nlm.nih.gov/articles/PMC6785720 (Abstract, Results; строка 131)
- Вердикт: 

## 11. options.md:64
Утверждение: Сильнейшее возражение (критик, дословно): Закрывать продукт по сессиям американских приложений 2022 года [E20; E21, качество C] и по данным 2019 года обо всех установках [E18] — значит принимать необратимое решение на чужих и устаревших данных. При этом не посчитано ни что высвобождается, ни что теряем. Пока неизвестна собственная экономика подписчика и не исключены две устранимые причины [C5; C8], F — капитуляция без расчёта, а не вариант.
- E18: «On day 30, peer support (median 8.9%, n=2), mindfulness/meditation (median 4.7%, IQR 6.2%)» — https://pmc.ncbi.nlm.nih.gov/articles/PMC6785720 (Abstract, Results; строка 131)
- Вердикт: 

## 12. options.md:82
Утверждение: | Влияние на удержание | 1 — ничего не меняет | ? — бьёт по крупнейшей потере отрасли [C1; E50], но механизм не доказан [ГИП] | ? — зависит от доли сбоев оплаты [E53] | ? — корреляция между приложениями [E2] | ? [ГИП] | — |
- E50: «1000 стартов × 46,8% [E4] = 468 платящих (−532 в пробном); первое продление 51,5–77,1% [E5] → 241–361 во 2-м платном месяце (−107…−227); потеря в пробном больше в 2,3–5,0 раза» — projects/subscription-retention/state/analysis/funnel-benchmark.md (расчёт воронки)
- E53: «каждые 10% iOS-подписчиков с несостоявшимся списанием = 22–25 человек и 8 778–9 975 ₽ в месяц на 1000 платящих» — projects/subscription-retention/state/analysis/options-sensitivity.md (раздел C)
- E2: «Most apps with cheap annual plans retain up to 36% of users after a year, while high-priced monthly plans retain just 6.7%.» — https://www.revenuecat.com/blog/company/the-state-of-subscription-apps-2025-launch.md (строка 80; «Low prices keep users locked in»)
- Вердикт: 

## 13. options.md:87
Утверждение: | Уверенность в основаниях | 1 — сезонность не проверена [C8] | 1 — о проблеме есть данные [C1; C4], о действенности решения нет | 2 — факт отключения высокий, доля низкая [C5] | 1 — корреляция [E2] | 1 — нет данных | 1 — без своей экономики |
- E2: «Most apps with cheap annual plans retain up to 36% of users after a year, while high-priced monthly plans retain just 6.7%.» — https://www.revenuecat.com/blog/company/the-state-of-subscription-apps-2025-launch.md (строка 80; «Low prices keep users locked in»)
- Вердикт: 

## 14. options.md:96
Утверждение: - доля практики в день 0 или конверсия пробного периода ниже отраслевой (46,8% [E4]) или упала, и одинаково на обеих платформах → первым B, A/B-тестом со сторожевыми метриками (старты пробного периода, первое продление);
- E4: «Conversion is higher in the 5–9-day group than in the 10–16-day group: 46.8% versus 40.4%.» — https://www.revenuecat.com/blog/growth/free-trial-length.md (строка 166; Health & Fitness)
- Вердикт: 

## 15. options.md:103
Утверждение: **Целевой показатель удержания** (бриф требует назвать): доля стартов пробного периода, дошедших до второго платного месяца, раздельно по iOS и Android. Отраслевой ориентир — 241–361 на 1000 стартов [E50]; базу и цель на I квартал ставим по выгрузке на этапе 6. Сторожевые: доля стартов пробного периода и доля отмен «сбой оплаты».
- E50: «1000 стартов × 46,8% [E4] = 468 платящих (−532 в пробном); первое продление 51,5–77,1% [E5] → 241–361 во 2-м платном месяце (−107…−227); потеря в пробном больше в 2,3–5,0 раза» — projects/subscription-retention/state/analysis/funnel-benchmark.md (расчёт воронки)
- Вердикт: 

## 16. research.md:47
Утверждение: | Плательщик · первое продление | продолжить платить | мотивация: «мало пользуюсь» [E7]; неприятие потерь при списании [ГИП] | честное напоминание о списании с итогом практики; пауза вместо отмены | первое продление; доля «пауз» |
- E7: «The top reasons users cancel app subscriptions are: insufficient usage (37%), cost concerns (35%), better alternatives (10%), technical issues (7%), and billing errors (up to 28% on Google Play).» — https://www.revenuecat.com/blog/growth/subscription-app-churn-reasons-how-to-fix.md (строка 43; TL;DR)
- Вердикт: 

## 17. options.md:29
Утверждение: Ставка: новым пользователям — короткая первая практика или бесплатный базовый курс до экрана оплаты (как у «Мо» [E45]), выбор времени напоминания по схеме «если — то», ежедневный ритуал и видимый прогресс за неделю. Зачем: 90% стартов пробного периода приходятся на день установки [E13], короткие пробные периоды чаще всего отменяют в день 0–1 [E16], а главная заявленная причина отмен — «мало пользуюсь» [E7; C4].
- E45: «Бесплатный базовый курс познакомит вас с принципами формирования привычек и основами осознанности.» — https://apps.apple.com/ru/app/%D0%BC%D0%BE-%D0%BC%D0%B5%D0%B4%D0%B8%D1%82%D0%B0%D1%86%D0%B8%D1%8F-%D1%81%D0%BE%D0%BD-%D0%BF%D0%BE%D0%B4%D0%B4%D0%B5%D1%80%D0%B6%D0%BA%D0%B0/id1570156834 (блок НАЧНИТЕ БЕСПЛАТНО)
- E13: «90% of trial starts happen on the day of install.» — https://adapty.io/blog/markdown/subscription-app-success-2026.md (строка 84; «Myth #2»)
- E16: «Apps with three and seven-day trials had the highest cancellation rates on Day 0 and Day 1.» — https://athletechnews.com/fitness-apps-monetizable-winner-take-all-or-most/ (строка 68; «Longer Trial Periods Tend to Beat Shorter Ones»)
- E7: «The top reasons users cancel app subscriptions are: insufficient usage (37%), cost concerns (35%), better alternatives (10%), technical issues (7%), and billing errors (up to 28% on Google Play).» — https://www.revenuecat.com/blog/growth/subscription-app-churn-reasons-how-to-fix.md (строка 43; TL;DR)
- Вердикт: 

## 18. options.md:22
Утверждение: Что получаем / цена: новых затрат нет. Если верна гипотеза о непроизвольном оттоке на iOS [C5], каждые 10% iOS-подписчиков с несостоявшимся списанием — 8 778–9 975 ₽ в месяц на 1000 платящих [E53], и потеря повторяется каждый месяц [ГИП]; потери пробного периода остаются на уровне отрасли — до оплаты не доходит больше половины стартов [E4; C1].
- E53: «каждые 10% iOS-подписчиков с несостоявшимся списанием = 22–25 человек и 8 778–9 975 ₽ в месяц на 1000 платящих» — projects/subscription-retention/state/analysis/options-sensitivity.md (раздел C)
- E4: «Conversion is higher in the 5–9-day group than in the 10–16-day group: 46.8% versus 40.4%.» — https://www.revenuecat.com/blog/growth/free-trial-length.md (строка 166; Health & Fitness)
- Вердикт: 

## 19. options.md:62
Утверждение: Что получаем / цена: высвобождаются команда разработки, маркетинговый бюджет и время руководителя на квартал; теряем остаток выручки подписки, пользователей и позицию в категории, где есть российские конкуренты [E43; E45; E46]. Посчитать ни то, ни другое без внутренних данных нельзя [ГИП]: для решения нужны выручка в месяц, затраты команды и маркетинга, стоимость привлечения и доход с подписчика за жизнь — эти строки добавлены в выгрузку.
- E43: «1 месяц 379,00» — https://apps.apple.com/ru/app/%D0%BF%D1%80%D0%BE%D1%81%D1%82%D0%BE-%D0%BC%D0%B5%D0%B4%D0%B8%D1%82%D0%B0%D1%86%D0%B8%D1%8F-%D0%B8-%D1%81%D0%BE%D0%BD/id1490891826 (блок Встроенные покупки)
- E45: «Бесплатный базовый курс познакомит вас с принципами формирования привычек и основами осознанности.» — https://apps.apple.com/ru/app/%D0%BC%D0%BE-%D0%BC%D0%B5%D0%B4%D0%B8%D1%82%D0%B0%D1%86%D0%B8%D1%8F-%D1%81%D0%BE%D0%BD-%D0%BF%D0%BE%D0%B4%D0%B4%D0%B5%D1%80%D0%B6%D0%BA%D0%B0/id1570156834 (блок НАЧНИТЕ БЕСПЛАТНО)
- E46: «Медитация и Сон, Библиотека Мо 499,00» — https://apps.apple.com/ru/app/%D0%BC%D0%BE-%D0%BC%D0%B5%D0%B4%D0%B8%D1%82%D0%B0%D1%86%D0%B8%D1%8F-%D1%81%D0%BE%D0%BD-%D0%BF%D0%BE%D0%B4%D0%B4%D0%B5%D1%80%D0%B6%D0%BA%D0%B0/id1570156834 (блок Встроенные покупки)
- Вердикт: 

## 20. options.md:55
Утверждение: Риски: в квартал укладывается только разведка, а не выручка [ГИП]; низкая вовлечённость [E17; E18] переносится и на корпоративных пользователей — работодатель не продлит договор [ГИП]; данные о ментальном состоянии чувствительны — работодатель не должен видеть, кто пользуется [ГИП].
- E17: «The medians of app 15-day and 30-day retention rates were 3.9% (IQR 10.3%) and 3.3% (IQR 6.2%), respectively.» — https://pmc.ncbi.nlm.nih.gov/articles/PMC6785720 (Abstract, Results; строка 131)
- E18: «On day 30, peer support (median 8.9%, n=2), mindfulness/meditation (median 4.7%, IQR 6.2%)» — https://pmc.ncbi.nlm.nih.gov/articles/PMC6785720 (Abstract, Results; строка 131)
- Вердикт: 

## 21. research.md:53
Утверждение: - **Отказ в первую неделю.** 90% отказов [E34] против 75% участников с 9+ сессиями [E35] в одной статье. Различие в выборке: первое — пересказ данных о реальном использовании через панель (Baumel 2019, Android), второе — опрос людей, которые согласились участвовать, со смещением к активным. Для нас весомее первое, поскольку оно ближе к реальной воронке, но цифру 90% не используем как точную.
- E34: «a median of 90% of users dropping off within the first week of real-world use and an average 42% drop in participation in meditation app randomized controlled trials spanning 1-2 months» — https://www.jmir.org/2026/1/e71960 (Introduction, абзац об уровне вовлечённости)
- E35: «Notably, 402 (75%) participants reported more than 9 sessions, which contrasts with prior findings suggesting that most users disengage completely within a week of download.» — https://www.jmir.org/2026/1/e71960 (Discussion, абзац 2)
- Вердикт: 

## 22. options.md:31
Утверждение: Риски: в реестре нет ни одного источника о том, что практика до пейвола или напоминания поднимают конверсию — механизм B пока гипотеза [ГИП]; практика до пейвола может срезать старты пробного периода [ГИП]; рост доли платящих может снизить первое продление, если в оплату перейдут менее мотивированные [ГИП]; привычка формируется дольше пробного периода [E23] — один онбординг её не построит.
- E23: «it took, on average, 66 days for the habit to form» — https://blogs.ucl.ac.uk/bsh/2012/06/29/busting-the-21-days-habit-formation-myth/ (строка 34; о Lally et al. 2010)
- Вердикт: 

## 23. research.md:56
Утверждение: - **Доля iPhone.** «Почти 25%» [E31] против 22% (МТС) [E32] и 22,36% (Билайн) [E33]: разные базы операторов. Берём вилку 22–25%.
- E31: «Доля iPhone среди смартфонов россиян достигла почти 25%» — https://rg.ru/2026/04/23/operatory-v-rossii-kazhdyj-chetvertyj-abonent-polzuetsia-iphone.html (лид статьи)
- E32: «В пресс-службе МТС рассказали, что доля устройств Apple в сети достигла 22%» — https://rg.ru/2026/04/23/operatory-v-rossii-kazhdyj-chetvertyj-abonent-polzuetsia-iphone.html (абзац с пресс-службой МТС)
- E33: «доля пользователей Apple среди клиентов составляет 22,36%» — https://rg.ru/2026/04/23/operatory-v-rossii-kazhdyj-chetvertyj-abonent-polzuetsia-iphone.html (абзац с пресс-службой Билайна)
- Вердикт: 

## 24. research.md:30
Утверждение: **C7.** Тип плана сильнее связан с удержанием через год, чем длина пробного периода: дешёвые годовые планы удерживают до 36%, дорогие месячные — 6,7% [E2]. Но ~30% годовых подписок отменяют в первый месяц [E1], а основатель «Мо» называет продление годовой подписки главным вызовом бизнес-модели [E25]. Годовой план переносит проблему на 12-й месяц, а не снимает её. Российские аналоги: «Просто» — 379 ₽ за месяц [E43], оплата раз в 6 месяцев с 7 днями без оплаты [E41]; «Мо» — 499 ₽, период в карточке не указан [E46]. Наши 399 ₽ — внутри диапазона месячных тарифов «Просто» 379–499 ₽ [E54]. Цена не выделяется из рынка, и это согласуется с тем, что цена — вторая, а не первая причина отмен [E7; C4]. Уверенность средняя.
- E2: «Most apps with cheap annual plans retain up to 36% of users after a year, while high-priced monthly plans retain just 6.7%.» — https://www.revenuecat.com/blog/company/the-state-of-subscription-apps-2025-launch.md (строка 80; «Low prices keep users locked in»)
- E1: «Nearly 30% of annual subscriptions are canceled in the first month.» — https://www.revenuecat.com/blog/company/the-state-of-subscription-apps-2025-launch.md (строка 64; «Retention starts on day one»)
- E25: «Главным вызовом бизнес-модели Александр Горный называет продление пользователями годовой подписки.» — https://sberbusiness.live/publications/khoteli-povtorit-uspekh-headspace-kak-vykhodtsy-iz-mail-ru-sozdali-prilozhenie-dlia-meditatsii-s-1-6-mln-polzovatelei (строка 33; «Как зарабатывает «Мо»…»)
- E43: «1 месяц 379,00» — https://apps.apple.com/ru/app/%D0%BF%D1%80%D0%BE%D1%81%D1%82%D0%BE-%D0%BC%D0%B5%D0%B4%D0%B8%D1%82%D0%B0%D1%86%D0%B8%D1%8F-%D0%B8-%D1%81%D0%BE%D0%BD/id1490891826 (блок Встроенные покупки)
- E41: «Оплата раз в 6 мес., первые 7 дней без оплаты» — https://apps.apple.com/ru/app/%D0%BF%D1%80%D0%BE%D1%81%D1%82%D0%BE-%D0%BC%D0%B5%D0%B4%D0%B8%D1%82%D0%B0%D1%86%D0%B8%D1%8F-%D0%B8-%D1%81%D0%BE%D0%BD/id1490891826 (блок Подписки)
- E46: «Медитация и Сон, Библиотека Мо 499,00» — https://apps.apple.com/ru/app/%D0%BC%D0%BE-%D0%BC%D0%B5%D0%B4%D0%B8%D1%82%D0%B0%D1%86%D0%B8%D1%8F-%D1%81%D0%BE%D0%BD-%D0%BF%D0%BE%D0%B4%D0%B4%D0%B5%D1%80%D0%B6%D0%BA%D0%B0/id1570156834 (блок Встроенные покупки)
- E54: «399 ₽ (бриф) против двух месячных тарифов «Просто» 379 и 499 ₽ (снимок, строки 351 и 361): 399/379 = 1,05; 399/499 = 0,80 → наша цена внутри диапазона 379–499 ₽» — projects/subscription-retention/brief.md (цена брифа vs оба месячных тарифа «Просто»)
- E7: «The top reasons users cancel app subscriptions are: insufficient usage (37%), cost concerns (35%), better alternatives (10%), technical issues (7%), and billing errors (up to 28% on Google Play).» — https://www.revenuecat.com/blog/growth/subscription-app-churn-reasons-how-to-fix.md (строка 43; TL;DR)
- Вердикт: 

## 25. options.md:24
Утверждение: Сильнейшее возражение (критик, дословно): «Оставить как есть» — не нейтральный выбор. Это решение ещё квартал платить за привлечение людей, которые уходят, а мы не знаем почему. Единственный довод за A — сезонность [C8] — держится на американских данных 2022 года без методики [E12; E22] и не проверен ни на одной нашей когорте. Если A не включает даже выгрузку на 1–2 дня аналитика, в марте мы будем знать столько же, сколько сейчас.
- E12: «For example, RevenueCat data shows that refund rates for health and fitness apps jump by 20% in January, peaking at 2.4% during the third week of the month.» — https://www.revenuecat.com/blog/growth/how-to-tackle-new-year-subscription-churn/ (строка 69; «Preparing for the refund surge»)
- E22: «Calm did get a bump at the beginning of the year when almost all health & fitness apps have their best few months, but it started to decline dramatically shortly after Memorial Day.» — https://apptopia.com/en/insights/calm-and-headspace-losing-app-engagement/ (строка 28)
- Вердикт: 

