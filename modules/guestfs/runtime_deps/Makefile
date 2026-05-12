# SPDX-License-Identifier: copyleft-next-0.3.1

PHONY += guestfs-runtime-deps-setup
guestfs-runtime-deps-setup: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/guestfs.yml \
		--tags guestfs_runtime_deps_setup \
		--extra-vars=@./extra_vars.yaml)
