"""Перенос проекта между средами (Claude Code ↔ Cursor ↔ другая машина): архив папки проекта с проверкой целостности."""
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path

from . import paths
from .paths import SfError

MANIFEST = "sf-manifest.json"


def export(slug: str, target_dir: Path) -> Path:
    project = paths.project_dir(slug)
    target_dir.mkdir(parents=True, exist_ok=True)
    archive = target_dir / f"{slug}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    files = sorted(p for p in project.rglob("*") if p.is_file())
    manifest = {"slug": slug, "exported": datetime.now().isoformat(timespec="seconds"),
                "files": {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, f"{slug}/{path.relative_to(project)}")
        zf.writestr(f"{slug}/{MANIFEST}", json.dumps(manifest, ensure_ascii=False, indent=1))
    return archive


def import_archive(archive: Path) -> str:
    if not archive.is_file():
        raise SfError(f"Архив не найден: {archive}")
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        manifest_name = next((n for n in names if n.endswith("/" + MANIFEST)), None)
        if manifest_name is None:
            raise SfError("В архиве нет sf-manifest.json — это не экспорт sf.py.")
        manifest = json.loads(zf.read(manifest_name))
        slug = paths.validate_slug(manifest["slug"])
        target = paths.projects_dir() / slug
        if target.exists():
            raise SfError(f"Проект «{slug}» уже есть в projects/. Переименуйте или удалите его перед импортом.")
        for name in names:
            if ".." in Path(name).parts or Path(name).is_absolute() or not name.startswith(f"{slug}/"):
                raise SfError(f"Подозрительный путь в архиве: {name}")
        broken = [rel for rel, digest in manifest["files"].items()
                  if hashlib.sha256(zf.read(f"{slug}/{rel}")).hexdigest() != digest]
        if broken:
            raise SfError(f"Файлы повреждены: {', '.join(broken[:5])}")
        for name in names:
            if name == manifest_name or name.endswith("/"):
                continue
            out = paths.projects_dir() / name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(zf.read(name))
    paths.set_active(slug)
    return slug
