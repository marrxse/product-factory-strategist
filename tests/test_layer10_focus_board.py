"""Слой 10: синтетическая фокус-группа (персоны кодом, карта возражений без доли «купят») и совет взглядов."""
import json
import unittest
from pathlib import Path

from sflib import focus
from sflib.paths import SfError
from tests.fixtures import make_good_project, rewrite
from tests.helpers import REPO, TempRepo, run

SPEC = """
[focus]
n = 20
seed = 3
stimulus = "Кнопка помощи для близкого. 149 ₽ в месяц."
concerns = ["цена", "слежка и приватность", "не нужно мне"]

[[segments]]
name = "защищающий"
share = 0.5
age = [30, 50]
income = ["средний"]
phone_skill = ["уверенно"]
habit = ["звонит родителям"]
attitude = ["волнуется"]
situation = ["маме звонили"]

[[segments]]
name = "близкий"
share = 0.5
age = [60, 80]
income = ["пенсия"]
phone_skill = ["неуверенно"]
habit = ["отвечает на все звонки"]
attitude = ["стесняется"]
situation = ["ничего не случалось"]
"""


def write_spec(project: Path, text: str = SPEC) -> Path:
    path = project / "state" / "focus" / "spec.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class FocusTest(unittest.TestCase):
    def test_personas_are_reproducible_and_follow_shares(self):
        with TempRepo() as root:
            spec = focus.load_spec(write_spec(make_good_project(root)))
            first, second = focus.personas(spec), focus.personas(spec)
            self.assertEqual(first, second)                                    # то же зерно — те же персоны
            self.assertEqual(len(first), 20)
            self.assertEqual(sum(p.segment == "близкий" for p in first), 10)
            self.assertTrue(all(60 <= p.age <= 80 for p in first if p.segment == "близкий"))

    def test_spec_errors_are_explained(self):
        with TempRepo() as root:
            p = make_good_project(root)
            with self.assertRaisesRegex(SfError, "в сумме"):
                focus.load_spec(write_spec(p, SPEC.replace("share = 0.5\nage = [60", "share = 0.3\nage = [60")))
            with self.assertRaisesRegex(SfError, "n = 5"):
                focus.load_spec(write_spec(p, SPEC.replace("n = 20", "n = 5")))

    def test_setup_writes_batches_without_our_hypotheses(self):
        with TempRepo() as root:
            p = make_good_project(root)
            write_spec(p)
            code, out = run("focus", "setup")
            self.assertEqual(code, 0, out)
            batches = sorted((p / "state" / "focus").glob("batch-*.md"))
            self.assertEqual(len(batches), 2)
            text = batches[0].read_text(encoding="utf-8")
            self.assertIn("Кнопка помощи для близкого", text)
            self.assertNotIn("options", text)                                  # варианты и гипотезы не передаются

    def test_map_counts_stop_factors_and_never_reports_buyers(self):
        with TempRepo() as root:
            p = make_good_project(root)
            write_spec(p)
            ids = [x.id for x in focus.personas(focus.load_spec(p / "state" / "focus" / "spec.toml"))]
            lines = [json.dumps({"id": i, "retell": "кнопка зовёт сына", "stop": ["цена"] if n % 2 else ["слежка и приватность", "ерунда"],
                                 "stop_text": "дорого" if n % 2 else "за мной будут следить", "condition": "бесплатный месяц"},
                                ensure_ascii=False) for n, i in enumerate(ids[:-1])]
            lines += ["мусор", json.dumps({"id": ids[0], "stop": []}), json.dumps({"id": "P999", "stop": []})]
            (p / "state" / "focus" / "responses.jsonl").write_text("\n".join(lines), encoding="utf-8")
            code, out = run("focus", "map", "--show")
            self.assertEqual(code, 0, out)
            self.assertIn("| слежка и приватность | ×10 из 19 |", out)
            self.assertIn("| другое | ×10 из 19 |", out)                        # неизвестный код не теряется
            self.assertIn("неизвестная персона «P999»", out)
            self.assertIn("повтор P001", out)
            self.assertIn(f"нет ответов: {ids[-1]}", out)
            self.assertNotRegex(out, r"(?i)\bкупят\b|готов\w* платить|процент покуп")

    def test_validate_blocks_synthetic_as_buy_verdict(self):
        with TempRepo() as root:
            p = make_good_project(root)
            run("evidence", "add", "--kind", "synthetic", "--source", "brief.md", "--quote", "дорого", "--quality", "C")
            rewrite(p, "research.md", "## Чего мы не знаем", "Из 60 персон купят 20 [СИНТ S1].\n\n## Чего мы не знаем")
            code, out = run("validate")
            self.assertEqual(code, 1, out)
            self.assertIn("синтетика использована как доказательство спроса", out)


class BoardTest(unittest.TestCase):
    def test_board_agent_uses_roles_not_real_people_and_has_model(self):
        text = (REPO / "agents" / "board.md").read_text(encoding="utf-8")
        for role in ("Финансовый директор", "Директор по маркетингу", "Юрист", "поддержки", "Голос клиента"):
            self.assertIn(role, text)
        self.assertIn("не говори от имени реальных персон", text)
        self.assertIn("Не суммируй голоса", text)
        config = (REPO / "config.toml").read_text(encoding="utf-8")
        self.assertRegex(config, r"(?m)^board\s*=")


if __name__ == "__main__":
    unittest.main()
