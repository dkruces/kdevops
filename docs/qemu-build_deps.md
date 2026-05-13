# qemu-build_deps — QEMU build dependencies

## When this matters

QEMU's build needs a fair-sized toolchain on the controller:
compiler, meson, ninja, pkg-config, plus a list of -dev / -devel
packages that varies by distribution (pixman, glib, slirp,
liburing, libfdt, libcap-ng, …). Without them, `make qemu` fails
at the meson configure step or later in ninja, depending on which
piece is missing.

The qemu module ships a sudo opt-in sub-module that installs the
distro-specific build deps in one step. If you would rather not
grant kdevops sudo on your developer machine, the manual sequence
below is equivalent.

## The opt-in path

```
make qemu-build-deps-setup
```

Drives `playbooks/qemu.yml` with `--tags qemu_build_deps_setup`
and runs `playbooks/roles/qemu/build_deps/setup/` under sudo.
The role dispatches on `ansible_facts['os_family']`:

- `Debian` → apt-get install of meson, ninja-build, pkg-config,
  libpixman-1-dev, libglib2.0-dev, libslirp-dev, libcap-ng-dev,
  libattr1-dev, libaio-dev, libfdt-dev, liburing-dev, plus
  python3-distlib for the meson subprojects machinery.
- `RedHat` (non-Fedora) → dnf install of the rpm-named equivalents.
- `RedHat` (Fedora) → same set, dnf.
- `Suse` → zypper install, with SLE/Leap/Tumbleweed-specific tweaks
  to handle `acpica` packaging differences.

After the install you can run `make qemu` and the build runs
cleanly without sudo.

## The manual path

### Debian / Ubuntu

```
sudo apt-get update
sudo apt-get install \
    meson ninja-build pkg-config \
    libpixman-1-dev libglib2.0-dev libslirp-dev \
    libcap-ng-dev libattr1-dev libaio-dev \
    libfdt-dev liburing-dev \
    python3-distlib
```

### Fedora / RHEL / CentOS Stream

```
sudo dnf install \
    meson ninja-build pkgconf-pkg-config \
    pixman-devel glib2-devel libslirp-devel \
    libcap-ng-devel libattr-devel libaio-devel \
    libfdt-devel liburing-devel
```

### openSUSE / SLES

```
sudo zypper install \
    meson ninja pkg-config \
    libpixman-1-0-devel glib2-devel libslirp-devel \
    libcap-ng-devel libattr-devel libaio-devel \
    libfdt-devel liburing-devel
```

After the manual install, the verify path in the qemu module's
default execution passes silently and `make qemu` builds against
the system toolchain.

## What the verify path checks

`playbooks/roles/qemu/build_deps/verify/tasks/main.yml` runs
without sudo on every `make qemu` and stats the controller's
`PATH` for
`meson`, `ninja`, `pkg-config`, and `cc`. When any of those four
is missing the role fails with:

```
The QEMU build toolchain is incomplete on the controller.
Missing: <names>

Two ways to fix this:
  1. Run the opt-in sudo target:
         make qemu-build-deps-setup
  2. Install the toolchain manually following docs/qemu.md, then
     re-run the original make target.
```

The diagnostic names this document and the Make target by design;
users who skip the verify-path output and try to run `make qemu`
straight away get the same message at task #2 of the role.
