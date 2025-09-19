# fstests/XFS Manual Integration Analysis

## Overview
Analysis for adding fstests/XFS support to manual.yml workflow, following the existing modular GitHub Actions structure.

## Current State Assessment

### ✅ What Works Well
1. **Modular Actions Structure**: Clean 3-action setup (setup/test/cleanup)
2. **XFS Defconfigs Available**: 35+ XFS configurations in defconfigs/
3. **Test Action Intelligence**: Already routes XFS workflows to workflows/fstests (line 36)
4. **Manual.yml Framework**: Simple, extensible choice-based interface

### ❌ Critical Issues Found
1. **Missing Archive Action**:
   - main.yml:64 references `./.github/actions/archive` that doesn't exist
   - This breaks the main.yml workflow completely

2. **Setup Action Bug**:
   - setup/action.yml:64 references undefined `${{ inputs.kdevops_defconfig }}`
   - This input is not declared in the action inputs section

### 🔍 Key Insights
- fstests.yml.disabled uses direct make targets (not modular actions)
- Current manual.yml only has 1 XFS option: `linux-xfs-kpd` (symlinked to basic `xfs`)
- Test action already routes XFS workflows to `workflows/fstests` correctly
- Target configuration: `xfs_reflink_4k` (matches disabled fstests.yml)

## Implementation Plan

### Priority 1: Fix Missing Archive Action
**Problem**: main.yml references non-existent archive action
**Solution**: Create `.github/actions/archive/action.yml`
**Source**: Extract logic from fstests.yml.disabled (lines 84-92)

### Priority 2: Fix Setup Action Input Bug
**Problem**: Undefined input reference breaks workflow
**Solution**: Remove undefined `${{ inputs.kdevops_defconfig }}` reference
**Location**: setup/action.yml:64

### Priority 3: Add XFS Defconfigs to Manual.yml
**Goal**: Add all available XFS configurations as choices
**Count**: 35+ XFS defconfigs available
**Focus**: Include `xfs_reflink_4k` for CI testing

## Available XFS Defconfigs

### Core XFS Variants
- `xfs` - Basic XFS configuration
- `xfs_reflink_4k` - **Target config for CI** (matches fstests.yml.disabled)
- `xfs_crc` / `xfs_nocrc` - CRC enabled/disabled variants

### Size/Block Variants
- `xfs_nocrc_1k`, `xfs_nocrc_2k`, `xfs_nocrc_4k`, `xfs_nocrc_512`
- `xfs_nocrc_16k_4ks`, `xfs_nocrc_32_4ks`, `xfs_nocrc_64_4ks`, `xfs_nocrc_8k_4ks`

### Reflink Variants
- `xfs_reflink` - Basic reflink support
- `xfs_reflink_1024`, `xfs_reflink_2k`, `xfs_reflink_4k`
- `xfs_reflink_16k_4ks`, `xfs_reflink_32k_4ks`, `xfs_reflink_64k_4ks`
- `xfs_reflink_4k_8ks`, `xfs_reflink_dir_bsize_8k`
- `xfs_reflink_lbs`, `xfs_reflink_logdev`, `xfs_reflink_normapbt`
- `xfs_reflink_nrext64`, `xfs_reflink_stripe_len`

### Device/Feature Variants
- `xfs_crc_logdev`, `xfs_crc_rtdev`
- `xfs_crc_rtdev_extsize_28k`, `xfs_crc_rtdev_extsize_64k`
- `xfs_nocrc_lbs`, `xfs-soak`

### Large Block Size (LBS) Variants
- `lbs-xfs`, `lbs-xfs-small`
- `lbs-xfs-bdev-nvme`, `lbs-xfs-bdev-large-nvme`

## Technical Architecture Review

### Current Modular Structure (Keep)
```
.github/actions/
├── setup/action.yml    ✅ Environment preparation
├── test/action.yml     ✅ Test execution & routing
└── cleanup/action.yml  ✅ Resource cleanup
```

### Workflow Integration (Keep)
```
manual.yml → main.yml → setup → test → archive → cleanup
```

### Test Action Routing Logic (Works)
```yaml
case "${{ inputs.ci_workflow }}" in
  *xfs*) wpath="workflows/fstests" ;;  # ✅ Already handles XFS
```

## Changes Required

### 1. Create Archive Action
**File**: `.github/actions/archive/action.yml`
**Content**: Extract from fstests.yml.disabled archive logic

### 2. Fix Setup Action Bug
**File**: `.github/actions/setup/action.yml`
**Line 64**: Remove `${{ inputs.kdevops_defconfig }}` reference

### 3. Extend Manual.yml Choices
**File**: `.github/workflows/manual.yml`
**Add**: All XFS defconfig options to choice list

## Expected Outcome
- ✅ Fixed main.yml workflow (archive action available)
- ✅ Working setup action (no undefined inputs)
- ✅ 35+ XFS configurations available via manual.yml
- ✅ `xfs_reflink_4k` ready for CI testing
- ✅ Maintains existing modular architecture

## CI_WORKFLOW Parameter Deep Dive

### Why CI_WORKFLOW is Critical

The `CI_WORKFLOW` parameter is the backbone of kdevops standardization:

1. **Standardized Commands**: Regardless of workflow (fstests, blktests, selftests), the same make targets are used:
   - `make ci-build-test CI_WORKFLOW=<name>`
   - `make ci-test CI_WORKFLOW=<name>`
   - `make ci-archive CI_WORKFLOW=<name>`

2. **Dynamic Resolution**: `scripts/ci.Makefile` uses `CI_WORKFLOW` to:
   ```bash
   CI_WORKFLOW_BASENAME := $(shell basename $(CI_WORKFLOW))
   ```

3. **File-Based Configuration**: The `.ci/` directory structure defines what each workflow does:
   ```
   .ci/
   ├── build-test/
   │   ├── fstests      # "make fstests"
   │   ├── blktests     # "make blktests"
   │   └── selftests    # "make selftests"
   ├── test/
   │   ├── fstests      # "make fstests-baseline"
   │   ├── blktests     # "make blktests-baseline"
   │   └── selftests    # "make selftests"
   └── results/
       ├── fstests      # Lists result paths for archival
       ├── blktests     # workflows/blktests/results/, etc.
       └── selftests    # workflows/selftests/results/, etc.
   ```

### Archive Workflow Architecture

The archive process is **CI_WORKFLOW-agnostic**:

1. **scripts/archive.Makefile**: Handles archival via ansible playbook
   ```bash
   ci-archive:
       ansible-playbook playbooks/kdevops_archive.yml \
           --extra-vars=@./extra_vars.yaml
   ```

2. **No CI_WORKFLOW Logic**: Archive doesn't use `.ci/` files directly
   - Archive playbook reads from `extra_vars.yaml`
   - All workflow results are collected systematically
   - Results paths are determined by kdevops configuration, not CI_WORKFLOW

3. **V=1 Importance**: Verbose output shows:
   - Exact make commands being executed
   - Ansible playbook verbose output
   - Critical for debugging CI issues

### XFS Workflow Integration

For XFS support, the CI_WORKFLOW flow will be:

1. **manual.yml**: User selects `xfs_reflink_4k`
2. **CI_WORKFLOW**: Becomes `xfs_reflink_4k`
3. **ci.Makefile**: Resolves to basename `xfs_reflink_4k`
4. **Execution**:
   - `ci-build-test` → reads `.ci/build-test/fstests` → `make fstests`
   - `ci-test` → reads `.ci/test/fstests` → `make fstests-baseline`
   - `ci-archive` → runs ansible archival (CI_WORKFLOW passed for metadata)

### Key Insight: fstests Mapping

All XFS defconfigs map to the same `.ci/` files:
- `xfs`, `xfs_reflink_4k`, `xfs_crc`, etc. → **same** `.ci/*/fstests` files
- The specific XFS variant is handled by the **defconfig**, not the CI workflow
- CI_WORKFLOW for all XFS variants should resolve to `fstests`

## Implementation Notes
- Each fix should be atomic commit
- Follow CLAUDE.md commit formatting (Generated-by: Claude AI / Signed-off-by:)
- Test each change independently
- **Always use V=1**: Critical for debugging and transparency
- **CI_WORKFLOW parameter**: Essential for standardized execution
- No major refactoring needed - architecture is sound
