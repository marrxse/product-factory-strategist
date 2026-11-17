"""Отчёт для руководителя: метки превращаются в сноски и значки, служебная разметка не видна."""
import re
import unittest

from tests.fixtures import make_good_project
from tests.helpers import TempRepo, run


class ReportTest(unittest.TestCase):
    def test_report_converts_tags_and_lists_sources(self):
        with TempRepo() as root:
            p = make_good_project(root)
            code, out = run("report")
            self.assertEqual(code, 0, out)
            page = (p / "outputs" / "report.html").read_text(encoding="utf-8")
            text = re.sub(r"<[^>]+>", "", re.sub(r"<style>.*?</style>", "", page, flags=re.S))
            self.assertNotRegex(text, r"\[E\d+")                  # сырых меток доказательств нет
            self.assertNotIn("[ГИП]", text)
            self.assertIn('class="b hyp"', page)                   # гипотезы — значками
            self.assertIn('id="ev-E1"', page)                      # реестр источников — приложением
            self.assertIn('id="C1"', page)                         # якоря выводов
            self.assertIn("удержание падает", page)                # цитата источника в приложении
            self.assertTrue(page.index('id="decision-brief"') < page.index('id="research"'))  # решение раньше подробностей
        self.assertTrue(page.index('id="brief"') < page.index('id="decision-brief"'))     # задача руководителя — самой первой
        self.assertIn("Задача руководителя", page)
        self.assertIn("id='materials'", page)                  # приложение «Исходные материалы» — всё собранное, не только процитированное

    def test_report_is_printable_with_publication_dates(self):
        with TempRepo() as root:
            p = make_good_project(root)
            run("evidence", "published", "E1", "2025-03")
            run("report")
            page = (p / "outputs" / "report.html").read_text(encoding="utf-8")
            self.assertIn("@media print", page)                    # печать: светлая тема, разделы с новой страницы
            self.assertIn("counter(pages)", page)                  # номера страниц в PDF
            self.assertIn("ведёт к цитате в приложении", page)     # на бумаге сноска ведёт в приложение, а не «наведите»
            self.assertRegex(page, r'id="ev-E1".*?2025-03<br><span class="meta">доступ')

    def test_pdf_without_chrome_explains_manual_way(self):
        from unittest import mock
        from sflib import media, report
        with TempRepo() as root:
            p = make_good_project(root)
            run("report")
            with mock.patch.object(media, "find_chrome", return_value=None):
                with self.assertRaisesRegex(Exception, "Сохранить как PDF"):
                    report.to_pdf(p / "outputs" / "report.html")


if __name__ == "__main__":
    unittest.main()
