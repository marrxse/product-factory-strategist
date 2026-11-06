"""Слой 7: анализ поведения клиентов — журнал событий и таблица оттока."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from sflib import behavior
from tests.helpers import TempRepo, run


def write_events(path: Path) -> None:
    """3 клиента: u1 активен в январе и феврале и купил; u2 только в январе; u3 пришёл в феврале (данные до конца февраля). Плюс дубль и плохая дата."""
    rows = ["user_id,date,event,value",
            "u1,2026-01-03,open,0", "u1,2026-01-05,setup,0", "u1,2026-02-10,open,0", "u1,2026-02-11,pay,199",
            "u2,2026-01-20,open,0", "u2,2026-01-20,open,0",
            "u3,2026-02-02,open,0", "u3,2026-02-04,setup,0", "u3,2026-02-28,open,0",
            "u4,03.02.2026,open,0"]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


class WilsonTest(unittest.TestCase):
    def test_interval_contains_share_and_stays_in_bounds(self):
        low, high = behavior.wilson(30, 100)
        self.assertLess(low, 0.3)
        self.assertGreater(high, 0.3)
        self.assertEqual(behavior.wilson(0, 0), (0.0, 0.0))
        low, high = behavior.wilson(0, 10)
        self.assertEqual(low, 0.0)
        self.assertGreater(high, 0.0)


class EventsTest(unittest.TestCase):
    def test_data_check_cohorts_activation_and_path(self):
        with TempRepo() as root:
            run("new", "p1")
            data = root / "projects" / "p1" / "sources" / "events.csv"
            write_events(data)
            code, out = run("behavior", "events", "sources/events.csv", "--activation", "setup", "--target-event", "pay", "--show")
            self.assertEqual(code, 0, out)
            self.assertIn("полный дубль строки — 1", out)
            self.assertIn("дата не в формате ГГГГ-ММ-ДД — 1", out)
            self.assertIn("| 2026-01 | 2 | 100.0% | 50.0% |", out)
            self.assertNotIn("Последний месяц данных неполный", out)
            self.assertIn("в первые 7 дней: 2 из 3", out)
            self.assertIn("Дошли до «pay»: 1 из 3", out)
            self.assertIn("open (1)", out)
            self.assertTrue((root / "projects" / "p1" / "state" / "analysis" / "events-behavior.md").exists())

    def test_same_data_gives_same_numbers(self):
        with TempRepo() as root:
            run("new", "p1")
            data = root / "projects" / "p1" / "sources" / "events.csv"
            write_events(data)
            first = behavior.events_report(data, "setup", "pay", 7, 30)
            second = behavior.events_report(data, "setup", "pay", 7, 30)
            self.assertEqual(first, second)

    def test_missing_columns_explained(self):
        with TempRepo() as root:
            run("new", "p1")
            bad = root / "projects" / "p1" / "sources" / "bad.csv"
            bad.write_text("id,when\n1,2026-01-01\n", encoding="utf-8")
            code, out = run("behavior", "events", "sources/bad.csv")
            self.assertEqual(code, 1)
            self.assertIn("user_id, date, event", out)

    def test_segments_by_actions(self):
        end = date(2026, 6, 30)
        events = [behavior.Event("old-active", end - timedelta(days=d), "open", 0) for d in (5, 100)]
        events += [behavior.Event("at-risk", end - timedelta(days=d), "open", 0) for d in (45, 120)]
        events += [behavior.Event("sleeper", end - timedelta(days=d), "open", 0) for d in (150, 160)]
        events += [behavior.Event("newbie", end - timedelta(days=3), "open", 0)]
        segs = behavior.segments(sorted(events, key=lambda e: (e.user, e.day)), 30)
        self.assertEqual(len(segs["активные"]), 1)
        self.assertEqual(len(segs["под риском ухода"]), 1)
        self.assertEqual(len(segs["спящие"]), 1)
        self.assertEqual(len(segs["новые"]), 1)


def write_churn(path: Path) -> None:
    """Помесячный договор уходит чаще; внутри помесячного без защиты уходят чаще, чем с ней."""
    rows = ["id,contract,security,months,left"]
    n = 0
    for contract, security, total, churned in (("month", "no", 100, 50), ("month", "yes", 100, 20),
                                               ("year", "no", 100, 10), ("year", "yes", 100, 4)):
        for i in range(total):
            n += 1
            rows.append(f"c{n},{contract},{security},{i % 40},{'Yes' if i < churned else 'No'}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


class ChurnTest(unittest.TestCase):
    def test_rates_gaps_strata_and_filter(self):
        with TempRepo() as root:
            run("new", "p1")
            data = root / "projects" / "p1" / "sources" / "clients.csv"
            write_churn(data)
            code, out = run("behavior", "churn", "sources/clients.csv", "--target", "left", "--positive", "Yes",
                            "--within", "contract", "--show")
            self.assertEqual(code, 0, out)
            self.assertIn("Ушли («left» = Yes): 84", out)
            self.assertIn("Пропущены как идентификаторы", out)
            self.assertIn("| contract | 28.0 п. п.", out)
            self.assertIn("30.0 п. п. (no > yes)", out)
            self.assertIn("квартили", out)
            code, out = run("behavior", "churn", "sources/clients.csv", "--target", "left", "--positive", "Yes",
                            "--where", "contract=month", "--show")
            self.assertIn("Клиентов: 200 из 400 (условие: contract=month)", out)

    def test_bad_target_and_filter_rejected(self):
        with TempRepo() as root:
            run("new", "p1")
            data = root / "projects" / "p1" / "sources" / "clients.csv"
            write_churn(data)
            code, out = run("behavior", "churn", "sources/clients.csv", "--target", "nope", "--positive", "Yes")
            self.assertEqual(code, 1)
            self.assertIn("Нет колонки", out)
            code, out = run("behavior", "churn", "sources/clients.csv", "--target", "left", "--positive", "Yes", "--where", "x=1")
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
