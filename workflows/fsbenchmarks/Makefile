# SPDX-License-Identifier: copyleft-next-0.3.1
fsbenchmarks-help-menu:
	@echo "fsbenchmarks options:"
	@echo "fsbenchmarks   - Run selected fsbenchmarks sequentially"
	@echo ""

HELP_TARGETS += fsbenchmarks-help-menu

FSBENCHMARKS_TAGS :=
ifeq (y,$(CONFIG_FSBENCHMARKS_TMPFS_ENABLE))
FSBENCHMARKS_TAGS += "tmpfs"
endif

ifeq (y,$(CONFIG_FSBENCHMARKS_TMPFS_TEST00))
FSBENCHMARKS_TAGS += "tmpfs_test00"
endif

FSBENCHMARKS_TAGS := $(subst $(space),$(comma),$(FSBENCHMARKS_TAGS))

PHONY += fsbenchmarks
fsbenchmarks:
	$(Q)echo "FSBENCHMARKS_TAGS: $(FSBENCHMARKS_TAGS)"
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--forks 1 \
		--inventory hosts \
		--limit localhost \
		--tags $(FSBENCHMARKS_TAGS) \
		playbooks/fsbenchmarks.yml

.PHONY: $(PHONY)
