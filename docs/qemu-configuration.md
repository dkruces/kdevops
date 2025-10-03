# QEMU Configuration in kdevops

This document explains how kdevops manages QEMU binaries for virtualization-based testing.

## Overview

kdevops needs to know where to find the QEMU binary for libvirt-based virtualization. There are three distinct scenarios for QEMU usage, each with different configuration requirements.

## The Three QEMU Scenarios

### Scenario 1: kdevops Builds QEMU (`QEMU_BUILD=y`)

**Configuration:**
```
CONFIG_QEMU_BUILD=y
CONFIG_QEMU_USE_DEVELOPMENT_VERSION=y  # Automatically set
```

**What happens:**
- kdevops clones QEMU source from configured git repository
- Builds QEMU with selected target architecture
- Installs to `/usr/local/bin/qemu-system-*`
- Automatically sets `QEMU_USE_DEVELOPMENT_VERSION=y`

**Binary location:** `/usr/local/bin/qemu-system-{arch}`

**When to use:**
- Your distribution's QEMU package lacks required features (NVMe, CXL, etc.)
- Testing specific QEMU versions or patches
- 99% of kdevops workflows require NVMe emulation

**Example:**
```bash
make menuconfig
# Navigate to: Bring up methods -> Libvirt options
# Enable: "Should we build QEMU for you?"
# Select: QEMU git URL (upstream or jic23)
make qemu        # Builds and installs QEMU
make bringup     # Uses the newly built QEMU
```

---

### Scenario 2: Manually Built QEMU (`QEMU_USE_DEVELOPMENT_VERSION=y`)

**Configuration:**
```
CONFIG_QEMU_BUILD=n
CONFIG_QEMU_USE_DEVELOPMENT_VERSION=y  # User selects this
```

**What happens:**
- kdevops does NOT build QEMU
- libvirt looks for QEMU at `/usr/local/bin/qemu-system-*`
- User is responsible for building and installing QEMU

**Binary location:** `/usr/local/bin/qemu-system-{arch}` (user-provided)

**When to use:**
- You have your own QEMU build workflow
- Testing local QEMU patches before submission
- Using QEMU features not available in distro packages
- Want control over QEMU build options

**Example:**
```bash
# Manual QEMU build (outside kdevops)
cd ~/src/qemu
./configure --target-list=x86_64-softmmu
make -j$(nproc)
sudo make install  # Installs to /usr/local/bin/

# kdevops configuration
make menuconfig
# Navigate to: Bring up methods -> Libvirt options
# Ensure: "Should we build QEMU for you?" is DISABLED
# Enable: "Are you using a manually built development version of QEMU?"
make bringup  # Uses your manually built QEMU
```

---

### Scenario 3: Distribution QEMU Package (Default)

**Configuration:**
```
CONFIG_QEMU_BUILD=n
CONFIG_QEMU_USE_DEVELOPMENT_VERSION=n  # Default
```

**What happens:**
- Uses distribution-provided QEMU package
- Binary location is distro-specific
- No custom build required

**Binary locations (distro-specific):**
- Ubuntu/Debian x86_64: `/usr/bin/qemu-system-x86_64`
- CentOS/RHEL ARM64: `/usr/libexec/qemu-kvm`
- Fedora: `/usr/bin/qemu-system-{arch}`

**When to use:**
- Standard kernel testing without special QEMU features
- Distribution QEMU package has all required features
- Minimal setup preferred

**Limitations:**
- Distribution packages may lack:
  - NVMe emulation (required by most kdevops workflows)
  - CXL support
  - Latest QEMU features
- May not support all kdevops test scenarios

**Example:**
```bash
# Install distro QEMU package
sudo apt-get install qemu-system-x86  # Debian/Ubuntu
sudo dnf install qemu-kvm             # Fedora/CentOS

# kdevops configuration
make menuconfig
# Ensure both QEMU build options are DISABLED (default)
make bringup  # Uses distro QEMU
```

---

## Configuration Variables

### User-Facing Variables

#### `QEMU_BUILD`
- **Type:** bool
- **Location:** `kconfigs/Kconfig.qemu_build`
- **Purpose:** Enable kdevops to build QEMU from source
- **Exported to Ansible:** Yes (`output yaml`)

#### `QEMU_USE_DEVELOPMENT_VERSION`
- **Type:** bool (context-dependent)
- **Location:** `kconfigs/Kconfig.qemu_build`
- **Purpose:** Indicates QEMU is at `/usr/local/bin/` instead of distro location
- **Two definitions:**
  1. Inside `if QEMU_BUILD`: Automatic internal flag (not user-visible)
  2. Inside `if !QEMU_BUILD`: User-selectable option (visible in menuconfig)

#### `QEMU_BUILD_GIT`
- **Type:** string
- **Purpose:** Git repository URL for QEMU source
- **Exported to Ansible:** Yes

#### `QEMU_BUILD_GIT_VERSION`
- **Type:** string
- **Default:** `v10.1.0` (upstream), `cxl-2023-05-19` (jic23)
- **Purpose:** QEMU version/tag to build

#### `QEMU_TARGET`
- **Type:** string
- **Default:** Architecture-specific (`aarch64-softmmu`, `x86_64-softmmu`, etc.)
- **Purpose:** QEMU target architecture to build

### Internal Variables

#### `QEMU_BIN_PATH`
- **Type:** string
- **Purpose:** Resolved path to QEMU binary (used by Ansible)
- **Logic:**
  ```
  if QEMU_USE_DEVELOPMENT_VERSION:
      /usr/local/bin/qemu-system-{arch}
  else:
      /usr/bin/qemu-system-{arch}  (or distro-specific)
  ```

#### `QEMU_BIN_PATH_LIBVIRT`
- **Type:** string
- **Purpose:** Architecture and distro-specific QEMU binary path
- **Used by:** Libvirt XML templates

---

## Common Use Cases

### Use Case 1: First Time kdevops Setup (NVMe Testing)

**Problem:** Need NVMe emulation for blktests/fstests

**Solution:**
```bash
make defconfig-blktests_nvme  # Enables QEMU_BUILD by default
make qemu                      # Build QEMU with NVMe support
make bringup                   # Use built QEMU
```

### Use Case 2: CXL Testing

**Problem:** Need QEMU with CXL support (not in upstream yet)

**Solution:**
```bash
make menuconfig
# Enable: QEMU_BUILD
# Select: "https://gitlab.com/jic23/qemu.git" (jic23 fork)
make qemu
make bringup
```

### Use Case 3: QEMU Development Workflow

**Problem:** Testing QEMU patches locally before submission

**Solution:**
```bash
# Build your QEMU
cd ~/qemu
git checkout my-feature-branch
./configure --target-list=x86_64-softmmu
make -j$(nproc) && sudo make install

# Configure kdevops
cd ~/kdevops
make menuconfig
# Disable: QEMU_BUILD
# Enable: "Are you using a manually built development version of QEMU?"
make bringup  # Uses your patched QEMU
```

### Use Case 4: Minimal Setup (Basic Testing)

**Problem:** Simple kernel testing without special QEMU features

**Solution:**
```bash
sudo dnf install qemu-kvm  # Install distro package
make menuconfig
# Leave both QEMU options disabled (default)
make bringup
```

---

## Troubleshooting

### Issue: "QEMU binary not found"

**Symptoms:**
```
fatal: [localhost]: FAILED! => {"msg": "QEMU binary not found at /usr/local/bin/qemu-system-x86_64"}
```

**Diagnosis:**
- Check if `QEMU_USE_DEVELOPMENT_VERSION=y` but binary is missing
- Verify QEMU installation location matches configuration

**Solutions:**
1. If using kdevops build: Run `make qemu` to build QEMU
2. If using manual build: Verify `sudo make install` completed
3. If using distro package: Disable `QEMU_USE_DEVELOPMENT_VERSION`

### Issue: "NVMe device not supported"

**Symptoms:**
```
error: Failed to start domain: unsupported configuration: NVMe not supported by this QEMU
```

**Diagnosis:**
- Distribution QEMU package lacks NVMe support
- Using old QEMU version

**Solution:**
Enable `QEMU_BUILD` to build QEMU with NVMe support:
```bash
make menuconfig  # Enable QEMU_BUILD
make qemu
make destroy && make bringup
```

### Issue: "Wrong QEMU architecture"

**Symptoms:**
```
error: this qemu binary supports only x86_64 CPU, but host is aarch64
```

**Diagnosis:**
- `QEMU_TARGET` mismatch with host architecture
- Built wrong QEMU target

**Solution:**
```bash
make menuconfig
# Verify: QEMU_TARGET matches host architecture
make qemu        # Rebuild QEMU with correct target
```

---

## Historical Context

### Origin: March 2022 (commit c7cc051e6c1e)

**Original purpose:** Allow users to point to custom-built QEMU for development

**Initial implementation:**
```kconfig
config QEMU_USE_DEVELOPMENT_VERSION
    bool "Should we look for a development version of qemu?"
    help
      Say yes here if you are compiling your own version of qemu.
```

### Evolution: November 2022 (commit 78117410)

**Change:** CXL features required `QEMU_USE_DEVELOPMENT_VERSION`

**Rationale:** Some features (CXL) require development QEMU but users can build it themselves (not just through kdevops)

### Current: Two-Scope Design

**Implementation:**
- `if QEMU_BUILD`: Automatic flag (kdevops built QEMU)
- `if !QEMU_BUILD`: User option (manually built QEMU)

**Purpose:** Support both kdevops-managed and user-managed QEMU builds while maintaining correct binary path resolution for libvirt

---

## Technical Implementation

### Kconfig Structure

```
kconfigs/Kconfig.qemu_build:
  - QEMU_BUILD (main toggle)
  - if QEMU_BUILD:
      - Build source/version selection
      - Automatic QEMU_USE_DEVELOPMENT_VERSION=y
  - if !QEMU_BUILD:
      - User-selectable QEMU_USE_DEVELOPMENT_VERSION

kconfigs/Kconfig.libvirt:
  - QEMU_BIN_PATH (exported to Ansible)
  - QEMU_BIN_PATH_LIBVIRT (arch/distro-specific paths)
  - Uses QEMU_USE_DEVELOPMENT_VERSION for path resolution
```

### Variable Export Flow

```
Kconfig (with "output yaml")
    ↓
.extra_vars_auto.yaml
    ↓
extra_vars.yaml
    ↓
Ansible playbooks/roles
    ↓
Libvirt XML templates
```

### Binary Path Resolution Logic

```python
if QEMU_USE_DEVELOPMENT_VERSION:
    if TARGET_ARCH_X86_64:
        binary = "/usr/local/bin/qemu-system-x86_64"
    elif TARGET_ARCH_ARM64:
        binary = "/usr/local/bin/qemu-system-aarch64"
    elif TARGET_ARCH_PPC64LE:
        binary = "/usr/local/bin/qemu-system-ppc64le"
else:
    if TARGET_ARCH_X86_64:
        binary = "/usr/bin/qemu-system-x86_64"
    elif TARGET_ARCH_ARM64 and DISTRO_CENTOS:
        binary = "/usr/libexec/qemu-kvm"
    elif TARGET_ARCH_ARM64:
        binary = "/usr/bin/qemu-system-aarch64"
    elif TARGET_ARCH_PPC64LE:
        binary = "/usr/bin/qemu-system-ppc64le"
```

---

## See Also

- `kconfigs/Kconfig.qemu_build` - QEMU build configuration
- `kconfigs/Kconfig.libvirt` - Libvirt-specific QEMU settings
- `playbooks/build_qemu.yml` - QEMU build automation
- `playbooks/roles/build_qemu/` - QEMU build Ansible role
- `Makefile.build_qemu` - QEMU build Make targets
