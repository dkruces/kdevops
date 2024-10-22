{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.autoconf
    pkgs.automake
    pkgs.bash
    pkgs.bison
    pkgs.flex
    pkgs.gcc
    pkgs.libtool
    pkgs.libvirt
    pkgs.makeWrapper
    pkgs.ncurses
    pkgs.pkg-config
    pkgs.python3
    pkgs.python3Packages.pyyaml
  ];

  # shellHook = ''
  #   export SHELL="/usr/bin/env bash"
  # '';
}
