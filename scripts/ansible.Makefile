# SPDX-License-Identifier: copyleft-next-0.3.1
run_ansible_playbook_local = \
	$(Q)ansible-playbook \
		$(ANSIBLE_VERBOSE) \
		--inventory localhost, \
		--extra-vars=@./$(KDEVOPS_EXTRA_VARS) \
		--connection=local \
		$(1) \
		$(if $(2),$(2))
