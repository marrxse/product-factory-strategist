"""Слой 4: поиск по базе знаний (слова, смысл, связи) и память с исправлением и отзывом."""
import shutil
import unittest

from sflib import kb, memory
from tests.helpers import REPO, TempRepo, run


def top_files(query: str, limit: int = 3) -> list[str]:
    docs = kb.load_docs(REPO)
    return [h.doc.file for h in kb.search(query, docs, kb.synonym_groups(REPO), limit)]


class KnowledgeSearchTest(unittest.TestCase):
    def test_finds_by_wording(self):
        self.assertEqual(top_files("матрица сравнения вариантов")[0], "knowledge/option-matrix.md")

    def test_finds_by_meaning_through_synonyms(self):
        # в запросе нет слов из названия темы — найдено через группу синонимов
        self.assertIn("knowledge/metrics-pitfalls.md", top_files("churn"))
        self.assertEqual(top_files("сколько можно заработать")[0], "knowledge/unit-economics.md")
        self.assertEqual(top_files("люди не доверяют списаниям")[0], "knowledge/barriers.md")

    def test_adds_related_topics_marked_as_links(self):
        hits = kb.search("как задавать вопросы", kb.load_docs(REPO), kb.synonym_groups(REPO), 5)
        linked = [h for h in hits if h.via.startswith("связь")]
        self.assertTrue(linked, "ожидалась хотя бы одна тема по связи")
        self.assertTrue(all(h.score < hits[0].score for h in linked))

    def test_all_links_resolve_and_every_topic_is_indexed(self):
        docs = kb.load_docs(REPO)
        self.assertEqual(kb.broken_links(docs), [])
        index = (REPO / "knowledge" / "INDEX.md").read_text(encoding="utf-8")
        for doc in docs:
            self.assertIn(doc.file.split("/")[-1], index, f"{doc.file} нет в INDEX.md")

    def test_empty_query_returns_nothing(self):
        self.assertEqual(top_files("и в на"), [])


class MemoryTest(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()
        self.root = self.repo.__enter__()
        shutil.copytree(REPO / "knowledge", self.root / "knowledge")
        (self.root / "memory").mkdir()

    def tearDown(self):
        self.repo.__exit__(None, None, None)

    def test_agent_entry_requires_basis(self):
        code, out = run("memory", "add", "Удержание падает после пробного периода")
        self.assertEqual(code, 1)
        self.assertIn("без основания", out)

    def test_agent_entry_is_presented_as_observation_not_fact(self):
        run("memory", "add", "Удержание", "падает", "после", "пробного", "периода", "--basis", "demo/C1, E1")
        _, out = run("memory", "search", "отток")  # находит по смыслу: отток ~ удержание
        self.assertIn("Наблюдение агента от", out)
        self.assertIn("не факты", out)

    def test_correct_keeps_history_and_hides_old_from_search(self):
        run("memory", "add", "Пользователи", "ценят", "скидки", "--basis", "demo/C3")
        run("memory", "correct", "M1", "Пользователи", "ценят", "простоту", "--reason", "интервью опровергли", "--author", "human")
        entries = memory.load()
        self.assertEqual([(e.id, e.status) for e in entries], [("M1", "исправлена"), ("M2", "действует")])
        self.assertEqual(entries[0].replaced_by, "M2")
        _, out = run("memory", "search", "пользователи ценят")
        self.assertIn("M2", out)
        self.assertNotIn("M1 ·", out)
        _, everything = run("memory", "search", "пользователи ценят", "--all")
        self.assertIn("M1 ·", everything)

    def test_revoke_requires_reason_and_cannot_repeat(self):
        run("memory", "add", "Решили", "запускать", "B", "--author", "human", "--kind", "решение человека")
        self.assertEqual(run("memory", "revoke", "M1")[0], 1)
        self.assertEqual(run("memory", "revoke", "M1", "--reason", "решение отменено")[0], 0)
        code, out = run("memory", "revoke", "M1", "--reason", "ещё раз")
        self.assertEqual(code, 1)
        self.assertIn("уже отозвана", out)


if __name__ == "__main__":
    unittest.main()
