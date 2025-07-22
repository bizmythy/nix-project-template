# New Project Template

This repository serves as a starting off point for a new project. It has the basic setup for a `nix` development shell and my preferred formatters.

## `treefmt-nix` Formatting

[treefmt.nix](treefmt.nix) configures [treefmt-nix](https://github.com/numtide/treefmt-nix) to format all repository files.

The [pre-commit script](.githooks/pre-commit) is a [nushell](https://nushell.sh) script that formats staged files with `nix fmt` and warns if the `flake.lock` is outdated.

## `direnv` Development Shell

[.envrc](.envrc) configures [direnv](https://direnv.net/) to automatically activate the nix shell when inside the repository directory.
