# Requirements for kdevops

You must be on a recent Linux distribution, we highly recommend a rolling
Linux distribution or OS X. You must have installed:

  * Ansible
  * GNU Make
  * guestfs-tools

Then just run:

  * `make menuconfig-deps`

Then you can now run:

  * `make menuconfig`

## Python dependencies for plotting and analysis

kdevops includes Python scripts for plotting and analyzing test results from
various workflows (sysbench, fio-tests, fstests, blktests). These scripts
require Python packages like pandas, matplotlib, numpy, seaborn, and scipy.

### Option 1: Using uv or pipx (PEP 723, recommended)

If you have `uv` or `pipx` installed, the scripts can be run directly without
manual dependency installation:

```bash
uv run playbooks/python/workflows/sysbench/sysbench-tps-plot.py input.txt --output plot.png
```

Or with pipx:

```bash
pipx run playbooks/python/workflows/sysbench/sysbench-tps-plot.py input.txt --output plot.png
```

The dependencies will be automatically managed based on PEP 723 inline script
metadata.

### Option 2: Install dependencies with pip

Install all required Python packages using the requirements file:

```bash
pip3 install --user -r requirements.txt
```

Or in a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

# Supported base distributions for command and control

Examples of well tested rolling distributions recommended if using vagrant:

  * Debian testing
  * OpenSUSE Tumbleweed
  * Fedora
  * Latest Ubuntu

If using Terraform just ensure you can upgrade Terraform to the latest release
regularly.
