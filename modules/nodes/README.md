# nodes

## Purpose

Renders the kdevops node-list file consumed by the provisioner
backends. The output path is `$(KDEVOPS_NODES)` (set by the active
workflow). The active backend selects which template to render —
`guestfs_nodes.j2` for libvirt, `terraform_nodes.tf.j2` for cloud,
`nixos_nodes.j2` for NixOS.

## Tasks

| Task | Make target |
|---|---|
| `do_configure` | `make bringup` (transitive; builds `$(KDEVOPS_NODES)`) |

## Configuration

No user-facing Kconfig options. Template selection is driven by the
active backend's `scripts/<backend>.Makefile`, which sets
`KDEVOPS_NODES_TEMPLATE` to one of the per-backend templates.

## Layout

```
modules/nodes/
├── Kconfig
├── Makefile
└── README.md
playbooks/nodes.yml
playbooks/roles/nodes/
├── defaults/main.yml
├── tasks/{main.yml,gitr.yml,ltp.yml,nfstest.yml}
├── python/gen_pcie_passthrough_guestfs_xml.py
└── templates/
    ├── guestfs_nodes.j2          libvirt entry point
    ├── terraform_nodes.tf.j2     cloud entry point
    ├── nixos_nodes.j2            nixos entry point
    ├── hosts.j2                  internal helper (not the ansible_inventory inventory.j2)
    ├── gen_nodes_list.j2         internal helper
    ├── gen_drives.j2             internal helper
    ├── drives.j2                 internal helper
    ├── guestfs_q35.j2.xml        libvirt XML
    └── guestfs_virt.j2.xml       libvirt XML
```

## Sub-modules

None. The three backends are alternative outputs of one role, not
separately configurable units.

## Dependencies

The libvirt and qemu_build modules emit their configuration into
extra_vars.yaml via Kconfig `output yaml`, so the node templates
read every libvirt_*, qemu_*, and qemu_build_* key from there with
no extra Make-side plumbing. Three Make-side scalars
(`kdevops_nodes`, `kdevops_nodes_template`,
`kdevops_nodes_template_full_path`) come from the main Makefile's
`ANSIBLE_EXTRA_ARGS` because they depend on workflow/backend state
the Kconfig solver cannot see.

## Variable namespace collisions

(See the spec's "Variable namespace collisions with ansible" section
for the general rule.) The module name `nodes` does not share a
prefix with any `INTERNAL_STATIC_VARS` entry, so the per-module
prefix `nodes_*` is collision-free. No collisions in scope.

## Notes

The role contains one defensive cleanup task that escalates
privileges (`become_method: ansible.builtin.sudo`) to chown a stale
`$(KDEVOPS_NODES)` file if it exists with wrong ownership from a
prior run. It only fires when the file is already present, so a
fresh `make bringup` does not trigger sudo. Refactoring this sudo
escalation into `controller-setup` (or replacing it with a
fail-with-instruction pattern) is a separate concern from this
layout migration.
