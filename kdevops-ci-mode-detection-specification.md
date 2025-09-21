# kdevops CI Mode Auto-Detection Specification

## Overview

This document defines the automatic detection strategy for distinguishing between **kdevops-ci validation** (infrastructure verification) and **workflow testing** (comprehensive kernel testing) in kdevops CI workflows.

## The Two Worlds of kdevops

### 1. kdevops-ci Validation (Framework Testing)
- **Purpose**: Verify that kdevops framework works correctly
- **Scope**: Single test to validate infrastructure and workflow execution
- **Speed**: Fast (1-3 minutes)
- **Trigger**: Pull requests, infrastructure changes, framework validation
- **Header Format**: `kdevops-ci: <workflow>: <kdevops_hash> <kdevops_subject>`
- **No PASS/FAIL**: Focus is on framework functionality, not test results
- **Example**: `kdevops-ci: xfs_reflink_4k: 26e83c6a ("guestfs: fix destroy mode issues")`

### 2. Workflow Testing (Full Test Suites)
- **Purpose**: Run comprehensive testing for kernel development and regression detection
- **Scope**: Full test suite or targeted kernel testing
- **Speed**: Long (minutes to hours)
- **Trigger**: Manual testing, scheduled runs, kernel development workflows
- **Header Format**: `<workflow> (<kernel_tree> <kernel_version>): PASS/FAIL`
- **With PASS/FAIL**: Focus is on test results and kernel validation
- **Example**: `xfs_reflink_4k (linux v6.16-ga1b2c3d4): PASS`

## Auto-Detection Strategy (Option 2)

### Detection Logic Priority

1. **GitHub Context Detection** (Highest Priority)
   ```yaml
   # Automatic kdevops-ci validation for:
   - github.event_name == 'pull_request'
   - github.event_name == 'merge_request'
   - github.ref_name contains 'feature/' or 'fix/' or 'dev/'
   - Manual workflow dispatch with repository changes to kdevops core
   ```

2. **Test Parameter Detection** (Current Implementation)
   ```bash
   # kdevops-ci validation when:
   - TESTS parameter is set (e.g., TESTS="generic/003")
   - LIMIT_TESTS parameter is set
   - Single test execution detected
   ```

3. **Manual Override** (Fallback)
   ```yaml
   # User can override via workflow inputs:
   force_full_testing: true  # Force full testing even for PRs
   force_validation: true    # Force validation even for manual runs
   ```

### Implementation Rules

#### kdevops-ci Validation Mode Triggers
```bash
VALIDATION_MODE=true when:
- github.event_name == 'pull_request' OR
- github.event_name == 'pull_request_target' OR
- TESTS parameter is non-empty OR
- LIMIT_TESTS parameter is non-empty OR
- force_validation input is true
```

#### Full Testing Mode Triggers
```bash
FULL_TESTING_MODE=true when:
- Manual workflow_dispatch without PR context AND
- No TESTS/LIMIT_TESTS parameters AND
- force_full_testing input is true OR
- Scheduled workflow runs (cron triggers)
```

### Context-Aware Test Execution

#### For kdevops-ci Validation
```bash
# GitHub Actions: Set fast test parameters
case "${{ inputs.ci_workflow }}" in
  *fstests*|*xfs*|*btrfs*|*ext4*|*tmpfs*)
    export TESTS="generic/003"        # Single fast test
    export VALIDATION_MODE="true"
    ;;
  blktests*)
    export TESTS="block/003"          # Single block test
    export VALIDATION_MODE="true"
    ;;
  selftests*)
    export TESTS="kmod/test_001"      # Single selftest
    export VALIDATION_MODE="true"
    ;;
esac
```

#### For Full Testing Mode
```bash
# GitHub Actions: No TESTS parameter = full suite
unset TESTS
unset LIMIT_TESTS
export FULL_TESTING_MODE="true"
```

## Implementation Changes Required

### 1. GitHub Actions Workflow Updates

#### File: `.github/workflows/manual.yml`
```yaml
# Add mode detection inputs
inputs:
  force_validation:
    description: 'Force kdevops-ci validation mode (single test)'
    type: boolean
    default: false
  force_full_testing:
    description: 'Force full testing mode (complete suite)'
    type: boolean
    default: false
```

#### File: `.github/actions/test/action.yml`
```yaml
# Auto-detect mode based on context
- name: Determine CI execution mode
  shell: bash
  run: |
    # Priority 1: GitHub context
    if [[ "${{ github.event_name }}" == "pull_request"* ]]; then
      echo "KDEVOPS_CI_MODE=validation" >> $GITHUB_ENV
      echo "Auto-detected: kdevops-ci validation (PR context)"

    # Priority 2: Force overrides
    elif [[ "${{ inputs.force_validation }}" == "true" ]]; then
      echo "KDEVOPS_CI_MODE=validation" >> $GITHUB_ENV
      echo "User forced: kdevops-ci validation"

    elif [[ "${{ inputs.force_full_testing }}" == "true" ]]; then
      echo "KDEVOPS_CI_MODE=full_testing" >> $GITHUB_ENV
      echo "User forced: full testing"

    # Priority 3: Default based on trigger
    elif [[ "${{ github.event_name }}" == "workflow_dispatch" ]]; then
      echo "KDEVOPS_CI_MODE=full_testing" >> $GITHUB_ENV
      echo "Auto-detected: full testing (manual dispatch)"

    else
      echo "KDEVOPS_CI_MODE=validation" >> $GITHUB_ENV
      echo "Fallback: kdevops-ci validation"
    fi

# Set test parameters based on detected mode
- name: Configure test execution based on mode
  shell: bash
  run: |
    if [[ "$KDEVOPS_CI_MODE" == "validation" ]]; then
      case "${{ inputs.ci_workflow }}" in
        *fstests*|*xfs*|*btrfs*|*ext4*|*tmpfs*)
          export TESTS="generic/003"
          ;;
        blktests*)
          export TESTS="block/003"
          ;;
        selftests*)
          export TESTS="kmod/test_001"
          ;;
      esac
      echo "TESTS=${TESTS}" >> $GITHUB_ENV
      echo "kdevops-ci validation: single test ${TESTS}"
    else
      echo "Full testing mode: complete test suite"
    fi
```

### 2. Commit Message Script Updates

#### File: `scripts/generate_ci_commit_message.sh`

```bash
# Enhanced scope detection with context awareness
determine_scope() {
    # Priority 1: Check explicit CI mode
    if [[ "${KDEVOPS_CI_MODE:-}" == "validation" ]]; then
        echo "kdevops"
        return
    fi

    # Priority 2: GitHub context detection
    if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request"* ]]; then
        echo "kdevops"
        return
    fi

    # Priority 3: Test parameter detection (backward compatibility)
    if [[ -n "${TESTS:-}" ]] || [[ -n "${LIMIT_TESTS:-}" ]]; then
        echo "kdevops"
        return
    fi

    # Default: full testing
    echo "tests"
}

# Enhanced header generation
generate_header() {
    local scope=$(determine_scope)
    local kdevops_hash=$(git rev-parse --short=12 HEAD 2>/dev/null || echo "unknown")
    local kdevops_subject=$(git log -1 --pretty=format:"%s" 2>/dev/null || echo "unknown commit")

    if [ "$scope" = "kdevops" ]; then
        # kdevops-ci validation format
        header="kdevops-ci: $CI_WORKFLOW: $kdevops_hash"
        if [[ "$kdevops_subject" != "unknown commit" ]]; then
            header="$header (\"$kdevops_subject\")"
        fi
    else
        # Full test suite format with PASS/FAIL
        local status="PASS"
        if [ "$test_result" = "not ok" ] || [ "$test_result" = "fail" ]; then
            status="FAIL"
        fi
        header="$CI_WORKFLOW ($actual_kernel_tree $kernel_describe): $status"
    fi

    echo "$header"
}
```

### 3. Environment Variable Propagation

#### All GitHub Actions must propagate mode information:
```yaml
env:
  KDEVOPS_CI_MODE: ${{ env.KDEVOPS_CI_MODE }}
  GITHUB_EVENT_NAME: ${{ github.event_name }}
  TESTS: ${{ env.TESTS }}
```

## Expected Behaviors

### Pull Request Scenario
```yaml
# Trigger: PR opened/updated
# Auto-detection: kdevops-ci validation
# Execution: TESTS="generic/003"
# Header: "kdevops-ci: xfs_reflink_4k: 26e83c6a (\"fix destroy issues\")"
# Duration: ~2 minutes
```

### Manual Dispatch Scenario
```yaml
# Trigger: Manual workflow_dispatch
# Auto-detection: Full testing (unless overridden)
# Execution: Full test suite
# Header: "xfs_reflink_4k (linux v6.16-ga1b2c3d4): PASS"
# Duration: ~30+ minutes
```

### Force Override Scenarios
```yaml
# PR with force_full_testing=true
# Result: Full testing despite PR context

# Manual with force_validation=true
# Result: Single test despite manual context
```

## Validation and Testing

### Test Matrix
1. **PR Context**: Should auto-detect validation mode
2. **Manual Context**: Should auto-detect full testing mode
3. **Force Validation**: Should override auto-detection
4. **Force Full Testing**: Should override auto-detection
5. **Legacy TESTS Parameter**: Should maintain backward compatibility

### Expected Commit Message Formats

#### kdevops-ci Validation (PR or forced)
```
kdevops-ci: xfs_reflink_4k: 26e83c6a ("guestfs: fix destroy mode issues")

BUILD INFO:
  kdevops: 26e83c6a ("guestfs: fix destroy mode issues")
  Workflow: xfs_reflink_4k
  Test: generic/003
  Kernel: v6.16 ("Linux 6.16")
  Duration: 1m 48s

EXECUTION RESULTS:
Kernel tests results:

xfs_reflink_4k: 1 tests, 17 seconds
  generic/003  Pass     14s
Totals: 1 tests, 0 skipped, 0 failures, 0 errors, 14s

METADATA:
workflow: xfs_reflink_4k | scope: kdevops | test: generic/003 | requested: v6.16 | actual: v6.16 | result: ok
```

#### Full Testing (Manual or scheduled)
```
xfs_reflink_4k (linux v6.16): PASS

BUILD INFO:
  Kernel: v6.16 ("Linux 6.16")
  Workflow: xfs_reflink_4k
  kdevops: 26e83c6a ("guestfs: fix destroy mode issues")
  Scope: full test suite
  Duration: 32m 15s

EXECUTION RESULTS:
xfs_reflink_4k: 127 tests, 1845 seconds
  generic/001  Pass     12s
  generic/002  Pass     8s
  [... 125 more tests ...]
Totals: 127 tests, 2 skipped, 0 failures, 0 errors, 1845s

METADATA:
workflow: xfs_reflink_4k | tree: linux | ref: v6.16 | scope: tests | result: ok
```

## Benefits of Auto-Detection

1. **Smart Defaults**: No user decision required for common cases
2. **Context Awareness**: PRs automatically get fast validation
3. **Flexibility**: Manual override available when needed
4. **Backward Compatibility**: Existing TESTS parameter still works
5. **Clear Intent**: Headers clearly distinguish between validation and testing
6. **Performance**: PRs get fast feedback, manual runs get comprehensive testing

## Migration Strategy

### Phase 1: Implement Auto-Detection Logic
- Add mode detection to GitHub Actions
- Update commit message script
- Maintain backward compatibility

### Phase 2: Test and Validate
- Test PR scenarios with auto-validation
- Test manual scenarios with auto-full-testing
- Validate force override functionality

### Phase 3: Document and Deploy
- Update documentation
- Deploy to production workflows
- Monitor and refine detection logic

---

*This specification enables intelligent CI mode selection while maintaining explicit control when needed, providing the best of both automated convenience and manual flexibility.*