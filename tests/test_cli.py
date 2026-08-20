from click.testing import CliRunner

from nix_project_generator.cli import main


def test_help_lists_language_and_visibility_options() -> None:
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "--language" in result.output
    assert "rust" in result.output
    assert "typescript" in result.output
    assert "--private" in result.output


def test_invalid_language_is_rejected_before_generation() -> None:
    result = CliRunner().invoke(main, ["demo", "--language", "ruby"])

    assert result.exit_code == 2
    assert "Invalid value for '--language'" in result.output
