# qemu/build_deps — QEMU build dependencies (sudo opt-in)

## Purpose

Install the distro-specific packages QEMU's build requires:
compiler toolchain, meson, ninja, pkg-config, libpixman, glib, and
the platform-specific extras each distribution wants. This is
controller-side sudo work and is gated behind an opt-in Make
target per the module-spec sudo isolation rule.

## Tasks

| Task | Make target | Notes |
|---|---|---|
| Verify the toolchain (meson, ninja, pkg-config, cc) is present | runs by default as part of `playbooks/qemu.yml` | non-sudo |
| Install the distro build deps | `make qemu-build-deps-setup` | sudo |

## Manual alternative

### Debian / Ubuntu

```
sudo apt-get install \
    meson ninja-build pkg-config \
    libpixman-1-dev libglib2.0-dev libslirp-dev \
    libcap-ng-dev libattr1-dev libaio-dev \
    libfdt-dev liburing-dev \
    python3-distlib
```

### Fedora / RHEL / CentOS

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

After the manual install the verify path passes silently and
`make qemu` builds against the system toolchain.

## Layout

```
modules/qemu/build_deps/
├── Makefile
└── README.md

playbooks/roles/qemu/build_deps/
├── verify/tasks/main.yml   non-sudo precheck (default path)
└── setup/                   sudo install (opt-in)
    └── tasks/
        ├── main.yml          dispatches per distro
        └── install-deps/
            ├── debian/main.yml
            ├── fedora/main.yml
            ├── redhat/main.yml
            └── suse/main.yml
```

## Dependencies

The parent `qemu` module orchestrates this sub-module.
