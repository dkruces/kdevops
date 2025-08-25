#!/usr/bin/env python3
"""
Ansible-lint autofix script that processes one rule at a time.
Provides progress tracking, automatic commit message generation, and user confirmation.
"""

import subprocess
import sys
import os
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple
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


class CommitMessageBuilder:
    """Builds commit messages following project conventions."""

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

    def build_rule_commit_message(
        self, rule: str, target_path: str, description: str, changed_files: List[str]
    ) -> str:
        """Generate a commit message for a single rule fix."""
        file_count = len(changed_files)
        prefix = self._get_commit_prefix(target_path, changed_files)

        # Follow kdevops commit message format
        commit_msg = f"{prefix} ansible-lint fix {rule}\n\n"
        commit_msg += f"{description}\n\n"

        if file_count > 0:
            commit_msg += f"Fixed {rule} rule violations across {file_count} file(s).\n"

            # List some affected files if not too many
            if file_count <= Config.MAX_FILES_TO_LIST:
                commit_msg += "\nAffected files:\n"
                for file in changed_files[: Config.MAX_FILES_TO_LIST]:
                    commit_msg += f"- {file}\n"
            elif file_count > Config.MAX_FILES_TO_LIST:
                commit_msg += f"\nAffected files include:\n"
                for file in changed_files[: Config.FILES_TO_SHOW_BEFORE_TRUNCATION]:
                    commit_msg += f"- {file}\n"
                commit_msg += f"... and {file_count - Config.FILES_TO_SHOW_BEFORE_TRUNCATION} more files\n"

        commit_msg += (
            f"\nApplied using the ansible-lint-fix-rules.py script with --fix={rule}."
        )

        # Get dynamic git user info
        git_name, git_email = self.git_manager.get_user_info()
        commit_msg += f"\n\nGenerated-by: Ansible Lint (ansible-lint-fix-rules.py)\nSigned-off-by: {git_name} <{git_email}>"

        return commit_msg

    def build_tag_commit_message(
        self, tag: str, target_path: str, rules: List[str], changed_files: List[str]
    ) -> str:
        """Generate a commit message for tag-based fixes."""
        file_count = len(changed_files)
        prefix = self._get_commit_prefix(target_path, changed_files)

        commit_msg = f"{prefix} ansible-lint fix {tag} tag\n\n"
        commit_msg += f"Applied ansible-lint --fix={tag}\n"
        commit_msg += f"Rules: {', '.join(rules)}\n"

        if file_count > 0:
            commit_msg += f"\nFixed across {file_count} file(s).\n"

        commit_msg += "\nApplied using the ansible-lint-fix-rules.py script.\n"

        # Get dynamic git user info
        git_name, git_email = self.git_manager.get_user_info()
        commit_msg += f"\nGenerated-by: Ansible Lint (ansible-lint-fix-rules.py)\nSigned-off-by: {git_name} <{git_email}>"

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
                    import re

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
                    import re

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


class AnsibleLintFixer:
    """Main orchestrator for ansible-lint rule fixing."""

    def __init__(
        self,
        target_path: str = "playbooks/",
        dry_run: bool = False,
        auto_accept: bool = False,
    ):
        self.target_path = target_path
        self.dry_run = dry_run

        self.ui = UserInterface(auto_accept)
        self.processor = AnsibleLintProcessor(target_path)
        self.git_manager = GitManager()
        self.commit_builder = CommitMessageBuilder(self.git_manager)

        self.processed_rules = set()
        self.failed_rules = set()

    def _process_single_rule(self, rule: RuleInfo) -> bool:
        """Process a single rule and handle commits."""
        command = AnsibleLintCommand.fix_rule(rule.id, self.target_path)
        success, output = self.processor.run_fix(command)

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

            commit_message = self.commit_builder.build_rule_commit_message(
                rule.id,
                self.target_path,
                f"Fix {rule.id} ansible-lint rule violations",
                changed_files,
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
        """Main method to process all rules with progress tracking."""
        fixable_rules = self.processor.get_fixable_rules()
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
            return

        # Ask for confirmation
        should_process = self.ui.prompt_user(
            f"\nProcess {total_rules} fixable ansible-lint rules one by one?",
            auto_message=f"Auto-processing {total_rules} fixable ansible-lint rules one by one",
        )

        if not should_process:
            return

        # Process rules with progress bar
        processed = 0
        successful = 0

        if self.ui.console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
            ) as progress:

                task = progress.add_task(
                    "Processing ansible-lint rules...", total=total_rules
                )

                for rule in fixable_rules:
                    progress.update(task, description=f"Processing rule: {rule.id}")

                    # Pause progress bar for user interaction
                    progress.stop()

                    if self._process_single_rule(rule):
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
                    progress.update(task, advance=1)

        else:
            # Fallback without rich
            for i, rule in enumerate(fixable_rules, 1):
                print(f"\n[{i}/{total_rules}] Processing rule: {rule.id}")
                print("=" * 50)

                if self._process_single_rule(rule):
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

        # Final summary
        self.ui.show_final_summary(
            total_rules, successful, self.processed_rules, self.failed_rules
        )

    def process_by_tag(self, tag: str):
        """Process all rules with a specific tag."""
        tags_to_rules = self.processor.get_autofix_tags()

        if tag not in tags_to_rules:
            available_tags = ", ".join(sorted(tags_to_rules.keys()))
            self.ui.print_message(
                f"Tag '{tag}' not found. Available tags: {available_tags}", "red"
            )
            return

        rules_for_tag = tags_to_rules[tag]

        if self.dry_run:
            self.ui.print_message(
                f"\n🔍 DRY RUN: Would process {len(rules_for_tag)} rules with tag '{tag}'",
                "yellow bold",
            )
            self.ui.print_message(
                f"Command: ansible-lint --fix={tag} {self.target_path}", "cyan"
            )
            self.ui.print_message(f"Rules included: {', '.join(rules_for_tag)}", "dim")
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
        success, output = self.processor.run_fix(command)

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

    def list_autofix_tags(self):
        """List all available autofix tags."""
        tags_to_rules = self.processor.get_autofix_tags()

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

        print(f"\nUsage: --by-tag TAG  (process all rules with specific tag)")
        print(f"       --by-tag formatting  (YAML formatting, key order, FQCN)")
        print(f"       --by-tag idiom       (naming, shell usage)")
        print(f"       --by-tag deprecations (old syntax fixes)")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Process ansible-lint rules one at a time with progress tracking"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="playbooks/",
        help="Path to process (default: playbooks/)",
    )
    parser.add_argument(
        "--no-rich",
        action="store_true",
        help="Disable rich formatting (use plain text)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making changes",
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
        "--auto",
        action="store_true",
        help="Automatically accept all prompts (unattended mode)",
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

    # Create the fixer
    fixer = AnsibleLintFixer(args.path, args.dry_run, args.auto)

    # Handle different modes
    if args.list_tags:
        fixer.list_autofix_tags()
    elif args.by_tag:
        fixer.process_by_tag(args.by_tag)
    else:
        fixer.process_rules()


if __name__ == "__main__":
    main()
