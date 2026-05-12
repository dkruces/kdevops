# SPDX-License-Identifier: copyleft-next-0.3.1

PCIE_RUNTIME_VARS := "topdir_path": $(TOPDIR_PATH)

KDEVOPS_MRPROPER += modules/libvirt/pcie_passthrough/Kconfig.generated

ifneq (,$(KDEVOPS_ENABLE_PCIE_KCONFIG))
DYNAMIC_KCONFIG += dynamic_pcipassthrough_kconfig
PCIE_RUNTIME_VARS += , "kdevops_pcie_dynamic_kconfig": True
export KDEVOPS_ENABLE_PCIE_KCONFIG
endif
ifeq (,$(KDEVOPS_ENABLE_PCIE_KCONFIG))
DYNAMIC_KCONFIG += dynamic_pcipassthrough_kconfig_touch
dynamic_pcipassthrough_kconfig_touch:
	$(Q)mkdir -p modules/libvirt/pcie_passthrough
	$(Q)touch modules/libvirt/pcie_passthrough/Kconfig.generated
endif

ifeq (y,$(CONFIG_KDEVOPS_LIBVIRT_PCIE_PASSTHROUGH))

EXTRA_VAR_FRAGMENTS_LAST += $(EXTRA_VAR_FRAGMENTS_DIR)/pcie-passthrough.yml

DYNAMIC_KCONFIG_PCIE_ARGS += pcie_passthrough_enable=True

ifeq (y,$(CONFIG_KDEVOPS_LIBVIRT_PCIE_PASSTHROUGH_TYPE_FIRST))
DYNAMIC_KCONFIG_PCIE_ARGS += pcie_passthrough_target_type_first_guest=True
DYNAMIC_KCONFIG_PCIE_ARGS += pcie_passthrough_target_type='first_guest'
endif

ifeq (y,$(CONFIG_KDEVOPS_LIBVIRT_PCIE_PASSTHROUGH_TYPE_SPECIFIC))
DYNAMIC_KCONFIG_PCIE_ARGS += pcie_passthrough_target_type_all_one_guest_name=True
DYNAMIC_KCONFIG_PCIE_ARGS += pcie_passthrough_target='$(subst ",,$(CONFIG_KDEVOPS_LIBVIRT_PCIE_PASSTHROUGH_TARGET_HOSTNAME))'
DYNAMIC_KCONFIG_PCIE_ARGS += pcie_passthrough_target_type='all_one_guest_name'
endif

ifeq (y,$(CONFIG_KDEVOPS_LIBVIRT_PCIE_PASSTHROUGH_TYPE_EACH))
DYNAMIC_KCONFIG_PCIE_ARGS += pcie_passthrough_target_type_each_per_device=True
DYNAMIC_KCONFIG_PCIE_ARGS += pcie_passthrough_target_type='each_per_device'
endif

endif # CONFIG_KDEVOPS_LIBVIRT_PCIE_PASSTHROUGH

HELP_TARGETS += dynamic-kconfig-pci-help

dynamic_pcipassthrough_kconfig:
	$(Q)ansible-playbook \
		playbooks/gen-pci-kconfig.yml \
		--extra-vars '{ $(PCIE_RUNTIME_VARS) }'

dynamic-kconfig-pci-help:
	@echo "dynconfig-pci      - enables only pci dynamically generated kconfig content"
	@echo

PHONY += dynamic-kconfig-pci-help

$(EXTRA_VAR_FRAGMENTS_DIR)/pcie-passthrough.yml: .config | $(EXTRA_VAR_FRAGMENTS_DIR)
	$(Q)$(TOPDIR)/scripts/gen_pcie_passthrough_vars.sh > $@

dynconfig-pci:
	$(Q)$(MAKE) menuconfig KDEVOPS_ENABLE_PCIE_KCONFIG=1

PHONY += dynconfig-pci
