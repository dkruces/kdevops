#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

# Generate enhanced CI commit message for kdevops-results-archive
# This script creates commit messages following the kdevops CI format specification

set -euo pipefail

# Default values
CI_WORKFLOW="${CI_WORKFLOW:-demo}"
KERNEL_TREE="${KERNEL_TREE:-linux}"
TESTS_PARAM="${TESTS:-${LIMIT_TESTS:-}}"
DURATION="${DURATION:-unknown}"

# Input files (expected to be created by GitHub Actions)
CI_COMMIT_EXTRA="${CI_COMMIT_EXTRA:-ci.commit_extra}"
CI_RESULT="${CI_RESULT:-ci.result}"
CI_START_TIME="${CI_START_TIME:-ci.start_time}"
CI_REF="${CI_REF:-ci.ref}"
CI_TRIGGER="${CI_TRIGGER:-ci.trigger}"

# Helper function to wrap long commit subjects at 72 chars
wrap_commit_subject() {
    local subject="$1"
    if [ ${#subject} -le 68 ]; then  # 68 to account for quotes
        echo "\"$subject\""
    else
        echo "\"$subject\"" | fold -s -w 68 | sed '2,$s/^/          /'
    fi
}

# Calculate duration if start time available
calculate_duration() {
    if [ -f "$CI_START_TIME" ]; then
        local start_time=$(cat "$CI_START_TIME" 2>/dev/null || echo $(date +%s))
        local end_time=$(date +%s)
        local duration_sec=$((end_time - start_time))
        local minutes=$((duration_sec / 60))
        local seconds=$((duration_sec % 60))

        if [ $minutes -gt 0 ]; then
            echo "${minutes}m ${seconds}s"
        else
            echo "${seconds}s"
        fi
    else
        echo "unknown"
    fi
}

# Determine scope and header format
determine_scope() {
    # Debug output for troubleshooting
    echo "DEBUG: TESTS='${TESTS:-}'" >&2
    echo "DEBUG: LIMIT_TESTS='${LIMIT_TESTS:-}'" >&2
    echo "DEBUG: TESTS_PARAM='${TESTS_PARAM:-}'" >&2

    # Check for any test parameter indicating validation mode
    if [[ -n "${TESTS:-}" ]] || [[ -n "${LIMIT_TESTS:-}" ]] || [[ -n "${TESTS_PARAM:-}" ]]; then
        echo "DEBUG: Detected kdevops validation mode" >&2
        echo "kdevops"
    else
        echo "DEBUG: Detected full test suite mode" >&2
        echo "tests"
    fi
}

# Get kernel information
get_kernel_info() {
    # Try to get git describe from linux directory, fallback gracefully
    local kernel_describe="unknown"
    local kernel_hash="unknown"
    local kernel_subject="unknown commit"

    if [ -d "linux/.git" ]; then
        kernel_describe=$(cd linux && git describe --tags --always --dirty 2>/dev/null || echo "unknown")
        kernel_hash=$(cd linux && git rev-parse --short=12 HEAD 2>/dev/null || echo "unknown")
        kernel_subject=$(cd linux && git log -1 --pretty=format:"%s" 2>/dev/null || echo "unknown commit")
    fi

    echo "$kernel_describe|$kernel_hash|$kernel_subject"
}

# Get kdevops information (from kdevops directory context)
get_kdevops_info() {
    # This will be run from the kdevops directory
    local kdevops_hash=$(git rev-parse --short=12 HEAD 2>/dev/null || echo "unknown")
    local kdevops_subject=$(git log -1 --pretty=format:"%s" 2>/dev/null || echo "unknown commit")

    echo "$kdevops_hash|$kdevops_subject"
}

# Read test results
get_test_results() {
    local result_content=""
    local test_result="unknown"

    if [ -f "$CI_COMMIT_EXTRA" ]; then
        result_content=$(cat "$CI_COMMIT_EXTRA")
    else
        result_content="No test results available."
    fi

    if [ -f "$CI_RESULT" ]; then
        test_result=$(cat "$CI_RESULT" | tr -d '\n' | tr -d '\r')
    fi

    echo "$test_result|$result_content"
}

# Determine workflow type for result formatting
get_workflow_type() {
    case "$CI_WORKFLOW" in
        *xfs*|*btrfs*|*ext4*|*tmpfs*|*lbs-xfs*) echo "fstests" ;;
        blktests*) echo "blktests" ;;
        selftests*|*firmware*|*modules*|*mm*) echo "selftests" ;;
        ai_*) echo "ai" ;;
        mmtests_*) echo "mmtests" ;;
        ltp_*) echo "ltp" ;;
        fio-tests*|fio_*) echo "fio-tests" ;;
        minio_*) echo "minio" ;;
        *) echo "other" ;;
    esac
}

# Generate the enhanced commit message
generate_commit_message() {
    local scope=$(determine_scope)
    local workflow_type=$(get_workflow_type)
    local duration=$(calculate_duration)

    # Get kernel tree and ref from metadata files
    local actual_kernel_tree="$KERNEL_TREE"
    local actual_kernel_ref="unknown"

    if [ -f "$CI_TRIGGER" ]; then
        actual_kernel_tree=$(cat "$CI_TRIGGER" | tr -d '\n' | tr -d '\r')
    fi

    if [ -f "$CI_REF" ]; then
        actual_kernel_ref=$(cat "$CI_REF" | tr -d '\n' | tr -d '\r')
    fi

    # Get kernel info (this assumes we're in the kernel directory context)
    local kernel_info=$(get_kernel_info)
    local kernel_describe=$(echo "$kernel_info" | cut -d'|' -f1)
    local kernel_hash=$(echo "$kernel_info" | cut -d'|' -f2)
    local kernel_subject=$(echo "$kernel_info" | cut -d'|' -f3)

    # Use metadata ref if available, fallback to git describe
    # Ensure we use the most accurate kernel version consistently
    if [ "$actual_kernel_ref" != "unknown" ] && [ "$actual_kernel_ref" != "" ]; then
        kernel_describe="$actual_kernel_ref"
    fi

    # Debug kernel version information
    echo "DEBUG: kernel_describe from git: $(cd linux && git describe --tags --always --dirty 2>/dev/null || echo 'unknown')" >&2
    echo "DEBUG: actual_kernel_ref from CI: $actual_kernel_ref" >&2
    echo "DEBUG: final kernel_describe: $kernel_describe" >&2

    # Get kdevops info (this assumes we can access kdevops directory)
    local kdevops_info=$(get_kdevops_info)
    local kdevops_hash=$(echo "$kdevops_info" | cut -d'|' -f1)
    local kdevops_subject=$(echo "$kdevops_info" | cut -d'|' -f2)

    # Get test results
    local results_info=$(get_test_results)
    local test_result=$(echo "$results_info" | cut -d'|' -f1)
    local result_content=$(echo "$results_info" | cut -d'|' -f2-)

    # Build header
    local header=""
    if [ "$scope" = "kdevops" ]; then
        # kdevops-ci validation format: focus on kdevops commit being tested
        header="kdevops-ci: $CI_WORKFLOW: $kdevops_hash $kdevops_subject"
    else
        # Full test suite format: include PASS/FAIL status
        local status="PASS"
        if [ "$test_result" = "not ok" ] || [ "$test_result" = "fail" ]; then
            status="FAIL"
        fi
        header="$CI_WORKFLOW ($actual_kernel_tree $kernel_describe): $status"
    fi

    # Build scope description
    local scope_desc=""
    if [ "$scope" = "kdevops" ]; then
        local test_param="${TESTS:-${LIMIT_TESTS:-${TESTS_PARAM:-}}}"
        if [[ -n "$test_param" ]]; then
            scope_desc="kdevops validation (single test: $test_param)"
        else
            scope_desc="kdevops validation"
        fi
    else
        scope_desc="full test suite"
    fi

    # Wrap kernel commit subject
    local wrapped_kernel_subject=$(wrap_commit_subject "$kernel_subject")
    local wrapped_kdevops_subject=$(wrap_commit_subject "$kdevops_subject")

    # Generate metadata line with 72-char handling
    local metadata_line="workflow: $CI_WORKFLOW | tree: $actual_kernel_tree | ref: $kernel_describe | scope: $scope | result: $test_result"
    local metadata_output=""
    if [ ${#metadata_line} -gt 72 ]; then
        metadata_output="workflow: $CI_WORKFLOW | tree: $actual_kernel_tree"$'\n'"ref: $kernel_describe | scope: $scope | result: $test_result"
    else
        metadata_output="$metadata_line"
    fi

    # Build kernel validation info
    local kernel_info_line=""
    if [ "$actual_kernel_ref" != "unknown" ] && [ "$kernel_describe" != "$actual_kernel_ref" ]; then
        # Show both requested and actual if they differ
        kernel_info_line="  Kernel: $actual_kernel_ref (requested) → $kernel_describe (actual)"
    else
        # Show just the kernel version if they match or no metadata
        kernel_info_line="  Kernel: $kernel_describe"
    fi

    # Build the complete commit message based on scope
    if [ "$scope" = "kdevops" ]; then
        # kdevops-ci validation format
        cat << EOF
$header

BUILD INFO:
  kdevops: $kdevops_hash ($wrapped_kdevops_subject)
  Workflow: $CI_WORKFLOW
  Test: $TESTS
$kernel_info_line
  Duration: $duration

EXECUTION RESULTS:
$result_content

METADATA:
workflow: $CI_WORKFLOW | scope: kdevops | test: $TESTS | requested: $actual_kernel_ref | actual: $kernel_describe | result: $test_result
EOF
    else
        # Full test suite format
        cat << EOF
$header

BUILD INFO:
$kernel_info_line ($wrapped_kernel_subject)
  Workflow: $CI_WORKFLOW
  kdevops: $kdevops_hash ($wrapped_kdevops_subject)
  Scope: $scope_desc
  Duration: $duration

EXECUTION RESULTS:
$result_content

METADATA:
$metadata_output | requested: $actual_kernel_ref | actual: $kernel_describe
EOF
    fi
}

# Main execution
main() {
    # Validate required environment
    if [ -z "$CI_WORKFLOW" ]; then
        echo "Error: CI_WORKFLOW environment variable is required" >&2
        exit 1
    fi

    generate_commit_message
}

# Run main function
main "$@"