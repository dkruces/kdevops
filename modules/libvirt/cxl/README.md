# libvirt/cxl — CXL device emulation (config-only sub-module)

## Purpose

Declares the QEMU CXL emulation Kconfig knobs (QEMU_ENABLE_CXL plus
the topology choices: demo topo 1/2, switch topo 1, DCD demo topo 1).

This is a config-only sub-module: it owns no role, no playbook, no
Make targets. The Kconfig surface drives `output yaml` symbols that
land in extra_vars.yaml; the actual CXL plumbing on the guest is
performed by the `cxl` workflow role (separately maintained at
`playbooks/roles/cxl/`) and the QEMU command-line construction in
the `nodes` role's drive templates.

## Layout

```
modules/libvirt/cxl/
├── Kconfig
└── README.md
```

## Configuration

Knobs gated on `QEMU_ENABLE_CXL=y`:

- `QEMU_ENABLE_CXL` — master switch (depends on `BRINGUP_SUPPORTS_CXL`)
- `QEMU_ENABLE_CXL_DEMO_TOPOLOGY_1` / `_TOPOLOGY_2`
- `QEMU_ENABLE_CXL_SWITCH_TOPOLOGY_1`
- `QEMU_ENABLE_CXL_DEMO_DCD_TOPOLOGY_1`
- QMP-on-TCP knobs (`QEMU_START_QMP_ON_TCP_SOCKET`, etc.) — currently
  declared here but with no consumers in the tree.

## Dependencies

`libvirt/` parent module sources this Kconfig.
