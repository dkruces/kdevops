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
    """Information about an ansible-lint rule with source tracking."""

    id: str
    description: str
    tags: List[str] = None
    source: str = "ansible-lint"  # "ansible-lint" or "internal"

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
            table = Table(title="Rules to Process")
            table.add_column("Rule", style="cyan")
            table.add_column("Source", style="yellow", no_wrap=True, width=12)
            table.add_column("Description", style="white")

            for rule in rules:
                # Use rule's description if available, otherwise fallback to static descriptions
                description = (
                    rule.description
                    if hasattr(rule, "description") and rule.description
                    else rule_descriptions.get(rule.id, "Unknown rule")
                )
                source_display = (
                    "🔧 ansible-lint"
                    if rule.source == "ansible-lint"
                    else "🏠 internal"
                )
                table.add_row(rule.id, source_display, description)

            self.console.print(table)
        else:
            print(f"\n=== Rules to Process ({len(rules)} total) ===")
            for i, rule in enumerate(rules, 1):
                description = (
                    rule.description
                    if hasattr(rule, "description") and rule.description
                    else rule_descriptions.get(rule.id, "Unknown rule")
                )
                source_indicator = (
                    "[ansible-lint]" if rule.source == "ansible-lint" else "[internal]"
                )
                print(f"{i:2d}. {rule.id:25s} {source_indicator:13s} - {description}")

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

    def __init__(self, commit_ref: str = "HEAD~1"):
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
                ["git", "diff", f"{self.commit_ref}", "HEAD", "--unified=0", file_path],
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse the diff to find changed line numbers
            for line in result.stdout.split("\n"):
                if line.startswith("@@"):
                    # Format: @@ -old_start,old_count +new_start,new_count @@
                    match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
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
                ["git", "diff", "--name-only", self.commit_ref, "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            files = []
            for line in result.stdout.strip().split("\n"):
                if line and (line.endswith(".yml") or line.endswith(".yaml")):
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

    def __init__(self, exclude_patterns: List[str] = None):
        self.exclude_patterns = exclude_patterns or [
            ".git/**",
            "**/node_modules/**",
            "**/__pycache__/**",
            "**/venv/**",
            "**/env/**",
            "**/.tox/**",
            "**/build/**",
            "**/dist/**",
        ]

    def find_ansible_files(
        self,
        root_path: str,
        changes_only: bool = False,
        change_filter: ChangeFilter = None,
        include_patterns: List[str] = None,
        exclude_patterns: List[str] = None,
    ) -> List[str]:
        """Find all ansible YAML files with advanced filtering capabilities."""
        if changes_only and change_filter:
            files = change_filter.get_changed_ansible_files()
            return self._apply_filters(files, include_patterns, exclude_patterns)

        # Recursive discovery with intelligent filtering
        root = Path(root_path)
        if not root.exists():
            return []

        ansible_files = []

        # Use provided patterns or defaults
        search_patterns = include_patterns or ["**/*.yml", "**/*.yaml"]
        combined_excludes = list(self.exclude_patterns)
        if exclude_patterns:
            combined_excludes.extend(exclude_patterns)

        for pattern in search_patterns:
            for file_path in root.glob(pattern):
                if file_path.is_file():
                    # Apply exclusion filters
                    if self._should_exclude_file(file_path, combined_excludes):
                        continue

                    # Filter to likely ansible files
                    if self._is_ansible_file(file_path):
                        ansible_files.append(str(file_path))

        return sorted(ansible_files)

    def _should_exclude_file(
        self, file_path: Path, exclude_patterns: List[str]
    ) -> bool:
        """Check if file should be excluded based on patterns."""
        import fnmatch

        file_str = str(file_path)
        relative_path = (
            file_path.relative_to(Path.cwd()) if file_path.is_absolute() else file_path
        )
        relative_str = str(relative_path)

        for pattern in exclude_patterns:
            # Support both full path and relative path matching
            if fnmatch.fnmatch(file_str, pattern) or fnmatch.fnmatch(
                relative_str, pattern
            ):
                return True

            # Support directory-based exclusions
            if "/" in pattern:
                pattern_parts = pattern.split("/")
                path_parts = relative_str.split("/")

                # Check if any directory segment matches
                for i in range(len(path_parts) - len(pattern_parts) + 1):
                    segment = "/".join(path_parts[i : i + len(pattern_parts)])
                    if fnmatch.fnmatch(segment, pattern):
                        return True

        return False

    def _apply_filters(
        self,
        files: List[str],
        include_patterns: List[str] = None,
        exclude_patterns: List[str] = None,
    ) -> List[str]:
        """Apply include/exclude filters to a list of files."""
        if not files:
            return files

        filtered = []
        combined_excludes = list(self.exclude_patterns)
        if exclude_patterns:
            combined_excludes.extend(exclude_patterns)

        for file_str in files:
            file_path = Path(file_str)

            # Apply exclusion filters
            if self._should_exclude_file(file_path, combined_excludes):
                continue

            # Apply include filters if specified
            if include_patterns:
                import fnmatch

                included = False
                for pattern in include_patterns:
                    if fnmatch.fnmatch(file_str, pattern) or fnmatch.fnmatch(
                        str(
                            file_path.relative_to(Path.cwd())
                            if file_path.is_absolute()
                            else file_path
                        ),
                        pattern,
                    ):
                        included = True
                        break
                if not included:
                    continue

            filtered.append(file_str)

        return sorted(filtered)

    def _is_ansible_file(self, file_path: Path) -> bool:
        """Determine if a YAML file is likely an ansible file."""
        # Check if it's in common ansible directories
        parts = file_path.parts
        ansible_dirs = {
            "playbooks",
            "roles",
            "group_vars",
            "host_vars",
            "tasks",
            "handlers",
            "vars",
            "defaults",
            "meta",
        }

        if any(part in ansible_dirs for part in parts):
            return True

        # Check file content for ansible indicators
        try:
            with open(file_path, "r") as f:
                content = f.read(1024)  # Read first 1KB
                ansible_indicators = [
                    "- name:",
                    "- hosts:",
                    "ansible.builtin.",
                    "become:",
                    "tasks:",
                    "handlers:",
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
        """Generate a minimal commit message matching testing/lint branch format."""
        prefix = self._get_commit_prefix(target_path, changed_files)

        # Minimal commit format matching testing/lint branch
        commit_msg = f"{prefix} ansible-lint fix {rule}"

        # Add required tags per CLAUDE.md
        git_name, git_email = self.git_manager.get_user_info()
        commit_msg += (
            f"\n\nGenerated-by: Claude AI\nSigned-off-by: {git_name} <{git_email}>"
        )

        return commit_msg

    def build_tag_commit_message(
        self, tag: str, target_path: str, rules: List[str], changed_files: List[str]
    ) -> str:
        """Generate a minimal commit message for tag-based fixes."""
        prefix = self._get_commit_prefix(target_path, changed_files)

        # Use minimal format matching testing/lint branch
        commit_msg = f"{prefix} ansible-lint fix {tag} tag"

        # Add required tags per CLAUDE.md
        git_name, git_email = self.git_manager.get_user_info()
        commit_msg += (
            f"\n\nGenerated-by: Claude AI\nSigned-off-by: {git_name} <{git_email}>"
        )

        return commit_msg


class AnsibleLintProcessor:
    """Handles ansible-lint rule processing."""

    def __init__(self, target_path: str):
        self.target_path = target_path

    def run_verification(self, files: List[str] = None) -> Tuple[bool, Dict[str, int]]:
        """Run ansible-lint verification and return results summary."""
        target = files if files else [self.target_path]

        try:
            # Run ansible-lint with JSON output
            result = subprocess.run(
                ["ansible-lint", "--format", "json"] + target,
                capture_output=True,
                text=True,
                timeout=Config.ANSIBLE_LINT_TIMEOUT,
            )

            if result.stdout:
                try:
                    issues = json.loads(result.stdout)
                    # Group by rule type with context
                    by_rule = {}
                    for issue in issues:
                        rule_name = issue.get("check_name", "unknown")

                        # Create unique identifier with location context for verification table
                        location = issue.get("location", {})
                        path = location.get("path", "unknown")
                        line = location.get("lines", {}).get("begin", "unknown")
                        content = issue.get("content", {})
                        task_name = content.get("body", "").replace(
                            "Task/Handler: ", ""
                        )

                        # Create context-aware key for better identification
                        if task_name:
                            # Include task name for better context
                            rule_key = f"{rule_name} ({task_name})"
                        else:
                            # Fallback to file:line format
                            filename = Path(path).name if path != "unknown" else path
                            rule_key = f"{rule_name} ({filename}:{line})"

                        by_rule[rule_key] = by_rule.get(rule_key, 0) + 1

                    return result.returncode == 0, by_rule
                except json.JSONDecodeError:
                    return result.returncode == 0, {}
            else:
                return result.returncode == 0, {}

        except subprocess.TimeoutExpired:
            return False, {"timeout": 1}
        except subprocess.CalledProcessError:
            return False, {"error": 1}

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


class RuleFilter:
    """Handles filtering rules based on include/exclude patterns."""

    def __init__(
        self, include_patterns: List[str] = None, exclude_patterns: List[str] = None
    ):
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []

    def _matches_pattern(self, rule_id: str, pattern: str) -> bool:
        """Check if rule matches a pattern (supports wildcards)."""
        import fnmatch

        return fnmatch.fnmatch(rule_id, pattern)

    def should_process_rule(self, rule: RuleInfo) -> bool:
        """Determine if a rule should be processed based on filters."""
        # If include patterns specified, rule must match at least one
        if self.include_patterns:
            if not any(
                self._matches_pattern(rule.id, pattern)
                for pattern in self.include_patterns
            ):
                return False

        # If exclude patterns specified, rule must not match any
        if self.exclude_patterns:
            if any(
                self._matches_pattern(rule.id, pattern)
                for pattern in self.exclude_patterns
            ):
                return False

        return True

    def filter_rules(self, rules: List[RuleInfo]) -> List[RuleInfo]:
        """Filter a list of rules based on include/exclude patterns."""
        return [rule for rule in rules if self.should_process_rule(rule)]


class ManualFixProcessor:
    """Handles manual fixes for rules ansible-lint can't auto-fix."""

    # Internal rules that we provide manual fixes for
    INTERNAL_RULES = [
        RuleInfo(
            "yaml[brackets]", "Fix spacing inside brackets", ["formatting"], "internal"
        ),
        RuleInfo(
            "yaml[truthy]", "Convert yes/no to true/false", ["formatting"], "internal"
        ),
        RuleInfo(
            "jinja[spacing]", "Fix Jinja2 template spacing", ["formatting"], "internal"
        ),
        RuleInfo(
            "fqcn[action-core]",
            "Use Fully Qualified Collection Names for core modules",
            ["idiom"],
            "internal",
        ),
        RuleInfo(
            "ignore-errors",
            "Convert ignore_errors to failed_when",
            ["idiom"],
            "internal",
        ),
        RuleInfo(
            "role-path", "Fix relative role path references", ["idiom"], "internal"
        ),
    ]

    # Map of short module names to their FQCN (from fix_ansible_lint.py)
    FQCN_MAP = {
        # Core modules
        "apt": "ansible.builtin.apt",
        "apt_key": "ansible.builtin.apt_key",
        "apt_repository": "ansible.builtin.apt_repository",
        "assemble": "ansible.builtin.assemble",
        "assert": "ansible.builtin.assert",
        "async_status": "ansible.builtin.async_status",
        "blockinfile": "ansible.builtin.blockinfile",
        "command": "ansible.builtin.command",
        "copy": "ansible.builtin.copy",
        "debug": "ansible.builtin.debug",
        "dnf": "ansible.builtin.dnf",
        "fail": "ansible.builtin.fail",
        "fetch": "ansible.builtin.fetch",
        "file": "ansible.builtin.file",
        "find": "ansible.builtin.find",
        "get_url": "ansible.builtin.get_url",
        "git": "ansible.builtin.git",
        "group": "ansible.builtin.group",
        "hostname": "ansible.builtin.hostname",
        "import_playbook": "ansible.builtin.import_playbook",
        "import_role": "ansible.builtin.import_role",
        "import_tasks": "ansible.builtin.import_tasks",
        "include": "ansible.builtin.include",
        "include_role": "ansible.builtin.include_role",
        "include_tasks": "ansible.builtin.include_tasks",
        "include_vars": "ansible.builtin.include_vars",
        "lineinfile": "ansible.builtin.lineinfile",
        "meta": "ansible.builtin.meta",
        "package": "ansible.builtin.package",
        "pause": "ansible.builtin.pause",
        "ping": "ansible.builtin.ping",
        "pip": "ansible.builtin.pip",
        "raw": "ansible.builtin.raw",
        "reboot": "ansible.builtin.reboot",
        "replace": "ansible.builtin.replace",
        "rpm_key": "ansible.builtin.rpm_key",
        "script": "ansible.builtin.script",
        "service": "ansible.builtin.service",
        "service_facts": "ansible.builtin.service_facts",
        "set_fact": "ansible.builtin.set_fact",
        "setup": "ansible.builtin.setup",
        "shell": "ansible.builtin.shell",
        "slurp": "ansible.builtin.slurp",
        "stat": "ansible.builtin.stat",
        "systemd": "ansible.builtin.systemd",
        "sysctl": "ansible.builtin.sysctl",
        "template": "ansible.builtin.template",
        "unarchive": "ansible.builtin.unarchive",
        "uri": "ansible.builtin.uri",
        "user": "ansible.builtin.user",
        "wait_for": "ansible.builtin.wait_for",
        "wait_for_connection": "ansible.builtin.wait_for_connection",
        "yum": "ansible.builtin.yum",
        "yum_repository": "ansible.builtin.yum_repository",
        # Community modules
        "docker_compose": "community.docker.docker_compose",
        "docker_container": "community.docker.docker_container",
        "docker_image": "community.docker.docker_image",
        "docker_network": "community.docker.docker_network",
        "docker_volume": "community.docker.docker_volume",
        # POSIX modules
        "synchronize": "ansible.posix.synchronize",
        "mount": "ansible.posix.mount",
        "seboolean": "ansible.posix.seboolean",
        "selinux": "ansible.posix.selinux",
    }

    def __init__(self, change_filter: ChangeFilter = None):
        self.change_filter = change_filter

    @classmethod
    def get_internal_rules(cls) -> List[RuleInfo]:
        """Get list of rules that can be fixed by internal manual fixes."""
        return cls.INTERNAL_RULES

    def should_fix_line(self, file_path: str, line_num: int) -> bool:
        """Check if a line should be fixed based on the mode."""
        if not self.change_filter:
            return True
        return self.change_filter.should_fix_line(file_path, line_num)

    def fix_yaml_brackets(self, content: str, file_path: str) -> str:
        """Fix 'Too many spaces inside brackets' issues."""
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if not self.should_fix_line(file_path, i + 1):
                continue

            # Fix spacing in brackets: [ foo ] -> [foo]
            fixed_line = re.sub(r"\[\s+", "[", line)
            fixed_line = re.sub(r"\s+\]", "]", fixed_line)
            lines[i] = fixed_line
        return "\n".join(lines)

    def fix_yaml_truthy(self, content: str, file_path: str) -> str:
        """Fix truthy value issues (yes/no -> true/false)."""
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if not self.should_fix_line(file_path, i + 1):
                continue

            # Fix standalone yes/no values
            fixed_line = re.sub(r":\s+yes\s*$", ": true", line)
            fixed_line = re.sub(r":\s+no\s*$", ": false", fixed_line)
            fixed_line = re.sub(r":\s+Yes\s*$", ": true", fixed_line)
            fixed_line = re.sub(r":\s+No\s*$", ": false", fixed_line)
            fixed_line = re.sub(r":\s+YES\s*$", ": true", fixed_line)
            fixed_line = re.sub(r":\s+NO\s*$", ": false", fixed_line)
            fixed_line = re.sub(r":\s+on\s*$", ": true", fixed_line)
            fixed_line = re.sub(r":\s+off\s*$", ": false", fixed_line)
            lines[i] = fixed_line
        return "\n".join(lines)

    def fix_jinja_spacing(self, content: str, file_path: str) -> str:
        """Fix Jinja2 spacing issues."""
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if not self.should_fix_line(file_path, i + 1):
                continue

            # Fix spacing around | in Jinja2 expressions
            # Match patterns like: {{var|filter}} or "{{var|filter}}"
            def fix_jinja_expr(match):
                expr = match.group(1)
                # Add spaces around |
                expr = re.sub(r"([^|\s])\|([^|\s])", r"\1 | \2", expr)
                # Fix multiple spaces
                expr = re.sub(r"\s+\|\s+", " | ", expr)
                return "{{" + expr + "}}"

            fixed_line = re.sub(r"\{\{(.+?)\}\}", fix_jinja_expr, line)

            # Also fix in when: conditions without {{ }}
            if re.match(r"\s*(when|changed_when|failed_when):", line):
                # Extract the condition part
                parts = line.split(":", 1)
                if len(parts) == 2:
                    condition = parts[1]
                    # Fix spacing around | in conditions
                    condition = re.sub(r"([^|\s])\|([^|\s])", r"\1 | \2", condition)
                    condition = re.sub(r"\s+\|\s+", " | ", condition)
                    fixed_line = parts[0] + ":" + condition

            lines[i] = fixed_line
        return "\n".join(lines)

    def fix_fqcn(self, content: str, file_path: str) -> str:
        """Fix FQCN (Fully Qualified Collection Name) issues."""
        lines = content.split("\n")
        in_task = False
        task_start_line = 0

        for i, line in enumerate(lines):
            # Detect task start
            if re.match(r"\s*-\s+name:", line):
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
            match = re.match(r"^(\s*-?\s*)([a-z_]+)(\s*:.*)", line)
            if not match and in_task:
                # Pattern 2: Module name as a key (without dash)
                match = re.match(r"^(\s*)([a-z_]+)(\s*:.*)", line)

            if match:
                indent = match.group(1)
                module = match.group(2)
                rest = match.group(3)

                if module in self.FQCN_MAP:
                    lines[i] = indent + self.FQCN_MAP[module] + rest
                    in_task = False  # Task module found, reset

            # Reset task flag if we hit another task or play
            if re.match(r"\s*-\s+(name|hosts):", line) and i != task_start_line:
                in_task = re.match(r"\s*-\s+name:", line) is not None
                if in_task:
                    task_start_line = i

        return "\n".join(lines)

    def fix_ignore_errors(self, content: str, file_path: str) -> str:
        """
        Convert ignore_errors to failed_when where appropriate.
        This is a more conservative fix - only for simple cases.
        """
        lines = content.split("\n")
        i = 0
        while i < len(lines):
            if not self.should_fix_line(file_path, i + 1):
                i += 1
                continue

            line = lines[i]
            # Look for ignore_errors: yes/true
            if re.match(r"\s*ignore_errors:\s*(yes|true|True)", line):
                # Check if there's already a failed_when
                has_failed_when = False
                indent = len(line) - len(line.lstrip())

                # Look ahead for failed_when at the same indent level
                for j in range(i + 1, min(i + 10, len(lines))):
                    next_line = lines[j]
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent < indent and next_line.strip():
                        break
                    if re.match(r"\s*failed_when:", next_line):
                        has_failed_when = True
                        break

                # Only convert if this is safe (no existing failed_when)
                # Add a comment to indicate manual review needed
                if not has_failed_when:
                    lines[i] = line.replace(
                        "ignore_errors:", "# TODO: Review - was ignore_errors:"
                    )
                    # Add a conservative failed_when
                    lines.insert(
                        i + 1,
                        " " * indent
                        + "failed_when: false  # Always succeed - review this condition",
                    )
                    i += 1

            i += 1
        return "\n".join(lines)

    def fix_role_path(self, content: str, file_path: str) -> str:
        """Fix role path issues - remove ../roles/ prefix."""
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if not self.should_fix_line(file_path, i + 1):
                continue

            # Fix role paths in import_role and include_role
            if "role:" in line or "name:" in line:
                # Remove ../roles/ prefix from role names
                fixed_line = re.sub(
                    r'(role:|name:)\s*["\']?\.\.\/roles\/([^"\'\s]+)', r"\1 \2", line
                )
                fixed_line = re.sub(
                    r"(role:|name:)\s*\.\.\/roles\/([^\s]+)", r"\1 \2", fixed_line
                )
                lines[i] = fixed_line

        return "\n".join(lines)

    def apply_manual_fixes(self, file_path: str, rule_filter=None) -> Tuple[bool, str]:
        """Apply all manual fixes to a file, optionally filtered by rules."""
        try:
            with open(file_path, "r") as f:
                original_content = f.read()
        except Exception as e:
            return False, f"Error reading {file_path}: {e}"

        # Determine which fixes to apply based on filtering
        fixes_to_apply = []

        if not rule_filter or rule_filter.should_process_rule(
            RuleInfo("yaml[brackets]", "", ["formatting"], "internal")
        ):
            fixes_to_apply.append(self.fix_yaml_brackets)
        if not rule_filter or rule_filter.should_process_rule(
            RuleInfo("yaml[truthy]", "", ["formatting"], "internal")
        ):
            fixes_to_apply.append(self.fix_yaml_truthy)
        if not rule_filter or rule_filter.should_process_rule(
            RuleInfo("jinja[spacing]", "", ["formatting"], "internal")
        ):
            fixes_to_apply.append(self.fix_jinja_spacing)
        if not rule_filter or rule_filter.should_process_rule(
            RuleInfo("fqcn[action-core]", "", ["idiom"], "internal")
        ):
            fixes_to_apply.append(self.fix_fqcn)
        if not rule_filter or rule_filter.should_process_rule(
            RuleInfo("ignore-errors", "", ["idiom"], "internal")
        ):
            fixes_to_apply.append(self.fix_ignore_errors)
        if not rule_filter or rule_filter.should_process_rule(
            RuleInfo("role-path", "", ["idiom"], "internal")
        ):
            fixes_to_apply.append(self.fix_role_path)

        # Apply selected fixes
        content = original_content
        for fix_func in fixes_to_apply:
            content = fix_func(content, file_path)

        # Check if anything changed
        if content != original_content:
            return True, content
        return False, original_content

    def apply_single_manual_fix(
        self, file_path: str, rule_name: str
    ) -> Tuple[bool, str]:
        """Apply a single manual fix rule to a file."""
        try:
            with open(file_path, "r") as f:
                original_content = f.read()
        except Exception as e:
            return False, f"Error reading {file_path}: {e}"

        # Map rule names to fix functions
        rule_to_function = {
            "yaml[brackets]": self.fix_yaml_brackets,
            "yaml[truthy]": self.fix_yaml_truthy,
            "jinja[spacing]": self.fix_jinja_spacing,
            "fqcn[action-core]": self.fix_fqcn,
            "ignore-errors": self.fix_ignore_errors,
            "role-path": self.fix_role_path,
        }

        if rule_name not in rule_to_function:
            return False, f"Unknown manual rule: {rule_name}"

        # Apply single fix
        content = rule_to_function[rule_name](original_content, file_path)

        # Check if anything changed
        if content != original_content:
            return True, content
        else:
            return False, original_content

    def get_available_manual_rules(self, rule_filter=None) -> List[RuleInfo]:
        """Get list of available manual rules, optionally filtered."""
        all_rules = [
            RuleInfo(
                "yaml[brackets]",
                "Fix YAML bracket formatting",
                ["formatting"],
                "internal",
            ),
            RuleInfo(
                "yaml[truthy]", "Fix YAML truthy values", ["formatting"], "internal"
            ),
            RuleInfo(
                "jinja[spacing]",
                "Fix Jinja2 expression spacing",
                ["formatting"],
                "internal",
            ),
            RuleInfo(
                "fqcn[action-core]",
                "Convert to FQCN for builtin actions",
                ["idiom"],
                "internal",
            ),
            RuleInfo(
                "ignore-errors",
                "Convert ignore_errors to failed_when",
                ["idiom"],
                "internal",
            ),
            RuleInfo(
                "role-path",
                "Fix ansible.builtin.file usage in include tasks",
                ["idiom"],
                "internal",
            ),
        ]

        if rule_filter:
            return [rule for rule in all_rules if rule_filter.should_process_rule(rule)]
        return all_rules


class ComprehensiveLintFixer:
    """Main orchestrator combining ansible-lint fixes and manual fixes."""

    def __init__(
        self,
        target_path: str = "playbooks/",
        recursive: bool = False,
        changes_only: bool = False,
        enable_manual_fixes: bool = False,
        enable_ansible_lint: bool = True,
        dry_run: bool = False,
        auto_accept: bool = False,
        verify: bool = True,
        include_patterns: List[str] = None,
        exclude_patterns: List[str] = None,
        include_rules: List[str] = None,
        exclude_rules: List[str] = None,
    ):
        self.target_path = target_path
        self.recursive = recursive
        self.changes_only = changes_only
        self.enable_manual_fixes = enable_manual_fixes
        self.enable_ansible_lint = enable_ansible_lint
        self.dry_run = dry_run
        self.verify = verify
        self.include_patterns = include_patterns
        self.exclude_patterns = exclude_patterns
        self.include_rules = include_rules
        self.exclude_rules = exclude_rules

        # Initialize components
        self.ui = UserInterface(auto_accept)
        self.git_manager = GitManager()
        self.commit_builder = CommitMessageBuilder(self.git_manager)
        self.rule_filter = RuleFilter(include_rules, exclude_rules)

        # Initialize processors
        self.change_filter = ChangeFilter() if changes_only else None
        self.recursive_processor = RecursiveProcessor(exclude_patterns)
        self.ansible_processor = AnsibleLintProcessor(target_path)
        # Always create manual processor for informational commands, but only use for processing if enabled
        self.manual_processor = ManualFixProcessor(self.change_filter)

        # Track processing results
        self.processed_rules = set()
        self.failed_rules = set()

    def get_target_files(self) -> List[str]:
        """Get list of files to process based on configuration."""
        if self.recursive:
            return self.recursive_processor.find_ansible_files(
                self.target_path,
                self.changes_only,
                self.change_filter,
                self.include_patterns,
                self.exclude_patterns,
            )
        elif self.changes_only and self.change_filter:
            files = self.change_filter.get_changed_ansible_files()
            return self.recursive_processor._apply_filters(
                files, self.include_patterns, self.exclude_patterns
            )
        else:
            # Single path processing (original behavior)
            return [self.target_path]

    def show_discovered_files(self):
        """Show discovered files for filter testing."""
        target_files = self.get_target_files()

        if self.recursive or self.changes_only:
            total_files = len(target_files)
            self.ui.print_message(
                f"🔍 Discovered {total_files} ansible files", "cyan bold"
            )

            if self.include_patterns:
                self.ui.print_message(
                    f"📥 Include patterns: {', '.join(self.include_patterns)}", "blue"
                )
            if self.exclude_patterns:
                self.ui.print_message(
                    f"🚫 Exclude patterns: {', '.join(self.exclude_patterns)}", "red"
                )

            # Show files grouped by directory for better readability
            files_by_dir = {}
            for file_path in target_files:
                dir_name = str(Path(file_path).parent)
                if dir_name not in files_by_dir:
                    files_by_dir[dir_name] = []
                files_by_dir[dir_name].append(Path(file_path).name)

            # Display organized by directory
            for dir_name in sorted(files_by_dir.keys()):
                files = sorted(files_by_dir[dir_name])
                self.ui.print_message(f"\n📁 {dir_name}/", "yellow")
                for file_name in files[:10]:  # Show first 10 files per directory
                    self.ui.print_message(f"  - {file_name}", "dim")
                if len(files) > 10:
                    self.ui.print_message(
                        f"  ... and {len(files) - 10} more files", "dim"
                    )
        else:
            self.ui.print_message(f"🎯 Target: {self.target_path}", "cyan")

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
            self.ui.print_message(
                f"📁 Found {len(target_files)} ansible files for processing", "blue"
            )
        elif self.changes_only:
            self.ui.print_message(
                f"🔄 Found {len(target_files)} changed ansible files", "blue"
            )

        # Get fixable rules based on enabled types
        ansible_rules = []
        if self.enable_ansible_lint:
            ansible_rules = self.ansible_processor.get_fixable_rules()

        # Start with ansible rules if enabled
        all_rules = ansible_rules[:]

        # Add internal rules if manual fixes enabled
        if self.enable_manual_fixes and self.manual_processor:
            internal_rules = self.manual_processor.get_internal_rules()
            all_rules.extend(internal_rules)

        # Apply rule filtering
        if self.rule_filter.include_patterns or self.rule_filter.exclude_patterns:
            filtered_rules = self.rule_filter.filter_rules(all_rules)
            filtered_ansible_rules = [
                r for r in filtered_rules if r.source == "ansible-lint"
            ]
            filtered_internal_rules = [
                r for r in filtered_rules if r.source == "internal"
            ]

            # Show filtering information
            self.ui.print_message(
                f"🔍 Rule filtering: {len(all_rules)} → {len(filtered_rules)} rules "
                f"({len(filtered_ansible_rules)} ansible-lint + {len(filtered_internal_rules)} internal)",
                "yellow",
            )
            if self.rule_filter.include_patterns:
                self.ui.print_message(
                    f"   Include patterns: {', '.join(self.rule_filter.include_patterns)}",
                    "dim",
                )
            if self.rule_filter.exclude_patterns:
                self.ui.print_message(
                    f"   Exclude patterns: {', '.join(self.rule_filter.exclude_patterns)}",
                    "dim",
                )

            all_rules = filtered_rules
            ansible_rules = filtered_ansible_rules

        total_rules = len(all_rules)

        # Show summary with source information
        self.ui.show_rule_summary(all_rules)

        if self.dry_run:
            self.ui.print_message(
                f"\n🔍 DRY RUN: Would process {total_rules} rules",
                "yellow bold",
            )
            self.ui.print_message("Commands that would be executed:", "cyan")
            # Only show ansible-lint commands in dry-run (internal rules handled by manual fixes)
            for rule in ansible_rules:
                self.ui.print_message(
                    f"  ansible-lint --fix={rule.id} {self.target_path}", "dim"
                )
            if self.enable_manual_fixes and self.manual_processor:
                # Get internal rules and filter them too
                internal_rules = self.manual_processor.get_internal_rules()
                if (
                    self.rule_filter.include_patterns
                    or self.rule_filter.exclude_patterns
                ):
                    internal_rules = [
                        r
                        for r in internal_rules
                        if self.rule_filter.should_process_rule(r)
                    ]

                self.ui.print_message(
                    f"  + {len(internal_rules)} internal manual fixes:", "dim"
                )
                for rule in internal_rules:
                    self.ui.print_message(
                        f"    🏠 {rule.id}: {rule.description}", "dim"
                    )
            return

        # Ask for confirmation
        ansible_rules_count = len(ansible_rules)
        internal_rules_count = total_rules - ansible_rules_count
        should_process = self.ui.prompt_user(
            f"\nProcess {total_rules} rules ({ansible_rules_count} ansible-lint + {internal_rules_count} internal)?",
            auto_message=f"Auto-processing {total_rules} rules ({ansible_rules_count} ansible-lint + {internal_rules_count} internal)",
        )

        if not should_process:
            return

        # Process rules with enhanced progress tracking
        processed = 0
        successful = 0
        total_phases = 1 + (
            1 if self.enable_manual_fixes else 0
        )  # ansible-lint + manual fixes

        # Only process ansible-lint rules individually (internal rules handled in manual fixes phase)

        if self.ui.console and self.enable_ansible_lint and ansible_rules:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
            ) as progress:

                # Phase 1: Ansible-lint rules
                rules_task = progress.add_task(
                    "Processing ansible-lint rules...", total=ansible_rules_count
                )

                for rule in ansible_rules:
                    rule_display = (
                        f"🔧 {rule.id}"
                        if rule.source == "ansible-lint"
                        else f"🏠 {rule.id}"
                    )
                    progress.update(
                        rules_task, description=f"Processing: {rule_display}"
                    )

                    # Pause progress bar for user interaction
                    progress.stop()

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

                    # Resume progress bar
                    progress.start()
                    progress.update(rules_task, advance=1)

                # Phase 2: Manual fixes if enabled
                if self.enable_manual_fixes and self.manual_processor:
                    progress.update(
                        rules_task, description="Ansible-lint rules complete"
                    )

                    internal_rules_count = len(
                        self.manual_processor.get_internal_rules()
                    )
                    manual_task = progress.add_task(
                        f"Applying 🏠 internal fixes ({internal_rules_count} rules)...",
                        total=100,
                    )

                    progress.start()
                    self._apply_manual_fixes_with_progress(
                        target_files, progress, manual_task
                    )
                    progress.update(manual_task, completed=100)

        elif self.enable_ansible_lint and ansible_rules:
            # Fallback without rich - only process if ansible-lint is enabled
            for i, rule in enumerate(ansible_rules, 1):
                print(
                    f"\n[{i}/{ansible_rules_count}] Processing ansible-lint rule: {rule.id}"
                )
                print("=" * 50)

                if self._process_single_rule(rule, target_files):
                    successful += 1
                    self.processed_rules.add(rule.id)
                else:
                    if self.git_manager.has_changes():
                        self.failed_rules.add(rule.id)
                    else:
                        print(f"⏭️  Rule '{rule.id}' - no changes needed")

                processed += 1

                # Ask if user wants to continue to next rule
                if i < total_rules:
                    should_continue = self.ui.prompt_user(
                        f"Continue to next rule? ({total_rules - i} rules remaining)",
                        default=True,
                    )
                    if not should_continue:
                        print("⏹️  Stopping at user request")
                        break

            # Apply manual fixes if enabled (without progress)
            if self.enable_manual_fixes and self.manual_processor:
                internal_rules_count = len(self.manual_processor.get_internal_rules())
                print(f"\n🏠 Applying internal fixes ({internal_rules_count} rules)...")
                self._apply_manual_fixes(target_files)

        # Handle case where only manual fixes are enabled (no ansible-lint processing)
        elif (
            self.enable_manual_fixes
            and self.manual_processor
            and not self.enable_ansible_lint
        ):
            self.ui.print_message("🏠 Processing internal custom rules only", "blue")
            self._apply_manual_fixes(target_files)

        # Post-processing verification
        if (
            self.verify
            and not self.dry_run
            and (successful > 0 or (self.enable_manual_fixes and self.manual_processor))
        ):
            self._run_post_fix_verification(target_files)

        # Final summary
        self.ui.show_final_summary(
            total_rules, successful, self.processed_rules, self.failed_rules
        )

    def _apply_manual_fixes(self, target_files: List[str]):
        """Apply manual fixes to target files with individual rule commits."""
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

        if not files_to_fix:
            self.ui.print_message("No files to process for manual fixes", "yellow")
            return

        # Get available manual rules for individual processing
        manual_rules = self.manual_processor.get_available_manual_rules(
            self.rule_filter
        )

        if not manual_rules:
            self.ui.print_message("No manual rules to process (filtered out)", "yellow")
            return

        self.ui.print_message(
            f"🔧 Processing {len(manual_rules)} manual rules on {len(files_to_fix)} files",
            "blue",
        )

        # Process each manual rule individually
        successful_rules = []
        for i, rule in enumerate(manual_rules, 1):
            self.ui.print_message(
                f"[{i}/{len(manual_rules)}] Processing manual rule: {rule.id}", "cyan"
            )

            modified_files = []
            for file_path in files_to_fix:
                was_modified, content = self.manual_processor.apply_single_manual_fix(
                    file_path, rule.id
                )
                if was_modified:
                    if not self.dry_run:
                        with open(file_path, "w") as f:
                            f.write(content)
                    modified_files.append(file_path)

            if modified_files:
                self.ui.print_message(
                    f"  ✅ Rule '{rule.id}' modified {len(modified_files)} files",
                    "green",
                )

                # Commit this individual rule if not dry run
                if not self.dry_run:
                    should_commit = self.ui.prompt_user(
                        f"Commit changes for rule '{rule.id}'?",
                        default=True,
                        auto_message=f"Auto-committing rule '{rule.id}'",
                    )

                    if should_commit:
                        if self.git_manager.add_files(modified_files):
                            commit_message = f"playbooks: ansible-lint fix {rule.id}\n\nGenerated-by: Claude AI\nSigned-off-by: {self.git_manager.get_user_info()[0]} <{self.git_manager.get_user_info()[1]}>"

                            if self.git_manager.create_commit(commit_message):
                                self.ui.print_message(
                                    f"✅ Rule '{rule.id}' committed successfully!",
                                    "green",
                                )
                                successful_rules.append(rule.id)
                            else:
                                self.ui.print_message(
                                    f"❌ Failed to commit rule '{rule.id}'", "red"
                                )
                        else:
                            self.ui.print_message(
                                f"❌ Failed to stage files for rule '{rule.id}'", "red"
                            )
                    else:
                        self.ui.print_message(
                            f"⏭️  Skipped committing rule '{rule.id}'", "yellow"
                        )
                else:
                    successful_rules.append(rule.id)
            else:
                self.ui.print_message(
                    f"  ⏭️  Rule '{rule.id}' - no changes needed", "yellow"
                )

        if successful_rules:
            self.ui.print_message(
                f"🎉 Successfully processed {len(successful_rules)} manual rules: {', '.join(successful_rules)}",
                "green",
            )
        else:
            self.ui.print_message("ℹ️  No manual fixes needed", "dim")

    def _apply_manual_fixes_with_progress(
        self, target_files: List[str], progress, task_id
    ):
        """Apply manual fixes with Rich progress tracking and individual commits."""
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

        if not files_to_fix:
            progress.update(task_id, description="No files to process")
            return

        # Get available manual rules for individual processing
        manual_rules = self.manual_processor.get_available_manual_rules(
            self.rule_filter
        )

        if not manual_rules:
            progress.update(task_id, description="No manual rules to process")
            return

        progress.update(task_id, total=len(manual_rules))
        self.ui.print_message(
            f"🔧 Processing {len(manual_rules)} manual rules on {len(files_to_fix)} files",
            "blue",
        )

        # Process each manual rule individually
        successful_rules = []
        for i, rule in enumerate(manual_rules):
            progress.update(
                task_id, description=f"Processing rule: {rule.id}", completed=i
            )

            modified_files = []
            for file_path in files_to_fix:
                was_modified, content = self.manual_processor.apply_single_manual_fix(
                    file_path, rule.id
                )
                if was_modified:
                    if not self.dry_run:
                        with open(file_path, "w") as f:
                            f.write(content)
                    modified_files.append(file_path)

            if modified_files:
                self.ui.print_message(
                    f"  ✅ Rule '{rule.id}' modified {len(modified_files)} files",
                    "green",
                )

                # Commit this individual rule if not dry run
                if not self.dry_run:
                    # Pause progress for user interaction
                    progress.stop()

                    should_commit = self.ui.prompt_user(
                        f"Commit changes for rule '{rule.id}'?",
                        default=True,
                        auto_message=f"Auto-committing rule '{rule.id}'",
                    )

                    if should_commit:
                        if self.git_manager.add_files(modified_files):
                            commit_message = f"playbooks: ansible-lint fix {rule.id}\n\nGenerated-by: Claude AI\nSigned-off-by: {self.git_manager.get_user_info()[0]} <{self.git_manager.get_user_info()[1]}>"

                            if self.git_manager.create_commit(commit_message):
                                self.ui.print_message(
                                    f"✅ Rule '{rule.id}' committed successfully!",
                                    "green",
                                )
                                successful_rules.append(rule.id)
                            else:
                                self.ui.print_message(
                                    f"❌ Failed to commit rule '{rule.id}'", "red"
                                )
                        else:
                            self.ui.print_message(
                                f"❌ Failed to stage files for rule '{rule.id}'", "red"
                            )
                    else:
                        self.ui.print_message(
                            f"⏭️  Skipped committing rule '{rule.id}'", "yellow"
                        )

                    progress.start()
                else:
                    successful_rules.append(rule.id)
            else:
                self.ui.print_message(
                    f"  ⏭️  Rule '{rule.id}' - no changes needed", "yellow"
                )

        progress.update(task_id, completed=len(manual_rules))

        if successful_rules:
            progress.update(
                task_id,
                description=f"Successfully processed {len(successful_rules)} manual rules",
            )
            self.ui.print_message(
                f"🎉 Successfully processed {len(successful_rules)} manual rules: {', '.join(successful_rules)}",
                "green",
            )
        else:
            progress.update(task_id, description="No manual fixes needed")

    def _run_post_fix_verification(self, target_files: List[str]):
        """Run ansible-lint verification after fixes and show results."""
        self.ui.print_message(f"\n🔍 Running post-fix verification...", "cyan bold")

        # Determine what to verify
        if len(target_files) == 1 and target_files[0] == self.target_path:
            verify_target = None  # Use default target
        else:
            # For recursive/multiple files, verify the specific files
            files_to_verify = []
            for target in target_files:
                if os.path.isfile(target):
                    files_to_verify.append(target)
                elif os.path.isdir(target):
                    # Get files from directory
                    discovered = self.recursive_processor.find_ansible_files(target)
                    files_to_verify.extend(discovered)
            verify_target = list(set(files_to_verify))

        passed, remaining_issues = self.ansible_processor.run_verification(
            verify_target
        )

        if passed:
            self.ui.print_message("✅ All ansible-lint checks passed!", "green bold")
        else:
            total_issues = sum(remaining_issues.values())
            self.ui.print_message(
                f"⚠️  {total_issues} ansible-lint issues remain", "yellow"
            )

            if remaining_issues and self.ui.console:
                table = Table(title="Remaining Issues")
                table.add_column("Rule", style="cyan")
                table.add_column("Count", style="yellow")

                for rule, count in sorted(remaining_issues.items()):
                    table.add_row(rule, str(count))

                self.ui.console.print(table)
            else:
                self.ui.print_message("Remaining issues by type:", "yellow")
                for rule, count in sorted(remaining_issues.items()):
                    self.ui.print_message(f"  {rule}: {count}", "dim")

    def process_by_tag(self, tag: str):
        """Process all rules with a specific tag."""
        tags_to_rules = self.ansible_processor.get_autofix_tags()

        if tag not in tags_to_rules:
            available_tags = ", ".join(sorted(tags_to_rules.keys()))
            self.ui.print_message(
                f"Tag '{tag}' not found. Available tags: {available_tags}", "red"
            )
            return

        rules_for_tag = tags_to_rules[tag]

        # Get target files for display
        target_files = self.get_target_files()
        if self.recursive:
            self.ui.print_message(
                f"📁 Found {len(target_files)} ansible files for processing", "blue"
            )

        if self.dry_run:
            self.ui.print_message(
                f"\n🔍 DRY RUN: Would process {len(rules_for_tag)} rules with tag '{tag}'",
                "yellow bold",
            )
            self.ui.print_message(
                f"Command: ansible-lint --fix={tag} {self.target_path}", "cyan"
            )
            self.ui.print_message(f"Rules included: {', '.join(rules_for_tag)}", "dim")
            if self.enable_manual_fixes:
                self.ui.print_message("  + Manual fixes for remaining issues", "dim")
            return

        # Ask for confirmation
        should_process = self.ui.prompt_user(
            f"\nProcess {len(rules_for_tag)} rules with tag '{tag}'?",
            auto_message=f"Auto-processing {len(rules_for_tag)} rules with tag '{tag}'",
        )

        if not should_process:
            return

        # Process by tag
        command = AnsibleLintCommand.fix_tag(tag, self.target_path)
        success, output = self.ansible_processor.run_fix(command)

        if success and self.git_manager.has_changes():
            changed_files = self.git_manager.get_changed_files()
            self.ui.print_message(f"✅ Tag '{tag}' applied successfully!", "green bold")
            self.ui.print_message(f"Changed {len(changed_files)} files", "yellow")

            # Ask to commit
            should_commit = self.ui.prompt_user(
                f"Commit changes for tag '{tag}'?",
                default=True,
                auto_message=f"Auto-committing changes for tag '{tag}'",
            )

            if should_commit:
                if not self.git_manager.add_files(changed_files):
                    self.ui.print_message("❌ Failed to stage files!", "red")
                    return

                commit_message = self.commit_builder.build_tag_commit_message(
                    tag, self.target_path, rules_for_tag, changed_files
                )

                if self.git_manager.create_commit(commit_message):
                    self.ui.print_message("✅ Committed successfully!", "green")
                else:
                    self.ui.print_message("❌ Commit failed!", "red")
        else:
            self.ui.print_message(f"⏭️  Tag '{tag}' - no changes needed", "dim")

        # Apply manual fixes if enabled
        if self.enable_manual_fixes and self.manual_processor:
            self.ui.print_message(
                f"\n🔧 Applying manual fixes after tag processing...", "cyan bold"
            )
            self._apply_manual_fixes(target_files)

    def list_autofix_tags(self):
        """List all available autofix tags."""
        tags_to_rules = self.ansible_processor.get_autofix_tags()

        if self.ui.console:
            table = Table(title="Available Autofix Tags")
            table.add_column("Tag", style="cyan")
            table.add_column("Rules Count", style="yellow")
            table.add_column("Example Rules", style="white")

            for tag in sorted(tags_to_rules.keys()):
                rules = tags_to_rules[tag]
                example_rules = ", ".join(rules[:3])
                if len(rules) > 3:
                    example_rules += f", ... (+{len(rules)-3} more)"
                table.add_row(tag, str(len(rules)), example_rules)

            self.ui.console.print(table)
        else:
            print("\n=== Available Autofix Tags ===")
            for tag in sorted(tags_to_rules.keys()):
                rules = tags_to_rules[tag]
                print(f"{tag:15s} ({len(rules):2d} rules): {', '.join(rules[:3])}")
                if len(rules) > 3:
                    print(f"{'':17s} ... and {len(rules)-3} more")

        self.ui.print_message(
            f"\nUsage: --by-tag TAG  (process all rules with specific tag)", "cyan"
        )
        self.ui.print_message(
            f"       --by-tag formatting  (YAML formatting, key order, FQCN)", "dim"
        )
        self.ui.print_message(
            f"       --by-tag idiom       (naming, shell usage)", "dim"
        )
        self.ui.print_message(f"       --by-tag deprecations (old syntax fixes)", "dim")

    def list_all_rules(self):
        """List all available rules with source information."""
        # For informational purposes, always show all rules regardless of enabled flags
        ansible_rules = self.ansible_processor.get_fixable_rules()

        # Get all internal rules
        internal_rules = []
        if self.manual_processor:
            internal_rules = self.manual_processor.get_internal_rules()

        # Combine all rules
        all_rules = ansible_rules + internal_rules

        if self.ui.console:
            table = Table(title="All Available Rules", show_lines=True)
            table.add_column("Rule", style="cyan", no_wrap=True)
            table.add_column("Source", style="yellow", no_wrap=True, width=12)
            table.add_column("Tags", style="blue", no_wrap=True, width=15)
            table.add_column("Description", style="white")

            for rule in sorted(all_rules, key=lambda r: (r.source, r.id)):
                source_display = (
                    "🔧 ansible-lint"
                    if rule.source == "ansible-lint"
                    else "🏠 internal"
                )
                tags_display = ", ".join(rule.tags) if rule.tags else "N/A"
                description = (
                    rule.description
                    if hasattr(rule, "description") and rule.description
                    else "Unknown rule"
                )
                table.add_row(rule.id, source_display, tags_display, description)

            self.ui.console.print(table)
        else:
            print(f"\n=== All Available Rules ({len(all_rules)} total) ===")
            for rule in sorted(all_rules, key=lambda r: (r.source, r.id)):
                source_indicator = (
                    "[ansible-lint]" if rule.source == "ansible-lint" else "[internal]"
                )
                tags_display = ", ".join(rule.tags) if rule.tags else "N/A"
                description = (
                    rule.description
                    if hasattr(rule, "description") and rule.description
                    else "Unknown rule"
                )
                print(
                    f"{rule.id:25s} {source_indicator:13s} Tags: {tags_display:15s} - {description}"
                )

    def explain_rule(self, rule_id: str):
        """Show detailed information about a specific rule."""
        # For informational purposes, always show all rules regardless of enabled flags
        ansible_rules = self.ansible_processor.get_fixable_rules()
        internal_rules = self.manual_processor.get_internal_rules()
        all_rules = ansible_rules + internal_rules

        # Find the specific rule
        rule = next((r for r in all_rules if r.id == rule_id), None)

        if not rule:
            self.ui.print_message(f"Rule '{rule_id}' not found", "red")
            self.ui.print_message(
                f"Available rules: {', '.join(sorted([r.id for r in all_rules]))}",
                "dim",
            )
            return

        # Display detailed information
        if self.ui.console:
            panel_content = f"""[bold cyan]{rule.id}[/bold cyan]

[bold]Source:[/bold] {"🔧 ansible-lint" if rule.source == "ansible-lint" else "🏠 internal"}
[bold]Tags:[/bold] {", ".join(rule.tags) if rule.tags else "N/A"}
[bold]Description:[/bold] {rule.description}

[bold]Processing Method:[/bold]
{"• Official ansible-lint autofix using --fix=" + rule.id if rule.source == "ansible-lint" else "• Custom internal manual fix implementation"}

[bold]Usage Examples:[/bold]
• Include only this rule: --include-rules "{rule.id}"
• Exclude this rule: --exclude-rules "{rule.id}"
{"• Process by tag: --by-tag " + rule.tags[0] if rule.tags else "• No tag-based processing available"}
"""

            from rich.panel import Panel

            self.ui.console.print(
                Panel(
                    panel_content, title=f"Rule Details: {rule.id}", border_style="blue"
                )
            )
        else:
            print(f"\n=== Rule Details: {rule.id} ===")
            print(
                f"Source: {'[ansible-lint]' if rule.source == 'ansible-lint' else '[internal]'}"
            )
            print(f"Tags: {', '.join(rule.tags) if rule.tags else 'N/A'}")
            print(f"Description: {rule.description}")
            print(f"\nProcessing Method:")
            if rule.source == "ansible-lint":
                print(f"  • Official ansible-lint autofix using --fix={rule.id}")
            else:
                print(f"  • Custom internal manual fix implementation")
            print(f"\nUsage Examples:")
            print(f'  • Include only this rule: --include-rules "{rule.id}"')
            print(f'  • Exclude this rule: --exclude-rules "{rule.id}"')
            if rule.tags:
                print(f"  • Process by tag: --by-tag {rule.tags[0]}")
            else:
                print(f"  • No tag-based processing available")


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
    # Rule processing type selection (require at least one)
    parser.add_argument(
        "--fix-with-ansible-lint",
        action="store_true",
        help="Process official ansible-lint rules that have automated fixes",
    )
    parser.add_argument(
        "--fix-with-custom-rules",
        action="store_true",
        help="Process internal custom rules for additional manual fixes",
    )
    # Backward compatibility (deprecated)
    parser.add_argument(
        "--enable-manual-fixes",
        action="store_true",
        help="[DEPRECATED] Use --fix-with-custom-rules instead",
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
    parser.add_argument(
        "--by-tag",
        metavar="TAG",
        help="Process rules by tag instead of individually (e.g., formatting, idiom, deprecations)",
    )
    parser.add_argument(
        "--list-tags", action="store_true", help="List available autofix tags and exit"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run ansible-lint verification after fixes (enabled by default)",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip ansible-lint verification after fixes",
    )
    parser.add_argument(
        "--include",
        action="append",
        metavar="PATTERN",
        help="Include files matching pattern (can be used multiple times)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        metavar="PATTERN",
        help="Exclude files matching pattern (can be used multiple times)",
    )
    parser.add_argument(
        "--show-files",
        action="store_true",
        help="Show discovered files and exit (useful for testing filters)",
    )
    parser.add_argument(
        "--config",
        metavar="FILE",
        help="Load configuration from YAML/JSON file",
    )
    parser.add_argument(
        "--include-rules",
        action="append",
        metavar="PATTERN",
        help="Include only rules matching pattern (can be used multiple times)",
    )
    parser.add_argument(
        "--exclude-rules",
        action="append",
        metavar="PATTERN",
        help="Exclude rules matching pattern (can be used multiple times)",
    )
    parser.add_argument(
        "--list-rules",
        action="store_true",
        help="List all available rules with sources and exit",
    )
    parser.add_argument(
        "--explain-rule",
        metavar="RULE",
        help="Show detailed information about a specific rule and exit",
    )

    args = parser.parse_args()

    # Load configuration file if specified
    config_overrides = {}
    if args.config:
        try:
            import yaml

            with open(args.config, "r") as f:
                if args.config.endswith(".json"):
                    import json

                    config_overrides = json.load(f)
                else:
                    config_overrides = yaml.safe_load(f)
        except ImportError:
            print(
                "Warning: yaml library not available. Install with: pip install pyyaml"
            )
        except Exception as e:
            print(f"Error loading config file {args.config}: {e}")
            sys.exit(1)

    # Process comma-separated rule patterns
    def process_rule_patterns(patterns):
        """Split comma-separated patterns and flatten the list."""
        if not patterns:
            return None
        result = []
        for pattern_group in patterns:
            if "," in pattern_group:
                result.extend([p.strip() for p in pattern_group.split(",")])
            else:
                result.append(pattern_group.strip())
        return result if result else None

    args.include_rules = process_rule_patterns(args.include_rules)
    args.exclude_rules = process_rule_patterns(args.exclude_rules)

    # Apply config file overrides
    for key, value in config_overrides.items():
        if hasattr(args, key):
            # Convert lists for include/exclude patterns
            if key in ["include", "exclude", "include_rules", "exclude_rules"]:
                if isinstance(value, str):
                    value = [value]
                if getattr(args, key) is None:
                    setattr(args, key, value)
                else:
                    getattr(args, key).extend(value)
            # Only set if not already specified on command line
            elif getattr(args, key) is None or (
                isinstance(getattr(args, key), bool) and not getattr(args, key)
            ):
                setattr(args, key, value)

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

    # Handle verification flags
    verify = not args.no_verify if hasattr(args, "no_verify") else True
    if hasattr(args, "verify") and args.verify:
        verify = True

    # Handle flag transition and validation
    fix_with_ansible_lint = args.fix_with_ansible_lint
    fix_with_custom_rules = args.fix_with_custom_rules

    # Handle backward compatibility for deprecated flag
    if args.enable_manual_fixes:
        print(
            "Warning: --enable-manual-fixes is deprecated. Use --fix-with-custom-rules instead."
        )
        fix_with_custom_rules = True

    # Validate that at least one processing type is selected
    if not (fix_with_ansible_lint or fix_with_custom_rules):
        # Don't require flags for informational modes
        info_modes = [
            args.list_rules,
            args.explain_rule,
            args.show_files,
            args.list_tags,
            args.dry_run,
        ]
        if not any(info_modes):
            print("Error: Must specify at least one processing type.")
            print("\nAvailable options:")
            print("  --fix-with-ansible-lint    Process official ansible-lint rules")
            print("  --fix-with-custom-rules    Process internal custom rules")
            print(
                "  --fix-with-ansible-lint --fix-with-custom-rules    Process both types"
            )
            print("\nExample usage:")
            print("  # Process only ansible-lint rules")
            print("  ./script.py --fix-with-ansible-lint --auto playbooks/")
            print("  # Process all rule types")
            print(
                "  ./script.py --fix-with-ansible-lint --fix-with-custom-rules --auto playbooks/"
            )
            sys.exit(1)

    # Create the comprehensive fixer
    fixer = ComprehensiveLintFixer(
        target_path=args.path,
        recursive=args.recursive,
        changes_only=args.changes_only,
        enable_manual_fixes=fix_with_custom_rules,
        enable_ansible_lint=fix_with_ansible_lint,
        dry_run=args.dry_run,
        auto_accept=args.auto,
        verify=verify,
        include_patterns=args.include,
        exclude_patterns=args.exclude,
        include_rules=args.include_rules,
        exclude_rules=args.exclude_rules,
    )

    try:
        # Handle different modes
        if args.list_rules:
            fixer.list_all_rules()
        elif args.explain_rule:
            fixer.explain_rule(args.explain_rule)
        elif args.show_files:
            fixer.show_discovered_files()
        elif args.list_tags:
            fixer.list_autofix_tags()
        elif args.by_tag:
            fixer.process_by_tag(args.by_tag)
        else:
            fixer.process_rules()
    except KeyboardInterrupt:
        print("\n⏹️  Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
