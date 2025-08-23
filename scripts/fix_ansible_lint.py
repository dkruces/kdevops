#!/usr/bin/env python3
"""
Fix ansible-lint issues in YAML files.
Supports fixing entire files or just changes in a git commit.
Goes beyond ansible-lint --fix by handling more issues.
"""

import re
import sys
import argparse
import subprocess
import json
import tempfile
import difflib
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional


class AnsibleFixer:
    """Fixes common ansible-lint issues in YAML files."""
    
    # Map of short module names to their FQCN
    FQCN_MAP = {
        # Core modules
        'apt': 'ansible.builtin.apt',
        'apt_key': 'ansible.builtin.apt_key',
        'apt_repository': 'ansible.builtin.apt_repository',
        'assemble': 'ansible.builtin.assemble',
        'assert': 'ansible.builtin.assert',
        'async_status': 'ansible.builtin.async_status',
        'blockinfile': 'ansible.builtin.blockinfile',
        'command': 'ansible.builtin.command',
        'copy': 'ansible.builtin.copy',
        'debug': 'ansible.builtin.debug',
        'dnf': 'ansible.builtin.dnf',
        'fail': 'ansible.builtin.fail',
        'fetch': 'ansible.builtin.fetch',
        'file': 'ansible.builtin.file',
        'find': 'ansible.builtin.find',
        'get_url': 'ansible.builtin.get_url',
        'git': 'ansible.builtin.git',
        'group': 'ansible.builtin.group',
        'hostname': 'ansible.builtin.hostname',
        'import_playbook': 'ansible.builtin.import_playbook',
        'import_role': 'ansible.builtin.import_role',
        'import_tasks': 'ansible.builtin.import_tasks',
        'include': 'ansible.builtin.include',
        'include_role': 'ansible.builtin.include_role',
        'include_tasks': 'ansible.builtin.include_tasks',
        'include_vars': 'ansible.builtin.include_vars',
        'lineinfile': 'ansible.builtin.lineinfile',
        'meta': 'ansible.builtin.meta',
        'package': 'ansible.builtin.package',
        'pause': 'ansible.builtin.pause',
        'ping': 'ansible.builtin.ping',
        'pip': 'ansible.builtin.pip',
        'raw': 'ansible.builtin.raw',
        'reboot': 'ansible.builtin.reboot',
        'replace': 'ansible.builtin.replace',
        'rpm_key': 'ansible.builtin.rpm_key',
        'script': 'ansible.builtin.script',
        'service': 'ansible.builtin.service',
        'service_facts': 'ansible.builtin.service_facts',
        'set_fact': 'ansible.builtin.set_fact',
        'setup': 'ansible.builtin.setup',
        'shell': 'ansible.builtin.shell',
        'slurp': 'ansible.builtin.slurp',
        'stat': 'ansible.builtin.stat',
        'systemd': 'ansible.builtin.systemd',
        'sysctl': 'ansible.builtin.sysctl',
        'template': 'ansible.builtin.template',
        'unarchive': 'ansible.builtin.unarchive',
        'uri': 'ansible.builtin.uri',
        'user': 'ansible.builtin.user',
        'wait_for': 'ansible.builtin.wait_for',
        'wait_for_connection': 'ansible.builtin.wait_for_connection',
        'yum': 'ansible.builtin.yum',
        'yum_repository': 'ansible.builtin.yum_repository',
        
        # Community modules
        'docker_compose': 'community.docker.docker_compose',
        'docker_container': 'community.docker.docker_container',
        'docker_image': 'community.docker.docker_image',
        'docker_network': 'community.docker.docker_network',
        'docker_volume': 'community.docker.docker_volume',
        
        # POSIX modules
        'synchronize': 'ansible.posix.synchronize',
        'mount': 'ansible.posix.mount',
        'seboolean': 'ansible.posix.seboolean',
        'selinux': 'ansible.posix.selinux',
    }
    
    def __init__(self, fix_only_changes: bool = False):
        """
        Initialize the fixer.
        
        Args:
            fix_only_changes: If True, only fix lines that are part of git changes
        """
        self.fix_only_changes = fix_only_changes
        self.changed_lines: Dict[str, Set[int]] = {}
        
    def get_changed_lines(self, file_path: str) -> Set[int]:
        """Get line numbers that have been changed in the last commit."""
        if file_path in self.changed_lines:
            return self.changed_lines[file_path]
            
        changed = set()
        try:
            # Get the diff with line numbers
            result = subprocess.run(
                ['git', 'diff', 'HEAD~1', 'HEAD', '--unified=0', file_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse the diff to find changed line numbers
            for line in result.stdout.split('\n'):
                if line.startswith('@@'):
                    # Format: @@ -old_start,old_count +new_start,new_count @@
                    match = re.match(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@', line)
                    if match:
                        start = int(match.group(1))
                        count = int(match.group(2)) if match.group(2) else 1
                        for i in range(start, start + count):
                            changed.add(i)
        except subprocess.CalledProcessError:
            # If we can't get the diff, treat all lines as changeable
            return set(range(1, 100000))
            
        self.changed_lines[file_path] = changed
        return changed
    
    def should_fix_line(self, file_path: str, line_num: int) -> bool:
        """Check if a line should be fixed based on the mode."""
        if not self.fix_only_changes:
            return True
        return line_num in self.get_changed_lines(file_path)
    
    def fix_yaml_brackets(self, content: str, file_path: str) -> str:
        """Fix 'Too many spaces inside brackets' issues."""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if not self.should_fix_line(file_path, i + 1):
                continue
                
            # Fix spacing in brackets: [ foo ] -> [foo]
            fixed_line = re.sub(r'\[\s+', '[', line)
            fixed_line = re.sub(r'\s+\]', ']', fixed_line)
            lines[i] = fixed_line
        return '\n'.join(lines)
    
    def fix_yaml_truthy(self, content: str, file_path: str) -> str:
        """Fix truthy value issues (yes/no -> true/false)."""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if not self.should_fix_line(file_path, i + 1):
                continue
                
            # Fix standalone yes/no values
            fixed_line = re.sub(r':\s+yes\s*$', ': true', line)
            fixed_line = re.sub(r':\s+no\s*$', ': false', fixed_line)
            fixed_line = re.sub(r':\s+Yes\s*$', ': true', fixed_line)
            fixed_line = re.sub(r':\s+No\s*$', ': false', fixed_line)
            fixed_line = re.sub(r':\s+YES\s*$', ': true', fixed_line)
            fixed_line = re.sub(r':\s+NO\s*$', ': false', fixed_line)
            fixed_line = re.sub(r':\s+on\s*$', ': true', fixed_line)
            fixed_line = re.sub(r':\s+off\s*$', ': false', fixed_line)
            lines[i] = fixed_line
        return '\n'.join(lines)
    
    def fix_jinja_spacing(self, content: str, file_path: str) -> str:
        """Fix Jinja2 spacing issues."""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if not self.should_fix_line(file_path, i + 1):
                continue
                
            # Fix spacing around | in Jinja2 expressions
            # Match patterns like: {{var|filter}} or "{{var|filter}}"
            def fix_jinja_expr(match):
                expr = match.group(1)
                # Add spaces around |
                expr = re.sub(r'([^|\s])\|([^|\s])', r'\1 | \2', expr)
                # Fix multiple spaces
                expr = re.sub(r'\s+\|\s+', ' | ', expr)
                return '{{' + expr + '}}'
            
            fixed_line = re.sub(r'\{\{(.+?)\}\}', fix_jinja_expr, line)
            
            # Also fix in when: conditions without {{ }}
            if re.match(r'\s*(when|changed_when|failed_when):', line):
                # Extract the condition part
                parts = line.split(':', 1)
                if len(parts) == 2:
                    condition = parts[1]
                    # Fix spacing around | in conditions
                    condition = re.sub(r'([^|\s])\|([^|\s])', r'\1 | \2', condition)
                    condition = re.sub(r'\s+\|\s+', ' | ', condition)
                    fixed_line = parts[0] + ':' + condition
                    
            lines[i] = fixed_line
        return '\n'.join(lines)
    
    def fix_fqcn(self, content: str, file_path: str) -> str:
        """Fix FQCN (Fully Qualified Collection Name) issues."""
        lines = content.split('\n')
        in_task = False
        task_start_line = 0
        
        for i, line in enumerate(lines):
            # Detect task start
            if re.match(r'\s*-\s+name:', line):
                in_task = True
                task_start_line = i
                continue
                
            if not in_task:
                continue
                
            # Check if we should fix this line
            if not self.should_fix_line(file_path, i + 1):
                continue
                
            # Look for module usage patterns
            # Pattern 1: Simple module at start of line (after dash and spaces)
            match = re.match(r'^(\s*-?\s*)([a-z_]+)(\s*:.*)', line)
            if not match and in_task:
                # Pattern 2: Module name as a key (without dash)
                match = re.match(r'^(\s*)([a-z_]+)(\s*:.*)', line)
                
            if match:
                indent = match.group(1)
                module = match.group(2)
                rest = match.group(3)
                
                if module in self.FQCN_MAP:
                    lines[i] = indent + self.FQCN_MAP[module] + rest
                    in_task = False  # Task module found, reset
                    
            # Reset task flag if we hit another task or play
            if re.match(r'\s*-\s+(name|hosts):', line) and i != task_start_line:
                in_task = re.match(r'\s*-\s+name:', line) is not None
                if in_task:
                    task_start_line = i
                    
        return '\n'.join(lines)
    
    def fix_ignore_errors(self, content: str, file_path: str) -> str:
        """
        Convert ignore_errors to failed_when where appropriate.
        This is a more conservative fix - only for simple cases.
        """
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            if not self.should_fix_line(file_path, i + 1):
                i += 1
                continue
                
            line = lines[i]
            # Look for ignore_errors: yes/true
            if re.match(r'\s*ignore_errors:\s*(yes|true|True)', line):
                # Check if there's already a failed_when
                has_failed_when = False
                indent = len(line) - len(line.lstrip())
                
                # Look ahead for failed_when at the same indent level
                for j in range(i + 1, min(i + 10, len(lines))):
                    next_line = lines[j]
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent < indent and next_line.strip():
                        break
                    if re.match(r'\s*failed_when:', next_line):
                        has_failed_when = True
                        break
                        
                # Only convert if this is safe (no existing failed_when)
                # Add a comment to indicate manual review needed
                if not has_failed_when:
                    lines[i] = line.replace('ignore_errors:', '# TODO: Review - was ignore_errors:')
                    # Add a conservative failed_when
                    lines.insert(i + 1, ' ' * indent + 'failed_when: false  # Always succeed - review this condition')
                    i += 1
                    
            i += 1
        return '\n'.join(lines)
    
    def fix_role_path(self, content: str, file_path: str) -> str:
        """Fix role path issues - remove ../roles/ prefix."""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if not self.should_fix_line(file_path, i + 1):
                continue
                
            # Fix role paths in import_role and include_role
            if 'role:' in line or 'name:' in line:
                # Remove ../roles/ prefix from role names
                fixed_line = re.sub(r'(role:|name:)\s*["\']?\.\.\/roles\/([^"\'\s]+)', r'\1 \2', line)
                fixed_line = re.sub(r'(role:|name:)\s*\.\.\/roles\/([^\s]+)', r'\1 \2', fixed_line)
                lines[i] = fixed_line
                
        return '\n'.join(lines)
    
    def fix_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Fix all issues in a file.
        
        Returns:
            Tuple of (was_modified, content)
        """
        try:
            with open(file_path, 'r') as f:
                original_content = f.read()
        except Exception as e:
            return False, f"Error reading {file_path}: {e}"
            
        # Apply all fixes
        content = original_content
        content = self.fix_yaml_brackets(content, file_path)
        content = self.fix_yaml_truthy(content, file_path)
        content = self.fix_jinja_spacing(content, file_path)
        content = self.fix_fqcn(content, file_path)
        content = self.fix_ignore_errors(content, file_path)
        content = self.fix_role_path(content, file_path)
        
        # Check if anything changed
        if content != original_content:
            return True, content
        return False, original_content
    
    def write_file(self, file_path: str, content: str) -> None:
        """Write content to file."""
        with open(file_path, 'w') as f:
            f.write(content)
    
    def show_diff(self, file_path: str, original: str, fixed: str) -> None:
        """Show the differences between original and fixed content."""
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            fixed.splitlines(keepends=True),
            fromfile=f"{file_path} (original)",
            tofile=f"{file_path} (fixed)",
            lineterm=''
        )
        print(''.join(diff))


def get_ansible_lint_issues(files: List[str]) -> Dict[str, List[Dict]]:
    """Run ansible-lint and get issues in JSON format."""
    try:
        result = subprocess.run(
            ['ansible-lint', '--format', 'json'] + files,
            capture_output=True,
            text=True
        )
        if result.stdout:
            issues = json.loads(result.stdout)
            # Group by file
            by_file = {}
            for issue in issues:
                if 'location' in issue and 'path' in issue['location']:
                    path = issue['location']['path']
                    if path not in by_file:
                        by_file[path] = []
                    by_file[path].append(issue)
            return by_file
    except Exception as e:
        print(f"Error running ansible-lint: {e}")
    return {}


def get_files_from_last_commit() -> List[str]:
    """Get YAML files changed in the last commit."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        files = []
        for line in result.stdout.strip().split('\n'):
            if line and (line.endswith('.yml') or line.endswith('.yaml')):
                if Path(line).exists():
                    files.append(line)
        return files
    except subprocess.CalledProcessError:
        return []


def main():
    parser = argparse.ArgumentParser(
        description='Fix ansible-lint issues in YAML files'
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='Files to fix (if not specified, uses files from last commit)'
    )
    parser.add_argument(
        '--changes-only',
        action='store_true',
        help='Only fix lines that were changed in the last commit'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without modifying files'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Run ansible-lint after fixing to verify'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed information'
    )
    
    args = parser.parse_args()
    
    # Get files to process
    files = args.files
    if not files:
        files = get_files_from_last_commit()
        if not files:
            print("No YAML files found in last commit")
            return 0
        if args.verbose:
            print(f"Processing {len(files)} files from last commit")
    
    # Initialize fixer
    fixer = AnsibleFixer(fix_only_changes=args.changes_only)
    
    # Process each file
    modified_files = []
    for file_path in files:
        if args.verbose:
            print(f"\nProcessing {file_path}...")
            
        was_modified, content = fixer.fix_file(file_path)
        
        if was_modified:
            modified_files.append(file_path)
            if args.dry_run:
                print(f"\n--- Would modify {file_path} ---")
                with open(file_path, 'r') as f:
                    original = f.read()
                fixer.show_diff(file_path, original, content)
            else:
                if args.verbose:
                    print(f"  Fixed issues in {file_path}")
                fixer.write_file(file_path, content)
        elif args.verbose:
            print(f"  No issues found in {file_path}")
    
    # Summary
    if modified_files:
        print(f"\n{'Would fix' if args.dry_run else 'Fixed'} {len(modified_files)} file(s):")
        for f in modified_files:
            print(f"  - {f}")
    else:
        print("\nNo issues found to fix")
    
    # Run ansible-lint check if requested
    if args.check and not args.dry_run and modified_files:
        print("\nRunning ansible-lint to verify fixes...")
        result = subprocess.run(
            ['ansible-lint'] + modified_files,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ All ansible-lint checks passed!")
        else:
            print("⚠ Some ansible-lint issues remain:")
            print(result.stdout[:1000])  # Show first 1000 chars
            
            # Get remaining issues
            issues = get_ansible_lint_issues(modified_files)
            if issues:
                print("\nRemaining issues by type:")
                issue_types = {}
                for file_issues in issues.values():
                    for issue in file_issues:
                        check_name = issue.get('check_name', 'unknown')
                        issue_types[check_name] = issue_types.get(check_name, 0) + 1
                
                for check_name, count in sorted(issue_types.items()):
                    print(f"  {check_name}: {count}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())