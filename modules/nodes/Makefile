# SPDX-License-Identifier: copyleft-next-0.3.1

$(KDEVOPS_NODES): .config $(ANSIBLE_CONFIG_PATH) $(KDEVOPS_NODES_TEMPLATE) $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/nodes.yml \
		--extra-vars=@./extra_vars.yaml)
