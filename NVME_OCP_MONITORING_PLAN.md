# NVMe OCP Monitoring Integration Plan

## Overview
Add support for monitoring NVMe OCP (Open Compute Project) SMART statistics using `nvme ocp smart-add-log` command. This will collect extended SMART data with timestamps for trend analysis and plotting.

**Target Command**: `sudo nvme ocp smart-add-log --output-format=json <device>`

**Integration Pattern**: Follows existing monitoring framework established in commit be90d7b1 (monitoring framework for workflow execution).

## Phase 1: Kconfig Integration ✅

### 1.1 Update `kconfigs/monitors/Kconfig`
Add new section after existing folio migration config:

```kconfig
config MONITOR_NVME_OCP
	bool "Monitor NVMe OCP SMART statistics"
	output yaml
	default n
	help
	  Enable monitoring of NVMe OCP (Open Compute Project) extended SMART
	  statistics using nvme-cli ocp plugin.

	  Requires:
	  - nvme-cli with OCP plugin support
	  - NVMe devices with OCP SMART support
	  - Root privileges for nvme command execution

	  Collects statistics from: nvme ocp smart-add-log --output-format=json

config MONITOR_NVME_OCP_INTERVAL
	int "NVMe OCP monitoring interval (seconds)"
	output yaml
	default 300
	depends on MONITOR_NVME_OCP
	range 60 3600
	help
	  How often to collect NVMe OCP SMART statistics in seconds.
	  Default is 300 seconds (5 minutes).

	  Lower values provide more granular data but may impact system
	  performance. Higher values reduce overhead but may miss
	  short-lived device behavior changes.

config MONITOR_NVME_OCP_DEVICES
	string "NVMe devices to monitor (space-separated)"
	output yaml
	default "auto"
	depends on MONITOR_NVME_OCP
	help
	  Space-separated list of NVMe devices to monitor (e.g., "/dev/nvme0n1 /dev/nvme1n1").
	  
	  Use "auto" to automatically discover all available NVMe devices.
	  Use "ocp-only" to automatically discover only OCP-capable devices.
```

**Status**: Completed in commit 9256aeb2
- Added MONITOR_NVME_OCP, MONITOR_NVME_OCP_INTERVAL, MONITOR_NVME_OCP_DEVICES Kconfig options
- Updated monitoring role defaults with NVMe OCP variables
- Integrated with existing monitoring framework structure

## Phase 2: Monitoring Role Implementation ✅

### 2.1 Add NVMe OCP Support to `playbooks/roles/monitoring/tasks/monitor_run.yml`

Add tasks for:
- Device discovery (auto, ocp-only, manual modes)
- OCP capability validation
- Background monitoring process startup
- PID tracking for cleanup

```yaml
# NVMe OCP monitoring setup
- name: Check if NVMe OCP monitoring is enabled
  set_fact:
    nvme_ocp_enabled: "{{ monitor_nvme_ocp|default(false)|bool }}"
  when:
    - enable_monitoring|default(false)|bool

- name: Discover NVMe devices for OCP monitoring
  shell: |
    if [ "{{ monitor_nvme_ocp_devices }}" = "auto" ]; then
      find /dev -name 'nvme*n*' -type b 2>/dev/null | head -10
    elif [ "{{ monitor_nvme_ocp_devices }}" = "ocp-only" ]; then
      for dev in /dev/nvme*n*; do
        if [ -b "$dev" ] && nvme ocp smart-add-log "$dev" >/dev/null 2>&1; then
          echo "$dev"
        fi
      done
    else
      echo "{{ monitor_nvme_ocp_devices }}"
    fi
  register: nvme_devices_discovery
  changed_when: false
  failed_when: false
  when:
    - nvme_ocp_enabled|bool

- name: Set NVMe devices list for monitoring
  set_fact:
    nvme_devices_list: "{{ nvme_devices_discovery.stdout_lines|default([]) }}"
  when:
    - nvme_ocp_enabled|bool

- name: Start NVMe OCP monitoring for each device
  shell: |
    mkdir -p /root/monitoring
    device_name=$(basename {{ item }} | sed 's/\//_/g')
    nohup bash -c '
      while true; do
        echo "$(date "+%Y-%m-%d %H:%M:%S")"
        nvme ocp smart-add-log --output-format=json {{ item }} 2>/dev/null || echo "{\"error\":\"command_failed\"}"
        echo ""
        sleep {{ monitor_nvme_ocp_interval|default(300) }}
      done
    ' > /root/monitoring/nvme_ocp_${device_name}_stats.txt 2>&1 &
    echo $! > /root/monitoring/nvme_ocp_${device_name}.pid
  loop: "{{ nvme_devices_list }}"
  when:
    - nvme_ocp_enabled|bool
    - nvme_devices_list|length > 0
```

### 2.2 Add Collection Logic to `playbooks/roles/monitoring/tasks/monitor_collect.yml`

Add tasks for:
- Process termination
- Data file collection to control host
- Plot generation

```yaml
# NVMe OCP monitoring collection
- name: Check for NVMe OCP monitoring processes
  shell: "ls /root/monitoring/nvme_ocp_*.pid 2>/dev/null || true"
  register: nvme_ocp_pids
  changed_when: false
  when:
    - enable_monitoring|default(false)|bool

- name: Stop NVMe OCP monitoring processes
  shell: |
    for pidfile in /root/monitoring/nvme_ocp_*.pid; do
      if [ -f "$pidfile" ]; then
        kill $(cat "$pidfile") 2>/dev/null || true
        rm -f "$pidfile"
      fi
    done
  when:
    - enable_monitoring|default(false)|bool
    - nvme_ocp_pids.stdout != ""

- name: Collect NVMe OCP monitoring data
  fetch:
    src: "/root/monitoring/nvme_ocp_{{ item }}_stats.txt"
    dest: "{{ monitoring_results_base_path }}/{{ inventory_hostname }}_nvme_ocp_{{ item }}_stats.txt"
    flat: yes
  loop: "{{ nvme_devices_list|default([]) | map('basename') | map('regex_replace', '/', '_') | list }}"
  when:
    - enable_monitoring|default(false)|bool
    - nvme_ocp_enabled|default(false)|bool

- name: Generate NVMe OCP plots
  script: files/plot_nvme_ocp_stats.py {{ monitoring_results_base_path }}/{{ inventory_hostname }}_nvme_ocp_*_stats.txt -o {{ monitoring_results_base_path }}/{{ inventory_hostname }}_nvme_ocp_plot.png
  delegate_to: localhost
  run_once: false
  when:
    - enable_monitoring|default(false)|bool
    - nvme_ocp_enabled|default(false)|bool
```

**Status**: Completed in commit 9410272d
- Added device discovery logic with auto/ocp-only/manual modes
- Implemented background monitoring with timestamped JSON collection
- Added process verification and PID tracking for cleanup
- Created data collection and plotting integration

## Phase 3: Data Processing and Visualization ✅

### 3.1 Create `playbooks/roles/monitoring/files/plot_nvme_ocp_stats.py`

Python script features:
- **Timestamp parsing**: Handle "YYYY-MM-DD HH:MM:SS" format
- **JSON validation**: Parse and validate nvme ocp output
- **Multi-device support**: Handle multiple NVMe devices per host
- **Error handling**: Graceful handling of command failures or malformed JSON

### 3.2 Key Metrics to Visualize

#### Plot 1: Media Wear Indicators
- Physical media units written (cumulative)
- Physical media units read (cumulative)
- Max/Min user data erase counts

#### Plot 2: Health and Reliability
- Bad user/system NAND blocks (raw and normalized)
- Uncorrectable read error count
- End-to-end detected/corrected errors
- XOR recovery count

#### Plot 3: Performance and Thermal
- Number of thermal throttling events
- Current throttling status
- Unaligned I/O count
- Incomplete shutdowns

#### Plot 4: Advanced Metrics
- System data percent used
- Percent free blocks
- Capacitor health
- Endurance estimate

### 3.3 Data Format Structure

**Input file format**:
```
2025-09-02 14:30:00
{
  "Physical media units written": {"hi": 0, "lo": 527805403860992},
  "Physical media units read": {"hi": 0, "lo": 467772386381824},
  "Bad user nand blocks - Raw": 0,
  "Bad user nand blocks - Normalized": 100,
  ...
}

2025-09-02 14:35:00
{
  "Physical media units written": {"hi": 0, "lo": 527815403860992},
  ...
}
```

**Status**: Completed in commit 9410272d
- Created plot_nvme_ocp_stats.py with multi-panel visualization
- Implemented A/B comparison support and statistical analysis
- Added Hi/Lo 64-bit value handling for NVMe metrics
- Integrated human-readable formatting and comprehensive legends

## Phase 4: Workflow Integration ✅

### 4.1 Target Workflows for Integration
- **blktests**: Primary target for block device testing
- **fio-tests**: Storage performance testing
- **selftests**: Kernel block layer tests
- **fstests**: Filesystem testing (already has monitoring framework)

### 4.2 Integration Pattern
Follow existing fstests pattern:

```yaml
# In workflow main.yml files
- name: Start monitoring services
  include_role:
    name: monitoring
    tasks_from: monitor_run
  when:
    - workflow_condition|bool
    - enable_monitoring|default(false)|bool
  tags: ['monitoring', 'monitor_run']

# ... workflow tasks ...

- name: Stop monitoring services and collect data
  include_role:
    name: monitoring
    tasks_from: monitor_collect
  when:
    - workflow_condition|bool
    - enable_monitoring|default(false)|bool
  tags: ['monitoring', 'monitor_collect']
```

**Status**: Completed in commit dbb7b8a2
- Integrated monitoring with blktests workflow
- Added blktests-specific results path configuration
- Followed established monitoring integration pattern

## Phase 5: Documentation and Testing ✅

### 5.1 Update Documentation
- Add NVMe OCP section to `docs/monitoring.md`
- Include configuration examples
- Document device discovery modes
- Add troubleshooting guide for OCP support detection

### 5.2 Testing Strategy
- **Test with OCP devices**: Validate on systems with OCP-capable NVMe devices
- **Test without OCP**: Ensure graceful failure on non-OCP devices
- **Device discovery testing**: Validate auto, ocp-only, and manual modes
- **Long-duration testing**: Verify monitoring doesn't interfere with workflows
- **Plot generation**: Test visualization with real data

## Implementation Considerations

### Device Discovery Strategy
- **Auto mode**: Scan `/dev/nvme*n*` for all NVMe devices
- **OCP-only mode**: Test each device for OCP support before monitoring
- **Manual mode**: User-specified device list

### Error Handling
- Graceful failure when devices don't support OCP
- JSON parsing validation for malformed output
- Device hot-plug/removal during monitoring
- Command timeout handling

### Performance Impact
- 5-minute default interval balances data granularity vs overhead
- JSON output parsing on control host, not target nodes
- Background collection doesn't interfere with workflow execution
- Configurable monitoring intervals (60-3600 seconds)

### Data Format Considerations
- **Hi/Lo value handling**: Many metrics use 64-bit values split into hi/lo parts
- **Timestamp consistency**: Use ISO format matching existing monitoring
- **Device identification**: Handle device naming consistently across collection and plotting
- **JSON error states**: Handle command failures with structured error responses

## Expected Output Structure

### Result Files
- `<hostname>_nvme_ocp_<device>_stats.txt`: Raw timestamped JSON data
- `<hostname>_nvme_ocp_plot.png`: Multi-panel visualization
- Individual device plots for multi-device systems

### Directory Structure
```
workflows/<workflow>/results/monitoring/
├── hostname_nvme_ocp_nvme0n1_stats.txt
├── hostname_nvme_ocp_nvme1n1_stats.txt
└── hostname_nvme_ocp_plot.png
```

## Future Enhancements
- **Real-time monitoring**: Integration with Grafana/Prometheus
- **Alerting**: Threshold-based notifications for critical metrics
- **Historical trending**: Long-term data retention and analysis
- **Multiple plugin support**: Extend to other nvme-cli plugins beyond OCP
- **Advanced analytics**: Machine learning-based anomaly detection

---

**Status**: Completed in commit e9235e2e
- Updated monitoring.md with NVMe OCP configuration and usage
- Added blktests integration example and troubleshooting guide
- Documented device discovery modes and runtime configuration

## Status Tracking

- [x] Phase 1: Kconfig Integration (commit 9256aeb2)
- [x] Phase 2: Monitoring Role Implementation (commit 9410272d)
- [x] Phase 3: Data Processing and Visualization (commit 9410272d)
- [x] Phase 4: Workflow Integration (commit dbb7b8a2)
- [x] Phase 5: Documentation and Testing (commit e9235e2e)

**Started**: 2025-09-02
**Completed**: 2025-09-02
**Implementation Summary**: Full NVMe OCP SMART monitoring integration with kdevops monitoring framework