# SPDX-License-Identifier: copyleft-next-0.3.1
# runconf/Makefile

CONFIG_DIR := $(CURDIR)
CONFIG_FILE := $(CONFIG_DIR)/.config
CONFIG_DIR_NAME := ./$(shell basename $(CONFIG_DIR))
EXTRA_VARS_FILE := $(CONFIG_DIR_NAME)/extra_vars.yaml

# Debugging
$(info CONFIG_DIR=$(CONFIG_DIR))
$(info CONFIG_FILE=$(CONFIG_FILE))
$(info CONFIG_DIR_NAME=$(CONFIG_DIR_NAME))
$(info EXTRA_VARS_FILE=$(EXTRA_VARS_FILE))

export CONFIG_DIR_NAME

all:
	KCONFIG_CONFIG=$(CONFIG_FILE) KDEVOPS_EXTRA_VARS=$(EXTRA_VARS_FILE) $(MAKE) -C .. all

generate-kconfig-runconf:
	@echo "Generating Kconfig.runconf..."
	@echo "source \"$(CONFIG_DIR_NAME)/Kconfig\"" > ../Kconfig.runconf

menuconfig: generate-kconfig-runconf
	KCONFIG_CONFIG=$(CONFIG_FILE) $(MAKE) -C .. menuconfig

extra_vars.yaml:
	KCONFIG_CONFIG=$(CONFIG_FILE) KDEVOPS_EXTRA_VARS=$(EXTRA_VARS_FILE) $(MAKE) -C .. $(EXTRA_VARS_FILE)

%:
	KCONFIG_CONFIG=$(CONFIG_FILE) KDEVOPS_EXTRA_VARS=$(EXTRA_VARS_FILE) $(MAKE) -C .. $@
