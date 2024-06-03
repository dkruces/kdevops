# SPDX-License-Identifier: copyleft-next-0.3.1

GENERATED_REFS_NEXT := $(shell \
	./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_NEXT \
		--output workflows/linux/Kconfig.refs-next \
		--extra workflows/linux/next-refs.yaml \
		kreleases \
		--moniker linux-next \
	)

GENERATED_REFS_STABLE := $(shell \
	./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_STABLE \
		--output workflows/linux/Kconfig.refs-stable \
		--extra workflows/linux/stable-refs.yaml \
		kreleases \
		--moniker stable \
	)

GENERATED_REFS_LINUS := $(shell \
	./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_LINUS \
		--output workflows/linux/Kconfig.refs-linus \
		--extra workflows/linux/linus-refs.yaml \
		kreleases \
		--moniker mainline \
	)
