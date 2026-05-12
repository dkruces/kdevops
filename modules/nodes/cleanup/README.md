# nodes/cleanup — opt-in sudo recovery sub-module

## Purpose

Recover from a stale `kdevops_nodes` file left behind by a prior run
that executed under a different account. The file is owned by the
wrong user, so the next non-sudo write fails.

This sub-module exists to keep that sudo step out of the parent
role's default execution path, per the module spec's controller-side
sudo isolation rule.

## Tasks

| Task | Make target |
|---|---|
| Verify the kdevops_nodes file is writable (no sudo) | runs by default as part of the parent role |
| Claim ownership of the file (sudo) | `make nodes-cleanup` |

## Manual alternative

```
rm <TOPDIR>/<KDEVOPS_NODES>
```

The next non-sudo write recreates the file under the current user.

## Layout

```
modules/nodes/cleanup/
└── Makefile

playbooks/roles/nodes/cleanup/
└── tasks/
    ├── main.yml      defaults to verify.yml
    ├── verify.yml    pure-read precheck + fail-with-diagnostic
    └── setup.yml     the sudo chown
```

## Dependencies

None. Pure file-ownership repair on the controller.
