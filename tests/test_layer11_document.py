"""Слой 11: отдельный документ из outputs/ (бриф просит сдать один документ) и картинки в отчёте."""
from __future__ import annotations

import shutil
from pathlib import Path

from sflib import report

ROOT = Path(__file__).resolve().parents[1]


def _copy(tmp_path: Path) -> Path:
    project = tmp_path / "p"
    (project / "outputs").mkdir(parents=True)
    (project / "brief.md").write_text("# Бриф: Тест\n", encoding="utf-8")
    (project / "evidence.csv").write_text(
        (ROOT / "projects" / "megafon-family" / "evidence.csv").read_text(encoding="utf-8"), encoding="utf-8")
    return project


def test_build_document_renders_footnotes_and_sources(tmp_path: Path) -> None:
    project = _copy(tmp_path)
    (project / "outputs" / "strategy.md").write_text("# Стратегия: тест\n\nВывод про остаток [E4].\n", encoding="utf-8")
    target = report.build_document(project, "strategy.md")
    page = target.read_text(encoding="utf-8")
    assert target.name == "strategy.html"
    assert "<h1>Стратегия: тест</h1>" in page
    assert 'id="ev-E4"' in page and "Источники" in page


def test_markdown_image_becomes_figure(tmp_path: Path) -> None:
    html_out = report._md("![Окупаемость](img/payback.svg)", {}, [])
    assert '<img src="img/payback.svg"' in html_out and "<figcaption>Окупаемость</figcaption>" in html_out


def test_missing_document_is_clear_error(tmp_path: Path) -> None:
    project = _copy(tmp_path)
    try:
        report.build_document(project, "nope.md")
    except Exception as exc:  # SfError
        assert "nope.md" in str(exc)
    else:
        raise AssertionError("ожидалась ошибка")


def test_nested_list_items_render_inside_parent() -> None:
    out = report._md("- Родитель\n  - ребёнок 1\n  - ребёнок 2\n- Второй", {}, [])
    assert "<li>Родитель<ul><li>ребёнок 1</li><li>ребёнок 2</li></ul></li>" in out


def test_bold_spanning_a_source_tag_is_rendered() -> None:
    out = report._inline("**Главное допущение [ГИП].** Дальше", {}, [])
    assert "**" not in out and out.startswith("<b>")
