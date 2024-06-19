# SPDX-License-Identifier: copyleft-next-0.3.1
fsbenchmarks-help-menu:
	@echo "fsbenchmarks options:"
	@echo "fsbenchmarks   - Run selected fsbenchmarks sequentially"
	@echo ""

HELP_TARGETS += fsbenchmarks-help-menu

FSBENCHMARKS_TAGS :=
FSBENCHMARKS_ARGS :=
FSBENCHMARKS_FSTYP:=$(subst ",,$(CONFIG_FSBENCHMARKS_FSTYP))

include $(TOPDIR)/workflows/fsbenchmarks/tmpfs/Makefile
FSTESTS_ARGS += fsbenchmarks_fstyp='$(FSBENCHMARKS_FSTYP)'

FSBENCHMARKS_TAGS := $(subst $(space),$(comma),$(FSBENCHMARKS_TAGS))

FSBENCHMARKS_TESTS := $(subst $(space),$(comma),$(FSBENCHMARKS_TESTS))
FSBENCHMARKS_ARGS += fsbenchmarks_tests = '$(FSBENCHMARKS_TESTS)'

WORKFLOW_ARGS += $(FSBENCHMARKKS_ARGS)

PHONY += fsbenchmarks
fsbenchmarks:
	$(Q)echo "FSBENCHMARKS_TAGS: $(FSBENCHMARKS_TAGS)"
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--forks 1 \
		--inventory hosts \
		--limit localhost,baseline,dev \
		--tags $(FSBENCHMARKS_TAGS) \
		--extra-vars '{ $(FSBENCHMARKS_ARGS) }' \
		playbooks/fsbenchmarks.yml

.PHONY: $(PHONY)
