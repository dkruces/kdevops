# libvirt/pcie_passthrough — PCIe device passthrough (sudo opt-in)

## Purpose

Two distinct concerns share this sub-module:

1. **Config emission**: the dynamic Kconfig
   `modules/libvirt/pcie_passthrough/Kconfig.generated` is produced
   by the `gen_pci_kconfig` ansible role from the user's
   `.dynamic-kconfig.pci.txt` PCI device list, and sourced by the
   parent libvirt module's Kconfig. This is config-only and runs as
   part of `make dynconfig-pci`.

2. **Controller-side sudo setup**: set group ownership on each
   passed-through device's sysfs `driver_override`, `unbind`, and
   `iommu_group` files so the libvirt qemu user can rebind devices
   to vfio-pci without root. The parent role's verify path checks
   the ownership and fails with a structured diagnostic when it is
   wrong; the sudo work itself is gated behind a Make target.

## Tasks

| Task | Make target | Notes |
|---|---|---|
| Verify sysfs override files are owned by `libvirt_qemu_group` | runs by default as part of `playbooks/libvirt.yml` | non-sudo |
| Install udev rules + set sysfs ownership | `make libvirt-pcie-passthrough-setup` | sudo |
| Regenerate the dynamic Kconfig | `make dynconfig-pci` | sudo not required |

## Manual alternative

```
# For each device <BUS:DEV.FUNC> in your passthrough list:
sudo chgrp libvirt-qemu /sys/bus/pci/devices/0000:<BUS:DEV.FUNC>/driver_override
sudo chmod 0664       /sys/bus/pci/devices/0000:<BUS:DEV.FUNC>/driver_override
sudo chgrp libvirt-qemu /sys/bus/pci/devices/0000:<BUS:DEV.FUNC>/driver/unbind
sudo chmod 0220       /sys/bus/pci/devices/0000:<BUS:DEV.FUNC>/driver/unbind
sudo install -m 0644 modules/libvirt/pcie_passthrough/setup/templates/10-qemu-hw-users.rules \
    /etc/udev/rules.d/
```

## Layout

```
modules/libvirt/pcie_passthrough/
├── Kconfig                 (none — the dynamic Kconfig.generated is sourced from the parent)
├── Kconfig.generated       written by gen_pci_kconfig
├── Makefile                libvirt-pcie-passthrough-setup
└── README.md

playbooks/roles/libvirt/pcie_passthrough/
├── verify/tasks/main.yml   non-sudo precheck
└── setup/                   sudo opt-in
    ├── defaults/main.yml
    ├── tasks/main.yml
    └── templates/10-qemu-hw-users.rules
```

## Dependencies

- `libvirt/` parent module orchestrates this sub-module.
- `guestfs.Makefile` and `nixos.Makefile` (when applicable) call
  `make libvirt-pcie-passthrough-setup` rather than redefining the
  permissions target.
- `KDEVOPS_LIBVIRT_PCIE_PASSTHROUGH` Kconfig gates the entire feature.
