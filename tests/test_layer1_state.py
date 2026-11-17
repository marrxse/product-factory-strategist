"""Слой 1: создание проекта, этапы и ворота, журнал с защитой от повтора, сводка для возобновления."""
import unittest

from sflib import journal
from sflib import state as stmod
from tests.helpers import TempRepo, run


class ProjectLifecycleTest(unittest.TestCase):
    def test_new_project_creates_state_and_becomes_active(self):
        with TempRepo() as root:
            code, out = run("new", "demo-x", "--title", "Демо")
            self.assertEqual(code, 0, out)
            state_text = (root / "projects/demo-x/state/STATE.md").read_text(encoding="utf-8")
            rows = stmod.parse_rows(state_text)
            self.assertEqual(len(rows), 9)
            self.assertIn("Демо", state_text)
            self.assertEqual((root / "projects/.active").read_text().strip(), "demo-x")

    def test_duplicate_project_is_rejected(self):
        with TempRepo():
            run("new", "demo-x")
            code, out = run("new", "demo-x")
            self.assertEqual(code, 1)
            self.assertIn("уже существует", out)

    def test_bad_slug_is_rejected(self):
        with TempRepo():
            code, out = run("new", "Плохое Имя")
            self.assertEqual(code, 1)
            self.assertIn("не подходит", out)

    def test_status_without_active_project_is_a_friendly_start(self):
        with TempRepo():
            code, out = run("status")
            self.assertEqual(code, 0)                           # первый запуск — не ошибка
            self.assertNotIn("Ошибка", out)
            self.assertIn("начни <тема>", out)

    def test_command_without_active_project_explains_what_to_do(self):
        with TempRepo():
            code, out = run("evidence", "list")
            self.assertEqual(code, 1)
            self.assertIn("Нет активного проекта", out)


class StageGateTest(unittest.TestCase):
    def test_gated_stage_waits_for_human_then_completes(self):
        with TempRepo() as root:
            run("new", "p1")
            run("stage", "0", "start")
            run("stage", "0", "done")
            rows = stmod.parse_rows((root / "projects/p1/state/STATE.md").read_text(encoding="utf-8"))
            self.assertEqual((rows[0].status, rows[0].gate), ("ждёт решения", "ждёт"))
            _, summary = run("status")
            self.assertIn("Ждёт решения человека: этап 0", summary)

            run("gate", "0", "ok", "формулировка верна")
            rows = stmod.parse_rows((root / "projects/p1/state/STATE.md").read_text(encoding="utf-8"))
            self.assertEqual((rows[0].status, rows[0].gate), ("готов", "одобрено"))
            self.assertEqual(stmod.current_stage(rows).num, 1)

    def test_gate_fix_returns_stage_to_work(self):
        with TempRepo() as root:
            run("new", "p1")
            run("stage", "4", "done")
            run("gate", "4", "fix", "добавить вариант")
            rows = stmod.parse_rows((root / "projects/p1/state/STATE.md").read_text(encoding="utf-8"))
            self.assertEqual((rows[4].status, rows[4].gate), ("в работе", "правки"))

    def test_gate_on_stage_without_gate_fails(self):
        with TempRepo():
            run("new", "p1")
            code, out = run("gate", "1", "ok")
            self.assertEqual(code, 1)
            self.assertIn("нет ворот", out)


class IdempotentLogTest(unittest.TestCase):
    def test_done_step_is_not_silently_repeated(self):
        with TempRepo():
            run("new", "p1")
            self.assertEqual(run("log", "start", "collect:fetch:site", "качаю")[0], 0)
            run("log", "done", "collect:fetch:site", "ок")
            code, out = run("log", "start", "collect:fetch:site", "ещё раз")
            self.assertEqual(code, 3)
            self.assertIn("уже выполнен", out)

    def test_explicit_repeat_is_allowed_and_recorded(self):
        with TempRepo() as root:
            run("new", "p1")
            run("log", "start", "k1", "a")
            run("log", "done", "k1", "a")
            code, _ = run("log", "start", "k1", "b", "--repeat", "источник обновился")
            self.assertEqual(code, 0)
            entries = journal.read_entries(root / "projects/p1/state/log.md")
            self.assertEqual(entries[-1].kind, "REPEAT")
            self.assertIn("источник обновился", entries[-1].text)

    def test_interrupted_step_shows_up_on_resume(self):
        with TempRepo():
            run("new", "p1")
            run("log", "start", "research:q2", "сопоставляю")
            _, summary = run("status")
            self.assertIn("Незавершённые шаги", summary)
            self.assertIn("research:q2", summary)
            run("log", "done", "research:q2", "готово")
            _, summary = run("status")
            self.assertNotIn("research:q2 —", summary.split("Последние действия")[0])

    def test_pipe_in_text_does_not_break_log_format(self):
        with TempRepo() as root:
            run("new", "p1")
            run("log", "note", "k", "a | b")
            entries = journal.read_entries(root / "projects/p1/state/log.md")
            self.assertEqual(entries[-1].text, "a / b")


if __name__ == "__main__":
    unittest.main()
