# nixos-flake imageless (qsu) GPU-passthrough KV cache (vLLM + LMCache) V3 workload

This adds a kdevops path to run the **vLLM + LMCache KV cache workload** inside
a **nixos-flake qsu imageless guest**, replaying the **TensorMesh V3** agentic-trace benchmark
(`sammshen/lmcache-agentic-traces`: 787 sessions / 24,881 iterations from
SWE-bench, GAIA, WildClaw).

## Hardware dependency analysis (what the workload actually needs)

vLLM + LMCache do real CUDA compute, so a paravirtual display adapter
(virtio-gpu/QXL) is **not** sufficient — there is no CUDA device behind it. The
workload therefore depends on:

1. **A physical GPU passed into the guest via VFIO PCIe pass-through.** The
   guest must own the GPU exclusively. The graphics function `.0` carries the
   CUDA device; LMCache offload (HBM→DRAM→NVMe) and prefix-aware reuse all run
   on top of it.
2. **Host IOMMU (VT-d / AMD-Vi).** Required to isolate the GPU into its own
   IOMMU group so QEMU/VFIO can hand it to the guest safely. Host cmdline:
   `intel_iommu=on` (or `amd_iommu=on`) plus `iommu=pt`.
3. **`vfio-pci` bound to the GPU on the host.** The GPU must be detached from
   `nouveau`/`nvidia`/`amdgpu` and from the host display. qsu's
   `vfio-bind@<addr>.service` does the rebind on start (declared via
   `Requires=` in the per-VM service drop-in), but the host must not be
   actively using the device.
4. **The full IOMMU group passed through together.** Discrete NVIDIA GPUs
   expose an HDMI-audio function `.1` in the same group; both `.0` and `.1`
   must be assigned or the group won't bind.
5. **UEFI/OVMF guest firmware.** Modern large-BAR GPUs need Above-4G decoding,
   which the SeaBIOS/legacy path doesn't provide — the qemu-system@<vm>.service switches
   to OVMF when passthrough is on.
6. **Guest GPU driver + CUDA.** The NixOS module loads the proprietary NVIDIA
   driver and CUDA toolkit (or amdgpu+ROCm) so vLLM/LMCache see the device.

What it does **not** depend on: the GPU is not SR-IOV/vGPU-sliced here (full
device pass-through), and no GPUDirect Storage path is assumed for the smoke
test (LMCache NVMe offload uses ordinary block I/O to the guest's virtio disk).

## Files added/changed

- `defconfigs/nixosfi-kvcache-v3` — turnkey config.
- `kconfigs/Kconfig.qsu` — `QSU_PCI_PASSTHROUGH*` and `QSU_IOMMU_*` knobs.
- `kconfigs/Kconfig.nixos_flake` — `NIXOS_FLAKE_GPU_VENDOR` knob.
- `workflows/vllm/Kconfig` — `VLLM_BENCHMARK_V3*` knobs.
- `playbooks/roles/qsu/tasks/render-per-vm.yml` — PCI-addr → device list,
  threads `pci_passthrough` + `iommu` into the vm.env and service drop-in.
- `playbooks/roles/nixosfi/templates/default.nix.j2` — guest NVIDIA/AMD + CUDA.
- `playbooks/roles/vllm/templates/vllm-benchmark-v3.py.j2` — V3 replayer.
- `playbooks/roles/vllm/tasks/main.yml` — deploy + run V3 runner.
- `workflows/vllm/Makefile` — `make vllm-benchmark-v3`.
- `scripts/gpu-passthrough-check.sh` — host VFIO readiness check.

## Step-by-step

1. **Prep the host (hypervisor).** Enable IOMMU on the host kernel cmdline,
   bind the GPU to `vfio-pci`, then verify:
   ```
   scripts/gpu-passthrough-check.sh 0000:81:00.0 0000:81:00.1
   ```
   Fix every `[FAIL]` before continuing.

2. **Configure kdevops.** Use the defconfig, overriding the PCI addresses for
   your host:
   ```
   make defconfig-nixosfi-kvcache-v3 \
     QSU_PCI_PASSTHROUGH_PCI_ADDR=0000:81:00.0 \
   ```

3. **Bring up the guest** (defines the qemu-system@<vm>.service with the `<hostdev>`
   GPU and OVMF firmware, builds the NixOS system with the GPU driver+CUDA):
   ```
   make bringup
   ```

4. **Validate GPU is live in the guest:**
   ```
   ansible baseline:dev -i hosts -m command -a 'nvidia-smi -L'
   ```
   You should see the physical GPU listed from inside the guest.

5. **Deploy vLLM + LMCache** (GPU inference, KV-cache offload enabled):
   ```
   make vllm
   ```

6. **Run the V3 workload:**
   ```
   make vllm-benchmark-v3
   ```
   Results (CSV + JSON summary) land in `/data/vllm-benchmark/` inside the
   guest. Switch presets via `CONFIG_VLLM_BENCHMARK_V3_PRESET` or cap sessions
   with `CONFIG_VLLM_BENCHMARK_V3_MAX_SESSIONS` for a quick smoke run.

## Validation already performed on these files

- Python V3 runner: AST-parses; end-to-end smoke test with a mocked endpoint
  confirms worker-pool dispatch, **strictly sequential turns within a session**
  (prefix-growth invariant), preset timing modes, and CSV+JSON output.
- qsu vm.env: renders the `-device vfio-pci,host=<addr>` per device plus
  the matching IOMMU (`-device intel-iommu,intremap=on,caching-mode=on`)
  and flips `-accel` to `kvm,kernel-irqchip=split` automatically.
- qsu service drop-in: emits `Requires=vfio-bind@<addr>.service` per
  device and bumps `LimitMEMLOCK` to `ram+256M` for the VFIO DMA pin.
- `default.nix.j2` and the V3 template: pass Jinja2 parse.
- Edited Ansible tasks: pass YAML load.
- `scripts/gpu-passthrough-check.sh`: passes `bash -n`.

## Notes for the real (multi-GPU, large-model) run

For Qwen3-Coder-480B-AWQ with 8× tensor parallelism, list all eight
GPU PCI addresses (graphics .0 and, if in-group, audio .1) in
`QSU_PCI_PASSTHROUGH_DEVICES` as a comma-separated string, raise
`VLLM_TENSOR_PARALLEL_SIZE=8`, bump `QSU_RAM` well above the LMCache
CPU buffer, and add NVMe storage with `QSU_NVME_DRIVE_COUNT` /
`QSU_NVME_DRIVE_SIZE_GB`. All eight GPUs (and their audio functions,
if in-group) must be bound to `vfio-pci` and live in clean IOMMU
groups on the host.
