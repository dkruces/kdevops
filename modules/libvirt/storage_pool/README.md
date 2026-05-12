# libvirt/storage_pool — storage pool creation (sudo opt-in)

## Purpose

Define and start the libvirt storage pool kdevops uses to hold
domain disks. The pool is created with sudo on most distros and
without sudo under libvirt_session mode (Fedora's qemu:///session).
Per the module spec the work is gated behind an opt-in Make target.

## Tasks

| Task | Make target | Notes |
|---|---|---|
| Verify the pool exists (when CONFIG_LIBVIRT_STORAGE_POOL_CREATE=y) | runs by default as part of `playbooks/libvirt.yml` | non-sudo |
| Define + start + autostart the pool | `make libvirt-storage-pool-setup` | sudo (or non-sudo under libvirt_session) |

## Manual alternative

```
sudo virsh pool-define-as <pool> dir --target <path>
sudo virsh pool-start <pool>
sudo virsh pool-autostart <pool>
```

Under libvirt_session (Fedora) drop the `sudo`.

## Layout

```
modules/libvirt/storage_pool/
├── Makefile
└── README.md

playbooks/roles/libvirt/storage_pool/
├── verify/tasks/main.yml    non-sudo precheck (default path)
└── setup/tasks/main.yml     pool define/start/autostart (opt-in)
```

## Dependencies

`libvirt/` parent module orchestrates this sub-module.
The Kconfig knob `LIBVIRT_STORAGE_POOL_CREATE` gates whether pool
creation is wanted at all.
