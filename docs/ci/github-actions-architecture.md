# GitHub Actions Concurrent Architecture for kdevops

## Executive Summary

This document outlines the architectural solution for implementing concurrent, isolated GitHub Actions workflows in kdevops. The solution addresses fundamental limitations in GitHub Actions while providing true run isolation and efficient resource usage.

## Problem Statement

### Original Challenge
kdevops requires multiple concurrent CI workflows that can run independently without interference. Each workflow needs:

1. **Isolation**: Separate working directories per workflow run
2. **Concurrency**: Multiple workflows on the same runner without conflicts  
3. **Efficiency**: Minimal resource overhead
4. **Reliability**: No leftover artifacts from previous runs

### GitHub Actions Limitations Discovered

#### 1. Dynamic Paths in `uses:` Fields
**Limitation**: GitHub Actions `uses:` field cannot contain dynamic expressions.

```yaml
# ❌ This FAILS - dynamic expressions not allowed
uses: ./run-${{ github.run_id }}/.github/actions/setup

# ✅ This WORKS - static paths only
uses: ./.github/actions/setup
```

**Impact**: Cannot directly use unique directory names for action file locations.

#### 2. Action Resolution Timing
**Limitation**: GitHub Actions resolves all `uses:` references before workflow execution begins.

**Impact**: Actions must be discoverable at static paths before any workflow steps run, preventing dynamic action directory strategies.

#### 3. Checkout Path vs Action Discovery
**Limitation**: When using `actions/checkout@v4` with `path:` parameter, actions are not found at workspace root.

```yaml
# This creates run-123/repo but actions look in workspace/.github/actions
- uses: actions/checkout@v4
  with:
    path: run-${{ github.run_id }}
```

**Impact**: Creates conflict between isolation (custom paths) and action discovery (workspace root).

## Architectural Solution: Single Checkout + Dynamic Symlinks

### Core Concept
Use a single full repository checkout per workflow run combined with dynamically updated symlinks to solve the action discovery problem.

### Architecture Components

#### 1. Unique Working Directories
```yaml
path: ${{ inputs.ci_workflow }}-${{ github.run_id }}
```
- **Format**: `{workflow-name}-{run-id}` (e.g., `fstests-17990251359`)
- **Benefits**: 
  - True isolation per workflow run
  - Easy identification of running workflows
  - Natural cleanup based on run completion

#### 2. Dynamic Symlink Strategy
```yaml
- name: Ensure correct action symlink
  run: ln -sf "${{ inputs.ci_workflow }}-${{ github.run_id }}/.github/actions" ./actions

- name: Use action with static path
  uses: ./actions/setup
```

**Key Insight**: Update symlink before each action step to handle concurrent runner usage.

#### 3. Per-Step Symlink Updates
```yaml
steps:
  - name: Checkout isolated
    uses: actions/checkout@v4
    with:
      path: workflow-${{ github.run_id }}
      clean: true

  - name: Update symlink (step 1)
    run: ln -sf "workflow-${{ github.run_id }}/.github/actions" ./actions
  - uses: ./actions/setup

  - name: Update symlink (step 2)  
    run: ln -sf "workflow-${{ github.run_id }}/.github/actions" ./actions
  - uses: ./actions/test

  - name: Update symlink (step 3)
    run: ln -sf "workflow-${{ github.run_id }}/.github/actions" ./actions
  - uses: ./actions/cleanup
```

### Concurrency Handling

#### Race Condition Scenario
1. **Workflow A** (fstests-123) starts, creates symlink to its actions
2. **Workflow B** (blktests-456) starts on same runner, updates symlink to its actions  
3. **Workflow A** continues but now uses Workflow B's action files

#### Solution: Per-Step Symlink Updates
- Update symlink immediately before each action usage
- Ensures each step uses correct action files regardless of interference
- No blocking or coordination required between workflows

### Benefits of This Architecture

#### 1. True Concurrency
- ✅ Multiple workflows can run on same runner
- ✅ No blocking or waiting for resources
- ✅ Each run maintains complete isolation

#### 2. Efficient Resource Usage
- ✅ Single checkout per workflow (not dual sparse/full)
- ✅ Shared runner utilization
- ✅ No unnecessary file copying

#### 3. Clean State Management
- ✅ `clean: true` ensures no leftover artifacts
- ✅ Age-based cleanup in cleanup action
- ✅ Each run starts from pristine state

#### 4. Robust Error Handling
- ✅ Symlink updates are atomic operations
- ✅ Failed runs don't affect other concurrent runs
- ✅ Cleanup runs even if workflow fails

### Implementation Pattern

#### Workflow Level
```yaml
name: Concurrent Workflow Template
on:
  workflow_dispatch:
    inputs:
      ci_workflow:
        required: true
        type: string

jobs:
  isolated-job:
    runs-on: self-hosted
    env:
      WORK_DIR: ${{ inputs.ci_workflow }}-${{ github.run_id }}
    steps:
      - name: Checkout to isolated directory
        uses: actions/checkout@v4
        with:
          path: ${{ env.WORK_DIR }}
          clean: true
          fetch-depth: 1

      - name: Setup phase
        run: ln -sf "${{ env.WORK_DIR }}/.github/actions" ./actions
      - uses: ./actions/setup
        with:
          work_dir: ${{ env.WORK_DIR }}
          ci_workflow: ${{ inputs.ci_workflow }}

      - name: Test phase  
        run: ln -sf "${{ env.WORK_DIR }}/.github/actions" ./actions
      - uses: ./actions/test
        with:
          work_dir: ${{ env.WORK_DIR }}

      - name: Cleanup phase
        if: always()
        run: ln -sf "${{ env.WORK_DIR }}/.github/actions" ./actions
      - uses: ./actions/cleanup
        with:
          work_dir: ${{ env.WORK_DIR }}
```

#### Action Level  
```yaml
# actions/setup/action.yml
name: Setup
inputs:
  work_dir:
    required: true
  ci_workflow:
    required: true

runs:
  using: composite
  steps:
    - name: Setup in isolated directory
      shell: bash
      working-directory: ${{ inputs.work_dir }}
      run: |
        echo "Setting up ${{ inputs.ci_workflow }} in $(pwd)"
        # All operations happen in isolated directory
```

### Cleanup Strategy

#### Age-Based Cleanup
```bash
# Remove directories older than 60 minutes, except current run
find . -maxdepth 1 -name "*-[0-9]*" -type d -mmin +60 \
  -not -name "*${{ github.run_id }}*" | \
  xargs -r rm -rf
```

#### Benefits
- ✅ Prevents disk space accumulation
- ✅ Preserves currently running workflows  
- ✅ Configurable retention policy

## Comparison with Alternative Approaches

### Dual Checkout Approach (Rejected)
```yaml
# Sparse checkout for actions
- uses: actions/checkout@v4
  with:
    sparse-checkout: .github
    path: actions-dir

# Full checkout for work  
- uses: actions/checkout@v4
  with:
    path: work-dir
```

**Problems**:
- ❌ Two checkout operations per workflow
- ❌ Complex coordination between sparse/full checkouts
- ❌ Still requires symlink workaround for dynamic paths
- ❌ Version inconsistency risk between checkouts

### File Copying Approach (Rejected)
```yaml
- uses: actions/checkout@v4
- run: cp -r * unique-dir/
```

**Problems**:
- ❌ Recursive copy issues with large repositories
- ❌ Inefficient disk usage
- ❌ Complex error handling for copy failures
- ❌ Slow execution for large codebases

## Implementation Considerations

### Runner Requirements
- **Self-hosted runners**: Required for concurrent workflow execution
- **Disk space**: Monitor for accumulation of run directories
- **Permissions**: Ensure symlink creation permissions

### Workflow Design Patterns
- **Environment variables**: Use for consistent work directory references
- **Error handling**: Always run cleanup with `if: always()`
- **Validation**: Verify symlink and directory existence in actions

### Security Considerations
- **Isolation**: Each run operates in separate directory
- **Cleanup**: Old runs are automatically removed
- **Permissions**: Standard GitHub Actions security model applies

## Migration Path

### Phase 1: Proof of Concept
1. Create simple demo workflow using new architecture
2. Test concurrent execution scenarios
3. Validate cleanup mechanisms

### Phase 2: Core Workflow Migration  
1. Migrate 2-3 primary workflows (fstests, blktests)
2. Update existing actions to use `work_dir` parameter
3. Test production scenarios

### Phase 3: Full Migration
1. Migrate remaining workflows
2. Remove disabled workflow files
3. Update documentation and procedures

## Conclusion

The single checkout + dynamic symlink architecture solves fundamental GitHub Actions limitations while providing:

- **True concurrency**: Multiple isolated workflows per runner
- **Efficiency**: Single checkout, minimal overhead  
- **Reliability**: Clean state, robust error handling
- **Maintainability**: Simple, understandable pattern

This approach transforms GitHub Actions from a blocking, single-workflow-per-runner model into a truly concurrent, isolated execution environment suitable for complex CI/CD requirements.