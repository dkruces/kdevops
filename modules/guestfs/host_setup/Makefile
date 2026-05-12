# SPDX-License-Identifier: copyleft-next-0.3.1

PHONY += guestfs-host-setup
guestfs-host-setup: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/guestfs.yml \
		--tags guestfs_host_setup \
		--extra-vars=@./extra_vars.yaml)
