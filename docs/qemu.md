# qemu module

The qemu module builds QEMU from source on the controller and
installs it into a kdevops-owned directory without sudo and without
touching `/usr/local`. It is the foundation for workflows that need
a specific QEMU revision: new hardware features that have not landed
in distribution packages yet, bisects against upstream, local
patches under iteration. The libvirt module's emulator path
auto-tracks the build when `CONFIG_QEMU_BUILD=y`.

## Three directory layout

Under `CONFIG_KDEVOPS_CONTROLLER_DATA_PATH` (default `data/`):

```
data/qemu/            # source tree (clone or user-supplied)
data/qemu-build/      # out-of-tree build directory
data/qemu-destdir/    # install prefix (--prefix= here)
```

`ninja install` writes into `qemu-destdir/{bin,share,lib}` — a
self-contained tree the consumer reads at
`<destdir>/bin/qemu-system-<arch>`. The host's `/usr` and
`/usr/local` are never touched, and the install step needs no sudo.

The same shape is what `bootlinux`'s controller-mode build uses at
`playbooks/roles/bootlinux/tasks/build/controller.yml`, so the two
modules feel familiar side by side.

## Quick start

```
make defconfig-<workflow>
# Set CONFIG_QEMU_BUILD=y in menuconfig, or in a defconfig fragment.
make
make qemu-build-deps-setup     # one-time, sudo on the controller
make qemu                      # explicit no-sudo build
make bringup                   # pulls in `make qemu` via
                               # KDEVOPS_BRING_UP_DEPS_EARLY
```

`make qemu` is idempotent: ninja's source-level dependency tracking
catches "nothing to do" and exits in seconds. After the first
build, subsequent invocations rebuild only what actually changed.

## Pointing at your own QEMU checkout

Set `CONFIG_QEMU_BUILD_TREE_PATH` to an existing QEMU worktree on
your filesystem:

```
CONFIG_QEMU_BUILD_TREE_PATH="/home/you/src/qemu-project/qemu"
```

The role detects the existing `.git` at that path, skips clone,
and builds against whatever HEAD that tree happens to be on. This
is the iterate-against-working-tree-changes path — kdevops will
not switch branches or refs under you.

A git worktree (`.git` file pointing at a parent gitdir), a
symlink to another checkout, and a manually cloned tree all count
as "existing".

## Sub-modules

| Sub-module | Doc | Sudo opt-in target | Purpose |
|---|---|---|---|
| `build_deps` | [qemu-build_deps.md](qemu-build_deps.md) | `make qemu-build-deps-setup` | Install distro build packages (compiler, meson, ninja, pixman, …) |

The build itself is in the parent module and runs without sudo.
The `build_deps` sub-module is the only piece that requires
elevated privileges on the controller; it is opt-in per the
controller-side sudo isolation rule.

## Configuration

The module's Kconfig surface keeps the `QEMU_BUILD_*` symbol prefix
even after the rename from `build_qemu` to `qemu`: the module is
named `qemu`, the feature switch describes the build-from-source
flag, and the variable name happens to begin with `build_*`. The
prefix parses as `qemu_<var>` and stays spec-compliant.

| Symbol | Purpose |
|---|---|
| `CONFIG_QEMU_BUILD` | Master switch |
| `CONFIG_QEMU_BUILD_TREE_PATH` | Source tree (default `data/qemu/`) |
| `CONFIG_QEMU_BUILD_BUILDDIR` | Out-of-tree build dir |
| `CONFIG_QEMU_BUILD_DESTDIR` | `--prefix=` install destination |
| `CONFIG_QEMU_BUILD_BIN_PATH` | Synthetic per-arch binary path (derived) |
| `CONFIG_QEMU_BUILD_GIT` | Git remote |
| `CONFIG_QEMU_BUILD_GIT_VERSION` | Git ref (branch/tag/sha) |

## How libvirt picks up the build

The libvirt module's `CONFIG_QEMU_BIN_PATH` chains to
`CONFIG_QEMU_BUILD_BIN_PATH` when `CONFIG_QEMU_BUILD=y`:

```
config QEMU_BIN_PATH
        string
        output yaml
        default QEMU_BUILD_BIN_PATH if QEMU_BUILD
        default QEMU_BIN_PATH_LIBVIRT if LIBVIRT
```

Both symbols emit through `output yaml`, so the
`<emulator>` element in libvirt domain XML and the libvirt-config
plumbing in the `nodes` role pick up the controller-built path
automatically. No per-defconfig override is required.

## Re-running individual build phases

For debugging or iterating on one phase:

```
make qemu-configure   # only meson configure
make qemu-build       # only ninja
make qemu-install     # only ninja install
```

These bypass the upstream phases but assume the earlier ones have
run. They are equivalent to `ansible-playbook playbooks/qemu.yml`
with `--tags do_configure,vars`, `--tags do_build,vars`, and
`--tags do_install,vars` respectively.

## Spec conformance

- Module layout: canonical `modules/qemu/` per the spec.
- Tag taxonomy: tasks carry `do_fetch` (clone + mkdir + meson
  subprojects), `do_configure` (meson configure), `do_build`
  (ninja), `do_install` (ninja install + distro packages).
- Sudo isolation: only `build_deps` sub-module requires sudo; the
  parent module's default path runs a non-sudo verify that fails
  with an actionable diagnostic when the toolchain is missing.
- Make target convention: `make qemu` (module-default) and
  `make qemu-build-deps-setup` (sudo opt-in) match the
  `<module>` / `<module>-<sub>-setup` spelling.
