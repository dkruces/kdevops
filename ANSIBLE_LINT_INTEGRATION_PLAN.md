# Ansible-Lint Script Integration Plan

## Executive Summary

This document outlines the comprehensive plan to integrate features from three ansible-lint automation scripts:
1. Current `ansible-lint-fix-rules.py` (refactored 6-class architecture)
2. External `ansible-lint-fix-rules.py` (from GitHub, simpler wrapper approach)
3. `fix_ansible_lint.py` (manual fixes with git diff integration)

## Analysis Results

### Current ansible-lint-fix-rules.py (856 lines)
**Architecture**: 6 focused classes following Single Responsibility Principle
- Config, RuleInfo, UserInterface, AnsibleLintCommand, GitManager, CommitMessageBuilder, AnsibleLintProcessor, AnsibleLintFixer

**Key Features**:
- Rule-by-rule processing with user confirmation
- Tag-based processing (`--by-tag formatting`, `--by-tag idiom`)
- Rich CLI integration with progress bars
- Auto-accept mode (`--auto` flag) for unattended operation
- Professional commit message generation
- Smart git operations (atomic file staging)

**Commit Message Format**:
```
{prefix} ansible-lint fix {rule}

{description}

Fixed {rule} rule violations across {count} file(s).

Affected files:
- file1.yml
- file2.yml

Applied using the ansible-lint-fix-rules.py script with --fix={rule}.

Generated-by: Ansible Lint (ansible-lint-fix-rules.py)
Signed-off-by: {name} <{email}>
```

### External ansible-lint-fix-rules.py (GitHub)
**Architecture**: Simpler wrapper approach
**Key Differences**:
- Template-based commits (less verbose)
- Basic wrapper functionality around `ansible-lint --fix=<rule_id>`
- No Rich CLI integration
- No auto-accept mode

### fix_ansible_lint.py (500 lines)
**Architecture**: Single AnsibleFixer class
**Unique Capabilities**:
- **Last commit filtering**: `--changes-only` flag fixes only lines changed in recent commits
- **Manual fix implementations** for issues ansible-lint can't auto-fix:
  - YAML bracket spacing
  - Truthy values (yes/no → true/false)
  - Jinja2 spacing
  - FQCN conversion
  - ignore_errors → failed_when conversion
  - Role path cleanup
- **Comprehensive FQCN mapping** for 90+ ansible modules
- **Diff visualization** before applying changes
- **Verification mode** with post-fix ansible-lint check

## Target Architecture: ansible-lint-comprehensive-fixer.py

```
├── Core Classes (from current script)
│   ├── Config - Configuration constants  
│   ├── RuleInfo - Rule metadata
│   ├── UserInterface - Rich CLI with auto-accept
│   └── GitManager - Safe atomic git operations
│
├── Enhanced Command Building
│   ├── AnsibleLintCommand - Build lint commands
│   └── ManualFixCommand - Build manual fix commands
│
├── Dual Processing Engine  
│   ├── AnsibleLintProcessor - Official ansible-lint fixes
│   └── ManualFixProcessor - Custom fixes for unsupported rules
│
├── Smart Commit Management
│   ├── CommitMessageBuilder - Less verbose, template-based
│   └── ChangeFilter - Last commit line filtering
│
├── Enhanced Discovery
│   └── RecursiveProcessor - Directory tree traversal
│
└── Main Orchestrator
    └── ComprehensiveLintFixer - Unified workflow
```

## Key Integration Points

### 1. Recursive Application
```bash
# Apply to entire directory tree
./ansible-lint-comprehensive-fixer.py --recursive playbooks/

# Apply only to files changed in last commit
./ansible-lint-comprehensive-fixer.py --changes-only

# Combine both approaches
./ansible-lint-comprehensive-fixer.py --recursive --changes-only playbooks/
```

### 2. Two-Phase Processing
- **Phase 1**: Run official ansible-lint --fix for each rule
- **Phase 2**: Apply manual fixes for remaining issues

### 3. Enhanced Commit Messages (Less Verbose)
```
{prefix} ansible-lint fix {rule}

Fixed {rule} violations across {count} files.

Generated-by: Ansible Lint (ansible-lint-comprehensive-fixer.py)
Signed-off-by: {name} <{email}>
```

## Implementation Architecture

### RecursiveProcessor Class
```python
class RecursiveProcessor:
    def find_ansible_files(self, root_path: str, changes_only: bool = False) -> List[str]:
        """Find all ansible YAML files, optionally filtering to changed files."""
        
    def apply_recursively(self, processor_func, files: List[str]) -> Dict[str, bool]:
        """Apply processing function to all discovered files."""
```

### ChangeFilter Class  
```python
class ChangeFilter:
    def __init__(self, commit_ref: str = 'HEAD~1'):
        self.changed_lines_cache: Dict[str, Set[int]] = {}
    
    def get_changed_lines(self, file_path: str) -> Set[int]:
        """Get line numbers changed in specified commit."""
        
    def should_process_file(self, file_path: str, rule: str) -> bool:
        """Determine if file should be processed for given rule."""
```

### ManualFixProcessor Class
```python
class ManualFixProcessor:
    """Integrates all manual fix methods from fix_ansible_lint.py"""
    
    def fix_yaml_brackets(self, content: str, file_path: str) -> str:
    def fix_yaml_truthy(self, content: str, file_path: str) -> str:
    def fix_jinja_spacing(self, content: str, file_path: str) -> str:
    def fix_fqcn(self, content: str, file_path: str) -> str:
    def fix_ignore_errors(self, content: str, file_path: str) -> str:
    def fix_role_path(self, content: str, file_path: str) -> str:
```

## Implementation Task Phases

### Phase 1: Core Integration (High Priority)
1. **Create ansible-lint-comprehensive-fixer.py base structure**
   - Merge current ansible-lint-fix-rules.py classes
   - Integrate fix_ansible_lint.py's AnsibleFixer class
   - Create unified command-line interface

2. **Implement RecursiveProcessor class**
   - File discovery with pattern matching
   - Integration with existing path handling
   - Support for --recursive flag

3. **Implement ChangeFilter class**
   - Port git diff parsing from fix_ansible_lint.py
   - Add --changes-only flag support
   - Cache changed line information

### Phase 2: Enhanced Processing (High Priority)
4. **Create ManualFixProcessor class**
   - Port all manual fix methods from fix_ansible_lint.py
   - Integrate with existing rule processing workflow
   - Add support for fixes ansible-lint can't handle

5. **Implement two-phase processing workflow**
   - Phase 1: Official ansible-lint --fix processing
   - Phase 2: Manual fixes for remaining issues
   - Unified progress tracking across both phases

6. **Update CommitMessageBuilder for concise messages**
   - Implement template-based approach (external script style)
   - Remove verbose file listing (keep summary count)
   - Maintain proper attribution format

### Phase 3: Feature Enhancement (Medium Priority)
7. **Add advanced filtering capabilities**
   - Combine recursive + changes-only modes
   - Rule-specific file filtering
   - Support for excluding specific paths/patterns

8. **Implement verification and reporting**
   - Post-fix ansible-lint verification
   - Comprehensive reporting of fixes applied
   - Detection of unfixable issues requiring manual attention

9. **Add configuration file support**
   - YAML/JSON config files for default options
   - Per-project configuration overrides
   - Rule-specific configuration options

### Phase 4: Testing and Documentation (Medium Priority)
10. **Comprehensive testing suite**
    - Unit tests for all major components
    - Integration tests with real ansible files
    - Test coverage for all command-line options

11. **Update help documentation and examples**
    - Comprehensive --help output
    - Usage examples for all major workflows
    - Integration with existing kdevops documentation

### Phase 5: Backward Compatibility (Low Priority)
12. **Maintain compatibility with existing scripts**
    - Keep ansible-lint-fix-rules.py as legacy wrapper
    - Maintain fix_ansible_lint.py for specialized use cases
    - Provide migration path documentation

## User Requirements Validation

### ✅ "Apply recursively and one rule at a time"
- RecursiveProcessor class for directory tree traversal
- Maintains existing rule-by-rule processing architecture
- `--recursive` flag combines with existing single-rule workflow

### ✅ "Combine both scripts' features"  
- Integrates all classes from current ansible-lint-fix-rules.py
- Ports all manual fix methods from fix_ansible_lint.py
- Creates unified ManualFixProcessor for two-phase processing

### ✅ "Less verbose commit message templates"
- Simplified commit format removing detailed file listings
- Template-based approach matching external script style
- Maintains proper Generated-by attribution

### ✅ "Apply only to last commit's lines feature"
- ChangeFilter class ports git diff parsing logic
- `--changes-only` flag integration with rule processing
- Combines with recursive processing: `--recursive --changes-only`

### ✅ "ansible-lint --fix=<rule_id> wrapper functionality"
- Maintains existing AnsibleLintCommand.fix_rule() method
- Preserves rule-by-rule processing with user confirmation
- Extends with manual fixes for unsupported rules

## Command Examples

```bash
# Apply all rules recursively
./ansible-lint-comprehensive-fixer.py --recursive playbooks/

# Apply only to files changed in last commit
./ansible-lint-comprehensive-fixer.py --changes-only

# Combine recursive + changes-only modes
./ansible-lint-comprehensive-fixer.py --recursive --changes-only playbooks/

# Unattended processing
./ansible-lint-comprehensive-fixer.py --auto --recursive playbooks/

# Two-phase processing: official + manual fixes
./ansible-lint-comprehensive-fixer.py --enable-manual-fixes --recursive

# Process specific rule across all files
./ansible-lint-comprehensive-fixer.py --rule fqcn --recursive playbooks/

# Tag-based processing with manual fixes
./ansible-lint-comprehensive-fixer.py --by-tag formatting --enable-manual-fixes
```

## Risk Mitigation

- **Maintains existing functionality**: All current features preserved
- **Backward compatible**: Existing scripts remain available during transition
- **Incremental rollout**: Can implement and test phases independently
- **Git safety**: Uses existing atomic git operations (no `git add .`)

## Technical Implementation Notes

### Critical Integration Points
1. **Git diff parsing**: Use fix_ansible_lint.py's robust implementation
2. **Progress tracking**: Extend Rich progress bars to cover two-phase processing
3. **Error handling**: Maintain timeout and subprocess management from current script
4. **File discovery**: Smart ansible file detection with pattern matching
5. **Commit message consistency**: Follow kdevops project conventions

### Performance Considerations
- Cache git diff results to avoid repeated parsing
- Process files in batches for recursive operations
- Maintain memory efficiency for large repository scans
- Use existing timeout mechanisms for long-running operations

---

**Document Status**: Draft v1.0
**Last Updated**: Current session
**Next Action**: Begin Phase 1 implementation starting with base structure creation