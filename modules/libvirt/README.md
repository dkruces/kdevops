# libvirt module

## Purpose

Declares the libvirt provider's configuration (libvirt_*, qemu_*) and
groups three sudo-opt-in sub-modules that perform the
controller-side host setup needed before guests can be brought up
under libvirt. The guestfs role is the primary consumer of the
libvirt configuration; nothing in this module's parent role does
work on its own — it orchestrates sub-modules.

## Tasks

| Sub-module | Make target | Description |
|---|---|---|
| `user/` | `make libvirt-user-setup` | Add the controller user to the libvirt group(s). |
| `storage_pool/` | `make libvirt-storage-pool-setup` | Create the libvirt storage pool directory and grant ownership. |
| `pcie_passthrough/` | `make libvirt-pcie-passthrough-setup` | Set sysfs `driver_override` permissions for VFIO passthrough. |

All three are controller-side sudo operations and are opt-in per the
spec's sudo isolation rule. The parent role's default execution path
runs a non-sudo verify step for each, failing with a structured
diagnostic when the state is missing.

## Configuration

The Kconfig surface is large and historically organised. The
sub-modules `cxl/`, `largeio/`, `zns/`, and `pcie_passthrough/`
each own a slice; the remaining LIBVIRT_*, QEMU_BIN_PATH, and
VM-shape choices live directly in this module.

## Layout

```
modules/libvirt/
├── Kconfig
├── Makefile
├── README.md
├── scripts/              libvirt helper scripts shared by Kconfig $(shell, …)
├── cxl/                  emulated CXL devices (config-only)
├── largeio/              large-IO drive emulation (config-only)
├── zns/                  ZNS NVMe emulation (config-only)
├── user/                 sudo opt-in: libvirt group membership
├── storage_pool/         sudo opt-in: storage pool creation
└── pcie_passthrough/     PCIe passthrough config + sudo opt-in setup

playbooks/libvirt.yml     one orchestrator playbook
playbooks/roles/libvirt/  parent role with nested sub-roles
```

## Sub-modules

| Kconfig switch | Sub-module |
|---|---|
| `KDEVOPS_BRINGUP_SUPPORTS_CXL` | `cxl/` |
| `EXTRA_STORAGE_SUPPORTS_LARGEIO` | `largeio/` |
| `LIBVIRT_EXTRA_STORAGE_DRIVE_NVME_ZNS` | `zns/` |
| n/a (always available) | `user/`, `storage_pool/`, `pcie_passthrough/` |

## Dependencies

- `guestfs` consumes the libvirt_* and qemu_* extra_vars and is the
  primary driver of the configuration surface.
- `qemu_build` declares QEMU_BUILD_BIN_PATH which this module's
  QEMU_BIN_PATH chains to when QEMU_BUILD=y.
