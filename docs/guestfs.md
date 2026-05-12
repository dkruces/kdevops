# guestfs module

The guestfs module is kdevops's default local provisioning backend.
It pairs libguestfs-tools with libvirt to download a distro raw
image, customise it per target node, and spawn each node as a
libvirt domain. Production targets that want cloud VMs use the
terraform module; targets that want NixOS-declared VMs use the
nixos module.

## Quick start

```
make defconfig-<workflow>          # picks a guestfs backend by default
make libvirt-user-setup            # one-time sudo: libvirt group membership
# log out and back in
make guestfs-host-setup            # one-time sudo: libguestfs + pool + network
make bringup                       # spawn VMs
```

After `make libvirt-user-setup` and `make guestfs-host-setup`, the
controller is configured and bringup runs without prompting for
sudo on per-VM setup (the per-VM cp/sysprep calls do still use
sudo internally — see "Sudo footprint" below).

## Sudo footprint

guestfs has two distinct sudo contexts on the controller. The
first is one-time host configuration — installing distro
libguestfs packages, creating the libvirt storage pool directory
with the right group ownership, and getting the libvirt default
network up. That work lives in the [`host_setup`
sub-module](guestfs-host_setup.md) and is opt-in via
`make guestfs-host-setup`. Per the module spec's controller-side
sudo isolation rule, none of it runs on bare `make` or as a side
effect of `make bringup`; the bringup-time verify path catches
missing pieces and tells you which target to run.

The second is per-VM bringup sudo: `cp --reflink=auto` of the
base image into each VM's storage directory, `virt-sysprep`
customisation of the per-VM root image, and `chown` of the
console log file. These are intrinsic to libvirt-system-uri
domain creation and run on every `make bringup` invocation. They
are not gated separately because the user has already opted in
by typing `make bringup`; the spec's "default execution path"
exemption applies to bare `make`, not to explicit workflow
targets.

If you would rather avoid per-VM sudo entirely, switch to
`CONFIG_LIBVIRT_URI_SESSION` (qemu:///session) — the role drops
all per-VM `become: true` blocks in that mode.

## Layout

```
modules/guestfs/
├── Kconfig
├── Makefile                       module-private Make plumbing
├── README.md                      contributor reference
└── host_setup/                    sudo opt-in sub-module
    ├── Makefile                   `make guestfs-host-setup`
    └── README.md

playbooks/guestfs.yml
playbooks/roles/guestfs/
├── defaults/main.yml              role-private (tree-wide vars stay in extra_vars)
├── tasks/main.yml                 orchestrator (verify → bringup)
├── tasks/bringup/                 per-VM bringup work (sudo intrinsic)
├── tasks/destroy.yml              per-VM teardown (sudo intrinsic)
├── tasks/status/main.yml          status report (no sudo)
└── host_setup/                    sub-role
    ├── verify/tasks/main.yml      non-sudo precheck (default path)
    └── setup/                      sudo work (opt-in via tag)
        └── tasks/
            ├── main.yml
            ├── install-deps/      distro package install
            ├── network.yml        dnsmasq + libvirt default network
            └── storage-pool-path.yml   pool directory + ownership
```

## Make targets

| Target | Notes |
|---|---|
| `make bringup` | spawn target VMs |
| `make destroy` | tear down VMs |
| `make status` | per-VM status report |
| `make guestfs-host-setup` | one-time sudo host setup |

`make bringup` is wired through `KDEVOPS_PROVISION_METHOD =
bringup_guestfs` in the module's Makefile when `CONFIG_GUESTFS=y`.
`make destroy` and `make status` route through the analogous
`destroy_guestfs` / `status_guestfs` indirections.

## Tag taxonomy

The role's tasks carry the spec's `do_*` operation-kind tags:

| Tag | Tasks |
|---|---|
| `do_install` | distro package install, root-image cp, qemu-img create for extra disks |
| `do_configure` | storage pool directory mkdir + chown, virt-sysprep customisation, console.log chown |
| `do_deploy` | libvirt default network start, virsh define + start of each VM, PCIe passthrough attach |
| `do_destroy` | virsh shutdown + undefine + storage volume cleanup |

A power user invoking ansible-playbook directly can combine
sub-module gate tags with do_* tags, e.g.
`--tags guestfs_host_setup,do_install` to run only the package
install step inside the host_setup sub-module.

## Configuration

Key Kconfig symbols (all emit through `output yaml`):

| Symbol | Purpose |
|---|---|
| `CONFIG_GUESTFS` | Master switch (selected from the bring-up choice) |
| `CONFIG_GUESTFS_STORAGE_DIR` | Where domain disks live (Jinja-templated) |
| `CONFIG_GUESTFS_BASE_IMAGE_DIR` | Base OS image cache directory |
| `CONFIG_GUESTFS_HAS_CUSTOM_RAW_IMAGE_URL` | Use a distro raw image instead of virt-builder |
| `CONFIG_GUESTFS_REQUIRES_UEFI` | OVMF firmware for the VMs |
| `CONFIG_GUESTFS_LACKS_9P` | Disable 9P host-share mount for the guest |

## Dependencies

- `libvirt` supplies the configuration surface (libvirt_*, qemu_*
  extra_vars).
- `qemu` supplies the controller-built binary path via the
  `QEMU_BIN_PATH` chain when `CONFIG_QEMU_BUILD=y`.
- `nodes` supplies the `kdevops_nodes.yaml` file that lists
  target VMs to spawn.
- `ansible_inventory` supplies the hosts inventory used by every
  ansible-playbook invocation that talks to the targets after
  they are up.
