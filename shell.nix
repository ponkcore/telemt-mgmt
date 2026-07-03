# shell.nix — reproducible dev environment for NixOS
#
# Usage:
#   nix-shell                    # enter dev shell
#   nix-shell --run "uv run pytest -q"   # run tests directly
#
# This file is project-local. It does NOT modify your system.
# Nix creates a temporary sandbox with the tools below; exiting the
# shell removes everything. Think of it as `docker run` without Docker.
#
# LD_LIBRARY_PATH is set so that manylinux wheels (greenlet, asyncpg,
# Pillow, etc.) find libstdc++.so.6 without nix-ld or buildFHSUserEnv.

{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  nativeBuildInputs = [
    pkgs.uv
    pkgs.nodejs_22
    pkgs.python312
  ];

  # manylinux wheels expect /usr/lib/libstdc++.so.6 — provide it
  LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
    pkgs.stdenv.cc.cc.lib
  ];
}
