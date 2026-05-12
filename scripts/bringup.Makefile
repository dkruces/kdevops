# SPDX-License-Identifier: copyleft-next-0.3.1

ifeq (,$(wildcard $(CURDIR)/.config))
else
# stage-2-y targets gets called after all local config files have been generated
stage-2-$(CONFIG_TERRAFORM)			+= kdevops_terraform_deps

# Libvirt install + group configuration are controller-side sudo
# operations and are no longer wired here. They are opt-in via the
# dedicated Make target `make libvirt-user-setup`; the libvirt
# orchestrator role's verify path catches the missing setup on bare
# make and fails with a structured diagnostic naming the target.

kdevops_stage_2: .config
	$(Q)$(MAKE) -f Makefile.kdevops $(stage-2-y)

ifneq (,$(stage-2-y))
DEFAULT_DEPS += kdevops_stage_2
endif

endif

bringup: env $(KDEVOPS_BRING_UP_DEPS)

status: $(KDEVOPS_STATUS_DEPS)

destroy: $(KDEVOPS_DESTROY_DEPS)

bringup-help-menu:
	@echo "Bringup targets:"
	@echo "bringup            - Brings up target hosts"
	@echo "status             - Reports the status of target hosts"
	@echo "destroy            - Destroy all target hosts"
	@echo "cleancache	  - Remove all cached images"
	@echo ""

HELP_TARGETS+=bringup-help-menu

bringup-setup-help-menu:
	@echo "Generic bring up set up targets:"
	@echo "kdevops-deps        - Installs what we need on the localhost"

HELP_TARGETS += bringup-setup-help-menu

bringup-setup-help-end:
	@echo ""

HELP_TARGETS += bringup-setup-help-end
