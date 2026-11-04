"""Чтение config.toml (tomllib из стандартной библиотеки)."""
from __future__ import annotations

import tomllib
from functools import lru_cache
from typing import Any

from . import paths


@lru_cache(maxsize=4)
def _load(root: str) -> dict[str, Any]:
    path = paths.repo_root() / "config.toml"
    if not path.exists():
        raise paths.SfError("Нет config.toml в корне репозитория.")
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load() -> dict[str, Any]:
    return _load(str(paths.repo_root()))


def get(section: str, key: str, default: Any = None) -> Any:
    return load().get(section, {}).get(key, default)


def price(model: str) -> dict[str, float]:
    """Цена за 1 млн токенов: input, output, cache_read, cache_write_5m, cache_write_1h."""
    prices = load().get("prices", {})
    if model not in prices:
        known = ", ".join(sorted(k for k in prices if isinstance(prices[k], dict)))
        raise paths.SfError(f"Нет цены для модели «{model}» в config.toml [prices]. Известны: {known}")
    return prices[model]
