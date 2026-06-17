# SPDX-License-Identifier: copyleft-next-0.3.1
#
# AMD GPU driver and ROCm runtime for a guest that owns a real
# AMD card. Composes on top of any backend module that supplies
# the device through VFIO PCIe pass-through (the host-side qemu/
# libvirt machinery hands the device to the guest; this module
# loads amdgpu and ROCm so the guest can talk to it).
#
# allowUnfree is required because some ROCm components ship under
# a redistributable license that the free filter rejects.
{ pkgs, ... }:
{
  nixpkgs.config.allowUnfree = true;

  services.xserver.videoDrivers = [ "amdgpu" ];

  hardware.graphics.enable = true;

  environment.systemPackages = with pkgs; [
    rocmPackages.clr
    pciutils
  ];
}
