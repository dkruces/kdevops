# SPDX-License-Identifier: copyleft-next-0.3.1

KDEVOPS_NODES_TEMPLATE :=	$(KDEVOPS_PLAYBOOKS_DIR)/roles/nodes/templates/guestfs_nodes.j2
KDEVOPS_NODES :=		guestfs/kdevops_nodes.yaml

export KDEVOPS_PROVISIONED_SSH := $(KDEVOPS_PROVISIONED_SSH_DEFAULT_GUARD)

9P_HOST_CLONE :=
ifeq (y,$(CONFIG_BOOTLINUX_9P))
9P_HOST_CLONE := 9p_linux_clone
endif

LIBVIRT_PCIE_PASSTHROUGH :=
ifeq (y,$(CONFIG_KDEVOPS_LIBVIRT_PCIE_PASSTHROUGH))
LIBVIRT_PCIE_PASSTHROUGH := libvirt-pcie-passthrough-setup
endif

GUESTFS_BRINGUP_DEPS :=
GUESTFS_BRINGUP_DEPS +=  $(KDEVOPS_NODES)
GUESTFS_BRINGUP_DEPS +=  $(9P_HOST_CLONE)
GUESTFS_BRINGUP_DEPS +=  $(LIBVIRT_PCIE_PASSTHROUGH)

KDEVOPS_PROVISION_METHOD		:= bringup_guestfs
KDEVOPS_PROVISION_STATUS_METHOD		:= status_guestfs
KDEVOPS_PROVISION_DESTROY_METHOD	:= destroy_guestfs

9p_linux_clone:
	$(Q)make linux-clone

$(KDEVOPS_PROVISIONED_SSH):
ifeq (y,$(CONFIG_KDEVOPS_SSH_CONFIG_UPDATE))
	$(call run-ansible-playbook, \
		playbooks/update_ssh_config_guestfs.yml \
		--extra-vars=@./extra_vars.yaml)
	$(Q)LIBVIRT_DEFAULT_URI=$(CONFIG_LIBVIRT_URI) \
		$(TOPDIR)/scripts/update_ssh_config_guestfs.py
endif
	$(Q)ansible 'baseline:dev:service' -m wait_for_connection
	$(Q)touch $(KDEVOPS_PROVISIONED_SSH)

bringup_guestfs: $(GUESTFS_BRINGUP_DEPS)
	$(call run-ansible-playbook, \
		--limit localhost \
		$(KDEVOPS_PLAYBOOKS_DIR)/guestfs.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags base_image)
	$(call run-ansible-playbook, \
		--limit baseline:dev:service:ai \
		$(KDEVOPS_PLAYBOOKS_DIR)/guestfs.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags bringup)
	$(call run-ansible-playbook, \
		--limit localhost \
		$(KDEVOPS_PLAYBOOKS_DIR)/guestfs.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags console)
PHONY += bringup_guestfs

ifeq ($(wildcard $(KDEVOPS_PROVISIONED_SSH)),)
status_guestfs:
	@echo "status_guestfs: no provisioned state"
else
status_guestfs: $(KDEVOPS_EXTRA_VARS) $(ANSIBLE_INVENTORY_FILE)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/guestfs.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags status)
endif
PHONY += status_guestfs

ifeq ($(wildcard $(KDEVOPS_PROVISIONED_SSH)),)
destroy_guestfs:
	@echo "destroy_guestfs: no provisioned state, nothing to do"
else
destroy_guestfs: $(KDEVOPS_EXTRA_VARS) $(ANSIBLE_INVENTORY_FILE)
	$(call run-ansible-playbook, \
		--limit baseline:dev:service \
		$(KDEVOPS_PLAYBOOKS_DIR)/guestfs.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags destroy)
	$(Q)rm -f $(KDEVOPS_PROVISIONED_SSH) $(KDEVOPS_PROVISIONED_DEVCONFIG)
endif
PHONY += destroy_guestfs

cleancache:
	$(Q)rm -f $(CONFIG_LIBVIRT_STORAGE_POOL_PATH)/$(CONFIG_KDEVOPS_STORAGE_POOL_USER)/guestfs/base_images/*

include modules/guestfs/runtime_deps/Makefile
include modules/guestfs/network/Makefile
