#!/usr/bin/env bash
set -euxo pipefail

# Initialize log files
COMMAND_LOG="kdevops-sysbench-001.log"
OUTPUT_LOG="kdevops-sysbench-002.log"

# Clear previous logs
> "$COMMAND_LOG"
> "$OUTPUT_LOG"

# Function to log and execute commands
log_and_execute() {
    local cmd="$*"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Executing: $cmd" | tee -a "$COMMAND_LOG"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Executing: $cmd" >> "$OUTPUT_LOG"
    echo "----------------------------------------" >> "$OUTPUT_LOG"

    # Execute command with colors preserved for stdout, plain text for logs
    $cmd 2>&1 | tee >(sed 's/\x1b\[[0-9;]*m//g' >> "$OUTPUT_LOG")

    echo "----------------------------------------" >> "$OUTPUT_LOG"
    echo "" >> "$OUTPUT_LOG"
}

log_and_execute make destroy V=1 || true
log_and_execute make mrproper V=1
log_and_execute make dynamic_pcipassthrough_kconfig V=1 KDEVOPS_ENABLE_PCIE_KCONFIG=1
log_and_execute make defconfig-sysbench-postgresql-atomic-tps-variability V=1
log_and_execute ./scripts/kconfig/merge_config.sh \
-n .config \
defconfigs/configs/linux_kdevops.config \
defconfigs/configs/diy.config \
defconfigs/configs/monitor_smart_log.config \
defconfigs/configs/monitor_ocp_smart.config \
defconfigs/configs/sysbench-postgresql-4k.config \
defconfigs/configs/dagomez.config \
defconfigs/configs/pci.config \
defconfigs/configs/linux_v6.15.config \
defconfigs/configs/pci2.config

log_and_execute make V=1
log_and_execute make bringup V=1
log_and_execute make linux V=1
log_and_execute make uname V=1
log_and_execute make sysbench V=1
