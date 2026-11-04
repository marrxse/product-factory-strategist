"""Слой 5: перенос проекта между средами — экспорт, импорт, целостность, защита от подмены путей."""
import shutil
import unittest
import zipfile

from tests.fixtures import make_good_project
from tests.helpers import TempRepo, run


class PortableTest(unittest.TestCase):
    def test_export_then_import_restores_project_and_resume_works(self):
        with TempRepo() as root:
            make_good_project(root, "moved")
            code, out = run("export", "moved")
            self.assertEqual(code, 0, out)
            archive = next((root / "exports").glob("moved-*.zip"))
            shutil.rmtree(root / "projects" / "moved")          # «другая среда»: проекта нет
            code, out = run("import", str(archive))
            self.assertEqual(code, 0, out)
            self.assertIn("продолжи", out)
            code, status = run("status")
            self.assertIn("Проект: moved", status)
            self.assertEqual(run("validate", "--final")[0], 0)

    def test_import_refuses_existing_project(self):
        with TempRepo() as root:
            make_good_project(root, "moved")
            run("export", "moved")
            archive = next((root / "exports").glob("moved-*.zip"))
            code, out = run("import", str(archive))
            self.assertEqual(code, 1)
            self.assertIn("уже есть", out)

    def test_tampered_archive_is_rejected(self):
        with TempRepo() as root:
            make_good_project(root, "moved")
            run("export", "moved")
            archive = next((root / "exports").glob("moved-*.zip"))
            bad = root / "bad.zip"
            with zipfile.ZipFile(archive) as src, zipfile.ZipFile(bad, "w") as dst:
                for item in src.namelist():
                    data = src.read(item)
                    dst.writestr(item, data + b"x" if item.endswith("brief.md") else data)
            shutil.rmtree(root / "projects" / "moved")
            code, out = run("import", str(bad))
            self.assertEqual(code, 1)
            self.assertIn("повреждены", out)


if __name__ == "__main__":
    unittest.main()
