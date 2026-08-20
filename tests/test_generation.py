from __future__ import annotations

import itertools
from pathlib import Path

import pytest
from nix_manipulator import parse

from nix_project_generator.generator import GenerationOptions, render_project
from nix_project_generator.profiles import Language


def options(
    destination: Path,
    languages: tuple[Language, ...] = (),
    *,
    private: bool = False,
) -> GenerationOptions:
    return GenerationOptions(
        name="demo-project",
        destination=destination,
        languages=languages,
        private=private,
    )


def test_public_baseline_has_expected_shared_files_and_licenses(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "demo-project"

    render_project(options(destination), author="Example Author", year=2026)

    assert {
        ".envrc",
        ".githooks",
        ".gitignore",
        "LICENSE-APACHE",
        "LICENSE-MIT",
        "README.md",
        "flake.nix",
        "treefmt.nix",
        "yamlfmt.yaml",
    } == {path.name for path in destination.iterdir()}
    assert (
        "Copyright (c) 2026 Example Author"
        in (destination / "LICENSE-MIT").read_text()
    )
    assert (
        "MIT license at your option" in (destination / "README.md").read_text()
    )
    assert (destination / ".githooks/pre-commit").stat().st_mode & 0o111


def test_private_project_omits_licenses_and_license_claim(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "demo-project"

    render_project(options(destination, private=True), author="Example Author")

    assert not (destination / "LICENSE-MIT").exists()
    assert not (destination / "LICENSE-APACHE").exists()
    assert "## License" not in (destination / "README.md").read_text()


@pytest.mark.parametrize(
    "languages",
    [
        tuple(combination)
        for size in range(len(Language) + 1)
        for combination in itertools.combinations(Language, size)
    ],
)
def test_every_language_combination_generates_parseable_nix(
    tmp_path: Path,
    languages: tuple[Language, ...],
) -> None:
    destination = tmp_path / ("project-" + "-".join(languages) or "baseline")

    render_project(options(destination, languages), author="Example Author")

    flake = (destination / "flake.nix").read_text()
    treefmt = (destination / "treefmt.nix").read_text()
    assert parse(flake).rebuild()
    assert parse(treefmt).rebuild()
    assert ("fenix" in flake) is (Language.RUST in languages)
    assert ("stable.toolchain" in flake) is (Language.RUST in languages)
    assert ("wasm32" in flake) is False
    assert ("tsconfig.json" in treefmt) is (Language.TYPESCRIPT in languages)

    gitignore = (destination / ".gitignore").read_text()
    assert ("target/" in gitignore) is (Language.RUST in languages)
    assert (".venv/" in gitignore) is (Language.PYTHON in languages)
    assert (".ruff_cache/" in gitignore) is (Language.PYTHON in languages)
    assert ("node_modules/" in gitignore) is (Language.TYPESCRIPT in languages)

    expectations = {
        Language.RUST: ("            rustToolchain\n", "rustfmt ="),
        Language.PYTHON: (
            "            uv\n",
            "            ruff\n",
            "            ty\n",
            "ruff =",
        ),
        Language.GO: (
            "            go\n",
            "            golines\n",
            "            gofumpt\n",
            "golines =",
            "gofumpt =",
        ),
        Language.TYPESCRIPT: ("            bun\n", "biome ="),
    }
    combined = flake + treefmt
    for language, markers in expectations.items():
        for marker in markers:
            assert (marker in combined) is (language in languages)


def test_invalid_or_existing_destination_is_not_overwritten(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "already-there"
    destination.mkdir()
    marker = destination / "keep"
    marker.write_text("safe")

    with pytest.raises(FileExistsError):
        render_project(options(destination), author="Example Author")

    assert marker.read_text() == "safe"
