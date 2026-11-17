"""Слой 9: цена и готовность платить, свежесть данных по дате публикации, сторож оснований."""
import csv
import unittest
from datetime import date
from pathlib import Path

from sflib import evidence as ev
from sflib import graph, pricing, watch
from sflib.paths import SfError
from tests.fixtures import make_good_project, rewrite
from tests.helpers import TempRepo, run

PAGE_URL = "https://example.org/survey"
QUOTE = "Каждый третий житель сталкивался с мошенническими звонками за последний год"


def write_csv(path: Path, header: list[str], rows: list[list[float]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path


class PricingTest(unittest.TestCase):
    def test_van_westendorp_range_is_ordered_and_drops_inconsistent_answers(self):
        rows = [{"too_cheap": b * 0.5, "cheap": b * 0.8, "expensive": b * 1.2, "too_expensive": b * 1.6}
                for b in range(100, 260, 4)]
        rows.append({"too_cheap": 300, "cheap": 100, "expensive": 200, "too_expensive": 250})  # дёшево > дорого
        result = pricing.van_westendorp(rows)
        self.assertEqual(result.dropped, 1)
        self.assertEqual(result.respondents, 40)
        self.assertTrue(result.pmc < result.ipp < result.pme, result)
        self.assertTrue(result.pmc <= result.opp <= result.pme, result)

    def test_van_westendorp_needs_consistent_answers(self):
        with self.assertRaises(SfError):
            pricing.van_westendorp([{"too_cheap": 5, "cheap": 4, "expensive": 3, "too_expensive": 2}])

    def test_gabor_granger_picks_revenue_and_warns_when_prices_overlap(self):
        with TempRepo() as root:
            path = write_csv(root / "gg.csv", ["price", "shown", "bought"], [[99, 40, 6], [149, 40, 5], [199, 40, 3]])
            report = pricing.gg_report(path)
        self.assertIn("при цене **149**", report)
        self.assertIn("не различимы", report)
        self.assertIn("A/B с оплатой", report)

    def test_gabor_granger_rejects_impossible_counts(self):
        with self.assertRaises(SfError):
            pricing.gabor_granger([{"price": 100, "shown": 10, "bought": 11}])

    def test_cli_price_writes_report_and_warns_on_small_sample(self):
        with TempRepo() as root:
            run("new", "p1")
            proj = root / "projects" / "p1"
            write_csv(proj / "vw.csv", list(pricing.VW_COLUMNS),
                      [[b * 0.5, b * 0.8, b * 1.2, b * 1.6] for b in range(100, 200, 10)])
            code, out = run("price", "vw", "vw.csv", "--show")
            self.assertEqual(code, 0, out)
            self.assertIn("Приемлемый диапазон", out)
            self.assertIn("ответов меньше 30", out)
            self.assertTrue((proj / "state" / "analysis" / "price-vw-vw.md").exists())

    def test_strategy_without_price_section_fails_validate(self):
        with TempRepo() as root:
            proj = make_good_project(root)
            rewrite(proj, "product-strategy.md", "### Цена и готовность платить", "### Прочее")
            code, out = run("validate")
            self.assertEqual(code, 1, out)
            self.assertIn("нет раздела «Цена…»", out)


class FreshnessTest(unittest.TestCase):
    def test_published_end_covers_whole_period(self):
        self.assertEqual(ev.published_end("2021"), date(2021, 12, 31))
        self.assertEqual(ev.published_end("2025-03"), date(2025, 3, 28))
        self.assertEqual(ev.published_end("2026-07-16"), date(2026, 7, 16))
        self.assertIsNone(ev.published_end("весной"))

    def test_old_publication_is_stale_even_if_downloaded_today(self):
        with TempRepo() as root:
            proj = make_good_project(root)
            self.assertEqual(run("evidence", "published", "E1", "2021-06")[0], 0)
            issues = graph.stale(proj, max_age_days=180, max_data_age_days=730)
            self.assertTrue(any(i.startswith("E1: данные опубликованы 2021-06") for i in issues), issues)
            self.assertTrue(any(i.startswith("Без даты публикации") and "E1" not in i.split(":")[1] for i in issues), issues)

    def test_bad_published_value_is_refused(self):
        with TempRepo() as root:
            make_good_project(root)
            code, out = run("evidence", "published", "E1", "июнь")
            self.assertNotEqual(code, 0)
            self.assertIn("ГГГГ", out)

    def test_old_registry_without_published_column_still_loads(self):
        with TempRepo() as root:
            proj = make_good_project(root)
            path = ev.path_for(proj)
            lines = path.read_text(encoding="utf-8").splitlines()
            header = lines[0].split(",")
            keep = [i for i, name in enumerate(header) if name != "published"]
            rows = list(csv.reader(lines))
            with path.open("w", encoding="utf-8", newline="") as handle:
                csv.writer(handle).writerows([[r[i] for i in keep] for r in rows])
            self.assertTrue(all(r.published == "" for r in ev.load(proj)))


class WatchTest(unittest.TestCase):
    def test_quote_matching_ignores_typography_and_checks_every_fragment(self):
        page = "…по данным опроса, каждый третий житель  сталкивался с мошенническими звонками за последний год — и это много."
        self.assertTrue(watch.quote_in("«Каждый третий житель сталкивался с мошенническими звонками за последний год»", page))
        self.assertTrue(watch.quote_in("каждый третий житель … за последний год — и это много", page))
        self.assertFalse(watch.quote_in("каждый третий житель … за последние пять лет", page))
        self.assertIsNone(watch.quote_in("коротко", page))
        self.assertTrue(watch.quote_in("Вы можете добавить до 3 доверенных лиц.", "Вы можете добавить до 3&nbsp;**доверенных** лиц."))

    def _project_with_web_source(self, root: Path) -> Path:
        proj = make_good_project(root)
        snapshot = proj / "sources" / "web-example-2026-11-01.md"
        snapshot.write_text(f"# Опрос\n\n- URL: {PAGE_URL}\n- Дата доступа: 2026-11-01\n\n---\n\n{QUOTE}. Остальное.\n",
                            encoding="utf-8")
        ev.add(proj, "doc", "sources/web-example-2026-11-01.md", "абзац 1", QUOTE, "A")
        return proj

    def test_statuses_same_changed_unavailable(self):
        with TempRepo() as root:
            proj = self._project_with_web_source(root)
            new_id = ev.load(proj)[-1].id
            same = watch.check(proj, lambda url: ("", f"Сегодня: {QUOTE.lower()}. " + "текст " * 50), [new_id])
            self.assertEqual(same[0].status, watch.SAME)
            changed = watch.check(proj, lambda url: ("", "Каждый пятый житель сталкивался с мошенническими звонками. " + "текст " * 50), [new_id])
            self.assertEqual(changed[0].status, watch.CHANGED)

            def down(url: str) -> tuple[str, str]:
                raise SfError("Сайт недоступен")
            self.assertEqual(watch.check(proj, down, [new_id])[0].status, watch.UNAVAILABLE)
            empty = watch.check(proj, lambda url: ("", "   "), [new_id])[0]  # страница собирается скриптами
            self.assertEqual(empty.status, watch.UNAVAILABLE)
            self.assertIn("без текста", empty.detail)

    def test_quote_absent_from_own_snapshot_is_not_compared(self):
        with TempRepo() as root:
            proj = self._project_with_web_source(root)
            ev.add(proj, "doc", "sources/web-example-2026-11-01.md", "абзац 2", "Пересказ, которого нет в снимке дословно", "B")
            last = ev.load(proj)[-1].id
            result = watch.check(proj, lambda url: ("", "совсем другая страница без цитаты " * 20), [last])
            self.assertEqual(result[0].status, watch.NOT_COMPARABLE)

    def test_report_lists_changes_first_and_points_to_revisit(self):
        results = [watch.Result("E2", PAGE_URL, watch.SAME, "ok"), watch.Result("E5", PAGE_URL, watch.CHANGED, "нет", ("C1",))]
        text = watch.report(results, date(2026, 11, 17))
        self.assertLess(text.index("| E5 |"), text.index("| E2 |"))
        self.assertIn("sf.py revisit E5", text)

    def test_unknown_record_is_refused(self):
        with TempRepo() as root:
            proj = make_good_project(root)
            with self.assertRaises(SfError):
                watch.check(proj, lambda url: ("", ""), ["E999"])


if __name__ == "__main__":
    unittest.main()
