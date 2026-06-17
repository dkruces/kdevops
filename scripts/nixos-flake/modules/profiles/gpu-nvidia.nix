# SPDX-License-Identifier: copyleft-next-0.3.1
#
# NVIDIA GPU driver and CUDA toolkit for a guest that owns a real
# NVIDIA card. Composes on top of any backend module that supplies
# the device through VFIO PCIe pass-through (the host-side qemu/
# libvirt machinery hands the device to the guest; this module
# loads the proprietary driver and CUDA so the guest can talk to
# it).
#
# allowUnfree is required because nvidia-x11 and cudatoolkit ship
# under NVIDIA's redistributable license. nvidia-container-toolkit
# adds CDI support so OCI runtimes inside the guest can expose the
# GPU to containers.
{
  config,
  lib,
  pkgs,
  ...
}:
{
  nixpkgs.config.allowUnfree = true;

  services.xserver.videoDrivers = [ "nvidia" ];

  hardware.nvidia = {
    modesetting.enable = true;
    open = false;
    nvidiaSettings = false;
    package = config.boot.kernelPackages.nvidiaPackages.production;
  };

  hardware.graphics.enable = true;
  hardware.nvidia-container-toolkit.enable = true;

  environment.systemPackages = with pkgs; [
    cudaPackages.cudatoolkit
    pciutils
  ];
}
