# monitoring

## Purpose

Background data collection during workflow execution. The module
hosts a factory of independently-gated monitor sub-modules; each
monitor records one class of system metric (folio migration, memory
fragmentation, NVMe SMART, biolatency, …). Enable the parent gate
`CONFIG_ENABLE_MONITORING` and then opt into individual monitors
through their own `CONFIG_MONITOR_*` knobs.

The monitor factory follows the spec's
[Monitor sub-module factory](../../docs/module-spec.md#monitor-sub-module-factory)
pattern: each monitor has its own Kconfig and README under
`modules/monitoring/monitors/<name>/`, a real sub-role at
`playbooks/roles/monitoring/monitors/<name>/`, no Make target of
its own. Selection at runtime flows through the `monitor_<name>`
output yaml knob and the matching ansible tag axis.

## Tasks

| Task | Make target |
|---|---|
| Collect interim monitor data without stopping recorders | `make monitoring-results` |
| Stop all monitors and remove collected data | `make monitoring-cleanup` |

Monitors start automatically as part of any workflow that includes
the monitoring role. There is no separate `make monitoring` start
target; workflows reach into the role at their orchestration
boundaries.

## Configuration

| Symbol | Purpose |
|---|---|
| `CONFIG_ENABLE_MONITORING` | Master gate. Off by default. |
| `CONFIG_MONITOR_DEVELOPMENTAL_STATS` | Allow monitors that depend on out-of-tree kernel patches. |
| `CONFIG_MONITOR_FOLIO_MIGRATION` | Periodic snapshots of `/sys/kernel/debug/mm/migrate/stats`. |
| `CONFIG_MONITOR_FOLIO_MIGRATION_INTERVAL` | Sampling interval (seconds). |
| `CONFIG_MONITOR_MEMORY_FRAGMENTATION` | eBPF tracepoint-based fragmentation tracker. |
| `CONFIG_MONITOR_FRAGMENTATION_DURATION` | Tracker runtime (seconds, 0 = until workflow ends). |
| `CONFIG_MONITOR_FRAGMENTATION_OUTPUT_DIR` | Guest-side output directory. |

Per-monitor knobs live in their own sub-module Kconfig once the
sub-modules are split out.

## Layout

```
modules/monitoring/
├── Kconfig                          parent + per-monitor sources
├── Makefile                         monitoring-results, monitoring-cleanup
└── README.md

playbooks/monitoring.yml             single entry-point playbook
playbooks/roles/monitoring/          parent role + monitors/<name>/ sub-roles
```

## Sub-modules

The monitor sub-modules carve out of the parent Kconfig in a
follow-up commit; each lands at
`modules/monitoring/monitors/<name>/{Kconfig,README.md}` and is
sourced from this module's Kconfig.

## Dependencies

No hard module dependencies. Consumers (workflows that opt in) call
`monitoring-results` from their own targets.
