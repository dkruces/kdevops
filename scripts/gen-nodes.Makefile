# SPDX-License-Identifier: copyleft-next-0.3.1

GEN_NODES_EXTRA_ARGS += kdevops_nodes='$(KDEVOPS_NODES)'
GEN_NODES_EXTRA_ARGS += kdevops_nodes_template='$(KDEVOPS_NODES_TEMPLATE)'
GEN_NODES_EXTRA_ARGS += kdevops_nodes_template_full_path='$(TOPDIR_PATH)/$(KDEVOPS_NODES_TEMPLATE)'

ifeq (y,$(CONFIG_QEMU_BUILD))
  # When QEMU_BUILD=y, qemu_bin_path comes from the nodes
  # role's default (playbooks/roles/nodes/defaults/main.yml),
  # which chains through qemu_build_bin_path from the Kconfig
  # output yaml stream. Injecting it here would break Make's
  # foreach iteration over ANSIBLE_EXTRA_ARGS, because the value
  # is a Jinja2 template that contains whitespace
  # ({{ qemu_build_destdir }}/bin/...) and foreach splits on
  # whitespace.
else
GEN_NODES_EXTRA_ARGS += qemu_bin_path='$(subst ",,$(CONFIG_QEMU_BIN_PATH))'
endif

ANSIBLE_EXTRA_ARGS += $(GEN_NODES_EXTRA_ARGS)
