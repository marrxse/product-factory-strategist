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
            self.assertTrue(page.index('id="decision-brief"') < page.index('id="research"'))  # решение первым


if __name__ == "__main__":
    unittest.main()
