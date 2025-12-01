# SPDX-License-Identifier: copyleft-next-0.3.1

# Parse kconfig ansible verbosity setting, allow CLI to override
# Priority: CLI AV=N > Kconfig CONFIG_KDEVOPS_ANSIBLE_VERBOSE > default 0
ifneq (,$(wildcard .config))
ifneq ($(CONFIG_KDEVOPS_ANSIBLE_VERBOSE),)
ifneq ($(CONFIG_KDEVOPS_ANSIBLE_VERBOSE),0)
AV ?= $(CONFIG_KDEVOPS_ANSIBLE_VERBOSE)
endif
endif
endif

AV ?= 0
export ANSIBLE_VERBOSE := $(shell scripts/validate_av.py --av "$(AV)")

ansible-requirements:
	$(Q)ansible-galaxy install -r requirements.yml
PHONY += ansible-requirements
DEFAULT_DEPS += ansible-requirements
