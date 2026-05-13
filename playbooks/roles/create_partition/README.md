create_partition
================

The create_partition role lets you safely create and mount a Linux partition.

There are checks in place to ensure you only create the partition if the
partition didn't exist before. Devices upon bootup can change device names, and
so the assumption is we'd use a device name upon an initial boot, and later it
may move to another device name. This role would capture this as it scrape for
the partition label on other devices.

The partition label is used and relied upon.

Requirements
------------

You must have your respective partition userspace tools.  For instance,
xfsprogs if using xfs. If you specify 'xfs' then make.xfs is used. If you
specify 'foo' as your filesystem type, then you must have 'mkfs.foo'.

Role Variables
--------------

  * create_partition_disk_device: the target device to use
  * create_partition_disk_fstype: the filesystem type to use
  * create_partition_disk_mount_opts: extra mount options to use for /etc/fstab, should
    never be empty, if you want to use the default just do not override
    the defaults which is "defaults"
  * create_partition_disk_label: the filesystem label to use
  * create_partition_disk_fs_opts: additional filesystem options to pass
  * create_partition_disk_path: the path to mount the filesystem
  * create_partition_disk_user: the user to assign the directory path to
  * create_partition_disk_group: the group to assign the directory path to
  * create_partition_disk_mode: the mode of the root directory of the new filesystem

Dependencies
------------

None.

Example Playbook
----------------

Below is an example playbook task:

```
- name: Create /media/truncated if needed
  include_role:
    name: create_partition
  vars:
    create_partition_disk_device: "/dev/nvme2n1"
    create_partition_disk_fstype: "xfs"
    create_partition_disk_label : "truncated"
    create_partition_disk_fs_opts: "-L {{ create_partition_disk_label }}"
    create_partition_disk_path: "/media/truncated"
    create_partition_disk_user: "vagrant"
    create_partition_disk_group: "vagrant"
  tags: [ 'oscheck', 'truncated_partition' ]
```

For further examples refer to one of this role's users, the
[https://github.com/linux-kdevops/kdevops](kdevops) project.

License
-------

copyleft-next-0.3.1
