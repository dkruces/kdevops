 cat dagomez.sh
#!/usr/bin/env bash
set -euxo pipefail

FRAGMENTS_DIR=/home/dagomez.linux/src/kdevops-config-fragments

# Initialize log files
COMMAND_LOG="kdevops-cmd-0001.log"
OUTPUT_LOG="kdevops-out-0001.log"

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
log_and_execute make KDEVOPS_HOSTS_PREFIX=kci-18051236464-20 LINUX_TREE=/mirror/linux.git LINUX_TREE_REF=v6.15 \
defconfig-sysbench-postgresql-atomic-tps-variability V=1

log_and_execute ./scripts/kconfig/merge_config.sh -n \
.config \
defconfigs/configs/diy.config \
defconfigs/configs/ci.config \
defconfigs/configs/advance_pool.config \
defconfigs/configs/qemu_bin.config \
defconfigs/configs/sysbench-postgresql-4k.config \
defconfigs/configs/pcip.config \
defconfigs/configs/experiment-0000.config

log_and_execute make
log_and_execute make destroy
log_and_execute make bringup

# log_and_execute make linux
# log_and_execute make sysbench V=1

# log_and_execute make sysbench-test V=1
# log_and_execute make ci-build-test CI_WORKFLOW=blktests_nvme
# log_and_execute make ci-test CI_WORKFLOW=blktests_nvme
