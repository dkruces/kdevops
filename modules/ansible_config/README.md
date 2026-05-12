# ansible_config

## Purpose

Renders the kdevops `ansible.cfg` consumed by every `ansible-playbook`
invocation. The path and the inventory it points at are configurable
via Kconfig; the module also emits the `ansible_config_path` and
`ansible_config_inventory` ansible variables for downstream roles.

## Tasks

| Task | Make target |
|---|---|
| `do_install` | `make env` (transitive; builds `$(ANSIBLE_CONFIG_PATH)`) |

## Configuration

The Kconfig declares the full set of `[defaults]` and `[ssh_connection]`
knobs exposed by ansible-core. See `modules/ansible_config/Kconfig` for
the canonical list and per-symbol help. The two paths the module owns
are user-overridable:

- `CONFIG_ANSIBLE_CONFIG_PATH_CUSTOM` — set a custom location for the
  rendered `ansible.cfg`.
- `CONFIG_ANSIBLE_CONFIG_INVENTORY_CUSTOM` — set a custom inventory path
  to write into the rendered `ansible.cfg`'s `inventory=` key.

## Layout

```
modules/ansible_config/
├── Kconfig          user-facing options
├── Makefile         ANSIBLE_CONFIG_PATH rule
└── README.md
playbooks/ansible_config.yml
playbooks/roles/ansible_config/
```

## Sub-modules

None.

## Dependencies

The default inventory path the rendered `ansible.cfg` points at is
provided by the inventory-generating module.

## Variable namespace collisions

(See the spec's "Variable namespace collisions with ansible" section
for the general rule.) Specific to this module:

- **`ansible_config_file`** is in `INTERNAL_STATIC_VARS` and
  unconditionally re-set by `vars/manager.py:457` to ansible's own
  runtime `C.CONFIG_FILE`. To carry the path of the rendered
  `ansible.cfg` to the role, the module exposes `ANSIBLE_CONFIG_PATH`
  (YAML key `ansible_config_path`) instead.

All other `ansible_config_*` symbols this module emits are outside
the reserved set and pass through to ansible unchanged.
