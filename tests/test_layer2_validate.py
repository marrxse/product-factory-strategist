"""Слой 2: validate проходит на корректном проекте и падает на каждой специально внесённой ошибке."""
import unittest

from tests.fixtures import make_good_project, rewrite
from tests.helpers import TempRepo, run


class ValidateTest(unittest.TestCase):
    def assert_fails_with(self, root, fragment):
        code, out = run("validate")
        self.assertEqual(code, 1, out)
        self.assertIn(fragment, out)

    def test_good_project_passes(self):
        with TempRepo() as root:
            make_good_project(root)
            code, out = run("validate", "--final")
            self.assertEqual(code, 0, out)
            self.assertIn("ошибок 0", out)

    def test_missing_status_quo_option_fails(self):
        with TempRepo() as root:
            p = make_good_project(root)
            rewrite(p, "options.md", "оставить как есть", "ускорить продажи")
            self.assert_fails_with(root, "оставить как есть")

    def test_missing_close_option_fails(self):
        with TempRepo() as root:
            p = make_good_project(root)
            rewrite(p, "options.md", "закрыть направление", "сменить канал")
            self.assert_fails_with(root, "закрыть направление")

    def test_two_options_fail(self):
        with TempRepo() as root:
            p = make_good_project(root)
            rewrite(p, "options.md", "## Вариант B — переработать онбординг", "### Подробности")
            self.assert_fails_with(root, "вариантов 2")

    def test_option_without_objection_fails(self):
        with TempRepo() as root:
            p = make_good_project(root)
            rewrite(p, "options.md", "Сильнейшее возражение: причина может быть в цене", "Минус: причина может быть в цене")
            self.assert_fails_with(root, "нет сильнейшего возражения")

    def test_untagged_number_fails(self):
        with TempRepo() as root:
            p = make_good_project(root)
            rewrite(p, "research.md", "Отток в первый месяц 35% [E2].", "Отток в первый месяц 35%.")
            self.assert_fails_with(root, "число без метки")

    def test_unknown_reference_fails(self):
        with TempRepo() as root:
            p = make_good_project(root)
            rewrite(p, "research.md", "[E2]", "[E99]")
            self.assert_fails_with(root, "E99 нет в evidence.csv")

    def test_revoked_evidence_fails_and_revisit_finds_dependents(self):
        with TempRepo() as root:
            make_good_project(root)
            run("evidence", "revoke", "E1", "--reason", "отчёт отозван автором")
            self.assert_fails_with(root, "E1 отозвана")
            _, out = run("revisit", "E1")
            self.assertIn("C1", out)
            self.assertIn("C2", out)  # транзитивно: C2 опирается на C1
            self.assertIn("decision-brief.md", out)
            _, stale = run("revisit", "--stale")
            self.assertIn("ОТОЗВАНА", stale)

    def test_conclusion_without_basis_fails(self):
        with TempRepo() as root:
            p = make_good_project(root)
            rewrite(p, "options.md", "**C2.** Рекомендуем вариант B [C1; E1].", "**C2.** Рекомендуем вариант B.")
            self.assert_fails_with(root, "без оснований")

    def test_cycle_between_conclusions_fails(self):
        with TempRepo() as root:
            p = make_good_project(root)
            rewrite(p, "research.md", "**C1.** Удержание падает после пробного периода [E1].",
                    "**C1.** Удержание падает после пробного периода [E1; C2].")
            self.assert_fails_with(root, "циклическая опора")

    def test_synthetic_as_demand_proof_fails(self):
        with TempRepo() as root:
            p = make_good_project(root)
            run("evidence", "add", "--kind", "synthetic", "--source", "synthetic:persona-1", "--quote", "хочу проще", "--quality", "C")
            rewrite(p, "research.md", "## Чего мы не знаем",
                    "Большинство пользователей хотят простоты [СИНТ S1].\n\n## Чего мы не знаем")
            self.assert_fails_with(root, "доказательство спроса")

    def test_phrase_bez_sprosa_is_not_demand_claim(self):
        # ложное срабатывание, найденное на демо: «без спроса» = «не спросив»
        with TempRepo() as root:
            p = make_good_project(root)
            run("evidence", "add", "--kind", "synthetic", "--source", "synthetic:persona-1", "--quote", "включают без спроса", "--quality", "C")
            rewrite(p, "research.md", "## Чего мы не знаем",
                    "Подключение без спроса раздражает [СИНТ S1].\n\n## Чего мы не знаем")
            code, out = run("validate")
            self.assertEqual(code, 0, out)

    def test_synthetic_without_label_fails(self):
        with TempRepo() as root:
            p = make_good_project(root)
            run("evidence", "add", "--kind", "synthetic", "--source", "synthetic:persona-1", "--quote", "хочу проще", "--quality", "C")
            rewrite(p, "research.md", "## Чего мы не знаем", "Персона просит простоты [S1].\n\n## Чего мы не знаем")
            self.assert_fails_with(root, "без метки [СИНТ")

    def test_promise_without_product_support_fails(self):
        with TempRepo() as root:
            p = make_good_project(root)
            rewrite(p, "comms-strategy.md", "(опора: П1)", "(опора: П7)")
            self.assert_fails_with(root, "П7, которого нет")

    def test_empty_unknowns_section_fails(self):
        with TempRepo() as root:
            p = make_good_project(root)
            rewrite(p, "research.md", "- Причины оттока по сегментам: нет данных; закрыть интервью.\n", "")
            self.assert_fails_with(root, "пустой")

    def test_missing_strategy_file_fails_when_stage_reached(self):
        with TempRepo() as root:
            p = make_good_project(root)
            (p / "outputs" / "comms-strategy.md").unlink()
            self.assert_fails_with(root, "comms-strategy.md: нет файла")

    def test_secret_in_repo_fails(self):
        with TempRepo() as root:
            make_good_project(root)
            (root / "notes.md").write_text("key: " + "sk-ant-" + "a1" * 20 + "\n", encoding="utf-8")
            self.assert_fails_with(root, "похоже на секрет")

    def test_stage_cannot_be_closed_with_validate_errors(self):
        # процессная ошибка, найденная на втором примере: этап закрыли в одной команде с красным validate
        with TempRepo() as root:
            p = make_good_project(root)
            rewrite(p, "research.md", "Отток в первый месяц 35% [E2].", "Отток в первый месяц 35%.")
            run("stage", "3", "start")
            code, out = run("stage", "3", "done")
            self.assertEqual(code, 1)
            self.assertIn("не закрыт", out)
            code, _ = run("stage", "3", "done", "--force", "человек принял как есть")
            self.assertEqual(code, 0)
            self.assertIn("закрыт с ошибками", (p / "state/log.md").read_text(encoding="utf-8"))

    def test_combined_label_that_hides_synthetic_fails(self):
        # найдено на демо: [ГИП; СИНТ S1] не разбиралось, синтетика рядом с «готова платить» проходила незамеченной
        with TempRepo() as root:
            p = make_good_project(root)
            run("evidence", "add", "--kind", "synthetic", "--source", "synthetic:persona-1", "--quote", "x", "--quality", "C")
            rewrite(p, "research.md", "## Чего мы не знаем", "Люди хотят знать о звонках [ГИП; СИНТ S1].\n\n## Чего мы не знаем")
            self.assert_fails_with(root, "непонятная метка")

    def test_tag_with_comment_counts_as_tag(self):
        with TempRepo() as root:
            p = make_good_project(root)
            rewrite(p, "research.md", "## Чего мы не знаем",
                    "Может вырасти до 40% [ГИП: проверим интервью].\nРост 5% [ПРОГНОЗ C1: при той же цене].\n\n## Чего мы не знаем")
            code, out = run("validate")
            self.assertEqual(code, 0, out)

    def test_cyrillic_lookalike_reference_is_understood(self):
        with TempRepo() as root:
            p = make_good_project(root)
            rewrite(p, "research.md", "[E2]", "[Е2]")  # кириллическая Е
            code, out = run("validate")
            self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
