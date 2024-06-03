# SPDX-License-Identifier: copyleft-next-0.3.1

KRELEASES_TARGETS := gen_kreleases_linus
KRELEASES_TARGETS += gen_kreleases_next
KRELEASES_TARGETS += gen_kreleases_stable

KRELEASES_FORCE := $(if $(filter --force,$(KRELEASES_FORCE)),--force,)

.PHONY += gen_kreleases_next
gen_kreleases_next:
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_NEXT \
		--output workflows/linux/Kconfig.refs-next \
		--extra workflows/linux/next-refs.yaml \
		$(KRELEASES_FORCE) \
		kreleases \
		--moniker linux-next

.PHONY += gen_kreleases_stable
gen_kreleases_stable:
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_STABLE \
		--output workflows/linux/Kconfig.refs-stable \
		--extra workflows/linux/stable-refs.yaml \
		$(KRELEASES_FORCE) \
		kreleases \
		--moniker stable

.PHONY += gen_kreleases_linus
gen_kreleases_linus:
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_LINUS \
		--output workflows/linux/Kconfig.refs-linus \
		--extra workflows/linux/linus-refs.yaml \
		$(KRELEASES_FORCE) \
		kreleases \
		--moniker mainline

PHONY += gen-kreleases
gen-kreleases:
	$(Q)echo "Generating Kconfig.refs-{linus,next,stable} files..."
	$(Q)$(MAKE) $(KRELEASES_TARGETS) KRELEASES_FORCE="--force"

PHONY += _kreleases
_kreleases:
	$(Q)$(MAKE) $(KRELEASES_TARGETS)

.PHONY: $(PHONY)
