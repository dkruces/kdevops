# SPDX-License-Identifier: copyleft-next-0.3.1

$(info Generating git references...)

export SRC_URI_HTTPS_LINUS = https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
export SRC_URI_HTTPS_NEXT = https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git
export SRC_URI_HTTPS_STABLE = https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git

export SRC_URI_HTTPS_MCGROF_LINUS = https://git.kernel.org/pub/scm/linux/kernel/git/mcgrof/linux.git
export SRC_URI_HTTPS_MCGROF_NEXT = https://git.kernel.org/pub/scm/linux/kernel/git/mcgrof/linux-next.git
export SRC_URI_HTTPS_BTRFS_DEVEL = https://github.com/kdave/btrfs-devel.git
export SRC_URI_HTTPS_CEL_LINUX = https://git.kernel.org/pub/scm/linux/kernel/git/cel/linux.git
export SRC_URI_HTTPS_JLAYTON_LINUX = https://git.kernel.org/pub/scm/linux/kernel/git/jlayton/linux.git
export SRC_URI_HTTPS_KDEVOPS_LINUS = https://github.com/linux-kdevops/linux.git

GENERATED_REFS_LINUS := $(shell \
	./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_LINUS \
		--output workflows/linux/Kconfig.refs-linus \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_LINUS) \
		--refs 15 \
	)

GENERATED_REFS_NEXT := $(shell \
	./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_NEXT \
		--output workflows/linux/Kconfig.refs-next \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_NEXT) \
		--refs 15 \
		--filter-tags next* \
	)

GENERATED_REFS_STABLE := $(shell \
	./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_STABLE \
		--output workflows/linux/Kconfig.refs-stable \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_STABLE) \
		--refs 15 \
	)

GENERATED_REFS_MCGROF_LINUS := $(shell \
	./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_MCGROF_LINUS \
		--output workflows/linux/Kconfig.refs-mcgrof-linus \
		--extra workflows/linux/mcgrof-linus-refs.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_MCGROF_LINUS) \
		--refs 15 \
	)

GENERATED_REFS_MCGROF_NEXT := $(shell \
	./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_MCGROF_NEXT \
		--output workflows/linux/Kconfig.refs-mcgrof-next \
		--extra workflows/linux/mcgrof-next-refs.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_MCGROF_NEXT) \
		--refs 15 \
	)

GENERATED_REFS_BTRFS_DEVEL := $(shell \
	./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_BTRFS_DEVEL \
		--output workflows/linux/Kconfig.refs-btrfs-devel \
		--extra workflows/linux/btrfs-devel-refs.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_BTRFS_DEVEL) \
		--refs 15 \
	)

GENERATED_REFS_CEL_LINUX := $(shell \
	./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_CEL_LINUX \
		--output workflows/linux/Kconfig.refs-cel-linux \
		--extra workflows/linux/cel-linux-refs.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_CEL_LINUX) \
		--refs 15 \
	)

GENERATED_REFS_JLAYTON_LINUX := $(shell \
	./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_JLAYTON_LINUX \
		--output workflows/linux/Kconfig.refs-jlayton-linux \
		--extra workflows/linux/jlayton-linux-refs.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_JLAYTON_LINUX) \
		--refs 15 \
	)

GENERATED_REFS_KDEVOPS_LINUS := $(shell \
	./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_KDEVOPS_LINUS \
		--output workflows/linux/Kconfig.refs-kdevops-linus \
		--extra workflows/linux/kdevops-linus-refs.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_KDEVOPS_LINUS) \
		--refs 15 \
	)
