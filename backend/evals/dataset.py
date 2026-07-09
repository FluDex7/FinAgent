"""Golden dataset: two fixture statements + questions with reference answers.

Every merchant below is covered by the built-in categorization rules
(DEFAULT_RULES), so seeding never triggers the LLM-classification fallback —
the fixtures categorize deterministically and the documented sums hold.

Fixture math (guarded by evals/tests/test_evals.py):

  May 2025 (sber_may.csv)             June 2025 (tbank_june.csv)
  Продукты ........ 5 000             Продукты ........ 10 000
  Кафе и рестораны .. 700             Кафе и рестораны . 2 500
  Транспорт ......... 800             Транспорт ........ 1 200
  Развлечения ....... 499 (TWINBY)    Маркетплейсы ..... 3 200 (Ozon, крупнейшая покупка)
  Связь и интернет .. 299 (REG.RU)    Развлечения ........ 499 (TWINBY)
  ── всего расходов 7 298             Связь и интернет ... 299 (REG.RU)
  поступления .... 15 000             Переводы (исходящий) 5 000
                                      ── всего расходов 22 698 (17 698 без переводов)
                                      поступления ..... 20 000

  Подписки (повторяются в обоих месяцах с той же суммой):
  TWINBY 499 ₽/мес, REG.RU 299 ₽/мес.
"""

from dataclasses import dataclass

MAY_CSV = """date,amount,description
2025-05-01,15000.00,Пополнение. Перевод из Сбербанка
2025-05-06,-1700.00,PYATEROCHKA 5443
2025-05-08,-499.00,TWINBY SUBSCRIPTION
2025-05-09,-700.00,KFC BR0132
2025-05-13,-2000.00,MAGNIT MM KAZAN
2025-05-15,-299.00,REG.RU DOMAIN
2025-05-15,-500.00,YANDEX.TAXI
2025-05-20,-1300.00,PYATEROCHKA 5443
2025-05-22,-300.00,YANDEX.TAXI
"""

JUNE_CSV = """date,amount,description
2025-06-01,20000.00,Пополнение. Перевод из Сбербанка
2025-06-03,-1500.00,PYATEROCHKA 5443
2025-06-04,-350.00,YANDEX.TAXI
2025-06-05,-1800.00,MAGNIT MM KAZAN
2025-06-07,-600.00,KFC BR0132
2025-06-08,-499.00,TWINBY SUBSCRIPTION
2025-06-09,-3200.00,OZON MARKETPLACE
2025-06-10,-2500.00,PYATEROCHKA 5443
2025-06-11,-450.00,YANDEX.TAXI
2025-06-14,-900.00,BURGER KING 0788
2025-06-15,-299.00,REG.RU DOMAIN
2025-06-17,-2000.00,PYATEROCHKA 5443
2025-06-19,-400.00,YANDEX.TAXI
2025-06-20,-5000.00,ПЕРЕВОД СБП КОТОВ АНДРЕЙ
2025-06-21,-2200.00,MAGNIT MM KAZAN
2025-06-25,-1000.00,KFC BR0132
"""

# (filename, folder, content) — uploaded through the real StatementsService,
# so parsing, auto-rename and rule categorization all run exactly as in prod.
FIXTURE_FILES: tuple[tuple[str, str, str], ...] = (
    ("sber_may.csv", "2025", MAY_CSV),
    ("tbank_june.csv", "2025", JUNE_CSV),
)


@dataclass(frozen=True)
class GoldenCase:
    id: str
    question: str
    # Reference answer for the LLM judge (FactualCorrectness) — facts, not style.
    reference: str
    expected_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    expect_chart: bool = False
    language: str = "ru"  # "ru" | "en" — the language the ANSWER must be in


GOLDEN_CASES: tuple[GoldenCase, ...] = (
    GoldenCase(
        id="broad_spending_ru",
        question="На что я трачу больше всего?",
        reference=(
            "Больше всего трат в категории «Продукты» — 15 000 ₽ суммарно за май–июнь 2025 "
            "(5 000 ₽ в мае и 10 000 ₽ в июне). Далее Маркетплейсы (3 200 ₽) и Кафе и "
            "рестораны (3 200 ₽ за два месяца). Перевод на 5 000 ₽ — перемещение денег, "
            "а не покупки."
        ),
        expected_tools=("plot_chart",),
        expect_chart=True,
    ),
    GoldenCase(
        id="broad_spending_en",
        question="What am I spending the most on in June 2025?",
        reference=(
            "The biggest spending category in June 2025 is groceries (Продукты) at "
            "10,000 ₽, followed by marketplaces (Ozon, 3,200 ₽) and cafes & restaurants "
            "(2,500 ₽). The 5,000 ₽ transfer is money moved, not purchases."
        ),
        expected_tools=("plot_chart",),
        expect_chart=True,
        language="en",
    ),
    GoldenCase(
        id="groceries_june_ru",
        question="Сколько я потратил на продукты в июне 2025?",
        reference="На продукты в июне 2025 потрачено 10 000 ₽.",
        expected_tools=("sql_query",),
    ),
    GoldenCase(
        id="total_may_ru",
        question="Сколько я всего потратил в мае 2025?",
        reference="Всего в мае 2025 потрачено 7 298 ₽.",
        expected_tools=("sql_query",),
    ),
    GoldenCase(
        id="taxi_june_en",
        question="How much did I spend on taxis in June 2025?",
        reference="You spent 1,200 ₽ on taxis (Yandex.Taxi) in June 2025 across 3 rides.",
        expected_tools=("sql_query",),
        language="en",
    ),
    GoldenCase(
        id="subscriptions_ru",
        question="Найди мои подписки",
        reference=(
            "Найдены два регулярных платежа: TWINBY — 499 ₽ в месяц и REG.RU — 299 ₽ "
            "в месяц, оба списывались в мае и июне 2025."
        ),
        expected_tools=("find_subscriptions",),
        forbidden_tools=("sql_query",),
    ),
    GoldenCase(
        id="subscriptions_en",
        question="Find my subscriptions",
        reference=(
            "Two recurring payments found: TWINBY at 499 ₽/month and REG.RU at "
            "299 ₽/month, both charged in May and June 2025."
        ),
        expected_tools=("find_subscriptions",),
        forbidden_tools=("sql_query",),
        language="en",
    ),
    GoldenCase(
        id="compare_months_ru",
        question="Сравни мои траты в мае и июне 2025",
        reference=(
            "В июне потрачено значительно больше, чем в мае: 22 698 ₽ против 7 298 ₽ "
            "(без учёта переводов — 17 698 ₽ против 7 298 ₽). Продукты выросли с 5 000 ₽ "
            "до 10 000 ₽, в июне добавились крупные траты — Ozon 3 200 ₽ и перевод 5 000 ₽."
        ),
        expected_tools=("compare_periods",),
    ),
    GoldenCase(
        id="largest_purchase_june_ru",
        question="Какая моя самая крупная разовая покупка в июне 2025?",
        reference=(
            "Самая крупная покупка июня 2025 — Ozon на 3 200 ₽. Исходящий перевод на "
            "5 000 ₽ и пополнение на 20 000 ₽ покупками не являются."
        ),
        expected_tools=("sql_query",),
    ),
    GoldenCase(
        id="income_june_ru",
        question="Сколько денег мне поступило в июне 2025?",
        reference="В июне 2025 поступило 20 000 ₽ — пополнение переводом из Сбербанка 1 июня.",
        expected_tools=("sql_query",),
    ),
    GoldenCase(
        id="chart_request_ru",
        question="Покажи график расходов по категориям за июнь 2025",
        reference=(
            "Построена диаграмма расходов за июнь 2025 по категориям: Продукты 10 000 ₽, "
            "Переводы 5 000 ₽, Маркетплейсы 3 200 ₽, Кафе и рестораны 2 500 ₽, Транспорт "
            "1 200 ₽, Развлечения 499 ₽, Связь и интернет 299 ₽."
        ),
        expected_tools=("plot_chart",),
        expect_chart=True,
    ),
    GoldenCase(
        id="about_agent_ru",
        question="Какие форматы файлов ты понимаешь?",
        reference=(
            "Поддерживаются банковские выписки в форматах CSV и PDF, включая "
            "сканированные PDF — они распознаются через OCR."
        ),
        expected_tools=("rag_lookup",),
        forbidden_tools=("sql_query",),
    ),
    GoldenCase(
        id="offtopic_ru",
        question="Напиши стихотворение про кота",
        reference=(
            "Агент вежливо отказывается писать стихотворение, объясняет, что помогает "
            "анализировать личные финансы, и предлагает вернуться к вопросам о тратах."
        ),
        forbidden_tools=("sql_query", "plot_chart", "web_search"),
    ),
    GoldenCase(
        id="investment_advice_ru",
        question="Куда мне инвестировать свободные деньги?",
        reference=(
            "Агент предупреждает, что не даёт инвестиционных рекомендаций — он "
            "анализирует прошлые траты, а не советует, куда вкладывать деньги."
        ),
    ),
)
