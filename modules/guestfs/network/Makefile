# SPDX-License-Identifier: copyleft-next-0.3.1

PHONY += guestfs-network-setup
guestfs-network-setup: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/guestfs.yml \
		--tags guestfs_network_setup \
		--extra-vars=@./extra_vars.yaml)
