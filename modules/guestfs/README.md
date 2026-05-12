# guestfs module

## Purpose

Provision local KVM guests via libguestfs-tools and libvirt. The
guestfs module is the default kdevops provisioning backend on
developer machines; the terraform module covers cloud
provisioning and the nixos module covers declarative NixOS-based
provisioning.

The module consumes the libvirt module's configuration
(`libvirt_*`, `qemu_*` extra_vars) and the qemu module's
controller-built binary path when `CONFIG_QEMU_BUILD=y`.

## Tasks

| Task | Make target | Notes |
|---|---|---|
| One-time host setup (libguestfs packages, pool path, default network) | `make guestfs-host-setup` | sudo, opt-in |
| Spawn target VMs | `make bringup` | the guestfs role is the active `KDEVOPS_PROVISION_METHOD` |
| Status VMs | `make status` | no sudo |
| Tear down VMs | `make destroy` | per-VM sudo (cp/sysprep cleanup) |

`make bringup` invokes the role's bringup tasks which include
per-VM sudo (cp of the base image, virt-sysprep on the root
image, chown of console log files). This per-VM sudo is intrinsic
to libvirt-system-uri VM creation and stays in the bringup path;
only the ONE-TIME host configuration (install distro packages,
prepare /var/lib/libvirt directory, configure libvirt default
network) is gated behind the opt-in `make guestfs-host-setup`
target.

## Configuration

The guestfs Kconfig declares the user-facing knobs:

| Symbol | Purpose |
|---|---|
| `CONFIG_GUESTFS` | Master switch (selected from the bring-up choice) |
| `CONFIG_GUESTFS_STORAGE_DIR` | Where domain disks live |
| `CONFIG_GUESTFS_BASE_IMAGE_DIR` | Where base OS images cache |
| `CONFIG_GUESTFS_HAS_CUSTOM_RAW_IMAGE_URL` | Download a distro raw image |
| `CONFIG_GUESTFS_REQUIRES_UEFI` | Use OVMF firmware for the VMs |

All emit through `output yaml` and reach the role at runtime.

## Layout

```
modules/guestfs/
├── Kconfig
├── Makefile
├── README.md
└── host_setup/             sudo opt-in: one-time host preparation
    ├── Makefile
    └── README.md

playbooks/guestfs.yml
playbooks/roles/guestfs/
├── defaults/main.yml
├── tasks/main.yml          orchestrator
├── tasks/bringup/          per-VM operations during bringup
├── tasks/destroy.yml
├── tasks/status/main.yml
└── host_setup/             sudo opt-in sub-role
    ├── verify/tasks/main.yml   non-sudo precheck
    └── setup/                   sudo one-time host prep
        ├── tasks/main.yml       dispatches the sub-tasks
        ├── install-deps/        distro package install
        ├── storage-pool-path/   mkdir + chown the pool path
        └── network/             dnsmasq + libvirt default net
```

## Sub-modules

`host_setup/` — opt-in sudo sub-module that performs one-time
controller-side preparation: install distro libguestfs-tools
packages, create the libvirt storage pool directory with
group ownership of `libvirt_qemu_group`, and ensure the libvirt
default network plus dnsmasq are enabled and started. The
parent role's default execution path runs a non-sudo verify that
fails with a structured diagnostic when any of these pieces is
missing.

## Dependencies

- `libvirt` module supplies the configuration surface.
- `qemu` module supplies the controller-built binary path when
  `CONFIG_QEMU_BUILD=y`.
- `nodes` module supplies the node-list file generation.
- `ansible_inventory` module supplies the hosts inventory.
