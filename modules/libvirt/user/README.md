# libvirt/user — controller user / group setup (sudo opt-in)

## Purpose

Install libvirt and add the controller user to the libvirt, kvm, and
distro-specific qemu groups so the user can spawn libvirt guests
without root. This is sudo work on the controller host; per the
module spec it is gated behind an opt-in Make target.

## Tasks

| Task | Make target | Notes |
|---|---|---|
| Verify libvirt is installed and the user is in the required groups | runs by default as part of `playbooks/libvirt.yml` | non-sudo |
| Install libvirt packages + add user to groups | `make libvirt-user-setup` | sudo |

## Manual alternative

If you prefer not to grant the controller sudo to kdevops:

```
# Debian / Ubuntu
sudo apt-get install libvirt-clients libvirt-daemon-system qemu-system-x86 qemu-utils virtinst
sudo usermod -aG libvirt,kvm,libvirt-qemu $USER

# Fedora / RHEL
sudo dnf install libvirt-client libvirt-daemon-driver-qemu qemu-kvm virt-install
sudo usermod -aG libvirt,kvm,qemu $USER

# Then log out and back in.
```

After the manual setup the verify path passes silently and the rest
of the kdevops bringup proceeds.

## Layout

```
modules/libvirt/user/
├── Makefile
└── README.md

playbooks/roles/libvirt/user/
├── verify/tasks/main.yml    non-sudo precheck (default path)
└── setup/                    sudo work (opt-in via libvirt-user-setup tag)
    ├── defaults/main.yml
    └── tasks/
        ├── main.yml
        ├── install-deps/...  distro-specific package install
        └── enable-user/...   distro-specific group membership
```

## Dependencies

`libvirt/` parent module orchestrates this sub-module.
