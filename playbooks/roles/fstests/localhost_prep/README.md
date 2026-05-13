# fstests/localhost_prep -- controller-side prep (sudo opt-in)

## When this matters

The fstests workflow's results pipeline reads the per-section JUnit
XML output that `oscheck.sh` writes inside each guest, parses it on
the controller with `python3 -c 'from junitparser import ...'`, and
folds the per-section pass/fail counts into the aggregate report
that `make fstests-baseline-results` prints. That parser needs the
`junitparser` Python module on the controller, which is supplied by
the distro package (Debian / Suse) or `pip` (RedHat, Suse fallback).

Per the spec's controller-side sudo isolation rule the install does
not run on bare `make` or as a side effect of `make fstests`; the
verify path catches the missing module and tells the user to run
the opt-in target.

## The opt-in path

```
make fstests-localhost-prep-setup
```

Drives `playbooks/fstests.yml` with
`--tags fstests_localhost_prep_setup` and runs the
`playbooks/roles/fstests/localhost_prep/setup/` sub-role under
sudo on the controller. The sub-role dispatches on
`ansible_os_family`:

- `Debian` -> `apt install python3-junitparser`
- `RedHat` -> `dnf install python3-junitxml python-pip` plus
  `pip install junitparser`
- `Suse` -> `package install python3-junit-xml python3-pip` plus
  `pip install junitparser`

After the install the verify path passes silently and `make
fstests` proceeds.

## The manual path

```
sudo apt-get install python3-junitparser           # Debian / Ubuntu
sudo dnf install python3-junitxml python-pip \
    && sudo pip install junitparser                # Fedora / RHEL
sudo zypper install python3-junit-xml python3-pip \
    && sudo pip install junitparser                # Suse
```

## What the verify path checks

`playbooks/roles/fstests/localhost_prep/verify/tasks/main.yml`
runs without sudo on every `make fstests*` invocation and tries
`python3 -c "import junitparser"`. On failure it emits the
structured diagnostic naming the opt-in target and this document.
