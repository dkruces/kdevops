# guestfs/runtime_deps — runtime dependencies (sudo opt-in)

## Purpose

Install the distro packages guestfs needs at runtime to
orchestrate libvirt-backed VMs: libguestfs-tools (for
`virt-builder` and `virt-sysprep`), the python libvirt bindings
(used by the role's `community.libvirt.virt` tasks), OVMF
firmware (used as the UEFI BIOS for guests when
`CONFIG_GUESTFS_REQUIRES_UEFI=y`), and the DHCP client guests
need through libvirt's default network.

The sub-module name `runtime_deps` is the kdevops vocabulary for
[Yocto's `RDEPENDS`](https://docs.yoctoproject.org/ref-manual/variables.html#term-RDEPENDS):
runtime dependencies of a package. See `docs/module-spec.md`
"Module vocabulary" for the full taxonomy.

## Tasks

| Task | Make target | Notes |
|---|---|---|
| Verify `virsh` and `virt-builder` are on PATH | runs by default as part of `playbooks/guestfs.yml` | non-sudo |
| Install distro packages | `make guestfs-runtime-deps-setup` | sudo |

## Manual alternative

See `docs/guestfs-runtime_deps.md` for the per-distro manual
sequence.

## Layout

```
modules/guestfs/runtime_deps/
├── Makefile
└── README.md

playbooks/roles/guestfs/runtime_deps/
├── verify/tasks/main.yml   non-sudo precheck (default path)
└── setup/                   sudo opt-in
    └── tasks/
        ├── main.yml
        └── install-deps/    distro package install
            ├── debian/main.yml
            ├── redhat/main.yml
            └── suse/main.yml
```

## Dependencies

The parent `guestfs` module orchestrates this sub-module.
`libvirt/user` should be run first so the controller user has
the libvirt group membership the verify path checks for.
