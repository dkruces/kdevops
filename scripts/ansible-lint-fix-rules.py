#!/usr/bin/env python3
"""
Ansible-lint autofix script that processes one rule at a time.
Provides progress tracking, automatic commit message generation, and user confirmation.
"""

import subprocess
import sys
import os
import re
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple

try:
    from rich.console import Console
    from rich.progress import (
        Progress,
        BarColumn,
        TextColumn,
        SpinnerColumn,
        MofNCompleteColumn,
    )
    from rich.prompt import Confirm, Prompt
    from rich.table import Table
    from rich.panel import Panel

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' not available. Install with: pip install rich")
    print("Falling back to basic output...")


class AnsibleLintFixer:
    """Manages ansible-lint rule-by-rule fixing with progress tracking and git integration."""

    def __init__(
        self,
        target_path: str = "playbooks/",
        dry_run: bool = False,
        auto_accept: bool = False,
    ):
        self.target_path = target_path
        self.dry_run = dry_run
        self.auto_accept = auto_accept
        self.console = Console() if RICH_AVAILABLE else None
        self.processed_rules = set()
        self.failed_rules = set()

        # Rule descriptions for better commit messages (only fixable rules)
        self.rule_descriptions = {
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

    def print_message(self, message: str, style: str = None):
        """Print message with optional styling."""
        if self.console and style:
            self.console.print(message, style=style)
        else:
            print(message)

    def get_fixable_rules(self) -> List[str]:
        """Extract ansible-lint rules that support --fix (have autofix tag)."""
        try:
            # Try JSON format first (more reliable parsing)
            try:
                result = subprocess.run(
                    ["ansible-lint", "--list-rules", "-f", "json"],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                rules_data = json.loads(result.stdout)
                fixable_rules = []

                for rule in rules_data:
                    tags = rule.get("tags", [])
                    if "autofix" in tags:
                        fixable_rules.append(rule["id"])

                if fixable_rules:  # If we got rules via JSON, return them
                    return fixable_rules

            except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
                # Fall back to text parsing if JSON fails
                pass

            # Fallback: Parse text output
            result = subprocess.run(
                ["ansible-lint", "--list-rules", "--nocolor"],
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
                                fixable_rules.append(rule_name)

            return fixable_rules

        except subprocess.CalledProcessError as e:
            self.print_message(f"Error getting ansible-lint rules: {e}", "red")
            # Fallback to known fixable rules
            return [
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

    def get_autofix_tags(self) -> Dict[str, List[str]]:
        """Get available autofix tags and the rules they contain."""
        try:
            result = subprocess.run(
                ["ansible-lint", "--list-rules", "--nocolor"],
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

        except subprocess.CalledProcessError as e:
            self.print_message(f"Error getting ansible-lint tags: {e}", "red")
            return {}

    def list_autofix_tags(self):
        """List all available autofix tags."""
        tags_to_rules = self.get_autofix_tags()

        if self.console:
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

            self.console.print(table)
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

    def process_by_tag(self, tag: str):
        """Process all rules with a specific tag."""
        tags_to_rules = self.get_autofix_tags()

        if tag not in tags_to_rules:
            available_tags = ", ".join(sorted(tags_to_rules.keys()))
            self.print_message(
                f"Tag '{tag}' not found. Available tags: {available_tags}", "red"
            )
            return

        rules_for_tag = tags_to_rules[tag]

        if self.dry_run:
            self.print_message(
                f"\n🔍 DRY RUN: Would process {len(rules_for_tag)} rules with tag '{tag}'",
                "yellow bold",
            )
            self.print_message(
                f"Command: ansible-lint --fix={tag} {self.target_path}", "cyan"
            )
            self.print_message(f"Rules included: {', '.join(rules_for_tag)}", "dim")
            return

        # Ask for confirmation
        should_process = True
        if not self.auto_accept:
            if self.console:
                should_process = Confirm.ask(
                    f"\nProcess {len(rules_for_tag)} rules with tag '{tag}'?"
                )
            else:
                try:
                    response = input(
                        f"\nProcess {len(rules_for_tag)} rules with tag '{tag}'? (y/N): "
                    )
                    should_process = response.lower() in ["y", "yes"]
                except (EOFError, KeyboardInterrupt):
                    self.print_message("\nAborted by user", "yellow")
                    return
        else:
            self.print_message(
                f"Auto-processing {len(rules_for_tag)} rules with tag '{tag}'", "cyan"
            )

        if not should_process:
            return

        # Process by tag
        success, output = self.run_ansible_lint_fix_by_tag(tag)

        if success:
            changed_files = self.get_changed_files()
            if changed_files:
                self.print_message(
                    f"✅ Tag '{tag}' applied successfully!", "green bold"
                )
                self.print_message(f"Changed {len(changed_files)} files", "yellow")

                # Ask to commit
                should_commit = True
                if not self.auto_accept:
                    if self.console:
                        should_commit = Confirm.ask(
                            f"Commit changes for tag '{tag}'?", default=True
                        )
                    else:
                        response = input(f"Commit changes for tag '{tag}'? (Y/n): ")
                        should_commit = response.lower() not in ["n", "no"]
                else:
                    self.print_message(
                        f"Auto-committing changes for tag '{tag}'", "cyan"
                    )

                if should_commit:
                    if self.create_commit_by_tag(tag, rules_for_tag):
                        self.print_message("✅ Committed successfully!", "green")
                    else:
                        self.print_message("❌ Commit failed!", "red")
            else:
                self.print_message(f"⏭️  Tag '{tag}' - no changes needed", "dim")
        else:
            self.print_message(f"❌ Error processing tag '{tag}': {output}", "red")

    def run_ansible_lint_fix_by_tag(self, tag: str) -> Tuple[bool, str]:
        """Run ansible-lint --fix for a specific tag."""
        cmd = ["ansible-lint", f"--fix={tag}", self.target_path]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            has_changes = self.check_git_changes()
            return has_changes, result.stdout + result.stderr

        except subprocess.TimeoutExpired:
            return False, f"Timeout: Tag {tag} took too long to process"
        except subprocess.CalledProcessError as e:
            return False, f"Error processing tag {tag}: {e}"

    def create_commit_by_tag(self, tag: str, rules: List[str]) -> bool:
        """Create a git commit for tag-based changes."""
        try:
            subprocess.run(["git", "add", "."], check=True)

            # Generate commit message for tag
            changed_files = self.get_changed_files()
            file_count = len(changed_files)

            # Generate commit prefix based on path
            prefix = self.get_commit_prefix()

            commit_msg = f"{prefix} ansible-lint fix {tag} tag\n\n"
            commit_msg += f"Applied ansible-lint --fix={tag}\n"
            commit_msg += f"Rules: {', '.join(rules)}\n"

            if file_count > 0:
                commit_msg += f"\nFixed across {file_count} file(s).\n"

            commit_msg += "\nApplied using the ansible-lint-fix-rules.py script.\n"

            # Get dynamic git user info
            git_name, git_email = self._get_git_user_info()
            commit_msg += f"\nGenerated-by: Ansible Lint (ansible-lint-fix-rules.py)\nSigned-off-by: {git_name} <{git_email}>"

            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".txt"
            ) as f:
                f.write(commit_msg)
                temp_file = f.name

            try:
                subprocess.run(["git", "commit", "-F", temp_file], check=True)
                return True
            finally:
                os.unlink(temp_file)

        except subprocess.CalledProcessError as e:
            self.print_message(f"Error creating commit: {e}", "red")
            return False

    def run_ansible_lint_fix(self, rule: str) -> Tuple[bool, str]:
        """Run ansible-lint --fix for a specific rule."""
        cmd = ["ansible-lint", f"--fix={rule}", self.target_path]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300  # 5 minute timeout
            )

            # Check if any files were modified
            has_changes = self.check_git_changes()

            return has_changes, result.stdout + result.stderr

        except subprocess.TimeoutExpired:
            return False, f"Timeout: Rule {rule} took too long to process"
        except subprocess.CalledProcessError as e:
            return False, f"Error processing rule {rule}: {e}"

    def check_git_changes(self) -> bool:
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

    def _get_git_user_info(self) -> Tuple[str, str]:
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

    def get_commit_prefix(self) -> str:
        """Generate commit prefix based on target path and actual changed files."""
        changed_files = self.get_changed_files()
        target_path = Path(self.target_path).resolve()

        # Check if changes are actually limited to the target directory
        target_str = str(target_path)
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
        if "playbooks/roles/" in str(target_path):
            # Extract role name from path like playbooks/roles/ansible_cfg/
            parts = target_path.parts
            role_index = None
            for i, part in enumerate(parts):
                if part == "roles" and i > 0 and parts[i - 1] == "playbooks":
                    role_index = i
                    break

            if role_index and role_index + 1 < len(parts):
                role_name = parts[role_index + 1]
                return f"{role_name}:"

        # Handle general playbooks path
        if "playbooks" in str(target_path):
            return "playbooks:"

        # Default fallback
        return f"{target_path.name}:"

    def generate_commit_message(self, rule: str) -> str:
        """Generate a commit message following project conventions."""
        rule_description = self.rule_descriptions.get(
            rule, f"Fix {rule} ansible-lint rule violations"
        )

        # Get changed files for more context
        changed_files = self.get_changed_files()
        file_count = len(changed_files)

        # Generate commit prefix based on path
        prefix = self.get_commit_prefix()

        # Follow kdevops commit message format
        commit_msg = f"{prefix} ansible-lint fix {rule}\n\n"
        commit_msg += f"{rule_description}\n\n"

        if file_count > 0:
            commit_msg += f"Fixed {rule} rule violations across {file_count} file(s).\n"

            # List some affected files if not too many
            if file_count <= 10:
                commit_msg += "\nAffected files:\n"
                for file in changed_files[:10]:
                    commit_msg += f"- {file}\n"
            elif file_count > 10:
                commit_msg += f"\nAffected files include:\n"
                for file in changed_files[:5]:
                    commit_msg += f"- {file}\n"
                commit_msg += f"... and {file_count - 5} more files\n"

        commit_msg += (
            f"\nApplied using the ansible-lint-fix-rules.py script with --fix={rule}."
        )

        # Get dynamic git user info
        git_name, git_email = self._get_git_user_info()
        commit_msg += f"\n\nGenerated-by: Ansible Lint (ansible-lint-fix-rules.py)\nSigned-off-by: {git_name} <{git_email}>"

        return commit_msg

    def create_commit(self, rule: str) -> bool:
        """Create a git commit for the rule changes."""
        try:
            # Add all changes
            subprocess.run(["git", "add", "."], check=True)

            # Generate commit message
            commit_msg = self.generate_commit_message(rule)

            # Create commit with heredoc-style message
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".txt"
            ) as f:
                f.write(commit_msg)
                temp_file = f.name

            try:
                subprocess.run(["git", "commit", "-F", temp_file], check=True)
                return True
            finally:
                os.unlink(temp_file)

        except subprocess.CalledProcessError as e:
            self.print_message(f"Error creating commit: {e}", "red")
            return False

    def show_rule_summary(self, rules: List[str]):
        """Display a summary of rules to be processed."""
        if self.console:
            table = Table(title="Ansible-lint Rules to Process")
            table.add_column("Rule", style="cyan")
            table.add_column("Description", style="white")

            for rule in rules:
                description = self.rule_descriptions.get(rule, "Unknown rule")
                table.add_row(rule, description)

            self.console.print(table)
        else:
            print(f"\n=== Ansible-lint Rules to Process ({len(rules)} total) ===")
            for i, rule in enumerate(rules, 1):
                description = self.rule_descriptions.get(rule, "Unknown rule")
                print(f"{i:2d}. {rule:25s} - {description}")

    def process_rules(self):
        """Main method to process all rules with progress tracking."""
        # Get fixable rules only
        fixable_rules = self.get_fixable_rules()
        total_rules = len(fixable_rules)

        # Show summary
        self.show_rule_summary(fixable_rules)

        if self.dry_run:
            self.print_message(
                f"\n🔍 DRY RUN: Would process {total_rules} fixable rules",
                "yellow bold",
            )
            self.print_message("Commands that would be executed:", "cyan")
            for rule in fixable_rules:
                self.print_message(
                    f"  ansible-lint --fix={rule} {self.target_path}", "dim"
                )
            return

        # Ask for confirmation
        should_process = True
        if not self.auto_accept:
            if self.console:
                should_process = Confirm.ask(
                    f"\nProcess {total_rules} fixable ansible-lint rules one by one?"
                )
            else:
                try:
                    response = input(
                        f"\nProcess {total_rules} fixable ansible-lint rules one by one? (y/N): "
                    )
                    should_process = response.lower() in ["y", "yes"]
                except (EOFError, KeyboardInterrupt):
                    self.print_message("\nAborted by user", "yellow")
                    return
        else:
            self.print_message(
                f"Auto-processing {total_rules} fixable ansible-lint rules one by one",
                "cyan",
            )

        if not should_process:
            return

        # Process rules with progress bar
        processed = 0
        successful = 0

        if self.console:
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
                    progress.update(task, description=f"Processing rule: {rule}")

                    success, output = self.run_ansible_lint_fix(rule)
                    processed += 1

                    if success:
                        successful += 1
                        self.processed_rules.add(rule)

                        # Pause progress bar for user interaction
                        progress.stop()

                        # Show changes and ask for commit
                        changed_files = self.get_changed_files()

                        self.console.print(
                            f"\n✅ Rule '{rule}' applied successfully!",
                            style="green bold",
                        )
                        self.console.print(
                            f"Changed {len(changed_files)} files", style="yellow"
                        )

                        if changed_files:
                            # Show some changed files
                            for file in changed_files[:3]:
                                self.console.print(f"  - {file}", style="dim")
                            if len(changed_files) > 3:
                                self.console.print(
                                    f"  ... and {len(changed_files) - 3} more",
                                    style="dim",
                                )

                        # Ask to commit
                        try:
                            should_commit = True
                            if not self.auto_accept:
                                should_commit = Confirm.ask(
                                    f"Commit changes for rule '{rule}'?", default=True
                                )
                            else:
                                self.console.print(
                                    f"Auto-committing changes for rule '{rule}'",
                                    style="cyan",
                                )

                            if should_commit:
                                if self.create_commit(rule):
                                    self.console.print(
                                        "✅ Committed successfully!", style="green"
                                    )
                                else:
                                    self.console.print("❌ Commit failed!", style="red")
                                    self.failed_rules.add(rule)
                            else:
                                self.console.print("⏭️  Skipping commit", style="yellow")
                        except (EOFError, KeyboardInterrupt):
                            self.console.print(
                                "\n⚠️  Interrupted by user", style="yellow"
                            )
                            progress.stop()
                            return

                        # Ask if user wants to continue to next rule
                        if processed < total_rules and not self.auto_accept:
                            try:
                                should_continue = Confirm.ask(
                                    f"Continue to next rule? ({total_rules - processed} rules remaining)",
                                    default=True,
                                )
                                if not should_continue:
                                    self.console.print(
                                        "⏹️  Stopping at user request", style="yellow"
                                    )
                                    progress.stop()
                                    break
                            except (EOFError, KeyboardInterrupt):
                                self.console.print(
                                    "\n⚠️  Interrupted by user", style="yellow"
                                )
                                progress.stop()
                                return

                        # Resume progress bar
                        progress.start()

                    else:
                        self.console.print(
                            f"⏭️  Rule '{rule}' - no changes needed", style="dim"
                        )

                    progress.update(task, advance=1)

        else:
            # Fallback without rich
            for i, rule in enumerate(fixable_rules, 1):
                print(f"\n[{i}/{total_rules}] Processing rule: {rule}")
                print("=" * 50)

                success, output = self.run_ansible_lint_fix(rule)
                processed += 1

                if success:
                    successful += 1
                    self.processed_rules.add(rule)

                    changed_files = self.get_changed_files()
                    print(f"✅ Rule '{rule}' applied successfully!")
                    print(f"Changed {len(changed_files)} files")

                    if changed_files:
                        # Show some changed files
                        for file in changed_files[:3]:
                            print(f"  - {file}")
                        if len(changed_files) > 3:
                            print(f"  ... and {len(changed_files) - 3} more")

                    # Ask to commit
                    try:
                        should_commit = True
                        if not self.auto_accept:
                            response = input(
                                f"Commit changes for rule '{rule}'? (Y/n): "
                            )
                            should_commit = response.lower() not in ["n", "no"]
                        else:
                            print(f"Auto-committing changes for rule '{rule}'")

                        if should_commit:
                            if self.create_commit(rule):
                                print("✅ Committed successfully!")
                            else:
                                print("❌ Commit failed!")
                                self.failed_rules.add(rule)
                        else:
                            print("⏭️  Skipping commit")

                        # Ask if user wants to continue to next rule
                        if i < total_rules and not self.auto_accept:
                            response = input(
                                f"Continue to next rule? ({total_rules - i} rules remaining) (Y/n): "
                            )
                            if response.lower() in ["n", "no"]:
                                print("⏹️  Stopping at user request")
                                break

                    except (EOFError, KeyboardInterrupt):
                        print("\n⚠️  Interrupted by user")
                        return

                else:
                    print(f"⏭️  Rule '{rule}' - no changes needed")

        # Final summary
        self.print_final_summary(total_rules, successful)

    def print_final_summary(self, total: int, successful: int):
        """Print final processing summary."""
        if self.console:
            panel_content = f"""
[green]Successfully processed:[/green] {successful}/{total} rules
[blue]Rules with changes:[/blue] {', '.join(sorted(self.processed_rules)) if self.processed_rules else 'None'}
[red]Failed rules:[/red] {', '.join(sorted(self.failed_rules)) if self.failed_rules else 'None'}
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
                f"Rules with changes: {', '.join(sorted(self.processed_rules)) if self.processed_rules else 'None'}"
            )
            print(
                f"Failed rules: {', '.join(sorted(self.failed_rules)) if self.failed_rules else 'None'}"
            )
            print("=" * 60)


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
