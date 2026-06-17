#!/usr/bin/env bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Verify a host is ready to pass a GPU through to a kdevops NixOS/QEMU
# guest via VFIO. Run this on the HYPERVISOR before `make bringup`.
#
# Usage: scripts/gpu-passthrough-check.sh 0000:81:00.0 [0000:81:00.1 ...]

set -euo pipefail

if [ "$#" -lt 1 ]; then
	echo "usage: $0 <pci-addr> [<pci-addr> ...]" >&2
	echo "  e.g. $0 0000:81:00.0 0000:81:00.1" >&2
	exit 1
fi

fail=0
note() { printf '  %s\n' "$*"; }
ok()   { printf '[ OK ] %s\n' "$*"; }
bad()  { printf '[FAIL] %s\n' "$*"; fail=1; }

echo "== 1. IOMMU enabled on the host kernel =="
if [ -d /sys/kernel/iommu_groups ] && \
   [ "$(find /sys/kernel/iommu_groups -maxdepth 1 -type l 2>/dev/null | wc --lines)" -gt 0 ] || \
   [ "$(ls --format=single-column /sys/kernel/iommu_groups 2>/dev/null | wc --lines)" -gt 0 ]; then
	ok "IOMMU groups present"
else
	bad "No IOMMU groups. Add intel_iommu=on (or amd_iommu=on) iommu=pt to the host cmdline."
fi

echo "== 2. vfio-pci module available =="
if modinfo vfio-pci >/dev/null 2>&1 || lsmod | grep --quiet '^vfio_pci'; then
	ok "vfio-pci present"
else
	bad "vfio-pci module not found."
fi

echo "== 3. Per-device checks =="
for addr in "$@"; do
	echo "-- $addr --"
	if ! lspci -s "${addr#0000:}" >/dev/null 2>&1; then
		bad "$addr: device not found by lspci"
		continue
	fi
	lspci -nnks "${addr#0000:}" | sed 's/^/      /'

	# IOMMU group + group members
	grp_link="/sys/bus/pci/devices/$addr/iommu_group"
	if [ -e "$grp_link" ]; then
		grp="$(basename "$(readlink --canonicalize "$grp_link")")"
		note "IOMMU group: $grp"
		note "Group members (ALL must be passed through together):"
		for d in /sys/kernel/iommu_groups/"$grp"/devices/*; do
			b="$(basename "$d")"
			note "    $b  $(lspci -nns "${b#0000:}" | cut --delimiter=' ' --fields=2-)"
		done
	else
		bad "$addr: no iommu_group (IOMMU off?)"
	fi

	# Current kernel driver
	drv_link="/sys/bus/pci/devices/$addr/driver"
	if [ -e "$drv_link" ]; then
		drv="$(basename "$(readlink --canonicalize "$drv_link")")"
		if [ "$drv" = "vfio-pci" ]; then
			ok "$addr bound to vfio-pci"
		else
			bad "$addr bound to '$drv' (must be vfio-pci, not nouveau/nvidia/amdgpu)"
		fi
	else
		note "$addr currently has no driver bound (libvirt managed='yes' will bind vfio-pci)"
	fi
done

echo
if [ "$fail" -eq 0 ]; then
	echo "All checks passed. Host looks ready for GPU pass-through."
else
	echo "One or more checks failed. Fix the host before 'make bringup'." >&2
	exit 1
fi
