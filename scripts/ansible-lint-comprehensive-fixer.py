#!/usr/bin/env python3
"""
Comprehensive Ansible-lint fixer combining multiple automation approaches.

This script integrates features from:
- ansible-lint-fix-rules.py: Rule-by-rule processing with Rich CLI
- fix_ansible_lint.py: Manual fixes and git diff integration
- External wrapper: Template-based commits and simplified workflow

Features:
- Recursive directory processing
- Rule-by-rule with user confirmation
- Manual fixes for unsupported rules
- Git diff-based change filtering
- Two-phase processing (official + custom fixes)
- Less verbose commit messages
- Rich CLI with progress tracking
"""

import subprocess
import sys
import os
import json
import tempfile
import re
import difflib
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass

try:
    from rich.console import Console
    from rich.progress import (
        Progress,
        BarColumn,
        TextColumn,
        SpinnerColumn,
        MofNCompleteColumn,
    )
    from rich.prompt import Confirm
    from rich.table import Table
    from rich.panel import Panel

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' not available. Install with: pip install rich")
    print("Falling back to basic output...")


@dataclass
class Config:
    """Configuration constants."""

    ANSIBLE_LINT_TIMEOUT = 300  # 5 minutes
    MAX_FILES_TO_LIST = 10
    FILES_TO_SHOW_BEFORE_TRUNCATION = 5
    MAX_CHANGED_FILES_PREVIEW = 3


@dataclass
class RuleInfo:
    """Information about an ansible-lint rule."""

    id: str
    description: str
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class UserInterface:
    """Handles user interaction and display."""

    def __init__(self, auto_accept: bool = False):
        self.auto_accept = auto_accept
        self.console = Console() if RICH_AVAILABLE else None

    def print_message(self, message: str, style: str = None):
        """Print message with optional styling."""
        if self.console and style:
            self.console.print(message, style=style)
        else:
            print(message)

    def prompt_user(
        self, message: str, default: bool = False, auto_message: str = None
    ) -> bool:
        """Unified prompt handling with auto-accept support."""
        if self.auto_accept:
            if auto_message:
                self.print_message(auto_message, "cyan")
            return True

        if self.console:
            return Confirm.ask(message, default=default)
        else:
            default_text = "Y/n" if default else "y/N"
            response = input(f"{message} ({default_text}): ")
            if default:
                return response.lower() not in ["n", "no"]
            else:
                return response.lower() in ["y", "yes"]

    def show_rule_summary(self, rules: List[RuleInfo]):
        """Display a summary of rules to be processed."""
        rule_descriptions = {
            "command-instead-of-shell": "Use shell only when shell functionality is required",
            "deprecated-local-action": "Replace deprecated local_action with delegate_to: localhost",
            "fqcn": "Use FQCN (Fully Qualified Collection Names) for builtin actions",
            "jinja": "Fix Jinja2 template formatting and syntax issues",
            "key-order": "Ensure proper key ordering in YAML mappings",
            "name": "Add or improve task and play names for better readability",
            "no-free-form": "Fix discouraged free-form syntax for action modules",
            "no-jinja-when": "Remove Jinja2 templating from when conditions",
            "no-log-password": "Add no_log to tasks containing password parameters",
            "partial-become": "Fix become_user tasks missing corresponding become directive",
            "yaml": "Fix YAML formatting and syntax issues reported by yamllint",
        }

        if self.console:
            table = Table(title="Ansible-lint Rules to Process")
            table.add_column("Rule", style="cyan")
            table.add_column("Description", style="white")

            for rule in rules:
                description = rule_descriptions.get(rule.id, "Unknown rule")
                table.add_row(rule.id, description)

            self.console.print(table)
        else:
            print(f"\n=== Ansible-lint Rules to Process ({len(rules)} total) ===")
            for i, rule in enumerate(rules, 1):
                description = rule_descriptions.get(rule.id, "Unknown rule")
                print(f"{i:2d}. {rule.id:25s} - {description}")

    def show_final_summary(
        self, total: int, successful: int, processed_rules: set, failed_rules: set
    ):
        """Print final processing summary."""
        if self.console:
            panel_content = f"""
[green]Successfully processed:[/green] {successful}/{total} rules
[blue]Rules with changes:[/blue] {', '.join(sorted(processed_rules)) if processed_rules else 'None'}
[red]Failed rules:[/red] {', '.join(sorted(failed_rules)) if failed_rules else 'None'}
            """
            self.console.print(
                Panel(panel_content, title="Processing Complete", border_style="green")
            )
        else:
            print("\n" + "=" * 60)
            print("PROCESSING COMPLETE")
            print("=" * 60)
            print(f"Successfully processed: {successful}/{total} rules")
            print(
                f"Rules with changes: {', '.join(sorted(processed_rules)) if processed_rules else 'None'}"
            )
            print(
                f"Failed rules: {', '.join(sorted(failed_rules)) if failed_rules else 'None'}"
            )
            print("=" * 60)


class AnsibleLintCommand:
    """Builds ansible-lint commands."""

    @staticmethod
    def fix_rule(rule: str, target_path: str) -> List[str]:
        """Build command to fix a specific rule."""
        return ["ansible-lint", f"--fix={rule}", target_path]

    @staticmethod
    def fix_tag(tag: str, target_path: str) -> List[str]:
        """Build command to fix rules by tag."""
        return ["ansible-lint", f"--fix={tag}", target_path]

    @staticmethod
    def list_rules() -> List[str]:
        """Build command to list available rules."""
        return ["ansible-lint", "--list-rules", "--nocolor"]

    @staticmethod
    def list_rules_json() -> List[str]:
        """Build command to list rules in JSON format."""
        return ["ansible-lint", "--list-rules", "-f", "json"]


class GitManager:
    """Handles git operations."""

    def __init__(self):
        pass

    def get_user_info(self) -> Tuple[str, str]:
        """Get git user name and email from git config."""
        try:
            name_result = subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True,
                text=True,
                check=True,
            )
            email_result = subprocess.run(
                ["git", "config", "user.email"],
                capture_output=True,
                text=True,
                check=True,
            )
            return name_result.stdout.strip(), email_result.stdout.strip()
        except subprocess.CalledProcessError:
            # Fallback to generic values if git config fails
            return "Unknown User", "unknown@localhost"

    def has_changes(self) -> bool:
        """Check if there are any uncommitted changes."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                check=True,
            )
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False

    def get_changed_files(self) -> List[str]:
        """Get list of files with uncommitted changes."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                check=True,
            )
            return [f.strip() for f in result.stdout.split("\n") if f.strip()]
        except subprocess.CalledProcessError:
            return []

    def add_files(self, files: List[str]) -> bool:
        """Add specific files to git staging area."""
        try:
            for file in files:
                subprocess.run(["git", "add", file], check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def create_commit(self, commit_message: str) -> bool:
        """Create a git commit with the given message."""
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".txt"
            ) as f:
                f.write(commit_message)
                temp_file = f.name

            try:
                subprocess.run(["git", "commit", "-F", temp_file], check=True)
                return True
            finally:
                os.unlink(temp_file)

        except subprocess.CalledProcessError:
            return False


class ChangeFilter:
    """Filters files and lines based on git changes."""

    def __init__(self, commit_ref: str = 'HEAD~1'):
        self.commit_ref = commit_ref
        self.changed_lines_cache: Dict[str, Set[int]] = {}

    def get_changed_lines(self, file_path: str) -> Set[int]:
        """Get line numbers that have been changed in the specified commit."""
        if file_path in self.changed_lines_cache:
            return self.changed_lines_cache[file_path]
            
        changed = set()
        try:
            # Get the diff with line numbers
            result = subprocess.run(
                ['git', 'diff', f'{self.commit_ref}', 'HEAD', '--unified=0', file_path],
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
            
        self.changed_lines_cache[file_path] = changed
        return changed

    def get_changed_ansible_files(self) -> List[str]:
        """Get YAML files changed in the specified commit."""
        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', self.commit_ref, 'HEAD'],
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

    def should_fix_line(self, file_path: str, line_num: int) -> bool:
        """Check if a line should be fixed based on git changes."""
        return line_num in self.get_changed_lines(file_path)


class RecursiveProcessor:
    """Handles recursive file discovery and processing."""

    def __init__(self):
        pass

    def find_ansible_files(self, root_path: str, changes_only: bool = False, 
                          change_filter: ChangeFilter = None) -> List[str]:
        """Find all ansible YAML files, optionally filtering to changed files."""
        if changes_only and change_filter:
            return change_filter.get_changed_ansible_files()
        
        # Recursive discovery with intelligent filtering
        root = Path(root_path)
        if not root.exists():
            return []
            
        ansible_files = []
        
        # Common ansible directories and patterns
        ansible_patterns = [
            '**/*.yml',
            '**/*.yaml'
        ]
        
        for pattern in ansible_patterns:
            for file_path in root.glob(pattern):
                if file_path.is_file():
                    # Filter to likely ansible files
                    if self._is_ansible_file(file_path):
                        ansible_files.append(str(file_path))
        
        return sorted(ansible_files)

    def _is_ansible_file(self, file_path: Path) -> bool:
        """Determine if a YAML file is likely an ansible file."""
        # Check if it's in common ansible directories
        parts = file_path.parts
        ansible_dirs = {'playbooks', 'roles', 'group_vars', 'host_vars', 'tasks', 'handlers', 'vars', 'defaults', 'meta'}
        
        if any(part in ansible_dirs for part in parts):
            return True
            
        # Check file content for ansible indicators
        try:
            with open(file_path, 'r') as f:
                content = f.read(1024)  # Read first 1KB
                ansible_indicators = [
                    '- name:', '- hosts:', 'ansible.builtin.', 'become:', 'tasks:', 'handlers:'
                ]
                return any(indicator in content for indicator in ansible_indicators)
        except:
            return False


class CommitMessageBuilder:
    """Builds concise commit messages following project conventions."""

    def __init__(self, git_manager: GitManager):
        self.git_manager = git_manager

    def _get_commit_prefix(self, target_path: str, changed_files: List[str]) -> str:
        """Generate commit prefix based on target path and actual changed files."""
        target_path_obj = Path(target_path).resolve()

        # Check if changes are actually limited to the target directory
        target_str = str(target_path_obj)
        if changed_files:
            # Check if all changed files are within the target directory
            all_in_target = all(
                str(Path(f).resolve()).startswith(target_str) for f in changed_files
            )

            # If changes go beyond target directory, use broader scope
            if not all_in_target:
                # If target was a specific role but changes are broader, use playbooks
                if "playbooks/roles/" in target_str:
                    return "playbooks:"
                # Otherwise use the broader scope we detect
                return "playbooks:"

        # Handle specific role paths (when changes are actually limited to the role)
        if "playbooks/roles/" in str(target_path_obj):
            # Extract role name from path like playbooks/roles/ansible_cfg/
            parts = target_path_obj.parts
            role_index = None
            for i, part in enumerate(parts):
                if part == "roles" and i > 0 and parts[i - 1] == "playbooks":
                    role_index = i
                    break

            if role_index and role_index + 1 < len(parts):
                role_name = parts[role_index + 1]
                return f"{role_name}:"

        # Handle general playbooks path
        if "playbooks" in str(target_path_obj):
            return "playbooks:"

        # Default fallback
        return f"{target_path_obj.name}:"

    def build_concise_commit_message(
        self, rule: str, target_path: str, changed_files: List[str]
    ) -> str:
        """Generate a concise commit message following template-based approach."""
        file_count = len(changed_files)
        prefix = self._get_commit_prefix(target_path, changed_files)

        # Concise commit format
        commit_msg = f"{prefix} ansible-lint fix {rule}\n\n"
        commit_msg += f"Fixed {rule} violations across {file_count} file{'s' if file_count != 1 else ''}.\n"

        # Get dynamic git user info
        git_name, git_email = self.git_manager.get_user_info()
        commit_msg += f"\nGenerated-by: Ansible Lint (ansible-lint-comprehensive-fixer.py)\nSigned-off-by: {git_name} <{git_email}>"

        return commit_msg


class AnsibleLintProcessor:
    """Handles ansible-lint rule processing."""

    def __init__(self, target_path: str):
        self.target_path = target_path

    def get_fixable_rules(self) -> List[RuleInfo]:
        """Extract ansible-lint rules that support --fix (have autofix tag)."""
        try:
            # Try JSON format first (more reliable parsing)
            try:
                result = subprocess.run(
                    AnsibleLintCommand.list_rules_json(),
                    capture_output=True,
                    text=True,
                    check=True,
                )

                rules_data = json.loads(result.stdout)
                fixable_rules = []

                for rule in rules_data:
                    tags = rule.get("tags", [])
                    if "autofix" in tags:
                        fixable_rules.append(
                            RuleInfo(id=rule["id"], description="", tags=tags)
                        )

                if fixable_rules:  # If we got rules via JSON, return them
                    return fixable_rules

            except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
                # Fall back to text parsing if JSON fails
                pass

            # Fallback: Parse text output
            result = subprocess.run(
                AnsibleLintCommand.list_rules(),
                capture_output=True,
                text=True,
                check=True,
            )

            fixable_rules = []
            lines = result.stdout.split("\n")

            for i, line in enumerate(lines):
                if line.strip() and line.startswith("- "):
                    clean_line = re.sub(r"\x1b\[[0-9;]*m", "", line)
                    rule_name = clean_line.strip()[2:].split()[0]

                    # Check the next line for tags
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line.startswith("tags:"):
                            tags_part = next_line.split("tags:")[1].split()[0]
                            tags = [tag.strip() for tag in tags_part.split(",")]

                            if "autofix" in tags:
                                fixable_rules.append(
                                    RuleInfo(id=rule_name, description="", tags=tags)
                                )

            return fixable_rules

        except subprocess.CalledProcessError:
            # Fallback to known fixable rules
            known_rules = [
                "command-instead-of-shell",
                "deprecated-local-action",
                "fqcn",
                "jinja",
                "key-order",
                "name",
                "no-free-form",
                "no-jinja-when",
                "no-log-password",
                "partial-become",
                "yaml",
            ]
            return [RuleInfo(id=rule, description="", tags=[]) for rule in known_rules]

    def run_fix(self, command: List[str]) -> Tuple[bool, str]:
        """Run ansible-lint fix command and check for changes."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=Config.ANSIBLE_LINT_TIMEOUT,
            )
            # Don't check return code - ansible-lint may return non-zero even on successful fixes
            return True, result.stdout + result.stderr

        except subprocess.TimeoutExpired:
            return False, f"Timeout: Command took too long to process"
        except subprocess.CalledProcessError as e:
            return False, f"Error: {e}"

    def get_autofix_tags(self) -> Dict[str, List[str]]:
        """Get available autofix tags and the rules they contain."""
        try:
            result = subprocess.run(
                AnsibleLintCommand.list_rules(),
                capture_output=True,
                text=True,
                check=True,
            )

            tags_to_rules = {}
            lines = result.stdout.split("\n")

            for i, line in enumerate(lines):
                if line.strip() and line.startswith("- "):
                    clean_line = re.sub(r"\x1b\[[0-9;]*m", "", line)
                    rule_name = clean_line.strip()[2:].split()[0]

                    # Check the next line for tags
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line.startswith("tags:"):
                            tags_part = next_line.split("tags:")[1].split()[0]
                            tags = [tag.strip() for tag in tags_part.split(",")]

                            if "autofix" in tags:
                                for tag in tags:
                                    if tag != "autofix":  # Skip the autofix tag itself
                                        if tag not in tags_to_rules:
                                            tags_to_rules[tag] = []
                                        tags_to_rules[tag].append(rule_name)

            return tags_to_rules

        except subprocess.CalledProcessError:
            return {}


class ManualFixProcessor:
    """Handles manual fixes for rules ansible-lint can't auto-fix."""
    
    # Map of short module names to their FQCN (from fix_ansible_lint.py)
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

    def __init__(self, change_filter: ChangeFilter = None):
        self.change_filter = change_filter

    def should_fix_line(self, file_path: str, line_num: int) -> bool:
        """Check if a line should be fixed based on the mode."""
        if not self.change_filter:
            return True
        return self.change_filter.should_fix_line(file_path, line_num)

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

    def apply_manual_fixes(self, file_path: str) -> Tuple[bool, str]:
        """Apply all manual fixes to a file."""
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
        
        # Check if anything changed
        if content != original_content:
            return True, content
        return False, original_content


class ComprehensiveLintFixer:
    """Main orchestrator combining ansible-lint fixes and manual fixes."""

    def __init__(
        self,
        target_path: str = "playbooks/",
        recursive: bool = False,
        changes_only: bool = False,
        enable_manual_fixes: bool = False,
        dry_run: bool = False,
        auto_accept: bool = False,
    ):
        self.target_path = target_path
        self.recursive = recursive
        self.changes_only = changes_only
        self.enable_manual_fixes = enable_manual_fixes
        self.dry_run = dry_run

        # Initialize components
        self.ui = UserInterface(auto_accept)
        self.git_manager = GitManager()
        self.commit_builder = CommitMessageBuilder(self.git_manager)
        
        # Initialize processors
        self.change_filter = ChangeFilter() if changes_only else None
        self.recursive_processor = RecursiveProcessor()
        self.ansible_processor = AnsibleLintProcessor(target_path)
        self.manual_processor = ManualFixProcessor(self.change_filter) if enable_manual_fixes else None

        # Track processing results
        self.processed_rules = set()
        self.failed_rules = set()

    def get_target_files(self) -> List[str]:
        """Get list of files to process based on configuration."""
        if self.recursive:
            return self.recursive_processor.find_ansible_files(
                self.target_path, self.changes_only, self.change_filter
            )
        elif self.changes_only and self.change_filter:
            return self.change_filter.get_changed_ansible_files()
        else:
            # Single path processing (original behavior)
            return [self.target_path]

    def _process_single_rule(self, rule: RuleInfo, target_files: List[str]) -> bool:
        """Process a single rule across target files."""
        # Determine target for ansible-lint command
        if len(target_files) == 1 and target_files[0] == self.target_path:
            # Original single-path behavior
            lint_target = self.target_path
        else:
            # For multiple files or recursive, use the base target path
            lint_target = self.target_path

        command = AnsibleLintCommand.fix_rule(rule.id, lint_target)
        success, output = self.ansible_processor.run_fix(command)

        if not success:
            return False

        if not self.git_manager.has_changes():
            return False  # No changes made

        changed_files = self.git_manager.get_changed_files()
        self.ui.print_message(
            f"✅ Rule '{rule.id}' applied successfully!", "green bold"
        )
        self.ui.print_message(f"Changed {len(changed_files)} files", "yellow")

        # Show some changed files
        for file in changed_files[: Config.MAX_CHANGED_FILES_PREVIEW]:
            self.ui.print_message(f"  - {file}", "dim")
        if len(changed_files) > Config.MAX_CHANGED_FILES_PREVIEW:
            self.ui.print_message(
                f"  ... and {len(changed_files) - Config.MAX_CHANGED_FILES_PREVIEW} more",
                "dim",
            )

        # Ask to commit
        should_commit = self.ui.prompt_user(
            f"Commit changes for rule '{rule.id}'?",
            default=True,
            auto_message=f"Auto-committing changes for rule '{rule.id}'",
        )

        if should_commit:
            if not self.git_manager.add_files(changed_files):
                self.ui.print_message("❌ Failed to stage files!", "red")
                return False

            commit_message = self.commit_builder.build_concise_commit_message(
                rule.id, self.target_path, changed_files
            )

            if self.git_manager.create_commit(commit_message):
                self.ui.print_message("✅ Committed successfully!", "green")
                return True
            else:
                self.ui.print_message("❌ Commit failed!", "red")
                return False
        else:
            self.ui.print_message("⏭️  Skipping commit", "yellow")
            return True

    def process_rules(self):
        """Main method to process all rules with comprehensive workflow."""
        # Get target files
        target_files = self.get_target_files()
        
        # Show file discovery results
        if self.recursive:
            self.ui.print_message(f"📁 Found {len(target_files)} ansible files for processing", "blue")
        elif self.changes_only:
            self.ui.print_message(f"🔄 Found {len(target_files)} changed ansible files", "blue")

        # Get fixable rules
        fixable_rules = self.ansible_processor.get_fixable_rules()
        total_rules = len(fixable_rules)

        # Show summary
        self.ui.show_rule_summary(fixable_rules)

        if self.dry_run:
            self.ui.print_message(
                f"\n🔍 DRY RUN: Would process {total_rules} fixable rules",
                "yellow bold",
            )
            self.ui.print_message("Commands that would be executed:", "cyan")
            for rule in fixable_rules:
                self.ui.print_message(
                    f"  ansible-lint --fix={rule.id} {self.target_path}", "dim"
                )
            if self.enable_manual_fixes:
                self.ui.print_message("  + Manual fixes for remaining issues", "dim")
            return

        # Ask for confirmation
        should_process = self.ui.prompt_user(
            f"\nProcess {total_rules} fixable ansible-lint rules one by one?",
            auto_message=f"Auto-processing {total_rules} fixable ansible-lint rules one by one",
        )

        if not should_process:
            return

        # Process rules
        processed = 0
        successful = 0

        for rule in fixable_rules:
            self.ui.print_message(f"\n📋 Processing rule: {rule.id}", "cyan bold")
            
            if self._process_single_rule(rule, target_files):
                successful += 1
                self.processed_rules.add(rule.id)
            else:
                if self.git_manager.has_changes():
                    self.failed_rules.add(rule.id)
                else:
                    self.ui.print_message(
                        f"⏭️  Rule '{rule.id}' - no changes needed", "dim"
                    )

            processed += 1

            # Ask if user wants to continue to next rule
            if processed < total_rules:
                should_continue = self.ui.prompt_user(
                    f"Continue to next rule? ({total_rules - processed} rules remaining)",
                    default=True,
                )
                if not should_continue:
                    self.ui.print_message(
                        "⏹️  Stopping at user request", "yellow"
                    )
                    break

        # Apply manual fixes if enabled
        if self.enable_manual_fixes and self.manual_processor:
            self.ui.print_message(f"\n🔧 Applying manual fixes...", "cyan bold")
            self._apply_manual_fixes(target_files)

        # Final summary
        self.ui.show_final_summary(
            total_rules, successful, self.processed_rules, self.failed_rules
        )

    def _apply_manual_fixes(self, target_files: List[str]):
        """Apply manual fixes to target files."""
        if not target_files or not self.manual_processor:
            return
            
        # For manual fixes, we need individual files, not directory paths
        files_to_fix = []
        for target in target_files:
            if os.path.isfile(target):
                files_to_fix.append(target)
            elif os.path.isdir(target):
                # Get files from directory
                discovered = self.recursive_processor.find_ansible_files(target)
                files_to_fix.extend(discovered)
        
        # Remove duplicates and filter if changes-only
        files_to_fix = list(set(files_to_fix))
        if self.changes_only and self.change_filter:
            changed_files = self.change_filter.get_changed_ansible_files()
            files_to_fix = [f for f in files_to_fix if f in changed_files]

        self.ui.print_message(f"🔧 Applying manual fixes to {len(files_to_fix)} files", "blue")
        
        modified_files = []
        for file_path in files_to_fix:
            was_modified, content = self.manual_processor.apply_manual_fixes(file_path)
            if was_modified:
                if not self.dry_run:
                    with open(file_path, 'w') as f:
                        f.write(content)
                modified_files.append(file_path)
                self.ui.print_message(f"  ✅ Fixed: {file_path}", "green")
        
        if modified_files:
            self.ui.print_message(f"🔧 Manual fixes applied to {len(modified_files)} files", "green")
            
            # Commit manual fixes if not dry run
            if not self.dry_run:
                should_commit = self.ui.prompt_user(
                    "Commit manual fixes?",
                    default=True,
                    auto_message="Auto-committing manual fixes",
                )
                
                if should_commit:
                    if self.git_manager.add_files(modified_files):
                        commit_message = f"playbooks: apply manual ansible-lint fixes\n\nFixed remaining issues across {len(modified_files)} files.\n\nGenerated-by: Ansible Lint (ansible-lint-comprehensive-fixer.py)\nSigned-off-by: {self.git_manager.get_user_info()[0]} <{self.git_manager.get_user_info()[1]}>"
                        
                        if self.git_manager.create_commit(commit_message):
                            self.ui.print_message("✅ Manual fixes committed successfully!", "green")
                        else:
                            self.ui.print_message("❌ Failed to commit manual fixes!", "red")
        else:
            self.ui.print_message("ℹ️  No manual fixes needed", "dim")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Comprehensive ansible-lint fixer with recursive processing and manual fixes"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="playbooks/",
        help="Path to process (default: playbooks/)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Process files recursively in directory tree",
    )
    parser.add_argument(
        "--changes-only",
        action="store_true",
        help="Only fix lines that were changed in the last commit",
    )
    parser.add_argument(
        "--enable-manual-fixes",
        action="store_true",
        help="Apply manual fixes for rules ansible-lint can't handle",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatically accept all prompts (unattended mode)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making changes",
    )
    parser.add_argument(
        "--no-rich",
        action="store_true",
        help="Disable rich formatting (use plain text)",
    )

    args = parser.parse_args()

    # Override rich if requested
    if args.no_rich:
        global RICH_AVAILABLE
        RICH_AVAILABLE = False

    # Verify we're in a git repository
    if not os.path.exists(".git"):
        print("Error: Not in a git repository")
        sys.exit(1)

    # Verify ansible-lint is available
    try:
        subprocess.run(["ansible-lint", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ansible-lint not found. Please install ansible-lint")
        sys.exit(1)

    # Create the comprehensive fixer
    fixer = ComprehensiveLintFixer(
        target_path=args.path,
        recursive=args.recursive,
        changes_only=args.changes_only,
        enable_manual_fixes=args.enable_manual_fixes,
        dry_run=args.dry_run,
        auto_accept=args.auto,
    )

    try:
        # Process rules
        fixer.process_rules()
    except KeyboardInterrupt:
        print("\n⏹️  Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()