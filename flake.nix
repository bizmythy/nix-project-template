{
  description = "Configurable Nix project repository generator";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    nix-manipulator = {
      url = "github:hoh/nix-manipulator/6f99687860f6f6cbff327b02f997741cc3e33db8";
      flake = false;
    };
  };

  outputs =
    {
      nixpkgs,
      flake-utils,
      nix-manipulator,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python313;
        nixManipulator =
          (pkgs.callPackage "${nix-manipulator}/default.nix" { inherit pkgs; }).overridePythonAttrs (_: {
            # Upstream's lint check currently fails with nixpkgs' newer Ruff.
            # Its own pytest suite remains upstream's responsibility; this app
            # exercises the public API in its package tests.
            doCheck = false;
          });
        generator = python.pkgs.buildPythonApplication {
          pname = "nix-project-generator";
          version = "0.1.0";
          pyproject = true;
          src = ./.;

          build-system = [ python.pkgs.setuptools ];
          dependencies = with python.pkgs; [
            click
            jinja2
            nixManipulator
          ];
          nativeCheckInputs = [ python.pkgs.pytestCheckHook ];
          pythonImportsCheck = [ "nix_project_generator" ];
        };
      in
      {
        apps = {
          default = flake-utils.lib.mkApp {
            drv = generator;
            name = "new-repo";
          };
          new-repo = flake-utils.lib.mkApp {
            drv = generator;
            name = "new-repo";
          };
        };
      }
    );
}
