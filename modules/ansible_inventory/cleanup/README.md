# ansible_inventory/cleanup — opt-in sudo recovery sub-module

## Purpose

Recover from a stale `inventory` file left behind by a prior run that
executed under a different account (foreign sudo run, cross-tree
kdevops invocation). The file is owned by the wrong user, so the
next non-sudo write fails.

This sub-module exists to keep that sudo step out of the parent
role's default execution path, per the module spec's controller-side
sudo isolation rule.

## Tasks

| Task | Make target |
|---|---|
| Verify the inventory file is writable (no sudo) | runs by default as part of the parent role |
| Claim ownership of the file (sudo) | `make ansible-inventory-cleanup` |

## Manual alternative

```
rm <CONFIG_ANSIBLE_CONFIG_INVENTORY>
```

The next non-sudo write recreates the file under the current user.

## Layout

```
modules/ansible_inventory/cleanup/
└── Makefile

playbooks/roles/ansible_inventory/cleanup/
└── tasks/
    ├── main.yml      defaults to verify.yml
    ├── verify.yml    pure-read precheck + fail-with-diagnostic
    └── setup.yml     the sudo chown
```

## Dependencies

None. Pure file-ownership repair on the controller.
