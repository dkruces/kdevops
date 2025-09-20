# kdevops CI Commit Message Format Specification

## Overview

This document defines the commit message format for kdevops CI results archived in the kdevops-results-archive repository. The format distinguishes between **kdevops validation** (infrastructure verification with single tests) and **test results** (comprehensive testing outcomes).

## Current Implementation Status

### Current Format (As of September 2025)

The current implementation produces commit messages like:

```
linux: blktests: fix result collection and add fast CI test

This adds test results for:
  workflow: blktests
  tree: linux
  ref: v6.15
  test number: 0002
  test result: not ok

Detailed test report:

Kernel tests results:

Blktests summary:
Tests run: 2, Passed: 2, Failed: 0

Sample passed test:
```

### Legacy Implementation (fstests.yml.disabled)

The disabled fstests.yml workflow used this pattern:

```bash
# Metadata creation (lines 20-26)
echo "$(basename ${{ github.repository }})" > ci.trigger      # "kdevops"
git log -1 --pretty=format:"%s" > ci.subject                  # Commit subject
echo "not ok" > ci.result                                      # Pessimistic start
echo "Nothing to write home about." > ci.commit_extra         # Default message

# Result collection (line 66)
find workflows/fstests/results/last-run -name xunit_results.txt -type f -exec cat {} \; > ci.commit_extra || true

# Success detection (lines 67-69)
if ! grep -E "failures, [1-9]|errors, [1-9]" ci.commit_extra; then
  echo "ok" > ci.result
fi
```

## Proposed Enhanced Format Specification

### Header Format Rules

#### kdevops Validation (Single Test Execution)
```
kdevops: <workflow_name> (<tree_name> <kernel_version>)
```

#### Full Test Suite (Comprehensive Testing)
```
<workflow_name> (<tree_name> <kernel_version>): <PASS|FAIL>
```

### Workflow Name Structure and Terminology

The workflow name encodes multiple pieces of information using consistent **"section"** terminology as used in kdevops kconfig:

#### fstests Workflows
- **Format**: `<filesystem>_<section>`
- **filesystem**: `xfs`, `btrfs`, `ext4`, `tmpfs`
- **section**: Configuration profile (e.g., `reflink_4k`, `crc`, `1024`)
- **Examples**:
  - `xfs_reflink_4k` → workflow: fstests, fs: xfs, section: xfs_reflink_4k
  - `btrfs_compress` → workflow: fstests, fs: btrfs, section: btrfs_compress
  - `tmpfs_1024` → workflow: fstests, fs: tmpfs, section: tmpfs_1024

#### blktests Workflows
- **Format**: `blktests_<section>`
- **sections**: `block`, `nvme`, `meta`, `nbd`, `nvmemp`, `scsi`, `srp`, `zbd`
- **Examples**:
  - `blktests_nvme` → workflow: blktests, section: nvme
  - `blktests_scsi` → workflow: blktests, section: scsi
  - `blktests_block` → workflow: blktests, section: block

#### selftests Workflows
- **Format**: `selftests_<section>`
- **sections**: `radix`, `firmware`, `kmod`, `module`, `maple`, `sysctls`, `xarray`, `vma`
- **Examples**:
  - `selftests_kmod` → workflow: selftests, section: kmod
  - `selftests_firmware` → workflow: selftests, section: firmware
  - `selftests_xarray` → workflow: selftests, section: xarray

#### Additional Workflows (Currently Supported)

#### ai Workflows
- **Format**: `ai_<test_type>`
- **test_types**: `vector_database` (with A/B testing support)
- **Examples**:
  - `ai_vector_database` → workflow: ai, test_type: vector_database

#### mmtests Workflows
- **Format**: `mmtests_<test_type>`
- **test_types**: `thpcompact`, `thpchallenge` (memory management testing)
- **Examples**:
  - `mmtests_thpcompact` → workflow: mmtests, test_type: thpcompact
  - `mmtests_thpchallenge` → workflow: mmtests, test_type: thpchallenge

#### ltp Workflows
- **Format**: `ltp_<test_group>`
- **test_groups**: `cve`, `fcntl`, `fs`, `fs_bind`, `fs_perms_simple`, `fs_readonly`, `nfs`, `notify`, `rpc`, `smack`, and others
- **Examples**:
  - `ltp_cve` → workflow: ltp, test_group: cve
  - `ltp_fs` → workflow: ltp, test_group: fs

#### Other Supported Workflows
- **gitr**: Git regression testing
- **pynfs**: Python NFS testing
- **nfstest**: NFS testing framework
- **cxl**: CXL (Compute Express Link) testing
- **minio**: MinIO object storage testing (`minio_warp`)
- **fio-tests**: I/O performance testing
- **sysbench**: Database performance testing
- **steady_state**: Storage steady state testing

**Note**: Some workflows like `linux`, `demos`, `common`, and `kdevops` are infrastructure workflows that may not follow the standard naming patterns or may not be suitable for CI result archiving.

### Complete Enhanced Format Template

```
<HEADER>

BUILD INFO:
  Kernel: <git_describe> ("<commit_subject_wrapped>")
  Workflow: <workflow_name>
  kdevops: <hash_12> ("<commit_subject_wrapped>")
  Scope: <scope_description>
  Duration: <Xm Ys>

EXECUTION RESULTS:
  [Status: <PASS|FAIL> <✅|❌>]  # Only for full test suites
  Tests Run: <number>
  Passed: <number>
  Failed: <number>

[FAILED TESTS:]  # Only if failures exist
<test_name> - <brief_description>
...

TEST EVIDENCE:
<test_output_sample>

METADATA:
workflow: <name> | tree: <tree_name> | ref: <git_describe> |
scope: <kdevops|tests> | result: <ok|not ok>
```

### 72-Character Rule Compliance

#### Long Commit Subject Wrapping
```bash
wrap_commit_subject() {
    local subject="$1"
    if [ ${#subject} -le 68 ]; then  # 68 to account for quotes
        echo "\"$subject\""
    else
        echo "\"$subject\"" | fold -s -w 68 | sed '2,$s/^/          /'
    fi
}
```

#### Metadata Line Handling
```bash
METADATA_LINE="workflow: $CI_WORKFLOW | tree: $KERNEL_TREE | ref: $KERNEL_DESCRIBE | scope: $SCOPE_META | result: $RESULT_META"

if [ ${#METADATA_LINE} -gt 72 ]; then
    # Split into multiple lines at logical boundaries
    echo "METADATA:"
    echo "workflow: $CI_WORKFLOW | tree: $KERNEL_TREE"
    echo "ref: $KERNEL_DESCRIBE | scope: $SCOPE_META | result: $RESULT_META"
else
    echo "METADATA:"
    echo "$METADATA_LINE"
fi
```

## Implementation Examples

### Example 1: kdevops Validation (Infrastructure Verification)

**Trigger**: `TESTS=generic/003` or `LIMIT_TESTS=generic/003`

```
kdevops: xfs_reflink_4k (linux-stable v6.15-rc1-23-ga1b2c3d4)

BUILD INFO:
  Kernel: v6.15-rc1-23-ga1b2c3d4e5f6 ("mm: fix page allocation under memory
          pressure during high load conditions")
  Workflow: xfs_reflink_4k
  kdevops: 8e395d4b ("blktests: fix result collection and add fast CI test")
  Scope: kdevops validation (single test: generic/003)
  Duration: 2m 34s

EXECUTION RESULTS:
  Tests Run: 1
  Passed: 1
  Failed: 0

TEST EVIDENCE:
xfs_reflink_4k: 1 tests, 14 seconds
  generic/003  Pass     14s
Totals: 1 tests, 0 skipped, 0 failures, 0 errors, 14s

METADATA:
workflow: xfs_reflink_4k | tree: linux-stable
ref: v6.15-rc1-23-ga1b2c3d4e5f6 | scope: kdevops | result: ok
```

### Example 2: Full Test Suite with Failures

**Trigger**: No `TESTS` or `LIMIT_TESTS` parameter (full suite)

```
blktests_nvme (linux v6.15-ga1b2c3d4): FAIL

BUILD INFO:
  Kernel: v6.15-ga1b2c3d4e5f6 ("nvme: improve error handling in reset
          path for timeout scenarios")
  Workflow: blktests_nvme
  kdevops: 8e395d4b ("blktests: fix result collection and add fast CI test")
  Scope: full test suite
  Duration: 45m 12s

EXECUTION RESULTS:
  Status: FAIL ❌
  Tests Run: 87
  Passed: 85
  Failed: 2

FAILED TESTS:
nvme/019 - timeout during namespace creation
nvme/033 - unexpected reset behavior

TEST EVIDENCE:
Blktests summary:
Tests run: 87, Passed: 85, Failed: 2

Sample failed test:
status  fail
description     timeout during namespace creation
runtime 15.234s

METADATA:
workflow: blktests_nvme | tree: linux
ref: v6.15-ga1b2c3d4e5f6 | scope: tests | result: not ok
```

### Example 3: Successful selftests Validation

```
kdevops: selftests_kmod (linux-next next-20250120-ab12cd34)

BUILD INFO:
  Kernel: next-20250120-15-gab12cd34e5f6 ("kmod: add new test framework
          support for dynamic loading")
  Workflow: selftests_kmod
  kdevops: 8e395d4b ("blktests: fix result collection and add fast CI test")
  Scope: kdevops validation (single test: kmod/test_001)
  Duration: 1m 45s

EXECUTION RESULTS:
  Tests Run: 1
  Passed: 1
  Failed: 0

TEST EVIDENCE:
kmod: 1 tests, 1m 23s
  test_001  Pass     83s
Totals: 1 tests, 0 skipped, 0 failures, 0 errors, 83s

METADATA:
workflow: selftests_kmod | tree: linux-next
ref: next-20250120-15-gab12cd34e5f6 | scope: kdevops | result: ok
```

### Example 4: Memory Management Testing (mmtests)

```
mmtests_thpcompact (linux-mm v6.15-mm-ab12cd34): PASS

BUILD INFO:
  Kernel: v6.15-mm-15-gab12cd34e5f6 ("mm: improve transparent hugepage
          compaction performance")
  Workflow: mmtests_thpcompact
  kdevops: 8e395d4b ("blktests: fix result collection and add fast CI test")
  Scope: full test suite (A/B testing with baseline and dev nodes)
  Duration: 2h 15m 30s

EXECUTION RESULTS:
  Status: PASS ✅
  Tests Run: 1
  Passed: 1
  Failed: 0

TEST EVIDENCE:
mmtests thpcompact performance comparison:
  Baseline: 1.234s compaction time
  Development: 0.987s compaction time
  Improvement: 20.0% faster compaction

METADATA:
workflow: mmtests_thpcompact | tree: linux-mm
ref: v6.15-mm-15-gab12cd34e5f6 | scope: tests | result: ok
```

### Example 5: AI Vector Database Testing

```
kdevops: ai_vector_database (linux v6.15-ga1b2c3d4)

BUILD INFO:
  Kernel: v6.15-ga1b2c3d4e5f6 ("fs: optimize vector I/O operations")
  Workflow: ai_vector_database
  kdevops: 8e395d4b ("blktests: fix result collection and add fast CI test")
  Scope: kdevops validation (single test: vector_basic)
  Duration: 3m 12s

EXECUTION RESULTS:
  Tests Run: 1
  Passed: 1
  Failed: 0

TEST EVIDENCE:
Vector database performance test:
  Vector dimensions: 768
  Batch size: 1000
  Query latency: 12.5ms
  Throughput: 8,000 QPS

METADATA:
workflow: ai_vector_database | tree: linux
ref: v6.15-ga1b2c3d4e5f6 | scope: kdevops | result: ok
```

## Implementation Variables and Logic

### Core Detection Logic
```bash
# Determine execution scope based on test parameters
TESTS_PARAM="${TESTS:-${LIMIT_TESTS}}"
if [[ -n "$TESTS_PARAM" ]]; then
    SCOPE_TYPE="kdevops"
    SCOPE_DESC="kdevops validation (single test: $TESTS_PARAM)"
    HEADER_PREFIX="kdevops: "
    SHOW_STATUS=false
    SCOPE_META="kdevops"
else
    SCOPE_TYPE="tests"
    SCOPE_DESC="full test suite"
    HEADER_PREFIX=""
    SHOW_STATUS=true
    SCOPE_META="tests"
fi
```

### Workflow Mapping Logic
```bash
# Map CI_WORKFLOW to result collection logic (from scripts/ci.Makefile)
case "$CI_WORKFLOW" in
    *xfs*|*btrfs*|*ext4*|*tmpfs*|*lbs-xfs*)
        WORKFLOW_TYPE="fstests"
        ;;
    blktests*)
        WORKFLOW_TYPE="blktests"
        ;;
    selftests*|*firmware*|*modules*|*mm*)
        WORKFLOW_TYPE="selftests"
        ;;
    ai_*)
        WORKFLOW_TYPE="ai"
        ;;
    mmtests_*)
        WORKFLOW_TYPE="mmtests"
        ;;
    ltp_*)
        WORKFLOW_TYPE="ltp"
        ;;
    fio-tests*|fio_*)
        WORKFLOW_TYPE="fio-tests"
        ;;
    minio_*)
        WORKFLOW_TYPE="minio"
        ;;
    *)
        WORKFLOW_TYPE=$(echo "$CI_WORKFLOW" | cut -d'_' -f1)
        ;;
esac
```

### Kernel Version Information
```bash
# Get comprehensive kernel information
KERNEL_TREE="${{ inputs.kernel_tree }}"                      # From GitHub input
KERNEL_DESCRIBE=$(git describe --tags --always --dirty)      # v6.15-rc1-23-ga1b2c3d4
KERNEL_HASH=$(git rev-parse --short=12 HEAD)                 # a1b2c3d4e5f6
KERNEL_SUBJECT=$(git log -1 --pretty=format:"%s")            # Full commit subject

# kdevops version information
KDEVOPS_HASH=$(git rev-parse --short=12 HEAD)                # 8e395d4b
KDEVOPS_SUBJECT=$(git log -1 --pretty=format:"%s")           # kdevops commit subject
```

### Duration Calculation
```bash
# GitHub Actions built-in timing across stages
# In setup action:
echo "$(date +%s)" > ci.start_time

# In test action:
START_TIME=$(cat ci.start_time 2>/dev/null || echo $(date +%s))
END_TIME=$(date +%s)
DURATION_SEC=$((END_TIME - START_TIME))
MINUTES=$((DURATION_SEC / 60))
SECONDS=$((DURATION_SEC % 60))

if [ $MINUTES -gt 0 ]; then
    DURATION="${MINUTES}m ${SECONDS}s"
else
    DURATION="${SECONDS}s"
fi
```

### Header Construction
```bash
KERNEL_INFO="$KERNEL_TREE $KERNEL_DESCRIBE"
if [ "$SHOW_STATUS" = true ]; then
    HEADER="$CI_WORKFLOW ($KERNEL_INFO): $TEST_RESULT"
else
    HEADER="${HEADER_PREFIX}$CI_WORKFLOW ($KERNEL_INFO)"
fi
```

## Current vs Proposed Comparison

### Current Issues
1. **Unclear Purpose**: No distinction between validation and testing
2. **Missing Context**: No kernel commit hash or detailed version info
3. **Inconsistent Results**: Shows "not ok" despite 0 failures
4. **Limited Metadata**: Missing duration, kdevops version, scope
5. **Generic Headers**: No workflow-specific information in subject line

### Proposed Improvements
1. **Clear Purpose**: `kdevops:` prefix for validation vs plain headers for testing
2. **Rich Context**: Full kernel git describe + commit subject + kdevops version
3. **Accurate Results**: Proper PASS/FAIL determination based on actual failures
4. **Comprehensive Metadata**: Duration, scope, detailed version tracking
5. **Informative Headers**: Workflow name, kernel version, and result in subject

## Migration Strategy

### Phase 1: Enhanced Metadata Collection
- Implement git describe for kernel versions
- Add kdevops commit tracking
- Implement duration calculation across GitHub Actions stages

### Phase 2: Format Enhancement
- Update header generation logic
- Implement scope detection based on TESTS parameter
- Add proper PASS/FAIL logic for different contexts

### Phase 3: Validation and Rollout
- Test with debugging enabled across all workflow types
- Validate format consistency across fstests, blktests, selftests
- Deploy to production CI workflows

## Validation Rules

1. **Header Length**: Must not exceed 72 characters
2. **Metadata Wrapping**: Split at 72 characters on logical field boundaries
3. **Commit Subject Wrapping**: Wrap at word boundaries with proper indentation
4. **Scope Consistency**: `kdevops:` prefix only for validation runs (TESTS parameter present)
5. **Status Display**: PASS/FAIL only for full test suites, not validation runs
6. **Terminology**: Use "section" consistently throughout (matching kconfig)

## Future Extension Points

The format is designed for extensibility:

1. **New Workflow Types**: Add new `<workflow>_<section>` patterns
2. **Additional Metadata**: Extend metadata line with performance metrics
3. **Enhanced Evidence**: Add more detailed test output sections
4. **Build Information**: Add compiler, configuration, or environment details
5. **Performance Tracking**: Add timing, memory usage, or throughput data
6. **Cross-Reference**: Add links to related test runs or baselines

## References

- **Current Implementation**: `.github/actions/test/action.yml`
- **Legacy Format**: `.github/workflows/fstests.yml.disabled`
- **Archive Examples**: `/scratch/dagomez/linux-kdevops/kdevops-results-archive`
- **Configuration**: kdevops kconfig files for workflow sections
- **Documentation**: This specification serves as the authoritative format definition

---

*This specification was created to standardize kdevops CI commit messages and improve the clarity and usefulness of archived test results.*
