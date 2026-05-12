# guestfs-runtime_deps — Runtime dependencies

## When this matters

guestfs's role needs four pieces of distro-provided software at
runtime: `libguestfs-tools` (for `virt-builder` and
`virt-sysprep`), the python libvirt binding (used by the
`community.libvirt.virt` Ansible module), OVMF firmware (the
UEFI BIOS each guest boots when
`CONFIG_GUESTFS_REQUIRES_UEFI=y`), and the DHCP client guests
need through the default network's NAT.

The kdevops vocabulary calls this kind of package install a
**runtime_deps sub-module**, the term borrowed from
[Yocto's `RDEPENDS`](https://docs.yoctoproject.org/ref-manual/variables.html#term-RDEPENDS):
runtime dependencies of a package. The setup is sudo on the
controller and gated behind the opt-in Make target per the
spec's controller-side sudo isolation rule.

## The opt-in path

```
make guestfs-runtime-deps-setup
```

Drives `playbooks/guestfs.yml` with
`--tags guestfs_runtime_deps_setup` and runs the
`playbooks/roles/guestfs/runtime_deps/setup/` sub-role under
sudo. The sub-role dispatches on `ansible_os_family`:

- `Debian` → `apt-get install libguestfs-tools dhcpcd-base
  isc-dhcp-client python3-lxml python3-libvirt ovmf`.
- `RedHat` → `dnf install libguestfs-tools-c python3-libvirt
  edk2-ovmf`.
- `Suse` → `zypper install guestfs-tools python3-libvirt-python
  qemu-ovmf-x86_64`.

After the install the verify path passes silently and `make
bringup` proceeds without prompting for package-install sudo.

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
```

### Fedora / RHEL / CentOS Stream

```
sudo dnf install \
    libguestfs-tools-c \
    python3-libvirt \
    edk2-ovmf
```

### openSUSE / SLES

```
sudo zypper install \
    guestfs-tools \
    python3-libvirt-python \
    qemu-ovmf-x86_64
```

After the manual install the guestfs verify path passes silently
and `make bringup` proceeds.

## What the verify path checks

`playbooks/roles/guestfs/runtime_deps/verify/tasks/main.yml`
runs without sudo and stats the controller's PATH for `virsh`
and `virt-builder`. The diagnostic on failure names both
`make guestfs-runtime-deps-setup` and this document, so the user
has a clear next step.

The two checks are kept narrow on purpose: a working `virsh`
proves libvirt-clients is installed and `virt-builder` proves
libguestfs-tools is present. The rest of the package list
(python bindings, OVMF, DHCP client) is implied by those two
and surfaces through downstream task failures with
distro-specific messages.

## Dependencies

`libvirt/user` should be run before `guestfs-runtime-deps-setup`
on a fresh host so the user has the libvirt group membership the
verify path implicitly depends on. The recommended order is:

```
make libvirt-user-setup              # libvirt + kvm group membership
# log out and back in
make libvirt-storage-pool-setup      # pool dir + virsh pool object
make guestfs-runtime-deps-setup      # this target
make guestfs-network-setup           # libvirt default network
make bringup
```
