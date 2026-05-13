# monitoring/nvme_ocp_smart

## Purpose

Periodic sampler for the NVMe OCP (Open Compute Project) extended
SMART log via `nvme-cli`'s `ocp smart-add-log` subcommand. Discovers
OCP-compatible NVMe devices on the guest, starts one background
sampler per device, and writes JSON-formatted samples to
`/root/monitoring/nvme_ocp_smart_<dev>_stats.txt`. At workload end
the parent role's collect phase stops the samplers, fetches the
data files, and runs a localhost plotting script.

Unlike folio_migration and memory_fragmentation, this monitor does
not depend on developmental kernel features — OCP SMART is a stable
vendor-defined extension. The sub-module is sourced directly under
`ENABLE_MONITORING` rather than under `MONITOR_DEVELOPMENTAL_STATS`.

## Configuration

| Symbol | Purpose |
|---|---|
| `CONFIG_MONITOR_NVME_OCP_SMART` | Enable this monitor. |
| `CONFIG_MONITOR_NVME_OCP_SMART_INTERVAL` | Sampling interval in seconds (default 120, range 60-3600). |
| `CONFIG_MONITOR_NVME_OCP_SMART_DEVICES` | Space-separated device list, or `auto` for discovery. |

## Tags

The parent monitoring role wires this sub-module's run / collect /
interim phases into the do_run / do_collect tag axes. Selection at
runtime is gated on the `monitor_nvme_ocp_smart` yaml key emitted by
the Kconfig above and tagged with `monitor_nvme_ocp_smart` for
direct CLI selection.

## Dependencies

Requires `nvme-cli` on the guest. The `nvme ocp` subcommand was
upstreamed in nvme-cli 2.0; older releases lack OCP support. Real
hardware needs an OCP-compliant SSD; QEMU virtual NVMe devices
respond partially and the discovery logic accepts them when the
command returns a "Successful Completion" status even with GUID
mismatches.
