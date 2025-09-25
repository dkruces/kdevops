# Concurrent GitHub Actions Architecture - Implementation Plan

## Overview

This document outlines the step-by-step plan to implement the new concurrent GitHub Actions architecture for kdevops. The implementation follows a phased approach with atomic commits for each step.

## Implementation Phases

### Phase 1: Clean Slate Demo (Current Focus)
**Objective**: Create a simple demonstration of the new architecture from scratch.

### Phase 2: Core Workflow Migration  
**Objective**: Migrate 2-3 primary workflows to validate production scenarios.

### Phase 3: Full Infrastructure Migration
**Objective**: Complete migration of all workflows and cleanup.

---

## Phase 1: Clean Slate Demo Implementation

### Step 1: Remove Current Simple Test Infrastructure
**Objective**: Clean slate for new architecture demonstration.

#### 1.1 Remove Simple Test Workflow
- **Task**: Delete `.github/workflows/simple-test.yml`
- **Rationale**: Current implementation uses outdated dual-checkout approach
- **Commit**: "github: remove outdated simple-test workflow"

#### 1.2 Remove Simple Actions
- **Task**: Delete `.github/actions/simple-*` directories
- **Actions to remove**:
  - `.github/actions/simple-setup/`
  - `.github/actions/simple-test/`
  - `.github/actions/simple-cleanup/`
- **Rationale**: Actions designed for old architecture patterns
- **Commit**: "github: remove outdated simple actions"

### Step 2: Create New Demo Architecture
**Objective**: Implement single checkout + symlink architecture in a simple demo.

#### 2.1 Create Core Demo Action
- **File**: `.github/actions/concurrent-demo/action.yml`
- **Features**:
  - Accepts `work_dir` parameter
  - Uses `working-directory` for all operations
  - Demonstrates isolation principles
  - Includes validation steps
- **Commit**: "github: add concurrent-demo action"

#### 2.2 Create Demo Workflow
- **File**: `.github/workflows/concurrent-demo.yml`
- **Features**:
  - Single checkout with `clean: true`
  - Dynamic symlink updates before each action
  - Environment variable for work directory consistency
  - Demonstrates concurrent workflow pattern
- **Template**:
```yaml
name: Concurrent Architecture Demo
on:
  workflow_dispatch:
    inputs:
      demo_name:
        description: "Demo instance name"
        required: true
        default: 'demo'
        type: string

jobs:
  concurrent-demo:
    name: Concurrent Demo
    runs-on: self-hosted
    env:
      WORK_DIR: ${{ inputs.demo_name }}-${{ github.run_id }}
    steps:
      - name: Checkout to isolated directory
        uses: actions/checkout@v4
        with:
          path: ${{ env.WORK_DIR }}
          clean: true
          fetch-depth: 1

      - name: Demo setup phase
        run: ln -sf "${{ env.WORK_DIR }}/.github/actions" ./actions
      - uses: ./actions/concurrent-demo
        with:
          work_dir: ${{ env.WORK_DIR }}
          phase: setup

      - name: Demo test phase
        run: ln -sf "${{ env.WORK_DIR }}/.github/actions" ./actions  
      - uses: ./actions/concurrent-demo
        with:
          work_dir: ${{ env.WORK_DIR }}
          phase: test

      - name: Demo cleanup phase
        if: always()
        run: ln -sf "${{ env.WORK_DIR }}/.github/actions" ./actions
      - uses: ./actions/concurrent-demo
        with:
          work_dir: ${{ env.WORK_DIR }}
          phase: cleanup
```
- **Commit**: "github: add concurrent architecture demo workflow"

#### 2.3 Create Validation Documentation
- **File**: `docs/ci/concurrent-demo-validation.md`
- **Content**:
  - How to test concurrent execution
  - Expected behavior documentation
  - Validation checklist
  - Troubleshooting guide
- **Commit**: "docs: add concurrent demo validation guide"

### Step 3: Manual Testing Phase
**Objective**: Validate demo works correctly with concurrent execution.

#### 3.1 Single Workflow Testing
- **Action**: Manually trigger demo workflow
- **Validation**:
  - Workflow completes successfully
  - Correct directory isolation
  - Symlink updates work properly
  - Cleanup functions correctly

#### 3.2 Concurrent Workflow Testing  
- **Action**: Trigger multiple demo workflows simultaneously
- **Validation**:
  - No interference between workflows
  - Each maintains proper isolation
  - Symlink updates handle race conditions
  - All workflows complete successfully

#### 3.3 Document Results
- **Task**: Update validation documentation with test results
- **Commit**: "docs: update concurrent demo validation results"

---

## Phase 2: Core Workflow Migration

### Step 4: Analyze Current Disabled Workflows
**Objective**: Understand existing workflow structure for migration.

#### 4.1 Inventory Disabled Workflows
- **Task**: List all `.yml.disabled` files
- **Analysis**:
  - Identify primary workflows (fstests, blktests, selftests)
  - Document current action dependencies
  - Map workflow → action relationships
- **Deliverable**: `docs/ci/workflow-migration-analysis.md`
- **Commit**: "docs: add workflow migration analysis"

#### 4.2 Select Migration Candidates
- **Criteria**:
  - High usage workflows
  - Representative action patterns
  - Good test coverage for validation
- **Candidates** (preliminary):
  1. `fstests.yml` - Filesystem testing workflow
  2. `blktests.yml` - Block layer testing workflow
  3. `selftests.yml` - Kernel selftests workflow
- **Commit**: "docs: identify core workflow migration candidates"

### Step 5: Create Migration Action Templates
**Objective**: Design reusable action patterns for migrated workflows.

#### 5.1 Create Base Setup Action
- **File**: `.github/actions/kdevops-setup/action.yml`
- **Features**:
  - Accepts standard parameters (work_dir, ci_workflow, etc.)
  - Handles common setup tasks (defconfig, host generation)
  - Uses working-directory consistently
  - Includes validation and error handling
- **Commit**: "github: add kdevops-setup base action"

#### 5.2 Create Base Test Action
- **File**: `.github/actions/kdevops-test/action.yml`
- **Features**:
  - Generic test execution framework
  - Configurable test commands
  - Result collection and archival
  - Timeout and error handling
- **Commit**: "github: add kdevops-test base action"

#### 5.3 Create Base Cleanup Action
- **File**: `.github/actions/kdevops-cleanup/action.yml`
- **Features**:
  - Age-based directory cleanup
  - Artifact collection
  - Resource cleanup (processes, mounts)
  - Always-run cleanup tasks
- **Commit**: "github: add kdevops-cleanup base action"

### Step 6: Migrate First Core Workflow
**Objective**: Migrate one workflow completely to validate migration approach.

#### 6.1 Choose Migration Target
- **Selection**: Start with `fstests` workflow (most representative)
- **Rationale**: 
  - Well-understood workflow
  - Good test coverage
  - Representative of kdevops patterns

#### 6.2 Create Migrated Workflow
- **File**: `.github/workflows/fstests-concurrent.yml`
- **Features**:
  - Single checkout + symlink pattern
  - Environment variable consistency
  - Reusable action integration
  - Proper error handling and cleanup
- **Commit**: "github: add concurrent fstests workflow"

#### 6.3 Create Workflow-Specific Actions
- **Files** (if needed):
  - `.github/actions/fstests-setup/action.yml`
  - `.github/actions/fstests-test/action.yml`
  - Any fstests-specific logic
- **Commit**: "github: add fstests-specific actions"

#### 6.4 Testing and Validation
- **Process**:
  - Manual testing with various configurations
  - Concurrent execution validation
  - Result comparison with old workflow (if available)
- **Documentation**: Update validation results

### Step 7: Iterate and Refine
**Objective**: Apply lessons learned to improve the architecture.

#### 7.1 Document Migration Lessons
- **File**: `docs/ci/migration-lessons-learned.md`
- **Content**:
  - Issues encountered during migration
  - Solutions implemented
  - Architectural refinements
  - Best practices identified
- **Commit**: "docs: document migration lessons learned"

#### 7.2 Refine Action Templates
- **Task**: Update base actions based on migration experience
- **Improvements**:
  - Better error handling
  - More flexible parameter handling
  - Performance optimizations
  - Additional validation steps
- **Commit**: "github: refine base actions from migration experience"

---

## Phase 3: Full Infrastructure Migration

### Step 8: Batch Migrate Remaining Workflows
**Objective**: Apply proven migration patterns to all workflows.

#### 8.1 Create Migration Script
- **File**: `scripts/migrate-workflow.sh`
- **Features**:
  - Automated conversion of old workflow patterns
  - Template substitution
  - Validation of migration results
- **Commit**: "scripts: add workflow migration automation"

#### 8.2 Migrate Secondary Workflows
- **Target workflows**:
  - `blktests.yml`
  - `selftests.yml`
  - Other high-priority workflows
- **Process**: Use migration script + manual review
- **Commits**: One per workflow migration

#### 8.3 Migrate Remaining Workflows
- **Target**: All remaining `.yml.disabled` files
- **Process**: Batch migration with validation
- **Commits**: Logical groups of related workflows

### Step 9: Cleanup and Documentation
**Objective**: Remove old infrastructure and finalize documentation.

#### 9.1 Remove Disabled Workflows
- **Task**: Delete all `.yml.disabled` files
- **Validation**: Ensure all functionality migrated
- **Commit**: "github: remove legacy disabled workflows"

#### 9.2 Update Primary Documentation
- **Files**:
  - `README.md` - Update CI/CD section
  - `docs/ci/` - Comprehensive workflow documentation
  - `CLAUDE.md` - Update any CI-related guidance
- **Commit**: "docs: update documentation for concurrent architecture"

#### 9.3 Create Operational Runbook
- **File**: `docs/ci/concurrent-workflows-operations.md`
- **Content**:
  - How to create new workflows
  - Troubleshooting guide
  - Performance monitoring
  - Maintenance procedures
- **Commit**: "docs: add concurrent workflows operational runbook"

---

## Implementation Tracking

### Todo Checklist

#### Phase 1: Clean Slate Demo
- [ ] 1.1 Remove simple-test workflow
- [ ] 1.2 Remove simple actions
- [ ] 2.1 Create concurrent-demo action  
- [ ] 2.2 Create concurrent-demo workflow
- [ ] 2.3 Create validation documentation
- [ ] 3.1 Single workflow testing
- [ ] 3.2 Concurrent workflow testing
- [ ] 3.3 Document test results

#### Phase 2: Core Migration
- [ ] 4.1 Inventory disabled workflows
- [ ] 4.2 Select migration candidates
- [ ] 5.1 Create base setup action
- [ ] 5.2 Create base test action
- [ ] 5.3 Create base cleanup action
- [ ] 6.1 Choose migration target
- [ ] 6.2 Create migrated workflow
- [ ] 6.3 Create workflow-specific actions
- [ ] 6.4 Testing and validation
- [ ] 7.1 Document lessons learned
- [ ] 7.2 Refine action templates

#### Phase 3: Full Migration
- [ ] 8.1 Create migration script
- [ ] 8.2 Migrate secondary workflows
- [ ] 8.3 Migrate remaining workflows
- [ ] 9.1 Remove disabled workflows
- [ ] 9.2 Update primary documentation
- [ ] 9.3 Create operational runbook

### Success Criteria

#### Phase 1 Success
- [ ] Demo workflow runs successfully in isolation
- [ ] Multiple concurrent demos execute without interference
- [ ] Symlink updates handle race conditions properly
- [ ] Cleanup functions remove old run directories

#### Phase 2 Success
- [ ] At least one core workflow fully migrated and tested
- [ ] Migration patterns documented and reusable
- [ ] Performance comparable to or better than original
- [ ] No regression in functionality

#### Phase 3 Success
- [ ] All workflows migrated to concurrent architecture
- [ ] No disabled workflow files remaining
- [ ] Complete documentation and operational procedures
- [ ] Team trained on new architecture

### Risk Mitigation

#### Technical Risks
- **Symlink race conditions**: Mitigated by per-step updates
- **Disk space accumulation**: Addressed by age-based cleanup
- **Performance degradation**: Monitored during migration

#### Process Risks
- **Migration complexity**: Phased approach reduces risk
- **Testing coverage**: Manual and automated validation
- **Rollback capability**: Keep disabled workflows until validation complete

---

## Next Steps

1. **Execute Phase 1**: Start with clean slate demo implementation
2. **Manual Testing**: Validate concurrent execution works as designed
3. **Iterate Based on Results**: Refine approach based on demo testing
4. **Proceed to Phase 2**: Begin core workflow migration

This plan provides a structured approach to implementing the concurrent GitHub Actions architecture while maintaining system stability and providing clear validation at each step.