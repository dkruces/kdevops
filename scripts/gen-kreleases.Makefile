# SPDX-License-Identifier: copyleft-next-0.3.1

GENERATED_REFS_NEXT := $(shell \
	./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_NEXT \
		--output workflows/linux/Kconfig.refs-next \
		kreleases \
		--moniker linux-next \
	)

GENERATED_REFS_STABLE := $(shell \
	./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_STABLE \
		--output workflows/linux/Kconfig.refs-stable \
		kreleases \
		--moniker stable \
	)

GENERATED_REFS_LINUS := $(shell \
	./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_LINUS \
		--output workflows/linux/Kconfig.refs-linus \
		kreleases \
		--moniker mainline \
	)
