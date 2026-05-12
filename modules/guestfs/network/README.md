# guestfs/network — libvirt default network setup (sudo opt-in)

## Purpose

Ensure libvirt's default NAT network is defined and running on
the controller, and that no standalone dnsmasq instance conflicts
with the dnsmasq libvirt bundles. The verify path catches the
common failure modes (default network down, dnsmasq present
standalone on Debian/Ubuntu) and the setup path's
`virsh net-start default` brings the network up.

This sub-module is a host-configuration sub-module (no Yocto
analog — Yocto recipes do not configure the build host). See
`docs/module-spec.md` "Host-configuration vocabulary" for the
spec naming.

## Tasks

| Task | Make target | Notes |
|---|---|---|
| Verify the default network is up | runs by default as part of `playbooks/guestfs.yml` | non-sudo |
| Configure dnsmasq state and start the default network | `make guestfs-network-setup` | sudo |

## Manual alternative

See `docs/guestfs-network.md` for the manual sequence.

## Layout

```
modules/guestfs/network/
├── Makefile
└── README.md

playbooks/roles/guestfs/network/
├── verify/tasks/main.yml   non-sudo precheck (default path)
└── setup/                   sudo opt-in
    └── tasks/
        ├── main.yml          dispatcher
        └── network.yml       dnsmasq + libvirt default network
```

## Dependencies

The parent `guestfs` module orchestrates this sub-module.
`libvirt/storage_pool` typically runs first since both target
libvirt-system URI setup; the order is recorded in
`docs/guestfs.md`.
