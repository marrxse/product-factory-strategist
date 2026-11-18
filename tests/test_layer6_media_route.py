"""Слой 6: изображения, аудио, видео (media) и маршрутизация модели и инструмента (route)."""
import shutil
import struct
import unittest
import wave
import zlib
from pathlib import Path

from sflib import media
from tests.fixtures import make_good_project
from tests.helpers import TempRepo, run


def png_bytes(width: int, height: int) -> bytes:
    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def jpeg_header(width: int, height: int) -> bytes:
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof0 = b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, height, width, 1) + b"\x01\x11\x00"
    return b"\xff\xd8" + app0 + sof0 + b"\xff\xd9"


class ImageSizeTest(unittest.TestCase):
    def test_reads_png_gif_jpeg_webp_headers(self):
        self.assertEqual(media.image_size(png_bytes(3, 2)), (3, 2))
        self.assertEqual(media.image_size(b"GIF89a" + struct.pack("<HH", 40, 30) + b"\x00" * 8), (40, 30))
        self.assertEqual(media.image_size(jpeg_header(640, 480)), (640, 480))
        webp = b"RIFF" + b"\x00" * 4 + b"WEBPVP8X" + b"\x00" * 8 + (1439).to_bytes(3, "little") + (899).to_bytes(3, "little")
        self.assertEqual(media.image_size(webp), (1440, 900))

    def test_unknown_bytes_give_none(self):
        self.assertIsNone(media.image_size(b"not an image at all"))


class MediaCommandTest(unittest.TestCase):
    def test_inspect_image_and_wav(self):
        with TempRepo() as root:
            run("new", "p1")
            screens = root / "projects" / "p1" / "sources" / "screens"
            screens.mkdir(parents=True)
            (screens / "home.png").write_bytes(png_bytes(4, 3))
            code, out = run("media", "inspect", "sources/screens/home.png")
            self.assertEqual(code, 0)
            self.assertIn("image", out)
            self.assertIn("4×3 px", out)
            with wave.open(str(screens.parent / "call.wav"), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(8000)
                handle.writeframes(b"\x00\x00" * 16000)
            code, out = run("media", "inspect", "sources/call.wav")
            self.assertIn("2.0 с", out)
            self.assertIn("расшифровка", out)

    def test_missing_tool_is_logged_as_fail_not_silent(self):
        if shutil.which("ffmpeg"):
            self.skipTest("ffmpeg установлен — проверяется только поведение без него")
        with TempRepo() as root:
            run("new", "p1")
            video = root / "projects" / "p1" / "sources" / "demo.mp4"
            video.write_bytes(b"\x00" * 64)
            code, out = run("media", "frames", "sources/demo.mp4")
            self.assertEqual(code, 1)
            self.assertIn("Нет ffmpeg", out)
            log = (root / "projects" / "p1" / "state" / "log.md").read_text(encoding="utf-8")
            self.assertIn("FAIL", log)
            self.assertIn("collect:frames:demo.mp4", log)

    def test_shot_rejects_non_http_address(self):
        with TempRepo():
            run("new", "p1")
            code, out = run("media", "shot", "file:///etc/passwd")
            self.assertEqual(code, 1)
            self.assertIn("http", out)

    def test_image_evidence_requires_existing_file(self):
        with TempRepo() as root:
            run("new", "p1")
            args = ("evidence", "add", "--kind", "image", "--source", "sources/screens/a.png",
                    "--locator", "телефон, первый экран", "--quote", "Подключить за 149 ₽", "--quality", "A")
            code, out = run(*args)
            self.assertEqual(code, 1)
            self.assertIn("не найден", out)
            screens = root / "projects" / "p1" / "sources" / "screens"
            screens.mkdir(parents=True)
            (screens / "a.png").write_bytes(png_bytes(2, 2))
            self.assertEqual(run(*args)[0], 0)


class RouteTest(unittest.TestCase):
    CASES = {
        "почему падает удержание — есть таблица когорт": "behavior-analysis",
        "посчитать конверсию воронки по таблице": "data-analysis",
        # пример вопроса из задания; найдено проверкой «глазами жюри»: «приложение» уводило в разбор интерфейса
        "почему падает удержание в приложении": "behavior-analysis",
        "кому и как продавать новый сервис": "по этапу",
        # реальная ошибка маршрута из демо (журнал revisit:behavior:route): правила для поведения не было
        "почему люди не покупают защиту и уходят: анализ поведения клиентов, таблица оттока": "behavior-analysis",
        "разобрать экран оформления подписки в приложении": "ux-review",
        "оценить качество источников в реестре": "collect",
        "подготовить гайд интервью": "interview-guide",
        "найти сильнейшие возражения к варианту B": "quality-review",
        "пересмотреть выводы после новых данных": "decision-support",
        "поговорить с синтетическими респондентами": "synthetic-respondents",
        # реальная ошибка маршрута из демо (журнал revisit:ux:route): «страницу» уводило в сбор фактов
        "разобрать страницу подписки конкурента на компьютере и телефоне: путь пользователя": "ux-review",
        # найдено проверкой 17.11: новые процедуры не были в маршрутизаторе
        "какую цену поставить на подписку": "product-strategy",
        "готовы ли платить за семейную защиту и что дороже для нас": "product-strategy",
        "проверь, не изменились ли источники решения": "decision-support",
        # найдено репетицией видео 17.11: «мобильном» уводило вопрос об удержании в разбор интерфейса
        "почему падает удержание подписки в мобильном приложении": "behavior-analysis",
        "провести фокус-группу на 60 персонах по сообщению": "synthetic-respondents",
        "собрать совет взглядов по вариантам": "options",
    }

    def test_choose_picks_expected_skill(self):
        with TempRepo():
            run("new", "p1")
            for task, skill in self.CASES.items():
                _, out = run("route", "choose", task)
                self.assertIn(f"навык {skill}", out, task)

    def test_interface_and_interview_do_not_collide(self):
        with TempRepo():
            run("new", "p1")
            _, out = run("route", "choose", "интерфейс")
            self.assertIn("ux-review", out)
            _, out = run("route", "choose", "интервью")
            self.assertIn("interview-guide", out)

    def test_unknown_task_falls_back_to_orchestrator(self):
        with TempRepo():
            run("new", "p1")
            _, out = run("route", "choose", "абракадабра")
            self.assertIn("общая работа", out)

    def test_choose_with_key_writes_route_entry(self):
        with TempRepo() as root:
            run("new", "p1")
            run("route", "choose", "разобрать скриншоты лендинга", "--key", "research:ux")
            log = (root / "projects" / "p1" / "state" / "log.md").read_text(encoding="utf-8")
            self.assertIn("ROUTE", log)
            self.assertIn("ux-review", log)

    def test_escalate_climbs_ladder_and_stops_at_top(self):
        with TempRepo() as root:
            run("new", "p1")
            code, out = run("route", "escalate", "классификатор ошибся", "--key", "collect:classify", "--model", "claude-haiku-5-5")
            self.assertEqual(code, 0)
            self.assertIn("claude-sonnet-5-5", out)
            log = (root / "projects" / "p1" / "state" / "log.md").read_text(encoding="utf-8")
            self.assertIn("claude-haiku-5-5 → claude-sonnet-5-5", log)
            code, out = run("route", "escalate", "x", "--key", "k", "--model", "claude-opus-5-5")
            self.assertEqual(code, 1)
            self.assertIn("человек", out)

    def test_classifier_input_hides_quality_and_compare_finds_disagreements(self):
        with TempRepo() as root:
            project = make_good_project(root)
            run("route", "classify-input")
            hidden = (project / "state" / "routing" / "classify-input.csv").read_text(encoding="utf-8")
            self.assertNotIn("quality", hidden.splitlines()[0])
            classified = project / "state" / "routing" / "classified.csv"
            classified.write_text("id,quality,reason\nE1,B,деловое СМИ\nE2,C,нет даты\n", encoding="utf-8")
            code, out = run("route", "compare", "state/routing/classified.csv")
            self.assertEqual(code, 1)
            self.assertIn("1 из 2", out)
            self.assertIn("E2: реестр A, классификатор C", out)


class EvidenceQualityTest(unittest.TestCase):
    def test_quality_change_needs_reason_and_keeps_trail(self):
        with TempRepo() as root:
            project = make_good_project(root)
            code, out = run("evidence", "quality", "E1", "C")
            self.assertEqual(code, 1)
            self.assertIn("причину", out)
            code, out = run("evidence", "quality", "E1", "C", "--reason", "пересказ без первоисточника")
            self.assertEqual(code, 0)
            self.assertIn("B → C", out)
            _, shown = run("evidence", "show", "E1")
            self.assertIn("качество C", shown)
            self.assertIn("B → C: пересказ без первоисточника", shown)
            log = (project / "state" / "log.md").read_text(encoding="utf-8")
            self.assertIn("evidence:quality:E1", log)


class PipelineDocTest(unittest.TestCase):
    def test_committed_pipeline_matches_code_and_skills(self):
        from sflib import pipeline, stages
        from tests.helpers import REPO
        self.assertTrue(pipeline.is_current(REPO), "docs/PIPELINE.md устарел — python3 sf.py pipeline")
        self.assertEqual([s.stage for s in pipeline.STEPS], [s.num for s in stages.STAGES])
        for step in pipeline.STEPS:
            for skill in step.skills:
                self.assertTrue((REPO / "skills" / skill / "SKILL.md").exists(), skill)
            for agent in step.subagents:
                self.assertTrue((REPO / "agents" / f"{agent}.md").exists(), agent)


class UxReviewValidateTest(unittest.TestCase):
    def test_ux_review_requires_sections(self):
        with TempRepo() as root:
            project = make_good_project(root)
            (project / "outputs" / "ux-review.md").write_text("# Анализ\n\n## Находки\nтекст\n", encoding="utf-8")
            code, out = run("validate")
            self.assertEqual(code, 1)
            self.assertIn("Путь пользователя", out)


if __name__ == "__main__":
    unittest.main()
