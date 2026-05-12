# SPDX-License-Identifier: copyleft-next-0.3.1

PHONY += ansible-inventory-cleanup
ansible-inventory-cleanup: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/ansible_inventory.yml \
		--tags cleanup_setup \
		--extra-vars=@./extra_vars.yaml)
