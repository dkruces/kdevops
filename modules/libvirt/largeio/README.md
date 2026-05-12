# libvirt/largeio — Large-IO drive emulation (config-only sub-module)

## Purpose

Declares the Kconfig knobs for creating per-block-size families of
QEMU drives used by large-IO and bs>4K experimentation. The drive
emission itself happens in the `nodes` role's `gen_drives.j2` /
`drives.j2` templates which read the libvirt_enable_largeio /
qemu_largeio_compat_size / qemu_largeio_max_pow_limit /
qemu_extra_drive_largeio_compat /
qemu_extra_drive_largeio_num_drives_per_space keys this sub-module
emits via `output yaml`.

## Layout

```
modules/libvirt/largeio/
├── Kconfig
└── README.md
```

## Configuration

Knobs gated on `EXTRA_STORAGE_SUPPORTS_LARGEIO`:

- `QEMU_ENABLE_EXTRA_DRIVE_LARGEIO` — master switch
- `QEMU_EXTRA_DRIVE_LARGEIO_NUM_DRIVES_PER_SPACE`
- `QEMU_EXTRA_DRIVE_LARGEIO_BASE_SIZE`
- `QEMU_EXTRA_DRIVE_LARGEIO_COMPAT` / `_COMPAT_SIZE`
- `QEMU_EXTRA_DRIVE_LARGEIO_MAX_POW_LIMIT`

Hidden shadow symbols emit `output yaml` for the iteration loop in
the drive templates:

- `LIBVIRT_ENABLE_LARGEIO`
- `QEMU_LARGEIO_DRIVE_BASE_SIZE`
- `QEMU_LARGEIO_COMPAT_SIZE`
- `QEMU_LARGEIO_MAX_POW_LIMIT`

## Dependencies

- `libvirt/` parent module sources this Kconfig.
- `guestfs` consumes `libvirt_enable_largeio` to decide whether to
  create the extra largeio devices at bringup time.
