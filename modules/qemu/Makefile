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

# Build QEMU as a bringup-time dependency rather than a default-make
# step. LOCALHOST_SETUP_WORK feeds DEFAULT_DEPS in the top-level
# Makefile, which ran qemu on every bare `make` invocation; that
# made `make` (no target) trigger a heavy controller-side build
# which is surprising and inconsistent with how bootlinux handles
# its build (`make linux` is explicit, `make` does not). Hooking
# into KDEVOPS_BRING_UP_DEPS_EARLY instead means:
#
#   * `make`            : controller setup only (no qemu build).
#   * `make qemu`       : explicit qemu build step.
#   * `make bringup`    : auto-builds qemu first (ninja-incremental,
#                         a no-op walks the dep graph in seconds).
#
# Mirrors the firstconfig.Makefile and journal-server.Makefile
# usage of KDEVOPS_BRING_UP_DEPS_EARLY for setup work that must
# complete before any bringup_* method runs.
KDEVOPS_BRING_UP_DEPS_EARLY += qemu

include modules/qemu/build_deps/Makefile
