# SPDX-License-Identifier: copyleft-next-0.3.1

PHONY += nodes-cleanup
nodes-cleanup: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/nodes.yml \
		--tags cleanup_setup \
		--extra-vars=@./extra_vars.yaml)
