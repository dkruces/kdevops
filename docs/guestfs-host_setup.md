# guestfs-host_setup — One-time host configuration

## When this matters

Before kdevops can spawn libvirt-backed guests with guestfs, the
controller host needs three pieces of one-time configuration:

1. **libguestfs and supporting packages** installed system-wide
   so `virt-builder`, `virt-sysprep`, and the Python libvirt
   bindings are available.
2. **The libvirt storage pool directory** (`libvirt_storage_pool_path`,
   default `/var/lib/libvirt/images`) created with group ownership
   of `libvirt_qemu_group` (`libvirt-qemu` on Debian/Ubuntu,
   `qemu` on Fedora/RHEL/SUSE) so non-root users can write domain
   disks there.
3. **The libvirt default network** defined and started, plus
   dnsmasq absent or compatible (the default network bundles its
   own dnsmasq instance and a system-wide one conflicts).

The guestfs module ships a sudo opt-in sub-module that performs
all three in one shot. If you would rather not grant kdevops
sudo, the manual sequence below is equivalent.

## The opt-in path

```
make guestfs-host-setup
```

Drives `playbooks/guestfs.yml` with
`--tags guestfs_host_setup` and runs the
`playbooks/roles/guestfs/host_setup/setup/` sub-role under sudo.
The sub-role dispatches three include_tasks:

- `install-deps/main.yml` → distro-specific package install
  (`apt-get` for Debian/Ubuntu, `dnf` for Red Hat/Fedora,
  `zypper` for SUSE). Installs `libguestfs-tools`, the python
  libvirt binding, OVMF, plus a dhcpcd client for the default
  network's DHCP service.
- `storage-pool-path.yml` → checks the running user is in
  `libvirt_qemu_group`, then `mkdir -p` and `chown :<group>` on
  `libvirt_storage_pool_path` and the guestfs sub-directory under
  it. Idempotent.
- `network.yml` → confirms dnsmasq isn't running standalone on
  Debian/Ubuntu (fails with a manual-remediation message if it
  is), then `virsh net-list` + `virsh net-start default` if the
  default network isn't already up.

After the run `make bringup` proceeds without prompting for
package-install or pool-directory sudo. Per-VM sudo (cp,
virt-sysprep) still runs at bringup time but is intrinsic to
the libvirt-system-uri model.

## The manual path

### Debian / Ubuntu

```
sudo apt-get update
sudo apt-get install \
    libguestfs-tools \
    dhcpcd-base \
    isc-dhcp-client \
    python3-lxml \
    python3-libvirt \
    ovmf

# If dnsmasq is installed standalone it conflicts with libvirt's
# default network. Either remove it or stop it before continuing:
#   sudo apt-get remove dnsmasq
#   sudo systemctl disable --now dnsmasq

sudo mkdir -p /var/lib/libvirt/images
sudo chgrp libvirt-qemu /var/lib/libvirt/images
sudo chmod 0775 /var/lib/libvirt/images

sudo virsh net-start default     # if not already up
sudo virsh net-autostart default # optional, makes it survive reboot
```

### Fedora / RHEL / CentOS Stream

```
sudo dnf install \
    libguestfs-tools-c \
    python3-libvirt \
    edk2-ovmf

sudo mkdir -p /var/lib/libvirt/images
sudo chgrp qemu /var/lib/libvirt/images
sudo chmod 0775 /var/lib/libvirt/images

sudo virsh net-start default
sudo virsh net-autostart default
```

### openSUSE / SLES

```
sudo zypper install \
    guestfs-tools \
    python3-libvirt-python \
    qemu-ovmf-x86_64

sudo mkdir -p /var/lib/libvirt/images
sudo chgrp qemu /var/lib/libvirt/images
sudo chmod 0775 /var/lib/libvirt/images

sudo virsh net-start default
sudo virsh net-autostart default
```

After the manual sequence, re-run the make target that originally
failed. The guestfs verify path stats the pool directory's group
ownership, checks for `virsh` and `virt-builder` on PATH, and
passes silently when everything is in place.

## What the verify path checks

`playbooks/roles/guestfs/host_setup/verify/tasks/main.yml` runs
without sudo on every default `make bringup` invocation and
emits an actionable diagnostic in any of the following cases:

- `virsh` is not on `PATH` → libvirt isn't installed.
- `virt-builder` is not on `PATH` → libguestfs isn't installed.
- `libvirt_storage_pool_path` does not exist → pool directory
  not created yet.
- `libvirt_storage_pool_path` is owned by the wrong group
  (under `libvirt_uri_system`) → guestfs cannot write domain
  disks without sudo.
- The controller user is not in `libvirt_qemu_group` (under
  `libvirt_uri_system`) → the libvirt module's user-setup is the
  fix, not guestfs's host-setup.

Each diagnostic names both the opt-in Make target and this
document, so the user has a clear next step regardless of which
piece is missing.

## Dependencies

`libvirt/user` should be set up before `guestfs-host-setup`,
since the verify path also checks for libvirt group membership.
The recommended order on a fresh host:

```
make libvirt-user-setup        # libvirt + kvm group membership (sudo)
# log out and back in
make guestfs-host-setup        # libguestfs + pool + network (sudo)
make bringup                   # the actual workflow (no extra sudo prompts)
```
