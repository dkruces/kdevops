# SPDX-License-Identifier: copyleft-next-0.3.1

# We can later remove kconfig options which match their respective ansible
# name once kconfig gets extra_vars.yaml output support. That means this
# Makfile can become empty :) in the future !
#
# When we do add support to kconfig to output extra_vars.yaml we will also
# add support so that only kconfig symbols which have an associated new option,
# say, select_yaml_output, will it be used to also be output to the yaml file.
# That would ensure that our extra_vars.yaml file won't be as long as our
# existing .config files.
ifeq (y,$(CONFIG_FSBENCHMARKS_TMPFS_ENABLE))
FSBENCHMARKS_TAGS += "tmpfs"
endif

ifeq (y,$(CONFIG_FSBENCHMARKS_TMPFS_TEST00))
FSBENCHMARKS_TAGS += "tmpfs_test00"

TMPFS_TEST00_NRFILES:=$(subst ",,$(CONFIG_FSBENCHMARKS_TMPFS_TEST00_NRFILES))
TMPFS_TEST00_FILESIZE:=$(subst ",,$(CONFIG_FSBENCHMARKS_TMPFS_TEST00_FILESIZE))
TMPFS_TEST00_NUMJOBS:=$(subst ",,$(CONFIG_FSBENCHMARKS_TMPFS_TEST00_NUMJOBS))
TMPFS_TEST00_MOUNTSIZE:=$(subst ",,$(CONFIG_FSBENCHMARKS_TMPFS_TEST00_MOUNTSIZE))

FSBENCHMARKS_ARGS += fsbenchmarks_test00_nrfiles = '$(TMPFS_TEST00_NRFILES)'
FSBENCHMARKS_ARGS += fsbenchmarks_test00_filesize = '$(TMPFS_TEST00_FILESIZE)'
FSBENCHMARKS_ARGS += fsbenchmarks_test00_numjobs = '$(TMPFS_TEST00_NUMJOBS)'
FSBENCHMARKS_ARGS += fsbenchmarks_test00_mountsize = '$(TMPFS_TEST00_MOUNTSIZE)'
endif
