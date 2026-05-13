# monitoring/folio_migration

## Purpose

Periodic sampler for the kernel's folio migration debugfs counters at
`/sys/kernel/debug/mm/migrate/stats`. The monitor takes a start
snapshot at the workload boundary, samples on a configurable
interval, and writes a final snapshot plus a comparison plot when
the workload finishes. The data exposes how many folios moved
between zones, lists, and migration types over the test window.

Gated by the parent module's `MONITOR_DEVELOPMENTAL_STATS` switch
because the underlying stats file depends on a kernel patch that is
not yet upstream.

## Configuration

| Symbol | Purpose |
|---|---|
| `CONFIG_MONITOR_FOLIO_MIGRATION` | Enable this monitor. |
| `CONFIG_MONITOR_FOLIO_MIGRATION_INTERVAL` | Sampling interval in seconds (default 60). |

## Tags

The parent monitoring role wires this sub-module's run / collect
phases into the do_run / do_collect tag axes. Selection at runtime
is gated on the `monitor_folio_migration` yaml key emitted by the
Kconfig above.

## Dependencies

Requires a kernel with `/sys/kernel/debug/mm/migrate/stats` exposed.
The verify path inspects the file at start; if it is missing the
monitor's run phase no-ops with a warning rather than failing the
workload.
