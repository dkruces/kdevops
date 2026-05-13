# SPDX-License-Identifier: copyleft-next-0.3.1

PROJECT = kdevops
VERSION = 5
PATCHLEVEL = 0
SUBLEVEL = 2
EXTRAVERSION =

# Bare `make` shows the primary-workflow help. Explicit targets (env,
# controller-setup, bringup, <workflow>) do the work. `make all` keeps the
# legacy "run DEFAULT_DEPS" behaviour for muscle-memory; `make deps` is the
# same. See make.texi "Other Special Variables" for .DEFAULT_GOAL.
.DEFAULT_GOAL := help-targets

all: deps

export KCONFIG_DIR=$(CURDIR)/scripts/kconfig
export KCONFIG_YAMLCFG=$(CURDIR)/.extra_vars_auto.yaml
include $(KCONFIG_DIR)/kconfig.Makefile
include Makefile.subtrees

export KDEVOPS_EXTRA_VARS ?=			extra_vars.yaml
export KDEVOPS_PLAYBOOKS_DIR :=			playbooks
export KDEVOPS_NODES :=
export PYTHONUNBUFFERED=1
export TOPDIR=./
export TOPDIR_PATH = $(shell readlink -f $(TOPDIR))
export TOPDIR_PATH_SHA256SUM = $(shell ./scripts/compute_sha256sum.sh $(TOPDIR_PATH))

# Export CLI override variables for Kconfig to detect them
# Note: We accept DECLARE_HOSTS but export as DECLARED_HOSTS for consistency
ifdef DECLARE_HOSTS
export DECLARED_HOSTS := $(DECLARE_HOSTS)
endif

# Export workflow CLI overrides
ifdef KNLP
export KNLP
endif

ifdef KEEP
export KEEP
endif

include scripts/refs.Makefile

export KDEVOPS_NODES_TEMPLATE :=
export KDEVOPS_MRPROPER :=

ifeq (y,$(CONFIG_ANSIBLE_CONFIG_INVENTORY_CUSTOM))
ANSIBLE_INVENTORY_FILE := $(shell echo $(CONFIG_ANSIBLE_CONFIG_INVENTORY) | tr --delete '"')
else
ANSIBLE_INVENTORY_FILE := $(TOPDIR_PATH)/inventory
endif

KDEVOPS_INSTALL_TARGETS :=

DEFAULT_DEPS :=
DEFAULT_DEPS_REQS_EXTRA_VARS :=
MAKEFLAGS += --no-print-directory
SHELL := /bin/bash
.DELETE_ON_ERROR:
HELP_TARGETS := kconfig-help-menu
KDEVOPS_DEPCHECK = .kdevops.depcheck

PHONY += kconfig-help-menu

define print_target
	echo "==> [$1]"
endef

# Parse kconfig verbosity setting early, allow CLI to override
ifneq (,$(wildcard .config))
ifeq ($(CONFIG_KDEVOPS_MAKE_VERBOSE),y)
V ?= 1
endif
endif

ifeq ($(V),1)
export Q=@$(call print_target,$@) && set -x &&
export NQ=true
else
export Q=@
export NQ=echo
endif

# Wrap ansible-playbook so the terminal replay is captured to a log
# file under $(KDEVOPS_LOG_DIR). Lucid's structured logs continue at
# .ansible/logs/ independently.
#
# Lucid's dynamic display (in-place TUI, ANSI cursor control) only
# engages when sys.stdout.isatty() is True. Make's recipe stdout is
# not a tty, so when lucid is the active callback we wrap with
# script(1) to allocate a pty for the child; the user then sees the
# dynamic display and the raw replay (including ANSI codes) lands in
# the log. For every other callback (default, dense, debug, diy),
# clearing the screen is not desired: the macro emits plain
# scrolling output via tee + pipefail.
KDEVOPS_LOG_DIR := .kdevops/logs
KDEVOPS_LOGFILE = $(KDEVOPS_LOG_DIR)/$(shell date +%Y%m%d-%H%M%S)-$(notdir $@).log

ifeq (y,$(CONFIG_ANSIBLE_CONFIG_CALLBACK_PLUGIN_LUCID))
UNAME_S := $(shell uname --kernel-name)
ifeq ($(UNAME_S),Darwin)
# BSD script(1) has no long-form flag aliases.
define run-ansible-playbook
	@mkdir -p $(KDEVOPS_LOG_DIR)
	script -q $(KDEVOPS_LOGFILE) ansible-playbook $(1)
endef
else
define run-ansible-playbook
	@mkdir -p $(KDEVOPS_LOG_DIR)
	script --quiet --return --log-out=$(KDEVOPS_LOGFILE) --command "ansible-playbook $(1)"
endef
endif
else
define run-ansible-playbook
	@mkdir -p $(KDEVOPS_LOG_DIR)
	set -o pipefail; ansible-playbook $(1) 2>&1 | tee $(KDEVOPS_LOGFILE)
endef
endif

include Makefile.min_deps
DEFAULT_DEPS += $(KDEVOPS_DEPCHECK)

# This will be used to generate our extra_args.yml file used to pass on
# configuration data for ansible roles through kconfig.
ANSIBLE_EXTRA_ARGS :=
ANSIBLE_EXTRA_ARGS_SEPARATED :=
ANSIBLE_EXTRA_ARGS_DIRECT :=
include Makefile.extra_vars

include scripts/ansible.Makefile

LIMIT_HOSTS :=
ifneq (,$(HOSTS))
LIMIT_HOSTS := --limit $(subst ${space},$(comma),$(HOSTS))
endif

export LIMIT_TESTS :=
ifneq (,$(TESTS))
LIMIT_TESTS := $(TESTS)
endif

INCLUDES = -I include/
CFLAGS += $(INCLUDES)

ANSIBLE_EXTRA_ARGS += kdevops_version='$(PROJECTRELEASE)'
ANSIBLE_EXTRA_ARGS += topdir_path_sha256sum='$(TOPDIR_PATH_SHA256SUM)'

include modules/ansible_config/Makefile
include modules/ansible_inventory/Makefile

LOCAL_DEVELOPMENT_ARGS	:=
ifeq (y,$(CONFIG_NEEDS_LOCAL_DEVELOPMENT_PATH))
include Makefile.local
endif # CONFIG_NEEDS_LOCAL_DEVELOPMENT_PATH

# Controller-side first-run work (sudo, package installs, hypervisor
# tuning). Contributors are pulled in only by `make controller-setup`,
# not by bare make. Add via `LOCALHOST_SETUP_WORK += <phony target>`.
LOCALHOST_SETUP_WORK :=

ANSIBLE_EXTRA_ARGS += $(LOCAL_DEVELOPMENT_ARGS)

# We may not need the extra_args.yaml file all the time.  If this file is empty
# you don't need it. All of our ansible kdevops roles check for this file
# without you having to specify it as an extra_args=@extra_args.yaml file. This
# helps us with allowing users call ansible on the command line themselves,
# instead of using the make constructs we have built here.
# Core dependencies now added before provision.Makefile include
ifneq (,$(ANSIBLE_EXTRA_ARGS))
DEFAULT_DEPS += $(KDEVOPS_EXTRA_VARS)
endif

DEFAULT_DEPS += $(ANSIBLE_CONFIG_PATH)
DEFAULT_DEPS += $(ANSIBLE_INVENTORY_FILE)

include scripts/provision.Makefile
include scripts/firstconfig.Makefile
include scripts/systemd-timesync.Makefile
include scripts/journal-server.Makefile
include scripts/update_etc_hosts.Makefile

# Included after the backend Makefiles set KDEVOPS_NODES + KDEVOPS_NODES_TEMPLATE.
include modules/nodes/Makefile

include modules/libvirt/Makefile

# Node-file selection comes from Make-side workflow/backend state
# (KDEVOPS_NODES, KDEVOPS_NODES_TEMPLATE) and cannot be derived from
# Kconfig, so it is injected directly into ANSIBLE_EXTRA_ARGS. Must
# follow the backend Makefile include above so the values are
# populated when the immediate-expansion += appends them here.
ANSIBLE_EXTRA_ARGS += kdevops_nodes='$(KDEVOPS_NODES)'
ANSIBLE_EXTRA_ARGS += kdevops_nodes_template='$(KDEVOPS_NODES_TEMPLATE)'
ANSIBLE_EXTRA_ARGS += kdevops_nodes_template_full_path='$(TOPDIR_PATH)/$(KDEVOPS_NODES_TEMPLATE)'

ifneq (,$(KDEVOPS_NODES))
DEFAULT_DEPS += $(KDEVOPS_NODES)
endif

KDEVOPS_BRING_UP_DEPS += $(KDEVOPS_BRING_UP_DEPS_EARLY)
KDEVOPS_BRING_UP_DEPS += $(KDEVOPS_PROVISIONED_DEVCONFIG)

ifeq (y,$(CONFIG_WORKFLOWS))
include workflows/Makefile
endif # CONFIG_WORKFLOWS

include scripts/rdma.Makefile
include scripts/ktls.Makefile
include scripts/iscsi.Makefile
include scripts/nfsd.Makefile
include scripts/smbd.Makefile
include scripts/krb5.Makefile

include scripts/devconfig.Makefile
include scripts/ssh.Makefile

ANSIBLE_CMD_KOTD_ENABLE := echo KOTD disabled so not running:
ifeq (y,$(CONFIG_WORKFLOW_KOTD_ENABLE))
include scripts/kotd.Makefile
endif # WORKFLOW_KOTD_ENABLE

DEFAULT_DEPS += $(DEFAULT_DEPS_REQS_EXTRA_VARS)

include scripts/install-menuconfig-deps.Makefile
include scripts/install-rcloud-deps.Makefile

include Makefile.btrfs_progs

ifeq (y,$(CONFIG_QEMU_BUILD))
include modules/qemu/Makefile
endif # CONFIG_QEMU_BUILD

ifeq (y,$(CONFIG_ENABLE_MONITORING))
include modules/monitoring/Makefile
endif # CONFIG_ENABLE_MONITORING

ifeq (y,$(CONFIG_SETUP_POSTFIX_EMAIL_RELAY))
include Makefile.postfix
endif # CONFIG_SETUP_POSTFIX_EMAIL_RELAY

ifeq (y,$(CONFIG_HYPERVISOR_TUNING))
include Makefile.hypervisor-tunings
endif # CONFIG_HYPERVISOR_TUNING

include Makefile.linux-mirror
include Makefile.docker-mirror

ifeq (y,$(CONFIG_RCLOUD))
include workflows/rcloud/Makefile
endif

ifeq (y,$(CONFIG_KDEVOPS_DISTRO_REG_METHOD_TWOLINE))
DEFAULT_DEPS += playbooks/secret.yml
endif

ifeq (y,$(CONFIG_KDEVOPS_ENABLE_DISTRO_EXTRA_ADDONS))
KDEVOPS_EXTRA_ADDON_SOURCE:=$(subst ",,$(CONFIG_KDEVOPS_EXTRA_ADDON_SOURCE))
endif

KDEVOPS_ANSIBLE_PROVISION_PLAYBOOK:=$(subst ",,$(CONFIG_KDEVOPS_ANSIBLE_PROVISION_PLAYBOOK))
ifeq (y,$(CONFIG_KDEVOPS_ANSIBLE_PROVISION_ENABLE))
ANSIBLE_EXTRA_ARGS += kdevops_ansible_provision_playbook='$(KDEVOPS_ANSIBLE_PROVISION_PLAYBOOK)'
endif

# disable built-in rules for this
.SUFFIXES:

.config:
	@(								\
	echo "/--------------"						;\
	echo "| $(PROJECT) isn't configured, please configure it" 	;\
	echo "| using one of the following options:"			;\
	echo "| To configure manually:"					;\
	echo "|     make oldconfig"					;\
	echo "|     make menuconfig"					;\
	echo "|"							;\
	make -f scripts/build.Makefile help                             ;\
	false)

playbooks/secret.yml:
	@if [[ "$(CONFIG_KDEVOPS_REG_TWOLINE_REGCODE)" == "" ]]; then \
		echo "Registration code is not set, this must be set for this configuration" ;\
		exit 1 ;\
	fi
	@echo --- > $@
	@echo "$(CONFIG_KDEVOPS_REG_TWOLINE_ENABLE_STRING): True" >> $@
	@echo "$(CONFIG_KDEVOPS_REG_TWOLINE_REGCODE_VAR): $(CONFIG_KDEVOPS_REG_TWOLINE_REGCODE)" >> $@

ifeq (y,$(CONFIG_KDEVOPS_ENABLE_DISTRO_EXTRA_ADDONS))
$(KDEVOPS_EXTRA_ADDON_DEST): .config $(ANSIBLE_CONFIG_PATH) $(KDEVOPS_EXTRA_ADDON_SOURCE)
	$(Q)cp $(KDEVOPS_EXTRA_ADDON_SOURCE) $(KDEVOPS_EXTRA_ADDON_DEST)
endif

KDEVOPS_BRING_UP_DEPS += $(KDEVOPS_BRING_UP_LATE_DEPS)

ifneq (,$(KDEVOPS_BRING_UP_DEPS))
include scripts/bringup.Makefile
endif

include scripts/tests.Makefile
include scripts/linux-ab-testing.Makefile
include scripts/ci.Makefile
include scripts/archive.Makefile
include scripts/defconfig.Makefile
include scripts/style.Makefile

PHONY += contrib-graph
contrib-graph:
	$(Q)python3 scripts/contrib_graph.py $(if $(YEAR),--year $(YEAR)) $(if $(MONTH),--month $(MONTH))

PHONY += clean
clean:
	$(Q)$(MAKE) -f scripts/build.Makefile $@

version-check:
	$(Q)$(MAKE) -f scripts/build.Makefile $@

PHONY += mrproper
mrproper:
	$(Q)$(MAKE) -f scripts/build.Makefile clean
	$(Q)$(MAKE) -f scripts/build.Makefile $@
	$(Q)rm -f $(KDEVOPS_DEPCHECK)
	$(Q)rm -f terraform/*/terraform.tfstat*
	$(Q)rm -f terraform/*/terraform.tfvars
	$(Q)rm -rf terraform/*/.terraform
	$(Q)rm -f terraform/*/.terraform.lock.hcl
	$(Q)rm -f $(KDEVOPS_NODES)
	$(Q)rm -f $(ANSIBLE_INVENTORY_FILE) $(KDEVOPS_MRPROPER)
	$(Q)rm -f .config .config.old extra_vars.yaml $(KCONFIG_YAMLCFG)
	$(Q)rm -rf $(EXTRA_VAR_FRAGMENTS_DIR)
	$(Q)rm -f $(ANSIBLE_CONFIG_PATH)
	$(Q)rm -f playbooks/secret.yml $(KDEVOPS_EXTRA_ADDON_DEST)
	$(Q)rm -rf include
	$(Q)rm -rf guestfs
	$(Q)$(MAKE) -f scripts/gen-refs-default.Makefile _refs-default-clean

kconfig-help-menu:
	$(Q)$(MAKE) -s -C scripts/kconfig help
	$(Q)$(MAKE) -f scripts/build.Makefile help

PHONY += env
env: $(KDEVOPS_EXTRA_VARS) $(ANSIBLE_CONFIG_PATH) $(ANSIBLE_INVENTORY_FILE)

PHONY += controller-setup
controller-setup: env $(KDEVOPS_DEPCHECK) $(LOCALHOST_SETUP_WORK)

HELP_TARGETS += help-targets
PHONY += help-targets
help-targets:
	@echo "Primary kdevops workflow:"
	@echo "  make defconfig-<X>      Configure (writes .config)"
	@echo "  make env                Render ansible.cfg + inventory"
	@echo "  make controller-setup   First-run controller deps (sudo)"
	@echo "  make bringup            Provision guests"
	@echo "  make <workflow>         Run a workflow (fstests, blktests, ...)"
	@echo "  make destroy            Tear down guests"
	@echo
	@echo "Use 'make help' for the full target list."

PHONY += $(HELP_TARGETS)

PHONY += help
help: $(HELP_TARGETS)

PHONY += deps
deps: $(DEFAULT_DEPS)

PHONY += install
install: $(KDEVOPS_INSTALL_TARGETS)
	$(Q)echo   Installed

.PHONY: $(PHONY)
