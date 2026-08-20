right now, i have a nix repository template available in this folder. then, i have a script in ~/nixconf that performs some operations on the files in this repo.
i would like if this could possibly have _multiple_ configurable things to be toggled on/off instead of just a fixed template file for any project.

to accomplish this, i think we should utilize [nix-manipulator](https://github.com/hoh/nix-manipulator) and make a python program that uses templates and other logic to create a new repository in the desired templated settings.

it should work as follows:
- be a CLI program that uses click
- user supplies the desired things, roughly same as script i have in ~/nixconf
- current template is the "default", but user can supply one or more languages to be additively configured for. options should be:
    - rust: see other projects in ~/personal for their flake config, use the specific flake setup i use for rust to get the correct toolchain version etc. (don't include wasm by default), enable rustfmt treefmt
    - python: configure a `uv` project using `uv init`, enable `ruff` in treefmt, install `ruff`, `uv`, and `ty`
    - go: configure a go project with go mod, enable `golines` and `gofumpt` in treefmt
    - typescript: install `bun` and `biome`, init a bun project, enable biome treefmt
- note that for these setup steps that they should be run within the active direnv environment after the flake is configured and such, see `direnv exec --help`
- generates a simple `README.md`
- creates repository, similar to how ~/nixconf script does
- `--private` flag can be specified
    - when unset, places license files in expected location for MIT + Apache 2.0 dual license (as is typical for rust projects, follow that standard)
    - when set, github repository is created as private and no license files are placed

this is a HARD SWITCH to the new paradigm of this repo being a generator script, you can assume no consumers expect the old layout and rip out everything that is currently in place.
when done, this repository's flake will only provide an app/program output that allows consumers to execute this program via python.
use `pytest` for any unit testing, `click` for CLI behavior, and the appropriate library for any other behaviors. try to avoid hand-rolling things that already exist in established libraries.

