# playbooks/roles/libvirt — libvirt module's parent role

## Purpose

Orchestrator role for the libvirt module. Performs no controller-side
work on its own. The `tasks/main.yml` body conditionally includes
each sub-role:

- `user/` — verify by default; sudo setup via `--tags libvirt_user_setup`.
- `storage_pool/` — verify by default; sudo setup via
  `--tags libvirt_storage_pool_setup`.
- `pcie_passthrough/` — verify by default; sudo setup via
  `--tags libvirt_pcie_passthrough_setup`.

The sub-role include lines are added incrementally as each sub-role
lands; the current stub keeps the orchestrator parseable in the
meantime.

## Sub-roles

| Sub-role | Path | Invocation tag |
|---|---|---|
| `user` | `playbooks/roles/libvirt/user/` | `libvirt_user_setup` (sudo) |
| `storage_pool` | `playbooks/roles/libvirt/storage_pool/` | `libvirt_storage_pool_setup` (sudo) |
| `pcie_passthrough` | `playbooks/roles/libvirt/pcie_passthrough/` | `libvirt_pcie_passthrough_setup` (sudo) |

Each sub-role splits internally into `verify/` (non-sudo precheck,
runs by default) and `setup/` (sudo opt-in, runs only when its tag
is selected).

## Spec conformance

Implements the spec's "Controller-side sudo isolation" rule: the
default path is non-sudo and the verify sub-sub-modules fail with
structured diagnostics that name the opt-in Make target and the
documentation page.
