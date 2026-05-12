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

ANSIBLE_EXTRA_ARGS += $(GEN_NODES_EXTRA_ARGS)
