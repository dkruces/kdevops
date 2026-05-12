# SPDX-License-Identifier: copyleft-next-0.3.1

PHONY += libvirt-user-setup
libvirt-user-setup: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/libvirt.yml \
		--tags libvirt_user_setup \
		--extra-vars=@./extra_vars.yaml)
