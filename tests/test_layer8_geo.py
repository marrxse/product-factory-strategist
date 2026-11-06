"""Слой 8: канал «ответы нейросетей» — разбор ответов ИИ-ассистентов."""
import unittest

from sflib import geo
from tests.helpers import TempRepo, run

ALICE = """# ответы
## Q1: Какой оператор лучше защищает?
По отзывам, МТС предлагает «Защитник», у МегаФона есть ассистент Ева. Подробнее: https://www.comnews.ru/a и https://mts.ru/b
## Q2: Обязаны ли операторы защищать бесплатно?
По закону операторы обязаны всё делать бесплатно. Источник: https://www.comnews.ru/c
"""
GIGA = """## Q1: Какой оператор лучше защищает?
МегаФон и МТС развивают защиту; Билайн тоже.
## Q2: Обязаны ли операторы защищать бесплатно?
Обязательна маркировка звонков от организаций.
"""


class GeoTest(unittest.TestCase):
    def test_mentions_order_sources_and_risky_claims(self):
        with TempRepo() as root:
            run("new", "p1")
            folder = root / "projects" / "p1" / "sources" / "geo"
            folder.mkdir(parents=True)
            (folder / "alice-2026-11-07.md").write_text(ALICE, encoding="utf-8")
            (folder / "gigachat-2026-11-07.md").write_text(GIGA, encoding="utf-8")
            (folder / "questions.md").write_text("## Q1: вопрос\n", encoding="utf-8")
            code, out = run("geo", "--brands", "МТС=МТС|MTS; МегаФон=МегаФон|Мегафон; Билайн=Билайн", "--risky", "по закону,100%", "--show")
            self.assertEqual(code, 0, out)
            self.assertIn("Ассистенты: alice, gigachat; ответов: 4; вопросов: 2", out)
            self.assertIn("| МТС | 1 из 2 | 1 из 2 | 2 из 4 | 1 |", out)
            self.assertIn("| МегаФон | 1 из 2 | 1 из 2 | 2 из 4 | 1 |", out)
            self.assertIn("comnews.ru — в 2 ответах", out)
            self.assertIn("alice Q2 «по закону»", out)
            self.assertTrue((root / "projects" / "p1" / "state" / "analysis" / "geo-answers.md").exists())
            self.assertIn("| Q2: Обязаны ли операторы защищать бесплатно? | — | — |", out)  # «mts.ru» в ссылке Q1 не считается, в Q2 брендов нет

    def test_bad_brand_spec_and_empty_folder(self):
        with self.assertRaises(Exception):
            geo.parse_brands("  ;  ")
        with TempRepo():
            run("new", "p1")
            code, out = run("geo", "--brands", "МТС=МТС")
            self.assertEqual(code, 1)
            self.assertIn("sources/geo", out)


if __name__ == "__main__":
    unittest.main()
