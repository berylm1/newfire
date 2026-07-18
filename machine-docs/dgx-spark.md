# `spark-a439` (DGX Spark) — GPU Inference Node

> Takeover-ready documentation. Generated from a live snapshot over Tailscale.

## 1. Overview

| Field | Value |
| --- | --- |
| Hostname | `spark-a439` |
| Tailscale hostname | `ghana` |
| Tailscale IP | `100.88.112.5` |
| OS | Ubuntu 24.04.4 LTS |
| Kernel | `6.17.0-1014-nvidia` (aarch64) |
| CPU cores | 20 (Grace CPU) |
| RAM | 119 GiB total / ~2.7 GiB available (heavily used by GPU workload) |
| Disk | 3.7 TB NVMe (`/dev/nvme0n1p2`), 39% used (1.4T/2.2T) |
| Swap | none |
| Uptime | ~7 days at snapshot |
| Primary user | `root` (and `newwave-dgx` for project files) |
| GPU | **NVIDIA GB10** (Grace Blackwell), Driver 580.142, CUDA 13.0 |
| CUDA toolkit | `/usr/local/cuda-13.0` |

## 2. Access

| Method | Address | Notes |
| --- | --- | --- |
| SSH (Tailscale) | `root@100.88.112.5` or `ghana.tail3a833f.ts.net` | root login works via Tailscale SSH |
| LAN | not exposed directly | reachable through Tailscale only from this network |

- The local user `newwave-dgx` owns the project/home directory `/home/newwave-dgx`.
- This box's `root` SSH authorized_keys includes the `newwaveclaw` ed25519 key.
- **No password sudo or interactive account policy documented — re-issue access on handover.**

## 3. Installed Tooling

| Tool | Version |
| --- | --- |
| Docker | 29.2.1 |
| Git | 2.43.0 |
| Python | 3.12.3 |
| Node.js | v22.22.2 |
| Go | present |
| CUDA | 13.0 (`/usr/local/cuda`) |
| `nvcc` | 13.0 |
| Ollama | installed (no instance running at snapshot) |
| `node_exporter` | running on `:9100` (systemd-style process) |

## 4. Running Workloads

### vLLM inference (primary role)

Only one model is **currently served** (observed binding `:8001`):

| Container | Image | Model served | Port | Status |
| --- | --- | --- | --- | --- |
| `qwen-spark` | `vllm-patched:26.06-py3` | `Qwen/Qwen3.6-27B-FP8` (served as `qwen`) | `0.0.0.0:8001` | Up 34h |

Served model flags (from running process):
`--max-model-len 219520 --max-num-seqs 4 --enable-prefix-caching
--enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3
--speculative-config {method: mtp, num_speculative_tokens: 5}`.

### Monitoring

| Process | Listen | Notes |
| --- | --- | --- |
| `node_exporter` | `:9100` | Prometheus node metrics |

### SSH / system

| Process | Listen | Notes |
| --- | --- | --- |
| `sshd` | `:22` | standard |
| `tailscaled` | TS IP `:43875` | Tailscale control/data |

## 5. Model Start Scripts (`/home/newwave-dgx/start_*.sh`)

These scripts launch vLLM for various models. The **currently active** one is
`start_qwen3_coder_30b_vllm.sh`-family / `qwen-spark` (Qwen3.6-27B). Available presets:

| Script | Served model name | Target model |
| --- | --- | --- |
| `start_qwen35_flash_vllm.sh` | `qwen3.5-flash` | `Qwen3.5-35B-A3B-NVFP4` |
| `start_qwen3_coder_30b_vllm.sh` | `qwen3-coder-30b` | `Qwen3-Coder-30B-A3B-Instruct-NVFP4` |
| `start_qwen_coder_7b_vllm.sh` | `qwen2.5-coder-7b` | `Qwen2.5-Coder-7B-Instruct` |
| `start_qwen_coder_7b_vllm_8001.sh` | `qwen2.5-coder-7b` | (port 8001 variant) |
| `start_dsr1_70b_vllm.sh` | `deepseek-r1-distill-70b` | `DeepSeek-R1-Distill-Llama-70B-NVFP4` |
| `start_nano_omni.sh` / `start_nano_omni_vllm.sh` | `nemotron-nano-omni` | `Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4` |
| `start_nemotron_super_vllm.sh` | `nemotron-super-vllm` | `Nemotron-3-Super-120B-A12B-NVFP4` |
| `start_super_llama.sh` / `start_super_vllm.sh` | `nemotron-super` | `Nemotron-3-Super-120B-A12B` |

> Only one vLLM instance should run at a time (GPU memory is shared). Stop the
> running container before launching a different model preset.

## 6. Model Weights on Disk (`/home/newwave-dgx/models`)

| Directory | Model |
| --- | --- |
| `kimi-k2.7` | Kimi K2.7 |
| `minimax-m2.7-gguf` | MiniMax M2.7 (GGUF) |
| `NVIDIA-Nemotron-3-Nano-Omni` | Nemotron-3 Nano Omni |
| `NVIDIA-Nemotron-3-Super-120B-A12B-UD-Q4_K_M` | Nemotron-3 Super 120B (Q4_K_M) |

Plus cached HuggingFace downloads under `/home/newwave-dgx/hf-cache` and
`/home/newwave-dgx/hf-venv`.

## 7. Project Codebases (`/home/newwave-dgx`)

| Path | Purpose |
| --- | --- |
| `NemoClaw/` | NVIDIA Nemotron agent framework (see its README/CLAUDE/AGENTS) |
| `minimax/` | MiniMax model serving / client (README, CLAUDE, config) |
| `spark-vllm-docker/` | Patched vLLM Docker build for GB10 (`vllm-patched` image source) |
| `dcgm-exporter/` | DCGM metrics exporter |
| `llama.cpp/` | Local llama.cpp build |
| `newfire-minimax-m3-showcase/` | Demo app |
| `newfire-nss-router/`, `newfire-nss-runner/` | NewFire NSS routing/runner |
| `qdrant-newfire/` | Qdrant vector store for RAG |
| `litellm-config*.yaml` | LiteLLM proxy configs (**may contain API keys — excluded from repo**) |

## 8. Secrets & Security (provision before takeover)

- **`litellm-config*.yaml` / `*.bak*`** may contain LLM provider API keys — **do not
  commit**; redact before any documentation export.
- **No Tailscale SSH user mapping for non-root** — access is `root` only via TS SSH;
  re-issue or scope down on handover.
- Docker images are built locally (`vllm-patched`); rebuild from
  `spark-vllm-docker/` if the image is lost.
- `~/.ssh/` and browser profiles (snap/firefox) contain credentials — exclude from any export.

## 9. Known Issues at Snapshot

1. RAM shows only ~2.7 GiB free — expected while a 27B model is resident in
   Grace-attached memory; do not panic, but watch OOM.
2. Many vLLM EngineCore internal ports (38xxx–43xxx) are bound to `127.0.0.1` —
   only `:8001` is the public API surface.
3. `ollama` is installed but no daemon is running — not the active inference path.

## 10. Takeover Checklist

- [ ] Gain Tailscale access to `ghana` (`100.88.112.5`) as root (or request key re-issue).
- [ ] Confirm `qwen-spark` vLLM is serving on `:8001`; test with a chat completion.
- [ ] Decide which model preset to run; stop current container before switching.
- [ ] Rebuild `vllm-patched` image from `spark-vllm-docker/` if needed.
- [ ] Rotate any LLM provider keys found in `litellm-config*.yaml`.
- [ ] Verify `node_exporter :9100` is scraped by the monitoring stack on `newwaveclaw`.
- [ ] Read companion doc `machine-docs/newwaveclaw.md` (control plane lives there).
