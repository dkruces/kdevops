# ansible_inventory

## Purpose

Renders the ansible inventory file consumed by every `ansible-playbook`
invocation. The output path is owned by `ansible_config` (Kconfig
`CONFIG_ANSIBLE_CONFIG_INVENTORY`). The template to render is selected
by `CONFIG_ANSIBLE_INVENTORY_TEMPLATE`; workflows override it.

## Tasks

| Task | Make target |
|---|---|
| `do_configure` | `make env` (transitive; builds `$(ANSIBLE_INVENTORY_FILE)`) |

## Configuration

- `CONFIG_ANSIBLE_INVENTORY_TEMPLATE` — short filename of the template
  inside the role's `templates/` directory (default `inventory.j2`).
- `CONFIG_ANSIBLE_INVENTORY_TEMPLATE_DIR` — absolute path to the
  template directory.

## Layout

```
modules/ansible_inventory/
├── Kconfig
├── Makefile
└── README.md
playbooks/ansible_inventory.yml
playbooks/roles/ansible_inventory/
├── defaults/main.yml
├── tasks/main.yml
└── templates/
    ├── inventory.j2     default
    ├── workflows/       workflow-specific subtemplates
    └── ...
```

## Sub-modules

None.

## Dependencies

`ansible_config` owns the output path. The role reads
`ansible_config_inventory` from extra_vars to know where to write.

## Variable namespace collisions

(See the spec's "Variable namespace collisions with ansible" section
for the general rule.) Specific to this module:

- **`ansible_inventory_sources`** is in `INTERNAL_STATIC_VARS`. Avoid
  a `*_sources` suffix here; use the singular or another distinct
  word.

The bare `inventory_*` prefix is far worse: `inventory_file`,
`inventory_dir`, `inventory_hostname` and `inventory_hostname_short`
are all actively overridden per host — which is why the module keeps
the `ansible_` qualifier.
