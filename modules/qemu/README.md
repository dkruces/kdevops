# qemu module

## Purpose

Build QEMU from source on the controller and install it into a
kdevops-owned destdir (no sudo for the install step, no
`/usr/local` pollution). Mirrors the bootlinux module's
controller-mode build pattern at
`playbooks/roles/bootlinux/tasks/build/controller.yml`.

The libvirt module's `QEMU_BIN_PATH` chains to this module's
`QEMU_BUILD_BIN_PATH` when `CONFIG_QEMU_BUILD=y`, so the libvirt
domain XML `<emulator>` element automatically references the
locally-built binary.

## Tasks

| Task | Make target | Notes |
|---|---|---|
| Build QEMU (clone + configure + ninja + ninja install) | `make qemu` | no sudo |
| Install distro build deps | `make qemu-build-deps-setup` | sudo |
| Re-run only the install step | `make qemu-install` | no sudo |
| Re-run only the configure step | `make qemu-configure` | no sudo |
| Re-run only the build step | `make qemu-build` | no sudo |

`make qemu` is invoked automatically from `make bringup` via
`KDEVOPS_BRING_UP_DEPS_EARLY` when `CONFIG_QEMU_BUILD=y`. ninja's
own dependency graph handles incremental rebuilds; a no-op walks
the graph and exits in seconds.

## Configuration

The Kconfig surface keeps the legacy `QEMU_BUILD_*` symbol prefix.
The prefix predates the canonical module rename: the module is
named `qemu` but its feature switch is the build-from-source
flag, so symbols spell "qemu build" explicitly. The module's
emitted YAML keys are `qemu_build_*` (compliant with the spec's
`<module>_<var>` rule via the `qemu_` module prefix plus the
multi-word var name `build_*`).

Key symbols:

| Symbol | Purpose |
|---|---|
| `CONFIG_QEMU_BUILD` | Master switch |
| `CONFIG_QEMU_BUILD_TREE_PATH` | Source tree (default `data/qemu/`) |
| `CONFIG_QEMU_BUILD_BUILDDIR` | Out-of-tree build dir |
| `CONFIG_QEMU_BUILD_DESTDIR` | `--prefix=` install destination |
| `CONFIG_QEMU_BUILD_BIN_PATH` | Synthetic per-arch binary path |
| `CONFIG_QEMU_BUILD_GIT` | Git remote |
| `CONFIG_QEMU_BUILD_GIT_VERSION` | Git ref (branch/tag/sha) |

## Layout

```
modules/qemu/
├── Kconfig
├── Makefile
├── README.md
└── build_deps/             sudo opt-in sub-module: distro build deps
    ├── Makefile
    └── README.md

playbooks/qemu.yml
playbooks/roles/qemu/
├── defaults/main.yml
├── tasks/main.yml          orchestrator (verify → build, no sudo)
└── build_deps/
    ├── verify/tasks/main.yml   non-sudo precheck
    └── setup/tasks/main.yml    sudo install-deps (apt/dnf/zypper)
```

## Sub-modules

`build_deps/` — opt-in sudo sub-module that installs the distro
build dependencies (compiler toolchain, meson, ninja, libpixman
and friends). Per the controller-side sudo isolation rule the
parent role runs a non-sudo verify path on the default
execution; the sudo work happens only via
`make qemu-build-deps-setup`.

## Dependencies

`libvirt` consumes this module's `qemu_build_bin_path` via the
`QEMU_BIN_PATH` chain in `modules/libvirt/Kconfig`.
