from __future__ import annotations

from pathlib import Path

import click

from .commands import CommandError, SubprocessRunner
from .generator import GenerationError, GenerationOptions, generate_repository
from .profiles import Language, normalized_languages


@click.command()
@click.argument("repository_name")
@click.option(
    "--language",
    "languages",
    type=click.Choice([language.value for language in Language]),
    multiple=True,
    help="Add a language profile. May be supplied more than once.",
)
@click.option(
    "--private",
    "private_repository",
    is_flag=True,
    help="Create a private repository and omit license files.",
)
def main(
    repository_name: str,
    languages: tuple[str, ...],
    private_repository: bool,
) -> None:
    """Create and publish REPOSITORY_NAME below the current directory."""
    options = GenerationOptions(
        name=repository_name,
        destination=Path.cwd() / repository_name,
        languages=normalized_languages(languages),
        private=private_repository,
    )
    try:
        result = generate_repository(options, SubprocessRunner())
    except (GenerationError, CommandError) as error:
        raise click.ClickException(str(error)) from error

    click.secho("new repository configured:", fg="green")
    click.echo(result.destination)
    click.echo(result.url)


if __name__ == "__main__":
    main()
