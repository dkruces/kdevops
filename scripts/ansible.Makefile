# SPDX-License-Identifier: copyleft-next-0.3.1

# AV controls verbosity level
AV ?= 0

# Use Python to safely determine ANSIBLE_VERBOSE
export ANSIBLE_VERBOSE := $(shell scripts/validate_av.py --av "$(AV)")
