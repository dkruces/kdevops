# guestfs/host_setup — one-time host configuration (sudo opt-in)

## Purpose

Prepare the controller host for libvirt-backed guestfs VM
provisioning in one shot. Three things happen here:

1. Install distro libguestfs and supporting packages (sudo,
   apt/dnf/zypper).
2. Create `libvirt_storage_pool_path` with group ownership of
   `libvirt_qemu_group` (sudo, file).
3. Ensure libvirt's default network is up and dnsmasq is in a
   compatible state (sudo, systemctl + virsh).

Per the module spec's controller-side sudo isolation rule the work
lives behind an opt-in Make target and the parent guestfs role
runs a non-sudo verify path on its default execution.

## Tasks

| Task | Make target | Notes |
|---|---|---|
| Verify libvirt, libguestfs, pool dir, dnsmasq state | runs by default as part of `make bringup` | non-sudo |
| Install + prepare the host | `make guestfs-host-setup` | sudo |

## Manual alternative

See [`docs/guestfs-host_setup.md`](../../../docs/guestfs-host_setup.md)
for the per-distro manual sequence.

## Layout

```
modules/guestfs/host_setup/
├── Makefile
└── README.md

playbooks/roles/guestfs/host_setup/
├── verify/tasks/main.yml   non-sudo precheck (default path)
└── setup/                   sudo (opt-in via guestfs_host_setup tag)
    └── tasks/
        ├── main.yml          dispatcher
        ├── install-deps/     distro package install
        ├── network.yml       dnsmasq + libvirt default network
        └── storage-pool-path.yml  pool directory mkdir + chown
```

## Dependencies

`libvirt/user` should be set up before `guestfs-host-setup` runs,
since the guestfs verify path also checks for libvirt group
membership. The typical first-run sequence on a fresh host is:

```
make libvirt-user-setup     # libvirt group membership
# log out and back in
make guestfs-host-setup     # libguestfs + pool + network
make bringup                # spawn VMs
```
