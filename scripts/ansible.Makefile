# SPDX-License-Identifier: copyleft-next-0.3.1

# AV controls the level of verbosity (-v, --verbose) of ansible-playbook executions.
# The number indicates the level.
AV ?= 0

_AVMAX := 6
ifeq ($(shell test $(AV) -gt $(_AVMAX) && echo OK || echo FAIL), OK)
    _AV := 6
else
    _AV := $(AV)
endif

define ANSIBLE_VERBOSE
$(shell [ $(_AV) -gt 0 ] && printf "%0.sv" $(shell seq 1 $(_AV)))
endef

ifneq ($(_AV),0)
export ANSIBLE_VERBOSE := "-$(ANSIBLE_VERBOSE)"
else
export ANSIBLE_VERBOSE :=
endif

run_ansible_playbook_local = \
	$(Q)ansible-playbook \
		$(ANSIBLE_VERBOSE) \
		--inventory localhost, \
		--extra-vars=@./$(KDEVOPS_EXTRA_VARS) \
		--connection=local \
		$(1) \
		$(if $(2),$(2))

run_ansible_playbook_local_noq = \
	ansible-playbook \
		$(ANSIBLE_VERBOSE) \
		--inventory localhost, \
		--extra-vars=@./$(KDEVOPS_EXTRA_VARS) \
		--connection=local \
		$(1) \
		$(if $(2),$(2))

run_ansible_playbook_hosts = \
	$(Q)ansible-playbook \
		$(ANSIBLE_VERBOSE) \
		--inventory $(KDEVOPS_HOSTFILE) \
		$(1) \
		$(if $(2),$(2))

run_ansible_playbook_hosts_noq = \
	ansible-playbook \
		$(ANSIBLE_VERBOSE) \
		--inventory $(KDEVOPS_HOSTFILE) \
		$(1) \
		$(if $(2),$(2))

run_ansible_playbook_hosts_extravars = \
	$(Q)ansible-playbook \
		$(ANSIBLE_VERBOSE) \
		--inventory $(KDEVOPS_HOSTFILE) \
		--extra-vars=@./$(KDEVOPS_EXTRA_VARS) \
		$(1) \
		$(if $(2),$(2))
