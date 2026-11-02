# CUDA Driver + PyTorch Enablement Plan — Quadro M5000 (Maxwell, sm_52)

## Goal

Get PyTorch running on the GPU with the newest software stack this hardware can actually use.

## Verified environment (2026-11-01)

| Item | Value | Evidence |
|---|---|---|
| OS / kernel | CachyOS rolling, `7.3.0-4-cachyos` | `/etc/os-release`, `uname -a` |
| GPU | NVIDIA Quadro M5000 (GM204, compute capability **5.2**) | `/proc/driver/nvidia/gpus/0000:03:00.0/information` |
| Driver | **580.196.07** (NVRM), loaded, DKMS | `/proc/driver/nvidia/version` |
| Driver packages | `nvidia-580xx-dkms`, `nvidia-580xx-utils`, `lib32-nvidia-580xx-utils` = 580.196.07; `nvidia-580xx-settings`/`libxnvctrl-580xx` = 580.178.04 | pacman local DB |
| Installed torch | **2.15.0+cpu** in conda env `ml-arch` (Python 3.11.18) | `site-packages/torch/version.py` |
| Repo pin | `requirements-lock.txt`: `torch==2.15.0` + `cuda-toolkit==13.2.2` + `nvidia-cudnn-cu13` | `requirements-lock.txt:141,463,886` |
| System CUDA toolkit | 13.4.3 (`cuda` package) — cannot compile sm_52 | pacman local DB |

### The two hard constraints

1. **Driver:** The 580 branch is the **last** NVIDIA branch supporting Maxwell/Pascal/Volta, and 580.196.07 is the newest 580 release. There is no "newer compatible driver". Installing `nvidia-utils` / `nvidia-open` 595.x or 610.x will leave a GM204 with no usable kernel module (nvidia-smi fails). Source: NVIDIA KB 3142 (Unix legacy releases) and KB 5706 (Quadro Maxwell plan).
2. **PyTorch:** CUDA 13 removed offline compilation for compute capability < 7.5, and PyTorch 2.15 removed all CUDA 12.6 wheels. **PyTorch 2.14.1+cu126 is the newest prebuilt release supporting sm_52.** Wheel indexes verified: `torch-2.14.1+cu126-cp311-...manylinux_2_28_x86_64.whl` and `torchvision-0.29.1+cu126-cp311-...` exist on `download.pytorch.org`.

**Conclusion:** the driver is already correct and should not be changed. The missing piece is the GPU PyTorch build. Do not "upgrade" the driver; install torch 2.14.1+cu126.

## Decisions

- Keep driver 580.196.07; only ever update within the 580.x series.
- Clone env `ml-arch` to `ml-arch-backup`, then replace CPU torch in `ml-arch` with `torch 2.14.1+cu126` + `torchvision 0.29.1+cu126` (user-selected).
- Do **not** install `torchaudio`: no cu126 build exists above 2.11.0, and the repo never imports it (verified: no `import torchaudio` matches).
- Do not touch notebooks; do not mutate source notebooks with outputs.

## Step-by-step tasks

### 1. Record the baseline (no changes)

```bash
nvidia-smi
cat /proc/driver/nvidia/version
dkms status
pacman -Q | grep -iE 'nvidia|^cuda|cccl'
/home/nola/anaconda3/bin/conda run -n ml-arch python -c "import torch;print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
/home/nola/anaconda3/bin/conda run -n ml-arch python -m pip freeze > /tmp/ml-arch-before.txt
df -h /home
```

Expected now: driver 580.196.07, `dkms status` shows `nvidia/580.196.07` installed for `7.3.0-4-cachyos`, torch prints `2.15.0+cpu None False`.

### 2. Verify driver/GPU compatibility (no install)

```bash
nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap --format=csv
```

Expected: `Quadro M5000, 580.196.07, 8192 MiB, 5.2`.

Compatibility rule to record: CUDA 12.6 runtime (bundled in the torch wheel) needs driver >= 525.60.13; 580.196.07 satisfies it. The 580 driver supports CUDA 12.x and 13.x runtimes, but **not** sm_52 compilation with CUDA 13 toolkits.

### 3. Confirm/refresh the driver only within the 580 branch

```bash
paru -Qu            # or: checkupdates
paru -Syu           # normal system update
```

- If `nvidia-580xx-*` has a newer 580.x version, let it update (DKMS rebuilds automatically; reboot afterwards).
- If `paru` proposes `nvidia-utils`/`nvidia-open` 595.x/610.x, **decline**; those replace the 580xx packages and kill GPU support.
- Recommended guard in `/etc/pacman.conf` (requires sudo, optional but strongly advised):

```ini
IgnorePkg = nvidia-utils nvidia-open nvidia-open-dkms nvidia nvidia-lts
```

  Keep `nvidia-580xx-*` updatable. Verify with `pacman -Q nvidia-580xx-dkms nvidia-580xx-utils`.

Clean reinstall path (only if the module ever stops loading):

```bash
sudo pacman -S --needed linux-cachyos-headers dkms
paru -S nvidia-580xx-dkms nvidia-580xx-utils lib32-nvidia-580xx-utils nvidia-580xx-settings
sudo dkms autoinstall
sudo reboot
```

Emergency fallback only (bypasses pacman, remove conflicting packages first): download `NVIDIA-Linux-x86_64-580.196.07.run` from `https://download.nvidia.com/XFree86/Linux-x86_64/580.196.07/` and run with `--dkms`. Prefer the distro/AUR packages on CachyOS.

### 4. Back up the conda env

```bash
/home/nola/anaconda3/bin/conda create -n ml-arch-backup --clone ml-arch -y
/home/nola/anaconda3/bin/conda env list
```

Do not proceed if the clone fails (disk: expect several GB).

### 5. Install the CUDA 12.6 PyTorch stack in `ml-arch`

```bash
conda activate ml-arch
python -m pip list | grep -iE 'nvidia-|cuda-|^torch'
```

If any CUDA-13 pip packages (`nvidia-cublas-cu13`, `nvidia-cudnn-cu13`, `cuda-toolkit`, ...) are present, uninstall them first, then:

```bash
python -m pip install --index-url https://download.pytorch.org/whl/cu126 \
  "torch==2.14.1+cu126" "torchvision==0.29.1+cu126"
python -m pip check
```

Notes:
- `--index-url` (not `--extra-index-url`) prevents pip from resolving to the CUDA 13/cu132 default wheels.
- Do not install/upgrade `torchaudio`; leave it absent or uninstalled.
- If pip reports conflicts from unrelated packages, fix only those that block torch; do not run a blanket `pip install -U`.

### 6. Verify the wheel actually targets sm_52 (must be before app testing)

```bash
python - <<'PY'
import torch
print("torch", torch.__version__)
print("cuda build", torch.version.cuda)
print("arch list", torch.cuda.get_arch_list())
print("available", torch.cuda.is_available())
print("capability", torch.cuda.get_device_capability(0))
print("name", torch.cuda.get_device_name(0))
print("cudnn", torch.backends.cudnn.version())
x = torch.randn(1024, 1024, device="cuda", requires_grad=True)
y = (x @ x).sum(); y.backward()
print("matmul+backward ok", float(y), x.grad.abs().sum().item())
conv = torch.nn.Conv2d(3, 8, 3).cuda()
out = conv(torch.randn(2, 3, 32, 32, device="cuda"))
out.mean().backward()
print("cudnn conv ok", tuple(out.shape))
PY
```

Pass criteria: `cuda build = 12.6`, `arch list` includes `sm_50`, `available = True`, `capability = (5, 2)`, both ops complete with no `no kernel image is available` error. `torch.cuda.is_available() == True` alone is **not** sufficient evidence.

### 7. Regression-test the repo

```bash
conda activate ml-arch
cd /home/nola/LMp2LMa
python -m pytest tests capstone/tests -m "not slow" -q          # baseline: 102 passed, 2 deselected
QUICK_MODE=1 python -m pytest --nbval-lax -q \
  track-01-ml-programmer/01_data_preprocessing.ipynb \
  track-01-ml-programmer/02_experiment_tracking.ipynb \
  track-02-dl-programmer/01_nn_fundamentals.ipynb \
  track-02-dl-programmer/02_cnn_vision.ipynb
```

If unit tests fail on a 2.15-only API, capture the failure and decide: pin code to 2.14-compatible APIs (preferred) vs. the source-build fallback in "Out of scope".

### 8. Update repo dependency metadata (implementation agent, source files)

- Add `requirements-gpu-cu126.txt` pinning the CPU-independent GPU set with an explicit header:
  `--index-url https://download.pytorch.org/whl/cu126` and `torch==2.14.1+cu126`, `torchvision==0.29.1+cu126`.
- Fix the stale CUDA 11.8 guidance in `requirements-gpu.txt:3-4` to point at cu126 and note the Maxwell constraint.
- Generate `requirements-gpu-cu126.lock` via `python -m pip freeze` from the validated env; leave `requirements-lock.txt` (CUDA 13/2.15, non-Maxwell) and `requirements-ci.lock` (CPU CI) untouched.
- Add a short note to `README.md` (or `capstone/docs/operations.md` next to the `conda activate ml-arch` line): this host must use the cu126 lock; torch >= 2.15 has no sm_52 binaries.

### 9. Document hardware limits (avoid future "broken install" reports)

Create/append a short compatibility note (README or docs):
- Maxwell supports fp32/fp16 storage; **no bf16, no TF32, no tensor cores, no flash-attn**.
- `torch.compile`/Triton requires sm_70+; do not enable it on this GPU (set `TORCHDYNAMO_DISABLE=1` if a notebook/library tries).
- `bitsandbytes` GPU kernels target newer architectures and are likely unusable; keep it out of the validated GPU set.
- 8 GB VRAM: keep `QUICK_MODE=1` for notebook sweeps.
- GPU PyTorch support on this card is frozen at 2.14/cu126; driver 580 is supported through ~2028.

### 10. Rollback

```bash
conda deactivate
/home/nola/anaconda3/bin/conda env remove -n ml-arch -y
/home/nola/anaconda3/bin/conda create -n ml-arch --clone ml-arch-backup -y
```

Driver rollback is only needed if a 580.x update broke DKMS: `paru -S nvidia-580xx-dkms=580.196.07-1 ...`, or boot the `linux-cachyos-lts` kernel, then `dkms autoinstall`.

## Failure modes and handling

| Symptom | Cause | Fix |
|---|---|---|
| `no kernel image is available` | CUDA 13 / torch 2.15 wheel on sm_52 | install 2.14.1+cu126; recheck `get_arch_list()` |
| `CUDA driver version is insufficient for CUDA runtime version` | driver older than 525 or 580 packages removed | restore `nvidia-580xx-*`, reboot |
| nvidia-smi fails after `pacman -Syu` | 595/610 `nvidia-utils` replaced 580xx | reinstall 580xx packages, add `IgnorePkg` |
| GPU gone after kernel update | DKMS module not rebuilt | `sudo dkms autoinstall`, reboot |
| OOM in notebooks | 8 GB VRAM | `QUICK_MODE=1`, smaller batches |
| `compute_52 is not supported` from nvcc | `CUDA_HOME=/opt/cuda` (13.4) used to build an extension | skip extension builds, or install CUDA 12.9 toolkit separately and set `CUDA_HOME` |

## Out of scope

- Compiling PyTorch >= 2.15 from source against CUDA 12.9 (only if a repo requirement hard-blocks 2.14).
- TensorFlow GPU enablement (separate stack; Maxwell support is also frozen).
- Docker/`.devcontainer` GPU setup and `requirements-gpu.lock` generation beyond the cu126 lock.
- Multi-GPU/distributed work; the machine has one GPU.

## Done criteria

- `nvidia-smi` reports 580.196.07 and Quadro M5000, compute capability 5.2.
- `torch.__version__ == 2.14.1+cu126`, `torch.version.cuda == "12.6"`, `sm_50` in `get_arch_list()`.
- Matmul+backward and cuDNN conv succeed on `cuda:0`.
- `pytest tests capstone/tests -m "not slow" -q` matches the 102-passed baseline.
- `ml-arch-backup` exists; rollback command documented.

> This plan requires sudo/pacman, conda env mutation, and pip installs — switch to an implementation-capable agent to execute it.
