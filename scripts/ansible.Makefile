# SPDX-License-Identifier: copyleft-next-0.3.1
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
