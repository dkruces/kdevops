# QEMU Build Module Refactoring Plan

## Goal
Convert QEMU build module from old `extra_vars.yaml` + Makefile variable injection method to modern `.extra_vars_auto.yaml` method using kconfig's `output yaml` directive.

## Current State Analysis

### Two Methods in kdevops

#### Old Method (`extra_vars.yaml`)
1. **Makefile** extracts values from `.config` using `$(subst ",,$(CONFIG_VAR))`
2. **Makefile** appends variables to `ANSIBLE_EXTRA_ARGS`
3. **Makefile.extra_vars** processes these and writes to `extra_vars.yaml`
4. Role `defaults/main.yml` provides fallback values
5. **Problem**: Complex, error-prone, mixes responsibilities

#### New Method (`.extra_vars_auto.yaml`)
1. **Kconfig** variables marked with `output yaml` directive
2. **kconfig** directly writes to `.extra_vars_auto.yaml`
3. **Makefile.extra_vars** copies `.extra_vars_auto.yaml` to `extra_vars.yaml` as first step
4. Role defaults only used if kconfig doesn't provide value
5. **Benefit**: Single source of truth, declarative, cleaner

### Current QEMU Module State

**Files Involved:**
- `kconfigs/Kconfig.libvirt` - QEMU configuration (mixed with libvirt)
- `Makefile.build_qemu` - QEMU-specific Makefile targets
- `playbooks/build_qemu.yml` - Playbook entry point
- `playbooks/roles/build_qemu/` - Ansible role

**Current Variable Flow:**

```
.config (kconfig output)
    ↓
Makefile.build_qemu extracts:
  - CONFIG_QEMU_BUILD_GIT → QEMU_GIT
  - CONFIG_QEMU_BUILD_GIT_VERSION → QEMU_GIT_VERSION
  - CONFIG_QEMU_BUILD_GIT_DATA_PATH → QEMU_DATA
  - CONFIG_TARGET_ARCH_* → qemu_target
    ↓
ANSIBLE_EXTRA_ARGS += QEMU_BUILD_SETUP_ARGS
    ↓
Makefile.extra_vars processes
    ↓
extra_vars.yaml contains:
  qemu_build: True
  qemu_git: /mirror/qemu.git
  qemu_data: "{{local_dev_path}}/qemu"
  qemu_version: v10.1.0
  qemu_target: aarch64-softmmu
    ↓
Ansible role reads these OR falls back to role/defaults/main.yml
```

**Issues with Current State:**
1. ❌ Makefile duplicates arch logic (lines 14-20) that kconfig already knows
2. ❌ Variable name transformation done in Makefile (CONFIG_X → ansible_var)
3. ❌ Role defaults/main.yml has hardcoded fallbacks that can conflict
4. ❌ **PARTIALLY FIXED**: Recent changes added `output yaml` to some QEMU variables but Makefile.build_qemu still does old-style extraction

### Reference: fstests Conversion (commit 4947aefdab7c)

**What was done:**
1. Added `output yaml` to 11 kconfig variables
2. Removed 46 lines of Makefile variable extraction/transformation
3. Kconfig variables automatically exported to `.extra_vars_auto.yaml`
4. No changes needed to playbooks/roles (variable names stayed same)

**Pattern:**
```diff
 config FSTESTS_GIT
    string "The fstests git tree to clone"
+   output yaml
    default DEFAULT_FSTESTS_HTTPS_URL
```

```diff
-FSTESTS_GIT:=$(subst ",,$(CONFIG_FSTESTS_GIT))
-FSTESTS_ARGS += fstests_git=$(FSTESTS_GIT)
+(removed - kconfig handles it)
```

## Refactoring Plan for QEMU

### Phase 1: Identify All QEMU Variables

**Currently in Makefile.build_qemu:**
- `qemu_build` (line 4)
- `qemu_git` (lines 6, 10)
- `qemu_data` (lines 8, 11)
- `qemu_version` (lines 7, 12)
- `qemu_target` (lines 14-20)

**Currently in Kconfig.libvirt (after recent changes):**
- ✅ `QEMU_BUILD` → `qemu_build` (HAS output yaml)
- ✅ `QEMU_BUILD_GIT` → `qemu_build_git` (HAS output yaml)
- ✅ `QEMU_BUILD_GIT_DATA_PATH` → `qemu_build_git_data_path` (HAS output yaml)
- ✅ `QEMU_BUILD_GIT_VERSION` → `qemu_build_git_version` (HAS output yaml)
- ✅ `QEMU_TARGET` → `qemu_target` (HAS output yaml)

**Variable Name Mismatch Problem:**
- Kconfig exports: `qemu_build_git`, `qemu_build_git_data_path`, `qemu_build_git_version`
- Makefile creates: `qemu_git`, `qemu_data`, `qemu_version`
- Playbook recently updated to use: `qemu_build_git`, `qemu_build_git_data_path`, `qemu_build_git_version`
- **Status**: Already aligned in recent commits!

### Phase 2: Remove Makefile Variable Extraction

**Files to modify:**

#### 1. `Makefile.build_qemu`

**Current (lines 3-20):**
```makefile
QEMU_BUILD_SETUP_ARGS :=
QEMU_BUILD_SETUP_ARGS += qemu_build=True

QEMU_GIT:=$(subst ",,$(CONFIG_QEMU_BUILD_GIT))
QEMU_GIT_VERSION:=$(subst ",,$(CONFIG_QEMU_BUILD_GIT_VERSION))
QEMU_DATA:=$(subst ",,$(CONFIG_QEMU_BUILD_GIT_DATA_PATH))

QEMU_BUILD_SETUP_ARGS += qemu_git=$(QEMU_GIT)
QEMU_BUILD_SETUP_ARGS += qemu_data=\"$(QEMU_DATA)\"
QEMU_BUILD_SETUP_ARGS += qemu_version='$(QEMU_GIT_VERSION)'

ifeq (y,$(CONFIG_TARGET_ARCH_X86_64))
QEMU_BUILD_SETUP_ARGS += qemu_target="x86_64-softmmu"
endif

ifeq (y,$(CONFIG_TARGET_ARCH_PPC64LE))
QEMU_BUILD_SETUP_ARGS += qemu_target="ppc64-softmmu"
endif
```

**Proposed (remove lines 3-20 entirely):**
```makefile
# QEMU variables now come from kconfig output yaml
# See kconfigs/Kconfig.libvirt for QEMU_BUILD, QEMU_BUILD_GIT,
# QEMU_BUILD_GIT_DATA_PATH, QEMU_BUILD_GIT_VERSION, QEMU_TARGET
```

**Current (line 57):**
```makefile
ANSIBLE_EXTRA_ARGS += $(QEMU_BUILD_SETUP_ARGS)
```

**Proposed:**
```makefile
# Remove line 57 - no longer needed
```

**Result:** Remove ~15 lines of Makefile code

#### 2. `kconfigs/Kconfig.libvirt`

**Verify all QEMU variables have `output yaml`:**

```kconfig
config QEMU_BUILD
    bool "Should we build QEMU for you?"
    output yaml  # ✅ CONFIRMED

config QEMU_BUILD_GIT
    string "Git tree for QEMU to clone on localhost"
    output yaml  # ✅ CONFIRMED

config QEMU_BUILD_GIT_DATA_PATH
    string "The destination directory where to clone the QEMU git tree"
    output yaml  # ✅ CONFIRMED

config QEMU_BUILD_GIT_VERSION
    string "The version of QEMU to build"
    output yaml  # ✅ CONFIRMED

config QEMU_TARGET
    string "QEMU target architecture to build"
    output yaml  # ✅ CONFIRMED
```

**Action:** None needed - already complete from recent commits

#### 3. `playbooks/roles/build_qemu/defaults/main.yml`

**Current:**
```yaml
qemu_build: false
qemu_force_install_if_present: false
qemu_bin_path: "/usr/local/bin/qemu-system-aarch64"
qemu_build_git_data_path: "{{ data_path }}/qemu"
qemu_build_git: "https://gitlab.com/qemu-project/qemu.git"
qemu_build_git_version: "v10.1.0"
qemu_build_dir: "{{ qemu_build_git_data_path }}/build"
qemu_target: "aarch64-softmmu"
```

**Proposed:**
```yaml
# Defaults only for variables NOT in kconfig
# Most QEMU config comes from kconfig output yaml - see kconfigs/Kconfig.libvirt
qemu_force_install_if_present: false
qemu_build_dir: "{{ qemu_build_git_data_path }}/build"
```

**Rationale:**
- `qemu_build`, `qemu_build_git`, `qemu_build_git_data_path`, `qemu_build_git_version`, `qemu_target` → all from kconfig
- `qemu_bin_path` → from kconfig (QEMU_BIN_PATH_LIBVIRT has output yaml)
- `qemu_force_install_if_present` → role-specific, not in kconfig (keep)
- `qemu_build_dir` → derived variable (keep)

**Action:** Clean up redundant defaults

### Phase 3: Testing & Validation

**Test Scenarios:**

1. **Clean build test:**
   ```bash
   make mrproper
   make defconfig-blktests_nvme
   make qemu
   # Verify: correct arch, correct version, correct repo
   ```

2. **Variable verification:**
   ```bash
   # Check .extra_vars_auto.yaml has qemu vars
   grep qemu .extra_vars_auto.yaml

   # Check extra_vars.yaml has qemu vars
   grep qemu extra_vars.yaml

   # Verify no duplication
   ```

3. **Cross-architecture test:**
   ```bash
   # Test on x86_64 host
   make defconfig-blktests
   grep qemu_target extra_vars.yaml  # Should be x86_64-softmmu

   # Test on ARM64 host
   make defconfig-blktests_nvme
   grep qemu_target extra_vars.yaml  # Should be aarch64-softmmu
   ```

4. **Different QEMU source test:**
   ```bash
   # Test upstream QEMU
   make menuconfig  # Select QEMU_BUILD_UPSTREAM
   make qemu

   # Test jic23 fork
   make menuconfig  # Select QEMU_BUILD_JIC23
   make qemu
   ```

### Phase 4: Documentation

**Update files:**

1. **`Makefile.build_qemu`** - Add header comment explaining new approach
2. **`playbooks/roles/build_qemu/README.md`** (if exists) - Document kconfig variables
3. **`kconfigs/Kconfig.libvirt`** - Improve help text for QEMU variables

### Benefits of Refactoring

✅ **Simplicity**: Remove ~15 lines of Makefile boilerplate
✅ **Correctness**: Single source of truth (kconfig)
✅ **Maintainability**: Changes only in one place (Kconfig)
✅ **Consistency**: Same pattern as fstests, blktests, etc.
✅ **Type Safety**: Kconfig validates types, Makefile doesn't
✅ **Documentation**: Kconfig help text serves as inline docs

### Migration Checklist

- [x] Add `output yaml` to all QEMU kconfig variables (done in recent commits)
- [x] Update playbook to use kconfig variable names (done in recent commits)
- [ ] Remove Makefile variable extraction from `Makefile.build_qemu`
- [ ] Remove ANSIBLE_EXTRA_ARGS injection for QEMU
- [ ] Clean up role defaults/main.yml
- [ ] Test on ARM64
- [ ] Test on x86_64
- [ ] Test with different QEMU sources (upstream vs jic23)
- [ ] Document the changes

### Risks & Mitigation

**Risk**: Variable names might not match between kconfig and Ansible
**Mitigation**: Already addressed - recent commits aligned names

**Risk**: Derived variables (like `qemu_build_dir`) might break
**Mitigation**: Keep derived variables in role defaults

**Risk**: Conditional logic in Makefile might be needed
**Mitigation**: Kconfig already handles conditionals (default ... if ...)

### Timeline

**Phase 1**: Audit ✅ (Complete - done in this planning session)
**Phase 2**: Implementation (1-2 commits)
  - Commit 1: Remove Makefile extraction
  - Commit 2: Clean up role defaults
**Phase 3**: Testing (validate all scenarios)
**Phase 4**: Documentation (update comments/READMEs)

### Related Work

This refactoring aligns with the broader kdevops effort to:
- Phase out `extra_vars.yaml` Makefile generation
- Standardize on `output yaml` kconfig directive
- Reduce Makefile complexity
- Improve maintainability

**Reference commits:**
- 48cf915ae: Introduced selective yamlconfig
- 4947aefdab7c: fstests conversion example
- f60c8defe6d9: workflows/Makefile cleanup
- 3655e5e6a86a: guestfs.Makefile conversion

---

**Status**: Ready for implementation
**Complexity**: Low (fstests pattern is proven)
**Impact**: Medium (simplifies QEMU build significantly)
