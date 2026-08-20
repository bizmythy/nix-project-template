from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Language(StrEnum):
    RUST = "rust"
    PYTHON = "python"
    GO = "go"
    TYPESCRIPT = "typescript"


@dataclass(frozen=True)
class Profile:
    packages: tuple[str, ...]
    formatters: tuple[str, ...]


PROFILES = {
    Language.RUST: Profile(
        packages=("rustToolchain",),
        formatters=("rustfmt",),
    ),
    Language.PYTHON: Profile(
        packages=("ruff", "uv", "ty"),
        formatters=("ruff",),
    ),
    Language.GO: Profile(
        packages=("go", "golines", "gofumpt"),
        formatters=("golines", "gofumpt"),
    ),
    Language.TYPESCRIPT: Profile(
        packages=(
            "bun",
            "biome",
        ),
        formatters=("biome",),
    ),
}


def normalized_languages(values: tuple[str, ...]) -> tuple[Language, ...]:
    """Return selected languages once, in stable profile order."""
    selected = {Language(value) for value in values}
    return tuple(language for language in Language if language in selected)
