# monitoring/memory_fragmentation

## Purpose

eBPF-based tracker for memory fragmentation. Attaches to allocation
tracepoints, computes a fragmentation index over the workload
window, and writes raw eBPF data, JSON metrics, and matplotlib
plots to an output directory. The tracker is the primary tool for
investigating whether Large Block Size support degrades
fragmentation under sustained workloads.

Gated by the parent module's `MONITOR_DEVELOPMENTAL_STATS` switch
because the tracker depends on tracepoints that may not be stable
across kernels.

## Configuration

| Symbol | Purpose |
|---|---|
| `CONFIG_MONITOR_MEMORY_FRAGMENTATION` | Enable this monitor. |
| `CONFIG_MONITOR_MEMORY_FRAGMENTATION_DURATION` | Tracker runtime in seconds (0 = until workflow ends). |
| `CONFIG_MONITOR_MEMORY_FRAGMENTATION_OUTPUT_DIR` | Guest-side output directory for raw data and plots. |

## Tags

The parent monitoring role wires this sub-module's run / collect
phases into the do_run / do_collect tag axes. Selection at runtime
is gated on the `monitor_memory_fragmentation` yaml key emitted by
the Kconfig above.

## Dependencies

Requires `python3-bpfcc` on the guest, root privileges for eBPF
attachment, and a kernel with the relevant memory tracepoints.
The build_deps / runtime_deps sub-modules under `monitoring`
install the python3-bpfcc package on supported distros.
