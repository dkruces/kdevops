# SPDX-License-Identifier: copyleft-next-0.3.1

PHONY += kconfig-env
kconfig-env:
	$(Q)ANSIBLE_STDOUT_CALLBACK=null ansible-playbook $(ANSIBLE_VERBOSE) --connection=local \
		--inventory localhost, \
		playbooks/kconfig.yml \
		-e 'ansible_python_interpreter=/usr/bin/python3' \
		--extra-vars "topdir_path=$(TOPDIR_PATH)"
	$(Q)$(TOPDIR_PATH)/scripts/kconfig/merge_config.sh -m .config \
	$(TOPDIR_PATH)/.env.config
	$(Q)$(MAKE) -C $(TOPDIR_PATH) olddefconfig

.PHONY = $(PHONY)
