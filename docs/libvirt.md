# libvirt module

The libvirt module configures the local KVM hypervisor that backs
the guestfs and nixos provisioning paths. Its Kconfig drives every
`libvirt_*` and `qemu_*` variable consumers — the nodes role's
drive templates, the guestfs role's image preparation, the qemu_build
module's binary path — read out of `extra_vars.yaml`.

The module ships three sudo opt-in sub-modules. They are gated
behind Make targets so a bare `make` or `make bringup` never
escalates privileges on the controller host. The orchestrator
runs a non-sudo verify path by default for each sub-module; the
verify path fails with a structured diagnostic that names both
the opt-in target and the per-sub-module doc when the host is not
ready.

## Sub-modules

| Sub-module | Doc | Sudo opt-in target | Purpose |
|---|---|---|---|
| `cxl` | (none) | n/a | CXL device emulation knobs |
| `largeio` | (none) | n/a | Large-IO drive emulation knobs |
| `zns` | (none) | n/a | ZNS NVMe emulation knobs |
| `user` | [libvirt-user.md](libvirt-user.md) | `make libvirt-user-setup` | libvirt package install + group membership |
| `storage_pool` | [libvirt-storage_pool.md](libvirt-storage_pool.md) | `make libvirt-storage-pool-setup` | libvirt storage pool creation |
| `pcie_passthrough` | [libvirt-pcie_passthrough.md](libvirt-pcie_passthrough.md) | `make libvirt-pcie-passthrough-setup` | sysfs `driver_override` permissions + udev rules |

## First-run workflow

A typical first run on a fresh kdevops checkout looks like:

```
make defconfig-<workflow>
make                                      # configures, generates extra_vars
make libvirt-user-setup                   # opts into libvirt group sudo
# log out and back in, or `newgrp libvirt`
make libvirt-storage-pool-setup           # opts into the storage pool sudo
make bringup
```

The verify path catches missing setup and points the user back at
the right opt-in target via its diagnostic message; the steps above
are the canonical order.

## Configuration

The Kconfig surface is large and is documented inline. The most
interesting knobs:

- `LIBVIRT_URI_SYSTEM` / `LIBVIRT_URI_SESSION` — session mode
- `LIBVIRT_VCPUS_*` / `LIBVIRT_MEM_*` — VM shape
- `LIBVIRT_MACHINE_TYPE_Q35` / `_VIRT` — emulated machine
- `LIBVIRT_AIO_MODE` / `LIBVIRT_AIO_CACHE_MODE` — qemu I/O backend
- `LIBVIRT_EXTRA_DRIVE_FORMAT_RAW` / `_QCOW2` — drive image format
- `LIBVIRT_EXTRA_STORAGE_DRIVE_NVME` / `_VIRTIO` / `_IDE` / `_SCSI` — drive class

All are emitted into `extra_vars.yaml` via Kconfig `output yaml`.
