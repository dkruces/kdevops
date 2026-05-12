# libvirt/zns — Zoned-NVMe emulation (config-only sub-module)

## Purpose

Declares the Kconfig knobs for emulated ZNS NVMe controllers
(zone capacity, zone size, ZASL, MAR/MOR, block sizes). These are
read by the QEMU command-line construction for nvme zone drives.

This is a config-only sub-module: it owns no role, no playbook, no
Make targets.

## Layout

```
modules/libvirt/zns/
├── Kconfig
└── README.md
```

## Configuration

Knobs gated on `LIBVIRT_EXTRA_STORAGE_DRIVE_NVME_ZNS`:

- `LIBVIRT_ENABLE_ZNS` — master switch
- `QEMU_NVME_ZONE_CAPACITY` / `_SIZE` / `_ZASL`
- `QEMU_NVME_ZONE_MAX_ACTIVE` / `_MAX_OPEN`
- `QEMU_NVME_ZONE_LOGICAL_BLOCK_SIZE` / `_PHYSICAL_BLOCK_SIZE`
- `QEMU_NVME_ZONE_DRIVE_SIZE`

## Dependencies

- `libvirt/` parent module sources this Kconfig.
- Currently no consumer reads the `nvme_zone_*` extra_vars keys; the
  ZNS drive emission path is wired separately at `cxl` workflow
  level. The Kconfig surface remains so a future ZNS consumer can
  pick it up.
