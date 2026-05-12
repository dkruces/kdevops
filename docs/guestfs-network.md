# guestfs-network — libvirt default network

## When this matters

guestfs relies on libvirt's default NAT network to give each
guest a DHCP address and outbound connectivity. The network
needs to be defined, started, and have dnsmasq running through
libvirt's bundled instance. On Debian/Ubuntu a standalone
dnsmasq package installed system-wide collides with the bundled
one and prevents the default network from coming up.

This is a host-configuration sub-module — no Yocto analog;
Yocto recipes do not configure the build host. See
`docs/module-spec.md` "Host-configuration vocabulary" for the
spec naming.

## The opt-in path

```
make guestfs-network-setup
```

Drives `playbooks/guestfs.yml` with
`--tags guestfs_network_setup` and runs the
`playbooks/roles/guestfs/network/setup/` sub-role under sudo.
The sub-role:

1. Stats `/etc/dnsmasq.conf` and `/etc/dnsmasq.d` on Debian-family
   distros and fails with a manual-remediation message if a
   standalone dnsmasq package is installed.
2. Runs `virsh net-list --name` and `virsh net-start default` if
   the default network is not already up.
3. On Debian-family distros also checks `systemctl is-enabled
   dnsmasq` and `systemctl is-active dnsmasq` and fails if a
   standalone dnsmasq is enabled or running, so the operator
   can disable it manually.

## The manual path

```
# Debian / Ubuntu only: if dnsmasq is installed standalone,
# either remove it or stop and disable it:
sudo apt-get remove dnsmasq
# or, to keep the package but ensure libvirt's bundled dnsmasq
# is the one that runs:
sudo systemctl disable --now dnsmasq

# All distros: start (and optionally autostart) the libvirt
# default network.
sudo virsh net-start default
sudo virsh net-autostart default
```

After the manual sequence the guestfs network verify path passes
silently.

## What the verify path checks

`playbooks/roles/guestfs/network/verify/tasks/main.yml` runs
without sudo and:

1. Skips entirely when the user picked libvirt session URI
   (`CONFIG_LIBVIRT_URI_SESSION=y`); the default network is only
   relevant for the system URI.
2. Runs `virsh net-list --name` and fails with the standard
   actionable diagnostic when `default` is not in the output.

## Dependencies

`libvirt/user` and `libvirt/storage_pool` should be set up
before `guestfs-network-setup`. The first-run sequence in
`docs/guestfs.md` records the canonical order.
