# lucid callback

Clean, minimal Ansible output with progressive verbosity levels and optional dynamic terminal display.

## Requirements

- Ansible 2.10+
- Python 3.8+
- Set as stdout callback in ansible.cfg

## Parameters

| Parameter | Choices/Defaults | Configuration | Comments |
|-----------|------------------|---------------|----------|
| time_threshold | Default: 3.0 | ini: [callback_lucid] time_threshold | Only show task times if duration exceeds this value (seconds) |
| show_all_times | Choices: true/false<br>Default: false | ini: [callback_lucid] show_all_times | Show all task times regardless of threshold |
| show_timestamps | Choices: true/false<br>Default: false | ini: [callback_lucid] show_timestamps | Show timestamps in output |
| timestamp_format | Choices: time/datetime/iso8601<br>Default: time | ini: [callback_lucid] timestamp_format | Timestamp format when show_timestamps is enabled |
| output_mode | Choices: auto/static/dynamic<br>Default: auto | ini: [callback_lucid] output_mode | Display mode: auto detects terminal, static for CI/CD, dynamic for live updates |
| log_file | Default: (empty) | ini: [callback_lucid] log_file | Path to log file. Empty uses auto-detect: .ansible/logs/, ~/.ansible/logs/, /var/log/ansible/ |
| log_append | Choices: true/false<br>Default: false | ini: [callback_lucid] log_append | Append to existing log file instead of creating new timestamped file |

## Notes

- Only shows changed and failed tasks by default. Use `-v` to show all tasks.
- Task-level control available via `output_verbosity` variable (0=always show, 1=show at -v, 2=show at -vv).
- Dynamic mode provides live updates with spinner when running in interactive terminals.
- Automatically detects CI/CD environments (GitHub Actions, Jenkins, GitLab CI) and uses static mode.
- Logs are always full verbosity regardless of display verbosity.
- Log files include playbook name and timestamp: `<playbook>-YYYY-MM-DD_HH-MM-SS.log`
- Compatible with ansible.posix.profile_tasks callback.

## Examples

### Enable in kdevops

```bash
./scripts/kconfig/merge_config.sh -n defconfigs/configs/lucid.config
make
```

### Task-level output control

```yaml
- name: Always visible task
  debug:
    msg: "Shown at all verbosity levels"
  vars:
    output_verbosity: 0

- name: Verbose task
  debug:
    msg: "Shown with -v flag"
  vars:
    output_verbosity: 1

- name: Debug task
  debug:
    msg: "Shown with -vv flag"
  vars:
    output_verbosity: 2
```

### Force static mode

```bash
# Via environment
TERM=dumb ansible-playbook playbooks/test.yml
```

## See Also

Other Ansible stdout callback plugins integrated in kdevops:

- [community.general.diy callback](https://docs.ansible.com/projects/ansible/latest/collections/community/general/diy_callback.html)
- [community.general.dense callback](https://docs.ansible.com/projects/ansible/latest/collections/community/general/dense_callback.html)
- [ansible.posix.debug callback](https://docs.ansible.com/projects/ansible/latest/collections/ansible/posix/debug_callback.html)
