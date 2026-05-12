# guestfs module

The guestfs module is kdevops's default local provisioning backend.
It pairs libguestfs-tools with libvirt to download a distro raw
image, customise it per target node, and spawn each node as a
libvirt domain. Production targets that want cloud VMs use the
terraform module; targets that want NixOS-declared VMs use the
nixos module.

## Quick start

```
make defconfig-<workflow>            # picks a guestfs backend by default
make libvirt-user-setup              # one-time sudo: libvirt group membership
# log out and back in
make libvirt-storage-pool-setup      # one-time sudo: pool dir + libvirt pool object
make guestfs-runtime-deps-setup      # one-time sudo: libguestfs + OVMF + python libvirt
make guestfs-network-setup           # one-time sudo: dnsmasq + libvirt default network
make bringup                         # spawn VMs
```

The order is intentional: `libvirt/user` first because the other
sub-modules check for libvirt group membership in their verify
paths; `libvirt/storage_pool` next because the pool directory
needs to exist before bringup tries to drop disks into it; the
guestfs-side `runtime_deps` and `network` after because they
build on libvirt being set up.

Each opt-in target is idempotent. Once the controller is
configured, only `make bringup` is needed for subsequent
workflow runs.

## Sudo footprint

guestfs has two distinct sudo contexts on the controller. The
first is one-time host configuration, split across the four Make
targets above per the spec's "Module vocabulary":

| Sub-module | Vocabulary | Purpose |
|---|---|---|
| `libvirt/user` | host-configuration | Controller user in `libvirt`, `kvm`, and the per-distro qemu group |
| `libvirt/storage_pool` | host-configuration | On-disk pool directory + virsh pool object |
| `guestfs/runtime_deps` | RDEPENDS | libguestfs-tools, OVMF, python libvirt, DHCP client |
| `guestfs/network` | host-configuration | dnsmasq state + libvirt default network |

Per the spec's controller-side sudo isolation rule, none of these
run on bare `make` or as a side effect of `make bringup`; the
bringup-time verify paths catch missing pieces and tell the user
which target to run.

The second sudo context is per-VM bringup: `cp --reflink=auto` of
the base image into each VM's storage directory, `virt-sysprep`
customisation of the per-VM root image, and `chown` of the
console log file. These are intrinsic to libvirt-system-uri
domain creation and run on every `make bringup` invocation. They
are not gated separately because the user has already opted in by
typing `make bringup`; the spec's "default execution path"
exemption applies to bare `make`, not to explicit workflow
targets.

If you would rather avoid per-VM sudo entirely, switch to
`CONFIG_LIBVIRT_URI_SESSION` (qemu:///session) — the role drops
all per-VM `become: true` blocks in that mode.

## Layout

```
modules/guestfs/
├── Kconfig
├── Makefile
├── README.md
├── runtime_deps/                  RDEPENDS sub-module (libguestfs install)
│   ├── Makefile                   `make guestfs-runtime-deps-setup`
│   └── README.md
└── network/                       host-configuration sub-module
    ├── Makefile                   `make guestfs-network-setup`
    └── README.md

playbooks/guestfs.yml
playbooks/roles/guestfs/
├── defaults/main.yml              role-private (tree-wide vars stay in extra_vars)
├── tasks/main.yml                 orchestrator
├── tasks/bringup/                 per-VM bringup work (sudo intrinsic)
├── tasks/destroy.yml              per-VM teardown (sudo intrinsic, do_clean)
├── tasks/status/main.yml          status report (no sudo)
├── runtime_deps/                  RDEPENDS sub-role
│   ├── verify/tasks/main.yml      non-sudo precheck
│   └── setup/                      sudo install (apt/dnf/zypper)
└── network/                       host-configuration sub-role
    ├── verify/tasks/main.yml      non-sudo precheck
    └── setup/                      sudo (dnsmasq + virsh net-start default)
```

## Make targets

| Target | Notes |
|---|---|
| `make bringup` | spawn target VMs |
| `make destroy` | tear down VMs (tagged `do_clean`) |
| `make status` | per-VM status report |
| `make guestfs-runtime-deps-setup` | one-time sudo: distro packages |
| `make guestfs-network-setup` | one-time sudo: libvirt default network |

The libvirt-owned targets (`libvirt-user-setup`,
`libvirt-storage-pool-setup`, `libvirt-pcie-passthrough-setup`)
live in the libvirt module and are documented in
[`docs/libvirt.md`](libvirt.md).

`make bringup` is wired through `KDEVOPS_PROVISION_METHOD =
bringup_guestfs` in the module's Makefile when `CONFIG_GUESTFS=y`.
`make destroy` and `make status` route through the analogous
`destroy_guestfs` / `status_guestfs` indirections.

## Tag taxonomy

The role's tasks carry the spec's `do_*` operation-kind tags
from the [Module vocabulary](module-spec.md):

| Tag | Tasks |
|---|---|
| `do_install` | distro package install, root-image cp, qemu-img create for extra disks, virt-sysprep image customisation |
| `do_configure` | console.log chown, per-VM storage pool directory mkdir |
| `do_deploy` | libvirt default network start, virsh define + start of each VM, PCIe passthrough attach |
| `do_clean` | virsh shutdown + undefine + storage volume cleanup |

A power user invoking ansible-playbook directly can combine
sub-module gate tags with do_* tags, e.g.
`--tags guestfs_runtime_deps_setup,do_install` to run only the
package install step inside the runtime_deps sub-module.

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
  extra_vars) and owns the user/storage_pool/pcie_passthrough
  sudo sub-modules guestfs depends on.
- `qemu` supplies the controller-built binary path via the
  `QEMU_BIN_PATH` chain when `CONFIG_QEMU_BUILD=y`.
- `nodes` supplies the `kdevops_nodes.yaml` file that lists
  target VMs to spawn.
- `ansible_inventory` supplies the hosts inventory used by every
  ansible-playbook invocation that talks to the targets after
  they are up.
