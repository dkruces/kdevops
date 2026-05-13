# libvirt-user — controller user and group setup

## When this matters

libvirt enforces group-based authorization for non-root users that
want to spawn guests. On most Linux distributions the relevant
groups are `libvirt`, `kvm`, and a distro-specific qemu group
(`libvirt-qemu` on Debian/Ubuntu, `qemu` on Fedora/RHEL/SUSE).
Without membership in those groups, `virsh` and the libvirt API
refuse to talk to the system daemon, and kdevops bringup fails at
the first guest-define step.

The kdevops libvirt module ships a sudo opt-in sub-module that
installs libvirt and adds the controller user to the required
groups in one step. If you would rather not grant kdevops sudo on
your developer machine, the manual sequence below is equivalent.

## The opt-in path

```
make libvirt-user-setup
```

This drives `playbooks/libvirt.yml` with the
`libvirt_user_setup` tag and runs the
`playbooks/roles/libvirt/user/setup/` sub-role under sudo. It
performs two distinct operations:

1. **Install libvirt and supporting packages** — distro-specific
   package list, see `setup/tasks/install_deps/`.
2. **Add the running user to the libvirt groups** — see
   `setup/tasks/enable_user/`.

After the run you must log out and log back in (or open a fresh
session with `newgrp libvirt`) for the new group memberships to
take effect; group changes only apply to future logins on Linux.

## The manual path

### Debian / Ubuntu

```
sudo apt-get install \
    libvirt-clients \
    libvirt-daemon-system \
    qemu-system-x86 \
    qemu-utils \
    virtinst
sudo usermod --append --groups libvirt,kvm,libvirt-qemu $USER
```

### Fedora / RHEL / CentOS

```
sudo dnf install \
    libvirt-client \
    libvirt-daemon-driver-qemu \
    qemu-kvm \
    virt-install
sudo usermod --append --groups libvirt,kvm,qemu $USER
```

### openSUSE / SLES

```
sudo zypper install \
    libvirt-client \
    libvirt-daemon-qemu \
    qemu \
    virt-install
sudo usermod --append --groups libvirt,kvm,qemu $USER
```

After the manual setup, log out and back in. Then re-run the make
target that originally failed; the libvirt module's verify path
will pass silently and bringup proceeds.

## What the verify path checks

`playbooks/roles/libvirt/user/verify/tasks/main.yml` runs without
sudo and:

1. Confirms the `virsh` binary is on `PATH`.
2. Confirms the controller user's effective groups include
   `libvirt`, `kvm`, and `{{ libvirt_qemu_group }}` (which the
   Kconfig sets per-distro).

It fails with an actionable diagnostic when either check fails;
the diagnostic names the opt-in Make target and this document.
