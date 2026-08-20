from __future__ import annotations

import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, StrictUndefined
from nix_manipulator import parse

from .commands import CommandError, Runner
from .profiles import PROFILES, Language


class GenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class GenerationOptions:
    name: str
    destination: Path
    languages: tuple[Language, ...] = ()
    private: bool = False


@dataclass(frozen=True)
class GenerationResult:
    destination: Path
    url: str


_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_BASE_FORMATTERS = (
    "nixfmt",
    "jsonfmt",
    "shellcheck",
    "yamlfmt",
    "toml-sort",
    "dos2unix",
    "keep-sorted",
    "topiary-nushell",
)
_REQUIRED_COMMANDS = ("nix", "direnv", "git", "gh")
_TEMPLATE_ROOT = files("nix_project_generator").joinpath("templates")
_JINJA = Environment(
    autoescape=False,
    keep_trailing_newline=True,
    undefined=StrictUndefined,
)


def _validate_name(name: str) -> None:
    if (
        not _NAME_PATTERN.fullmatch(name)
        or name in {".", ".."}
        or Path(name).name != name
    ):
        raise GenerationError(
            "repository name must be a single path component containing only "
            "letters, numbers, '.', '_', and '-'"
        )


def _template(template_path: str, **context: object) -> str:
    source = _TEMPLATE_ROOT.joinpath(template_path).read_text(encoding="utf-8")
    return _JINJA.from_string(source).render(**context)


def _package_name(name: str, separator: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", separator, name.lower()).strip(
        separator
    )
    if not normalized:
        normalized = "project"
    if normalized[0].isdigit():
        normalized = f"project{separator}{normalized}"
    return normalized


def _nix_sources(options: GenerationOptions) -> tuple[str, str]:
    selected_profiles = [PROFILES[language] for language in options.languages]
    packages = tuple(
        dict.fromkeys(
            package
            for profile in selected_profiles
            for package in profile.packages
        )
    )
    formatters = tuple(
        dict.fromkeys(
            (*_BASE_FORMATTERS,)
            + tuple(
                formatter
                for profile in selected_profiles
                for formatter in profile.formatters
            )
        )
    )

    flake = parse(
        _template(
            "project/flake.nix.j2",
            packages=packages,
            rust=Language.RUST in options.languages,
        )
    )
    if Language.RUST in options.languages:
        flake["inputs"]["fenix"] = {
            "url": "github:nix-community/fenix",
            "inputs": {"nixpkgs": {"follows": "nixpkgs"}},
        }

    treefmt = parse(_template("project/treefmt.nix.j2"))
    for formatter in formatters:
        treefmt["programs"][formatter] = {"enable": True}
    if Language.TYPESCRIPT in options.languages:
        # Bun's tsconfig is JSONC; jsonfmt only accepts strict JSON.
        treefmt["programs"]["jsonfmt"]["excludes"] = ["tsconfig.json"]

    return flake.rebuild(), treefmt.rebuild()


def _readme(options: GenerationOptions) -> str:
    return _template(
        "project/README.md.j2",
        name=options.name,
        languages=[language.value for language in options.languages],
        licensed=not options.private,
    )


def render_project(
    options: GenerationOptions,
    *,
    author: str,
    year: int | None = None,
) -> None:
    """Render a project into an already validated, absent destination."""
    flake, treefmt = _nix_sources(options)
    options.destination.mkdir(parents=True)

    generated = {
        "flake.nix": flake,
        "treefmt.nix": treefmt,
        "README.md": _readme(options),
        ".envrc": _template("project/envrc"),
        ".gitignore": _template(
            "project/gitignore",
            rust=Language.RUST in options.languages,
            python=Language.PYTHON in options.languages,
            typescript=Language.TYPESCRIPT in options.languages,
        ),
        "yamlfmt.yaml": _template("project/yamlfmt.yaml"),
        ".githooks/pre-commit": _template("project/pre-commit.nu"),
    }
    for relative_path, content in generated.items():
        target = options.destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    hook = options.destination / ".githooks/pre-commit"
    hook.chmod(0o755)

    if not options.private:
        license_mit = _template(
            "licenses/MIT.txt.j2",
            year=year or datetime.now(tz=UTC).year,
            author=author,
        )
        (options.destination / "LICENSE-MIT").write_text(
            license_mit, encoding="utf-8"
        )
        apache = _TEMPLATE_ROOT.joinpath("licenses/Apache-2.0.txt").read_text(
            encoding="utf-8"
        )
        (options.destination / "LICENSE-APACHE").write_text(
            apache, encoding="utf-8"
        )


def _initializers(options: GenerationOptions, owner: str) -> list[list[str]]:
    commands: list[list[str]] = []
    if Language.RUST in options.languages:
        commands.append(
            [
                "cargo",
                "init",
                "--vcs",
                "none",
                "--name",
                _package_name(options.name, "_"),
                ".",
            ]
        )
    if Language.PYTHON in options.languages:
        commands.append(
            [
                "uv",
                "init",
                "--name",
                _package_name(options.name, "-"),
                "--vcs",
                "none",
                "--no-readme",
                ".",
            ]
        )
    if Language.GO in options.languages:
        commands.append(
            ["go", "mod", "init", f"github.com/{owner}/{options.name}"]
        )
    if Language.TYPESCRIPT in options.languages:
        commands.append(["bun", "init", "--yes"])
    return commands


def _preflight(
    options: GenerationOptions,
    runner: Runner,
    which: Callable[[str], str | None],
) -> tuple[str, str]:
    _validate_name(options.name)
    if options.destination.exists():
        raise GenerationError(
            f"destination already exists: {options.destination}"
        )

    missing = [
        command for command in _REQUIRED_COMMANDS if which(command) is None
    ]
    if missing:
        raise GenerationError(
            f"required command not found: {', '.join(missing)}"
        )

    runner.run(["gh", "auth", "status"])
    owner = runner.run(["gh", "api", "user", "--jq", ".login"], capture=True)
    author = runner.run(["git", "config", "--get", "user.name"], capture=True)
    email = runner.run(["git", "config", "--get", "user.email"], capture=True)
    if not owner:
        raise GenerationError(
            "could not determine the authenticated GitHub owner"
        )
    if not author:
        raise GenerationError("git user.name must be configured")
    if not email:
        raise GenerationError("git user.email must be configured")
    return owner, author


def generate_repository(
    options: GenerationOptions,
    runner: Runner,
    *,
    which: Callable[[str], str | None] = shutil.which,
) -> GenerationResult:
    owner, author = _preflight(options, runner, which)
    render_project(options, author=author)

    try:
        # Establish a repository and track the flake before Nix evaluates it.
        # Otherwise Nix may treat an ancestor Git checkout as the flake root.
        runner.run(["git", "init"], cwd=options.destination)
        runner.run(
            ["git", "config", "core.hooksPath", ".githooks"],
            cwd=options.destination,
        )
        runner.run(["git", "add", "-A"], cwd=options.destination)
        runner.run(
            ["nix", "flake", "lock", f"path:{options.destination}"],
            cwd=options.destination,
        )
        runner.run(["git", "add", "flake.lock"], cwd=options.destination)
        runner.run(["direnv", "allow", str(options.destination)])
        for initializer in _initializers(options, owner):
            runner.run(
                ["direnv", "exec", str(options.destination), *initializer],
                cwd=options.destination,
            )

        # Project initializers do not own shared repository documentation.
        (options.destination / "README.md").write_text(
            _readme(options), encoding="utf-8"
        )

        lock_file = options.destination / "flake.lock"
        if not lock_file.exists():
            raise GenerationError(
                "nix did not create flake.lock; local files remain at "
                f"{options.destination}"
            )

        runner.run(["git", "add", "-A"], cwd=options.destination)
        runner.run(
            [
                "git",
                "commit",
                "-m",
                "init: generate project",
                "--",
                ".",
                ":!flake.lock",
            ],
            cwd=options.destination,
        )
        runner.run(
            ["git", "commit", "-m", "init: add flake lock"],
            cwd=options.destination,
        )

        visibility = "--private" if options.private else "--public"
        runner.run(
            [
                "gh",
                "repo",
                "create",
                f"{owner}/{options.name}",
                visibility,
                "--source",
                str(options.destination),
                "--remote",
                "origin",
            ]
        )
        branch = runner.run(
            ["git", "branch", "--show-current"],
            cwd=options.destination,
            capture=True,
        )
        runner.run(
            ["git", "push", "--set-upstream", "origin", branch],
            cwd=options.destination,
        )
    except CommandError as error:
        raise GenerationError(
            f"generation stopped; local files remain at {options.destination}: {error}"
        ) from error

    return GenerationResult(
        destination=options.destination,
        url=f"https://github.com/{owner}/{options.name}",
    )
