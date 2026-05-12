# SPDX-License-Identifier: copyleft-next-0.3.1

ifeq (y,$(CONFIG_ANSIBLE_CONFIG_PATH_CUSTOM))
ifneq ($(strip $(CONFIG_ANSIBLE_CONFIG_PATH)),)
ANSIBLE_CONFIG_PATH := $(shell echo $(CONFIG_ANSIBLE_CONFIG_PATH) | tr --delete '"')
export ANSIBLE_CONFIG := $(ANSIBLE_CONFIG_PATH)
endif
else
ANSIBLE_CONFIG_PATH := $(TOPDIR_PATH)/ansible.cfg
export ANSIBLE_CONFIG := $(ANSIBLE_CONFIG_PATH)
endif

$(ANSIBLE_CONFIG_PATH): .config
	$(call run-ansible-playbook, \
		--connection=local \
		--inventory localhost$(comma) \
		$(KDEVOPS_PLAYBOOKS_DIR)/ansible_config.yml \
		--extra-vars=@./.extra_vars_auto.yaml)
