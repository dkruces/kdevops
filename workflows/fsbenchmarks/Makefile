# SPDX-License-Identifier: copyleft-next-0.3.1
fsbenchmarks-help-menu:
	@echo "fsbenchmarks options:"
	@echo "fsbenchmarks   - Run selected fsbenchmarks sequentially"
	@echo ""

HELP_TARGETS += fsbenchmarks-help-menu

FSBENCHMARKS_TAGS :=
FSBENCHMARKS_ARGS :=

include $(TOPDIR)/workflows/fsbenchmarks/tmpfs/Makefile

FSBENCHMARKS_TAGS := $(subst $(space),$(comma),$(FSBENCHMARKS_TAGS))

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
