# Nix Project Generator

Generate an opinionated Nix project, initialize any selected language ecosystems, and publish it to GitHub.

## Prerequisites

- Nix with flakes enabled
- direnv
- Git with `user.name` configured
- GitHub CLI authenticated with `gh auth login`

Language tools are supplied by the generated Nix development shell; they do not need to be installed on the host.

## Usage

Run the generator from the directory that should contain the new checkout:

```console
nix run github:bizmythy/nix-project-template -- my-project
```

Select one or more additive language profiles with repeated `--language` options:

```console
nix run . -- my-project \
  --language rust \
  --language python \
  --language go \
  --language typescript
```

All selected projects are initialized in the same repository root. Profiles add:

- **Rust:** the stable Fenix toolchain and rustfmt (without WASM tooling)
- **Python:** a uv project with uv, Ruff, and ty
- **Go:** a Go module with golines and gofumpt
- **TypeScript:** a Bun project with Biome

By default, the generator creates a public GitHub repository and emits `LICENSE-MIT` and `LICENSE-APACHE`. Pass `--private` to create a private repository without license files:

```console
nix run . -- internal-tool --private --language python
```

The GitHub owner is the account currently active in `gh`. The destination is `<current-directory>/<repository-name>`.

## Generated workflow

The generator writes the complete flake before allowing direnv. Initializers run through `direnv exec`, so they use the pinned tools from that flake. It then creates two commits (project files followed by `flake.lock`), creates the GitHub remote, and pushes the current branch.

Remote creation happens last. If an earlier command fails, the generated directory is retained and the error reports its path. A remote or push failure also leaves local work intact for manual recovery.

Generated projects use:

```console
direnv allow
nix fmt
nix flake check
```

## Development

The application targets Python 3.13 and uses Click, Jinja2, nix-manipulator, and pytest. Run the package tests through the Nix build:

```console
# `path:.` includes newly added, not-yet-committed source files.
nix run path:. -- --help
nix shell nixpkgs#ruff --command ruff check src tests
nix shell nixpkgs#ruff --command ruff format --check src tests
```

nix-manipulator is pinned from source because its current Python/tree-sitter-nix combination is not reliably available from PyPI. Generated Nix is edited only through its documented mapping API and rebuilt before it is written.
