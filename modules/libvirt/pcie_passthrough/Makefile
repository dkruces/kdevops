# SPDX-License-Identifier: copyleft-next-0.3.1

PHONY += libvirt-pcie-passthrough-setup
libvirt-pcie-passthrough-setup: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/libvirt.yml \
		--tags libvirt_pcie_passthrough_setup \
		--extra-vars=@./extra_vars.yaml)
