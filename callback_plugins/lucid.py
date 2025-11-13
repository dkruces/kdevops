#!/usr/bin/env python3
"""
Lucid Ansible Callback Plugin

A modern stdout callback plugin providing:
- Clean, minimal output with progressive verbosity levels
- Task-level output control via output_verbosity variable
- Comprehensive logging (always max verbosity)
- Dynamic terminal display (Yocto/BitBake style) for interactive use
- Static output for CI/CD and non-interactive terminals
"""

from __future__ import annotations

import os
import sys
import time
import threading
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from collections import deque

from ansible.plugins.callback import CallbackBase
from ansible import constants as C

DOCUMENTATION = '''
    name: lucid
    type: stdout
    short_description: Clean, minimal Ansible output with dynamic display
    version_added: "2.10"
    description:
        - Provides clean, minimal output by default
        - Progressive verbosity levels (-v, -vv, -vvv)
        - Task-level output control via output_verbosity variable
        - Comprehensive logging independent of display verbosity
        - Dynamic live display for interactive terminals
        - Static output for CI/CD environments
    requirements:
        - Ansible 2.10+
        - Python 3.8+
    options:
        time_threshold:
            description: Only show task times if duration exceeds this value (seconds)
            default: 3.0
            type: float
            ini:
                - section: callback_lucid
                  key: time_threshold
        show_all_times:
            description: Show all task times regardless of threshold
            default: False
            type: bool
            ini:
                - section: callback_lucid
                  key: show_all_times
        show_timestamps:
            description: Show timestamps in stdout
            default: False
            type: bool
            ini:
                - section: callback_lucid
                  key: show_timestamps
        timestamp_format:
            description: Timestamp format (time, datetime, iso8601)
            default: time
            type: str
            ini:
                - section: callback_lucid
                  key: timestamp_format
        output_mode:
            description: Output display mode (auto, static, dynamic)
            default: auto
            type: str
            ini:
                - section: callback_lucid
                  key: output_mode
            choices: ['auto', 'static', 'dynamic']
        log_file:
            description: >
                Path to log file (empty for auto-detect).
                Auto-detect tries: .ansible/logs/, ~/.ansible/logs/, /var/log/ansible/
            default: ''
            type: str
            ini:
                - section: callback_lucid
                  key: log_file
        log_append:
            description: Append to existing log file instead of creating new
            default: False
            type: bool
            ini:
                - section: callback_lucid
                  key: log_append
'''


class CallbackModule(CallbackBase):
    """
    Lucid callback plugin for clean, minimal Ansible output
    with dynamic terminal display and comprehensive logging.
    """

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'lucid'

    # Spinner animation frames
    SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    def __init__(self):
        super(CallbackModule, self).__init__()

        # State tracking
        self.running_tasks: Dict[Tuple[str, str], Dict[str, Any]] = {}  # (host, task_uuid) -> task_info
        self.completed_tasks = deque(maxlen=3)  # Keep last 3 completed
        self.failed_tasks: List[Tuple] = []
        self.current_task_name: str = ''
        self.current_task_hosts: List[str] = []

        # Dynamic display state
        self.display_lines = 0
        self.last_update = 0.0
        self.spinner_index = 0
        self.is_interactive = False
        self.dynamic_mode = False
        self.update_thread: Optional[threading.Thread] = None
        self.update_thread_stop: Optional[threading.Event] = None
        self.task_lock = threading.Lock()

        # Will be set in set_options()
        self.time_threshold = 3.0
        self.show_all_times = False
        self.show_timestamps = False
        self.timestamp_format = 'time'
        self.output_mode = 'auto'
        self.log_file_path: Optional[str] = None
        self.log_append = False
        self.log_timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.log_write_failed = False

    def set_options(self, task_keys=None, var_options=None, direct=None):
        """Set plugin options from ansible.cfg"""
        super(CallbackModule, self).set_options(task_keys=task_keys, var_options=var_options, direct=direct)

        # Load configuration
        self.time_threshold = self.get_option('time_threshold')
        self.show_all_times = self.get_option('show_all_times')
        self.show_timestamps = self.get_option('show_timestamps')
        self.timestamp_format = self.get_option('timestamp_format')
        self.output_mode = self.get_option('output_mode')
        self.log_file_path = self.get_option('log_file')
        self.log_append = self.get_option('log_append')

        # Determine display mode based on configuration
        self.is_interactive = self._detect_interactive()
        if self.output_mode == 'static':
            self.dynamic_mode = False
        elif self.output_mode == 'dynamic':
            self.dynamic_mode = True
        else:  # 'auto' or any other value
            self.dynamic_mode = self.is_interactive

        # Initialize logging
        self._init_log_file()

        # Start update thread for dynamic mode
        if self.dynamic_mode:
            self._start_update_thread()

    def _detect_interactive(self) -> bool:
        """Detect if running in interactive terminal"""
        return (
            sys.stdout.isatty() and
            sys.stderr.isatty() and
            os.getenv('TERM') != 'dumb' and
            os.getenv('CI') is None and
            os.getenv('JENKINS_HOME') is None and
            os.getenv('GITHUB_ACTIONS') is None and
            os.getenv('GITLAB_CI') is None
        )

    def _init_log_file(self):
        """Initialize log file if custom path provided, otherwise defer until playbook name known"""
        if self.log_file_path:
            # Custom path provided, initialize immediately
            mode = 'a' if self.log_append else 'w'
            try:
                with open(self.log_file_path, mode) as f:
                    f.write(f"=== Ansible Playbook Log Started: {datetime.now().isoformat()} ===\n\n")
            except (PermissionError, OSError) as e:
                self._display.warning(f"Could not initialize log file {self.log_file_path}: {e}")
                self.log_file_path = None
        # If no custom path, defer log file creation until we have playbook name

    def _create_log_file(self, playbook_name: str):
        """Create log file with playbook name and timestamp"""
        if self.log_file_path:
            # Already initialized with custom path
            return

        # Remove extension from playbook name
        playbook_base = os.path.splitext(playbook_name)[0]

        # Try default locations in order (project dir first, then user home, then system)
        attempts = [
            f'.ansible/logs/{playbook_base}-{self.log_timestamp}.log',
            os.path.expanduser(f'~/.ansible/logs/{playbook_base}-{self.log_timestamp}.log'),
            f'/var/log/ansible/{playbook_base}-{self.log_timestamp}.log'
        ]

        for path in attempts:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                # Test write access
                with open(path, 'a'):
                    pass
                self.log_file_path = path
                break
            except (PermissionError, OSError):
                continue

        if self.log_file_path:
            mode = 'a' if self.log_append else 'w'
            try:
                with open(self.log_file_path, mode) as f:
                    f.write(f"=== Ansible Playbook Log Started: {datetime.now().isoformat()} ===\n")
                    f.write(f"=== Playbook: {playbook_name} ===\n\n")
            except (PermissionError, OSError) as e:
                self._display.warning(f"Could not initialize log file {self.log_file_path}: {e}")
                self.log_file_path = None

    def _write_to_log(self, message: str):
        """Write to log file with timestamp (always max verbosity)"""
        if self.log_file_path:
            timestamp = datetime.now().isoformat()
            try:
                with open(self.log_file_path, 'a') as f:
                    f.write(f"[{timestamp}] {message}\n")
            except (PermissionError, OSError) as e:
                # Warn once on first failure, then disable logging
                if not self.log_write_failed:
                    self._display.warning(f"Log write failed, disabling logging: {e}")
                    self.log_write_failed = True
                    self.log_file_path = None

    def _start_update_thread(self):
        """Start background thread for live display updates"""
        self.update_thread_stop = threading.Event()
        self.update_thread = threading.Thread(
            target=self._update_loop,
            daemon=True
        )
        self.update_thread.start()

    def _update_loop(self):
        """Update display every 0.5 seconds in dynamic mode"""
        while not self.update_thread_stop.is_set():
            if self.running_tasks:
                self._redraw_display()
            time.sleep(0.5)

    def _should_display_output(self, result, status: str) -> bool:
        """
        Determine if task output should be shown based on verbosity.

        Rules:
        - Changed tasks: ALWAYS show
        - Failed tasks: ALWAYS show
        - OK tasks: Show if current_verbosity >= task's output_verbosity
        - Skipped tasks: Only at -v or higher
        """
        # Changed and failed always show
        if status == 'changed' or status == 'failed' or status == 'unreachable':
            return True

        # Skipped only at -v
        if status == 'skipped':
            return self._display.verbosity >= 1

        # Get task verbosity setting (default is 1)
        task_verbosity = 1
        if hasattr(result, '_task_fields'):
            task_vars = result._task_fields.get('vars', {})
            task_verbosity = task_vars.get('output_verbosity', 1)
        elif hasattr(result, '_task'):
            task_vars = getattr(result._task, 'vars', {})
            task_verbosity = task_vars.get('output_verbosity', 1)

        # Compare with current verbosity
        current_verbosity = self._display.verbosity

        return current_verbosity >= task_verbosity

    def _format_timestamp(self) -> str:
        """Format timestamp based on configuration"""
        now = datetime.now()
        if self.timestamp_format == 'time':
            return now.strftime('%H:%M:%S')
        elif self.timestamp_format == 'datetime':
            return now.strftime('%Y-%m-%d %H:%M:%S')
        elif self.timestamp_format == 'iso8601':
            return now.isoformat()
        else:
            return now.strftime('%H:%M:%S')

    def _format_duration(self, seconds: float) -> str:
        """Format duration as human readable"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins}m"

    def _display_message(self, message: str, color=None):
        """Display message with optional timestamp and color"""
        if self.show_timestamps:
            timestamp = self._format_timestamp()
            message = f"[{timestamp}] {message}"

        if color:
            self._display.display(message, color=color)
        else:
            self._display.display(message)

    # ========================================================================
    # Ansible v2 Callback Methods
    # ========================================================================

    def v2_playbook_on_start(self, playbook):
        """Playbook started"""
        playbook_name = os.path.basename(playbook._file_name)

        # Create log file now that we have playbook name
        self._create_log_file(playbook_name)

        msg = f"PLAYBOOK: {playbook_name}"
        self._display_message(msg, C.COLOR_HIGHLIGHT)
        self._write_to_log(msg)

    def v2_playbook_on_play_start(self, play):
        """Play started"""
        name = play.get_name().strip()
        hosts = play.hosts
        if isinstance(hosts, list):
            hosts_str = ', '.join(hosts[:3])
            if len(hosts) > 3:
                hosts_str += f' (+{len(hosts) - 3} more)'
        else:
            hosts_str = str(hosts)

        msg = f"\nPLAY: {name} [{hosts_str}]"
        self._display_message(msg, C.COLOR_HIGHLIGHT)
        self._write_to_log(msg)

    def v2_playbook_on_task_start(self, task, is_conditional):
        """Task started"""
        self.current_task_name = task.get_name().strip()
        self.current_task_hosts = []

        # In static mode, print immediately (compact - no leading newline)
        if not self.dynamic_mode:
            msg = f"TASK: {self.current_task_name}"
            self._display_message(msg, C.COLOR_HIGHLIGHT)

        self._write_to_log(f"TASK: {self.current_task_name}")

    def v2_runner_on_start(self, host, task):
        """Task started on a host (for dynamic tracking)"""
        key = (host.name, task._uuid)
        with self.task_lock:
            self.running_tasks[key] = {
                'start_time': time.time(),
                'host': host.name,
                'task_name': task.get_name().strip()
            }

        if host.name not in self.current_task_hosts:
            self.current_task_hosts.append(host.name)

        if self.dynamic_mode:
            self._redraw_display()

    def v2_runner_on_ok(self, result):
        """Task succeeded"""
        changed = result._result.get('changed', False)
        status = 'changed' if changed else 'ok'
        self._handle_result(result, status)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        """Task failed"""
        self._handle_result(result, 'failed', ignore_errors=ignore_errors)

    def v2_runner_on_skipped(self, result):
        """Task skipped"""
        self._handle_result(result, 'skipped')

    def v2_runner_on_unreachable(self, result):
        """Host unreachable"""
        self._handle_result(result, 'unreachable')

    def v2_playbook_on_stats(self, stats):
        """Final summary"""
        # Stop update thread
        if self.update_thread_stop:
            self.update_thread_stop.set()
        if self.update_thread:
            self.update_thread.join(timeout=1.0)

        # Clear dynamic display if active
        if self.dynamic_mode and self.display_lines > 0:
            self._clear_display()

        # Print recap
        self._display_recap(stats)

        # Log file footer
        self._write_to_log(f"\n=== Playbook Completed: {datetime.now().isoformat()} ===")

        if self.log_file_path:
            self._display.display(f"\nLog: {self.log_file_path}")

    # ========================================================================
    # Result Handling
    # ========================================================================

    def _handle_result(self, result, status: str, ignore_errors: bool = False):
        """Unified result handler for all task outcomes"""
        host = result._host.name
        task_uuid = result._task._uuid
        key = (host, task_uuid)

        # Calculate duration
        with self.task_lock:
            task_info = self.running_tasks.pop(key, None)
        start_time = task_info['start_time'] if task_info else time.time()
        duration = time.time() - start_time

        # Store result data
        result_data = {
            'result': result,
            'status': status,
            'duration': duration,
            'host': host,
            'task_name': result._task.get_name().strip(),
            'ignore_errors': ignore_errors
        }

        # Track failures
        if status == 'failed' and not ignore_errors:
            self.failed_tasks.append(result_data)
        else:
            # Add to completed tasks (last 3 for dynamic mode)
            self.completed_tasks.append(result_data)

        # Log everything (max verbosity)
        self._log_result(result, status, duration)

        # Display based on mode
        if self.dynamic_mode:
            # Dynamic mode will update on next refresh
            # But if failed and not ignoring, freeze display
            if status == 'failed' and not ignore_errors:
                self._freeze_and_show_failure(result_data)
        else:
            # Static mode - display immediately
            self._display_result_static(result, status, duration)

    def _display_result_static(self, result, status: str, duration: float):
        """Display result in static mode"""
        host = result._host.name

        # Determine if we should show this result at all
        # At verbosity 0: only show changed, failed, unreachable
        # At verbosity 1+: show based on output_verbosity
        if status == 'ok' and self._display.verbosity < 1:
            # Hide OK tasks at verbosity 0
            return

        # Determine if we should show output
        show_output = self._should_display_output(result, status)

        # Skipped tasks only at verbosity 1+
        if status == 'skipped' and self._display.verbosity < 1:
            return

        # Format status line
        symbols = {
            'ok': '✓',
            'changed': '⚡',
            'failed': '✗',
            'skipped': '⊘',
            'unreachable': '⚠'
        }

        colors = {
            'ok': C.COLOR_OK,
            'changed': C.COLOR_CHANGED,
            'failed': C.COLOR_ERROR,
            'skipped': C.COLOR_SKIP,
            'unreachable': C.COLOR_UNREACHABLE
        }

        symbol = symbols.get(status, '?')
        color = colors.get(status, C.COLOR_OK)

        # Format time
        time_str = ''
        if (duration > self.time_threshold or self.show_all_times) and status not in ['skipped']:
            time_str = f" ({self._format_duration(duration)})"

        # Status line with unicode spacing (using regular spaces, not braille)
        status_line = f"  {symbol} [{host}]{time_str}"
        self._display_message(status_line, color)

        # Show output if conditions met
        if show_output:
            self._display_output(result)

    def _display_output(self, result):
        """Display stdout/stderr/msg from task result"""
        output = []
        res = result._result

        # stdout
        if 'stdout' in res and res['stdout']:
            output.append(f"\nSTDOUT:\n{res['stdout']}")

        # stderr
        if 'stderr' in res and res['stderr']:
            output.append(f"\nSTDERR:\n{res['stderr']}")

        # msg (only if no stdout)
        if 'msg' in res and res['msg'] and 'stdout' not in res:
            msg_text = res['msg']
            # Handle lists/dicts in msg
            if isinstance(msg_text, (list, dict)):
                import json
                msg_text = json.dumps(msg_text, indent=2)
            output.append(f"\nMSG:\n{msg_text}")

        if output:
            self._display.display(''.join(output))

    def _log_result(self, result, status: str, duration: float):
        """Write result to log file (always max verbosity)"""
        host = result._host.name
        res = result._result

        # Status line
        symbols = {
            'ok': '✓',
            'changed': '⚡',
            'failed': '✗',
            'skipped': '⊘',
            'unreachable': '⚠'
        }

        symbol = symbols.get(status, '?')
        time_str = self._format_duration(duration)
        log_line = f"  {symbol} [{host}] ({time_str})"
        self._write_to_log(log_line)

        # Always log full output
        if 'stdout' in res and res['stdout']:
            self._write_to_log(f"\nSTDOUT:\n{res['stdout']}\n")

        if 'stderr' in res and res['stderr']:
            self._write_to_log(f"\nSTDERR:\n{res['stderr']}\n")

        if 'msg' in res and res['msg']:
            msg_text = res['msg']
            if isinstance(msg_text, (list, dict)):
                import json
                msg_text = json.dumps(msg_text, indent=2)
            self._write_to_log(f"\nMSG:\n{msg_text}\n")

        if status == 'failed' and 'exception' in res:
            self._write_to_log(f"\nEXCEPTION:\n{res['exception']}\n")

    def _display_recap(self, stats):
        """Display final statistics"""
        self._display_message("\nPLAY RECAP", C.COLOR_HIGHLIGHT)

        hosts = sorted(stats.processed.keys())
        for host in hosts:
            summary = stats.summarize(host)

            # More compact format
            msg = (
                f"{host:25s} : "
                f"ok={summary['ok']:<3d} "
                f"changed={summary['changed']:<3d} "
                f"unreachable={summary['unreachable']:<3d} "
                f"failed={summary['failures']:<3d} "
                f"skipped={summary['skipped']:<3d}"
            )

            # Color based on status
            if summary['failures'] > 0 or summary['unreachable'] > 0:
                color = C.COLOR_ERROR
            elif summary['changed'] > 0:
                color = C.COLOR_CHANGED
            else:
                color = C.COLOR_OK

            self._display_message(msg, color)

    # ========================================================================
    # Dynamic Mode Display
    # ========================================================================

    def _redraw_display(self):
        """Redraw entire display in dynamic mode"""
        # Throttle updates (max once per 0.1s)
        now = time.time()
        if now - self.last_update < 0.1:
            return
        self.last_update = now

        # Increment spinner
        self.spinner_index = (self.spinner_index + 1) % len(self.SPINNER_FRAMES)

        # Clear previous display
        self._clear_display()

        # Build new display
        lines = []

        # Task header
        if self.current_task_name:
            lines.append(f"TASK: {self.current_task_name}")
            lines.append("")

        # Running tasks (first)
        # Create snapshot under lock to avoid holding lock during iteration
        with self.task_lock:
            tasks_snapshot = list(self.running_tasks.items())

        if tasks_snapshot:
            running_count = len(tasks_snapshot)
            total_hosts = len(self.current_task_hosts)
            lines.append(f"Running {running_count}/{total_hosts} host(s):")

            spinner = self.SPINNER_FRAMES[self.spinner_index]

            for (host, task_uuid), task_info in sorted(tasks_snapshot):
                elapsed = time.time() - task_info['start_time']
                duration_str = self._format_duration(elapsed)

                # Show spinner for tasks > 1 second
                if elapsed > 1.0:
                    lines.append(f"  ├─ [{host}] [{spinner}] {duration_str}")
                else:
                    lines.append(f"  ├─ [{host}] {duration_str}")

            lines.append("")

        # Recently completed (after running tasks)
        if self.completed_tasks:
            lines.append("Recent:")
            for task_data in self.completed_tasks:
                status = task_data['status']
                host = task_data['host']
                duration = task_data['duration']
                task_name = task_data.get('task_name', 'Unknown task')

                symbols = {'ok': '✓', 'changed': '⚡', 'skipped': '⊘'}
                symbol = symbols.get(status, '✓')

                time_str = self._format_duration(duration)
                # Truncate task name if too long
                max_task_len = 50
                if len(task_name) > max_task_len:
                    task_name = task_name[:max_task_len-3] + '...'
                lines.append(f"  {symbol} {task_name} [{host}] ({time_str})")
            lines.append("")

        # Display all lines
        if lines:
            output = '\n'.join(lines)
            # Write directly to avoid extra newlines
            sys.stdout.write(output)
            sys.stdout.flush()
            # Count actual lines printed (number of newlines + 1 for the last line)
            self.display_lines = output.count('\n') + 1
        else:
            self.display_lines = 0

    def _clear_display(self):
        """Clear dynamic display using ANSI escape codes"""
        if self.display_lines > 0:
            # Clear current line first
            sys.stdout.write('\r\033[2K')
            # Move up and clear remaining lines
            for _ in range(self.display_lines - 1):
                sys.stdout.write('\033[1A')  # Move cursor up one line
                sys.stdout.write('\033[2K')  # Clear entire line
            sys.stdout.flush()
            self.display_lines = 0

    def _freeze_and_show_failure(self, result_data):
        """Freeze display and show failure in dynamic mode"""
        # Clear dynamic display
        if self.display_lines > 0:
            self._clear_display()

        # Show failure in static format
        result = result_data['result']
        status = result_data['status']
        duration = result_data['duration']

        # Print task name if not already shown
        msg = f"TASK: {self.current_task_name}"
        self._display_message(msg, C.COLOR_HIGHLIGHT)

        # Show failure
        self._display_result_static(result, status, duration)

        # Disable dynamic mode for rest of playbook
        self.dynamic_mode = False
        if self.update_thread_stop:
            self.update_thread_stop.set()

    def __del__(self):
        """Cleanup when plugin is destroyed"""
        if self.update_thread_stop:
            self.update_thread_stop.set()
        if self.update_thread:
            self.update_thread.join(timeout=1.0)
