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

ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_DRIVE_NVME))
ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_NVME_LOGICAL_BLOCK_SIZE_512))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_nvme_logical_block_size='512'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_NVME_LOGICAL_BLOCK_SIZE_1K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_nvme_logical_block_size='1024'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_NVME_LOGICAL_BLOCK_SIZE_2K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_nvme_logical_block_size='2048'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_NVME_LOGICAL_BLOCK_SIZE_4K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_nvme_logical_block_size='4096'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_NVME_LOGICAL_BLOCK_SIZE_8K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_nvme_logical_block_size='8192'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_NVME_LOGICAL_BLOCK_SIZE_16K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_nvme_logical_block_size='16384'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_NVME_LOGICAL_BLOCK_SIZE_32K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_nvme_logical_block_size='32768'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_NVME_LOGICAL_BLOCK_SIZE_64K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_nvme_logical_block_size='65536'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_NVME_LOGICAL_BLOCK_SIZE_128K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_nvme_logical_block_size='131072'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_NVME_LOGICAL_BLOCK_SIZE_256K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_nvme_logical_block_size='262144'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_NVME_LOGICAL_BLOCK_SIZE_512K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_nvme_logical_block_size='524288'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_NVME_LOGICAL_BLOCK_SIZE_1M))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_nvme_logical_block_size='1048576'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_NVME_LOGICAL_BLOCK_SIZE_2M))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_nvme_logical_block_size='2097152'
else
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_nvme_logical_block_size='512'
endif
endif

ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_DRIVE_VIRTIO))
ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_PHYSICAL_BLOCK_SIZE_512))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_physical_block_size='512'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_PHYSICAL_BLOCK_SIZE_1K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_physical_block_size='1024'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_PHYSICAL_BLOCK_SIZE_2K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_physical_block_size='2048'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_PHYSICAL_BLOCK_SIZE_4K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_physical_block_size='4096'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_PHYSICAL_BLOCK_SIZE_8K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_physical_block_size='8192'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_PHYSICAL_BLOCK_SIZE_16K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_physical_block_size='16384'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_PHYSICAL_BLOCK_SIZE_32K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_physical_block_size='32768'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_PHYSICAL_BLOCK_SIZE_64K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_physical_block_size='65536'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_PHYSICAL_BLOCK_SIZE_128K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_physical_block_size='131072'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_PHYSICAL_BLOCK_SIZE_256K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_physical_block_size='262144'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_PHYSICAL_BLOCK_SIZE_512K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_physical_block_size='524288'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_PHYSICAL_BLOCK_SIZE_1M))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_physical_block_size='1048576'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_PHYSICAL_BLOCK_SIZE_2M))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_physical_block_size='2097152'
else
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_physical_block_size='512'
endif

ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_LOGICAL_BLOCK_SIZE_512))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_logical_block_size='512'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_LOGICAL_BLOCK_SIZE_1K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_logical_block_size='1024'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_LOGICAL_BLOCK_SIZE_2K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_logical_block_size='2048'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_LOGICAL_BLOCK_SIZE_4K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_logical_block_size='4096'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_LOGICAL_BLOCK_SIZE_8K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_logical_block_size='8192'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_LOGICAL_BLOCK_SIZE_16K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_logical_block_size='16384'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_LOGICAL_BLOCK_SIZE_32K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_logical_block_size='32768'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_LOGICAL_BLOCK_SIZE_64K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_logical_block_size='65536'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_LOGICAL_BLOCK_SIZE_128K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_logical_block_size='131072'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_LOGICAL_BLOCK_SIZE_256K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_logical_block_size='262144'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_LOGICAL_BLOCK_SIZE_512K))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_logical_block_size='524288'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_LOGICAL_BLOCK_SIZE_1M))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_logical_block_size='1048576'
else ifeq (y,$(CONFIG_LIBVIRT_EXTRA_STORAGE_VIRTIO_LOGICAL_BLOCK_SIZE_2M))
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_logical_block_size='2097152'
else
GEN_NODES_EXTRA_ARGS += libvirt_extra_storage_virtio_logical_block_size='512'
endif
endif

ifeq (y,$(CONFIG_LIBVIRT_EXTRA_DRIVE_FORMAT_RAW))
GEN_NODES_EXTRA_ARGS += libvirt_extra_drive_format='raw'
endif

ifeq (y,$(CONFIG_LIBVIRT_ENABLE_ZNS))
GEN_NODES_EXTRA_ARGS += nvme_zone_enable='True'
GEN_NODES_EXTRA_ARGS += nvme_zone_drive_size='$(subst ",,$(CONFIG_QEMU_NVME_ZONE_DRIVE_SIZE))'
GEN_NODES_EXTRA_ARGS += nvme_zone_size='$(subst ",,$(CONFIG_QEMU_NVME_ZONE_SIZE))'
GEN_NODES_EXTRA_ARGS += nvme_zone_zasl='$(subst ",,$(CONFIG_QEMU_NVME_ZONE_ZASL))'
GEN_NODES_EXTRA_ARGS += nvme_zone_capacity='$(subst ",,$(CONFIG_QEMU_NVME_ZONE_CAPACITY))'
GEN_NODES_EXTRA_ARGS += nvme_zone_max_active='$(subst ",,$(CONFIG_QEMU_NVME_ZONE_MAX_ACTIVE))'
GEN_NODES_EXTRA_ARGS += nvme_zone_max_open='$(subst ",,$(CONFIG_QEMU_NVME_ZONE_MAX_OPEN))'
GEN_NODES_EXTRA_ARGS += nvme_zone_physical_block_size='$(subst ",,$(CONFIG_QEMU_NVME_ZONE_PHYSICAL_BLOCK_SIZE))'
GEN_NODES_EXTRA_ARGS += nvme_zone_logical_block_size='$(subst ",,$(CONFIG_QEMU_NVME_ZONE_LOGICAL_BLOCK_SIZE))'
endif

ifeq (y,$(CONFIG_LIBVIRT_ENABLE_LARGEIO))
GEN_NODES_EXTRA_ARGS += libvirt_largeio_enable='True'
ifeq (y,$(CONFIG_QEMU_EXTRA_DRIVE_LARGEIO_COMPAT))
GEN_NODES_EXTRA_ARGS += libvirt_largeio_logical_compat='True'
endif
GEN_NODES_EXTRA_ARGS += libvirt_largeio_drives_per_space='$(subst ",,$(CONFIG_QEMU_EXTRA_DRIVE_LARGEIO_NUM_DRIVES_PER_SPACE))'
GEN_NODES_EXTRA_ARGS += libvirt_largeio_base_size='$(subst ",,$(CONFIG_QEMU_LARGEIO_DRIVE_BASE_SIZE))'
GEN_NODES_EXTRA_ARGS += libvirt_largeio_logical_compat_size='$(subst ",,$(CONFIG_QEMU_LARGEIO_COMPAT_SIZE))'
GEN_NODES_EXTRA_ARGS += libvirt_largeio_pow_limit='$(subst ",,$(CONFIG_QEMU_LARGEIO_MAX_POW_LIMIT))'
endif

ANSIBLE_EXTRA_ARGS += $(GEN_NODES_EXTRA_ARGS)
