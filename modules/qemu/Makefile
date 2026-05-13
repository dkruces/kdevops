# SPDX-License-Identifier: copyleft-next-0.3.1

qemu: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/qemu.yml \
		--extra-vars=@./extra_vars.yaml)
PHONY += qemu

qemu-install: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/qemu.yml \
		--extra-vars=@./extra_vars.yaml --tags vars$(comma)install)
PHONY += qemu-install

qemu-configure: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/qemu.yml \
		--extra-vars=@./extra_vars.yaml --tags vars$(comma)configure)
PHONY += qemu-configure

qemu-build: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/qemu.yml \
		--extra-vars=@./extra_vars.yaml --tags vars$(comma)build)
PHONY += qemu-build

qemu-help-menu:
	@echo "qemu options:"
	@echo "qemu                                 - Git clones qemu, builds and install it on localhost"
	@echo "qemu-configure                       - Configure qemu build"
	@echo "qemu-build                           - Build qemu"
	@echo "qemu-install                         - Do the install of the qemu build on localhost"
	@echo ""

HELP_TARGETS += qemu-help-menu

# Hooked into bringup-early so bare `make` does not trigger a
# heavy controller-side build; explicit `make qemu` still works.
KDEVOPS_BRING_UP_DEPS_EARLY += qemu

include modules/qemu/build_deps/Makefile
