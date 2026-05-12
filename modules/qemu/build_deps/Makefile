# SPDX-License-Identifier: copyleft-next-0.3.1

PHONY += qemu-build-deps-setup
qemu-build-deps-setup: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/qemu.yml \
		--tags qemu_build_deps_setup \
		--extra-vars=@./extra_vars.yaml)
