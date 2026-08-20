from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from nix_project_generator.commands import CommandError
from nix_project_generator.generator import (
    GenerationError,
    GenerationOptions,
    generate_repository,
)
from nix_project_generator.profiles import Language


class FakeRunner:
    def __init__(
        self, destination: Path, fail_on: tuple[str, ...] | None = None
    ):
        self.destination = destination
        self.fail_on = fail_on
        self.calls: list[tuple[tuple[str, ...], Path | None, bool]] = []

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        capture: bool = False,
    ) -> str:
        command = tuple(args)
        self.calls.append((command, cwd, capture))
        if self.fail_on and command[: len(self.fail_on)] == self.fail_on:
            raise CommandError("planned failure")
        if command[:3] == ("nix", "flake", "lock"):
            (self.destination / "flake.lock").write_text("{}")
        if command == ("gh", "api", "user", "--jq", ".login"):
            return "example"
        if command == ("git", "config", "--get", "user.name"):
            return "Example Author"
        if command == ("git", "config", "--get", "user.email"):
            return "author@example.com"
        if command == ("git", "branch", "--show-current"):
            return "main"
        return ""


def available(_: str) -> str:
    return "/bin/tool"


def all_options(
    destination: Path, *, private: bool = False
) -> GenerationOptions:
    return GenerationOptions(
        name="demo-project",
        destination=destination,
        languages=tuple(Language),
        private=private,
    )


def test_all_initializers_use_direnv_before_publish(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "demo-project"
    runner = FakeRunner(destination)

    result = generate_repository(
        all_options(destination), runner, which=available
    )

    commands = [call[0] for call in runner.calls]
    allow_index = commands.index(("direnv", "allow", str(destination)))
    initializer_commands = [
        command
        for command in commands
        if command[:3] == ("direnv", "exec", str(destination))
    ]
    assert [command[3] for command in initializer_commands] == [
        "cargo",
        "uv",
        "go",
        "bun",
    ]
    assert all(
        commands.index(command) > allow_index
        for command in initializer_commands
    )
    git_init_index = commands.index(("git", "init"))
    assert git_init_index < allow_index
    remote = next(
        command
        for command in commands
        if command[:3] == ("gh", "repo", "create")
    )
    assert "--public" in remote
    assert commands.index(remote) > git_init_index
    assert result.url == "https://github.com/example/demo-project"


def test_private_visibility_matches_license_behavior(tmp_path: Path) -> None:
    destination = tmp_path / "demo-project"
    runner = FakeRunner(destination)

    generate_repository(
        all_options(destination, private=True), runner, which=available
    )

    remote = next(
        call[0]
        for call in runner.calls
        if call[0][:3] == ("gh", "repo", "create")
    )
    assert "--private" in remote
    assert not (destination / "LICENSE-MIT").exists()
    assert not (destination / "LICENSE-APACHE").exists()


def test_failure_before_remote_keeps_local_files_and_skips_publish(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "demo-project"
    runner = FakeRunner(destination, fail_on=("direnv", "exec"))

    with pytest.raises(GenerationError, match="local files remain"):
        generate_repository(all_options(destination), runner, which=available)

    assert destination.exists()
    assert not any(
        call[0][:3] == ("gh", "repo", "create") for call in runner.calls
    )


def test_existing_destination_fails_before_external_commands(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "demo-project"
    destination.mkdir()
    runner = FakeRunner(destination)

    with pytest.raises(GenerationError, match="destination already exists"):
        generate_repository(all_options(destination), runner, which=available)

    assert runner.calls == []


@pytest.mark.parametrize(
    "name", ["../escape", "nested/project", ".", "bad name"]
)
def test_unsafe_name_fails_before_external_commands(
    tmp_path: Path, name: str
) -> None:
    runner = FakeRunner(tmp_path / "unused")
    options = GenerationOptions(name=name, destination=tmp_path / name)

    with pytest.raises(GenerationError, match="single path component"):
        generate_repository(options, runner, which=available)

    assert runner.calls == []
