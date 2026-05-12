# SPDX-License-Identifier: copyleft-next-0.3.1

# All extra_vars consumed by the guestfs role flow through Kconfig
# "output yaml": GUESTFS_PATH, DATA_HOME_DIR, VIRT_BUILDER_OS_VERSION,
# LIBVIRT_PROVIDER, GUESTFS_STORAGE_DIR, GUESTFS_BASE_IMAGE_DIR,
# GUESTFS_HAS_CUSTOM_RAW_IMAGE*, GUESTFS_REQUIRES_UEFI, and the
# RHEL_ORG_ID / RHEL_ACTIVATION_KEY pair in kconfigs/Kconfig.bringup.goals.
# The module spec requires this single canonical path for
# Make → Ansible value propagation; ANSIBLE_EXTRA_ARGS += foo=$(CONFIG_X)
# appenders are legacy.

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
# Distro package install (libguestfs-tools, OVMF, ...) is opt-in via
# `make guestfs-runtime-deps-setup` per the controller-side sudo
# isolation rule. The verify path in the role catches missing tools
# and fails with an actionable diagnostic naming the target.

KDEVOPS_PROVISION_METHOD		:= bringup_guestfs
KDEVOPS_PROVISION_STATUS_METHOD		:= status_guestfs
KDEVOPS_PROVISION_DESTROY_METHOD	:= destroy_guestfs

9p_linux_clone:
	$(Q)make linux-clone

$(KDEVOPS_PROVISIONED_SSH):
	$(Q)if [[ "$(CONFIG_KDEVOPS_SSH_CONFIG_UPDATE)" == "y" ]]; then \
		ansible-playbook \
			playbooks/update_ssh_config_guestfs.yml \
			--extra-vars=@./extra_vars.yaml; \
			LIBVIRT_DEFAULT_URI=$(CONFIG_LIBVIRT_URI) \
			$(TOPDIR)/scripts/update_ssh_config_guestfs.py; \
	fi
	$(Q)ansible 'baseline:dev:service' -m wait_for_connection
	$(Q)touch $(KDEVOPS_PROVISIONED_SSH)

bringup_guestfs: $(GUESTFS_BRINGUP_DEPS)
	$(Q)ansible-playbook \
		--limit 'localhost' \
		$(KDEVOPS_PLAYBOOKS_DIR)/guestfs.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags base_image
	$(Q)ansible-playbook \
		--limit 'baseline:dev:service:ai' \
		playbooks/guestfs.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags bringup
	$(Q)ansible-playbook \
		--limit 'localhost' \
		$(KDEVOPS_PLAYBOOKS_DIR)/guestfs.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags console
PHONY += bringup_guestfs

status_guestfs: $(if $(wildcard $(KDEVOPS_PROVISIONED_SSH)),$(KDEVOPS_EXTRA_VARS) $(ANSIBLE_INVENTORY_FILE))
	@if [ -f $(KDEVOPS_PROVISIONED_SSH) ]; then \
		ansible-playbook \
			playbooks/guestfs.yml \
			--extra-vars=@./extra_vars.yaml \
			--tags status ;\
	else \
		echo "status_guestfs: no provisioned state" ;\
	fi
PHONY += status_guestfs

destroy_guestfs: $(if $(wildcard $(KDEVOPS_PROVISIONED_SSH)),$(KDEVOPS_EXTRA_VARS) $(ANSIBLE_INVENTORY_FILE))
	@if [ -f $(KDEVOPS_PROVISIONED_SSH) ]; then \
		ansible-playbook \
			--limit 'baseline:dev:service' \
			playbooks/guestfs.yml \
			--extra-vars=@./extra_vars.yaml \
			--tags destroy ;\
	else \
		echo "destroy_guestfs: no provisioned state, nothing to do" ;\
	fi
	$(Q)rm -f $(KDEVOPS_PROVISIONED_SSH) $(KDEVOPS_PROVISIONED_DEVCONFIG)
PHONY += destroy_guestfs

cleancache:
	$(Q)rm -f $(CONFIG_LIBVIRT_STORAGE_POOL_PATH)/$(CONFIG_KDEVOPS_STORAGE_POOL_USER)/guestfs/base_images/*

include modules/guestfs/runtime_deps/Makefile
include modules/guestfs/network/Makefile
