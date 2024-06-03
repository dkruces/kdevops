# SPDX-License-Identifier: copyleft-next-0.3.1

SRC_URI_HTTPS_LINUS = https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
SRC_URI_HTTPS_NEXT = https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git
SRC_URI_HTTPS_STABLE = https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git

SRC_URI_HTTPS_MCGROF_LINUS = https://git.kernel.org/pub/scm/linux/kernel/git/mcgrof/linux.git
SRC_URI_HTTPS_MCGROF_NEXT = https://git.kernel.org/pub/scm/linux/kernel/git/mcgrof/linux-next.git
SRC_URI_HTTPS_BTRFS_DEVEL = https://github.com/kdave/btrfs-devel.git
SRC_URI_HTTPS_CEL_LINUX = https://git.kernel.org/pub/scm/linux/kernel/git/cel/linux.git
SRC_URI_HTTPS_JLAYTON_LINUX = https://git.kernel.org/pub/scm/linux/kernel/git/jlayton/linux.git
SRC_URI_HTTPS_KDEVOPS_LINUS = https://github.com/linux-kdevops/linux.git

GITREF_TARGETS := gen_gitref_linus
GITREF_TARGETS += gen_gitref_next
GITREF_TARGETS += gen_gitref_stable

GITREF_TARGETS += gen_gitref_mcgrof_linus
GITREF_TARGETS += gen_gitref_mcgrof_next
GITREF_TARGETS += gen_gitref_btrfs_devel
GITREF_TARGETS += gen_gitref_cel_linux
GITREF_TARGETS += gen_gitref_jlayton_linux
GITREF_TARGETS += gen_gitref_kdevops_linus

REFS_COUNT := 15
GITREF_EXT := $(if $(filter -gitref,$(GITREF_EXT)),-gitref,)

PHONY += gen_gitref_linus
gen_gitref_linus:
	$(Q)echo "Generating $(REFS_COUNT) git ref(s) for $(patsubst gen_gitref_%,%,$@)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_LINUS \
		--output workflows/linux/Kconfig.refs-linus$(GITREF_EXT) \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_LINUS) \
		--refs $(REFS_COUNT)

PHONY += gen_gitref_next
gen_gitref_next:
	$(Q)echo "Generating $(REFS_COUNT) git ref(s) for $(patsubst gen_gitref_%,%,$@)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_NEXT \
		--output workflows/linux/Kconfig.refs-next$(GITREF_EXT) \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_NEXT) \
		--refs $(REFS_COUNT) \
		--filter-tags next* \

PHONY += gen_gitref_stable
gen_gitref_stable:
	$(Q)echo "Generating $(REFS_COUNT) git ref(s) for $(patsubst gen_gitref_%,%,$@)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_STABLE \
		--output workflows/linux/Kconfig.refs-stable$(GITREF_EXT) \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_STABLE) \
		--refs $(REFS_COUNT)

PHONY += gen_gitref_mcgrof_linus
gen_gitref_mcgrof_linus:
	$(Q)echo "Generating $(REFS_COUNT) git ref(s) for $(patsubst gen_gitref_%,%,$@)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_MCGROF_LINUS \
		--output workflows/linux/Kconfig.refs-mcgrof-linus$(GITREF_EXT) \
		--extra workflows/linux/mcgrof-linus-refs.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_MCGROF_LINUS) \
		--refs $(REFS_COUNT)

PHONY += gen_gitref_mcgrof_next
gen_gitref_mcgrof_next:
	$(Q)echo "Generating $(REFS_COUNT) git ref(s) for $(patsubst gen_gitref_%,%,$@)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_MCGROF_NEXT \
		--output workflows/linux/Kconfig.refs-mcgrof-next$(GITREF_EXT) \
		--extra workflows/linux/mcgrof-next-refs.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_MCGROF_NEXT) \
		--refs $(REFS_COUNT)

PHONY += gen_gitref_btrfs_devel
gen_gitref_btrfs_devel:
	$(Q)echo "Generating $(REFS_COUNT) git ref(s) for $(patsubst gen_gitref_%,%,$@)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_BTRFS_DEVEL \
		--output workflows/linux/Kconfig.refs-btrfs-devel$(GITREF_EXT) \
		--extra workflows/linux/btrfs-devel-refs.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_BTRFS_DEVEL) \
		--refs $(REFS_COUNT)

PHONY += gen_gitref_cel_linux
gen_gitref_cel_linux:
	$(Q)echo "Generating $(REFS_COUNT) git ref(s) for $(patsubst gen_gitref_%,%,$@)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_CEL_LINUX \
		--output workflows/linux/Kconfig.refs-cel-linux$(GITREF_EXT) \
		--extra workflows/linux/cel-linux-refs.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_CEL_LINUX) \
		--refs $(REFS_COUNT)

PHONY += gen_gitref_jlayton_linux
gen_gitref_jlayton_linux:
	$(Q)echo "Generating $(REFS_COUNT) git ref(s) for $(patsubst gen_gitref_%,%,$@)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_JLAYTON_LINUX \
		--output workflows/linux/Kconfig.refs-jlayton-linux$(GITREF_EXT) \
		--extra workflows/linux/jlayton-linux-refs.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_JLAYTON_LINUX) \
		--refs $(REFS_COUNT)

PHONY += gen_gitref_kdevops_linus
gen_gitref_kdevops_linus:
	$(Q)echo "Generating $(REFS_COUNT) git ref(s) for $(patsubst gen_gitref_%,%,$@)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_KDEVOPS_LINUS \
		--output workflows/linux/Kconfig.refs-kdevops-linus$(GITREF_EXT) \
		--extra workflows/linux/kdevops-linus-refs.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_KDEVOPS_LINUS) \
		--refs $(REFS_COUNT)

PHONY += gen-gitref
gen-gitref:
	$(Q)echo "Generating Kconfig.refs-{linus,next,stable,mcgrof-linus,mcgrof-next,btrfs-devel,cel-linux-jlayton-linux-kdevops-linus}-gitref files..."
	$(Q)$(MAKE) REFS_COUNT=1 $(GITREF_TARGETS) GITREF_EXT="-gitref"

gen-gitref-0:
	$(Q)echo "Generating Kconfig.refs-{linus,next,stable,mcgrof-linus,mcgrof-next,btrfs-devel,cel-linux-jlayton-linux-kdevops-linus} files..."
	$(Q)$(MAKE) REFS_COUNT=0 $(GITREF_TARGETS)

PHONY += clean-gitref
clean-gitref:
	$(Q)truncate --size 0 workflows/linux/Kconfig.refs*gitref

.PHONY: $(PHONY)
