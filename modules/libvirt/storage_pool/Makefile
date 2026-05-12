# SPDX-License-Identifier: copyleft-next-0.3.1

PHONY += libvirt-storage-pool-setup
libvirt-storage-pool-setup: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/libvirt.yml \
		--tags libvirt_storage_pool_setup \
		--extra-vars=@./extra_vars.yaml)
