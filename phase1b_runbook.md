# Phase 1.b runbook: Nemotron-3-Super via vLLM-NVFP4 on DGX Spark

Plan generated 2026-05-13 after Phase 1.a (direct llama.cpp swap) was blocked by GGUF tensor-shape mismatch in llama.cpp build 9093. Phase 1.b pivots to NVIDIA's officially-documented serving path.

## Why this is the right next attempt

1. **NVIDIA officially documents this exact combination.** The [DGX Spark deployment guide for Nemotron-3-Super](https://docs.nvidia.com/nemotron/nightly/usage-cookbook/Nemotron-3-Super/SparkDeploymentGuide/README.html) prescribes vLLM with NVFP4 and specific env vars. Phase 1.a was attempting an unofficial path (community GGUF + standalone llama.cpp) on a brand-new model architecture. Phase 1.b uses the path NVIDIA validated.

2. **The 2026-04-30 vLLM crash had a knowable cause.** That host crash on FP8 was likely the FlashInfer MoE FP4 backend on sm_121, which the NVIDIA guide explicitly tells you to disable via three env vars (`VLLM_USE_FLASHINFER_MOE_FP4=0`, `VLLM_NVFP4_GEMM_BACKEND=marlin`, `FLASHINFER_FUSED_MOE_DISABLE_CUTLASS=1`). Without those, vLLM picks broken kernels. With them, it picks working ones.

3. **Native `qwen3_coder` tool-call parser support.** vLLM has `--tool-call-parser qwen3_coder` as a built-in flag. The Nemotron-3 family emits Qwen3-Coder-style tool calls per the NVIDIA guide. This is the path most likely to make OpenHands' agent loop work correctly. **It's not just about speed. It's about whether tasks complete at all.**

4. **Co-resident with Nano Omni.** NVFP4 footprint is ~67GB (vs 86GB for the community Q4 GGUF). Nano Omni at 32GB + vLLM at ~67GB + overhead ~10GB = ~109GB on 119GB. Tight but feasible. Means `nss-elite` doesn't go down during the swap if memory cooperates.

## Realistic performance expectations

Per primary sources, NVFP4 Nemotron-3-Super on DGX Spark currently gives **~16 tok/s decode**. That's slightly *slower* than the llama.cpp Q4 path would have given (17-20 tok/s) **but** the trade is reliability for raw speed. Specifically:

| Property | llama.cpp Q4 (Phase 1.a) | vLLM NVFP4 (Phase 1.b) |
|---|---|---|
| Decode tok/s | 17-20 | ~16 |
| Tool calls work | Fragile (no `qwen3_coder` parser) | **Native support** |
| Prefix caching across turns | Mamba SSM not cached (issue #16416) | Mamba SSM state managed by vLLM hybrid path |
| Memory footprint | 86GB | 67GB |
| Co-resident with Nano Omni | No | Yes (tight) |
| GGUF compatibility issues | Blocker right now | N/A |

For OpenHands, **tasks completing > raw tok/s.** That's the trade we're making.

## Time budget for the full Phase 1.b swap

| Step | Time | Notes |
|---|---|---|
| Pre-flight checks (Docker GPU, disk space) | 5 min | One-time |
| Pull `vllm/vllm-openai:cu130-nightly` | 5-15 min | Network-dependent. Can run anytime, no service impact |
| Download NVFP4 checkpoint (67GB) | 30-90 min | Background, no impact. **Do this well before swap window.** |
| Launch vLLM container | 5-10 min | Model load |
| Health check + benchmark | 5 min | |
| Tool-call probe | 2 min | |
| LiteLLM config splice + reload | 5 min | |
| OpenHands smoke test | 5 min | |
| Rollback if anything misbehaves | 5 min | |

**Total active swap time once prep is done: ~30-45 min.** Prep time can be days earlier with zero risk.

## Step-by-step

### Pre-session (run anytime, zero impact, can do tonight or while you sleep)

1. SCP `phase1b_prep.sh` to DGX:
   ```
   scp /Users/oluwajobamalomo/phase1b_prep.sh newwave-dgx@100.88.112.5:~/
   ```

2. SSH to DGX, start in tmux/screen so it survives disconnect:
   ```
   tmux new -s phase1b_prep
   bash ~/phase1b_prep.sh
   ```

3. Detach (`Ctrl-b d`) and let it run. Comes back in 30-90 min depending on bandwidth.

4. Verify when done:
   ```
   du -sh ~/.cache/huggingface/hub/nvidia--NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4
   docker images | grep vllm
   ```

   Should show ~67GB checkpoint and `vllm/vllm-openai:cu130-nightly` present.

### Swap session (one focused ~45 min window with attention)

1. SCP all execution scripts:
   ```
   scp /Users/oluwajobamalomo/{start_super_vllm.sh,stop_super_vllm.sh,bench_super_vllm.py,tool_probe_vllm.py,litellm_super_vllm_route.yaml} newwave-dgx@100.88.112.5:~/
   ```

2. Pre-flight: confirm Nano Omni is up so you know your baseline:
   ```
   ssh newwave-dgx@100.88.112.5 'curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:30000/health'
   ```
   Should return 200.

3. Launch vLLM Super:
   ```
   ssh newwave-dgx@100.88.112.5 'bash ~/start_super_vllm.sh'
   ```
   Watch the log tail. Server is ready when:
   ```
   ssh newwave-dgx@100.88.112.5 'curl -s http://127.0.0.1:30002/v1/models | head'
   ```
   returns a JSON model list.

4. **Memory pressure check.** Immediately after the model finishes loading:
   ```
   ssh newwave-dgx@100.88.112.5 'free -g ; docker stats --no-stream vllm-super-nvfp4'
   ```
   If free memory is under 5GB, **stop here and re-evaluate.** Do NOT proceed; you risk crashing the host like 2026-04-30.

5. Benchmark:
   ```
   ssh newwave-dgx@100.88.112.5 'python3 ~/bench_super_vllm.py'
   ```
   Target: 12-18 tok/s. If <5 tok/s, something's wrong with the env vars or backend selection.

6. Tool-call probe:
   ```
   ssh newwave-dgx@100.88.112.5 'python3 ~/tool_probe_vllm.py'
   ```
   Look for `VERDICT: vLLM emitted OpenAI-format tool_calls`. If verdict is NONE, the `qwen3_coder` parser isn't catching the format. Capture the raw content for debugging.

7. **Decision point.** Continue to LiteLLM wire-up only if BOTH benchmark and tool probe pass.

8. LiteLLM wire-up:
   ```
   ssh newwave-dgx@100.88.112.5
   docker cp litellm:/app/config.yaml ~/litellm-config.yaml.bak-pre-phase1b
   # Splice the three blocks from litellm_super_vllm_route.yaml into config.yaml
   # Verify with: docker exec litellm cat /app/config.yaml | grep -A3 nss-thinker-heavy-vllm
   docker exec litellm kill -HUP 1
   ```

9. Smoke test via LiteLLM:
   ```
   curl -X POST http://127.0.0.1:4000/v1/chat/completions \
     -H "Authorization: Bearer sk-newfire-litellm-key" \
     -H "Content-Type: application/json" \
     -d '{"model":"nss-thinker-heavy-vllm","messages":[{"role":"user","content":"Reason about this: 7 farmers split 23 bags of rice..."}],"max_tokens":300}'
   ```

10. OpenHands smoke test: send the Nigerian-context complex prompt through OpenHands with the route forced to `nss-thinker-heavy-vllm`. Watch for `AgentStuckInLoopError` recurrence. If clean, we've solved the parser problem.

### Rollback (any step that fails)

1. Stop vLLM: `bash ~/stop_super_vllm.sh`
2. Restore LiteLLM: `docker cp ~/litellm-config.yaml.bak-pre-phase1b litellm:/app/config.yaml && docker exec litellm kill -HUP 1`
3. Verify Nano Omni still up (it should never have been touched): `curl http://127.0.0.1:30000/health`

## Risk register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Memory pressure crashes host like 2026-04-30 | Medium | High | Three env vars + Step 4 memory check + `--gpu-memory-utilization 0.85` cap |
| vLLM hybrid Mamba path has unknown bugs on aarch64/sm_121 | Medium | Medium | Image is NVIDIA-recommended; if it crashes the container only, host stays up |
| `qwen3_coder` parser doesn't catch Nemotron-3 output | Medium | Medium (no tool calls) | tool_probe step is gate-keeping; can fall back to llama.cpp+rebuilt for non-tool workloads |
| 67GB NVFP4 download fails or is corrupted | Low | Medium | Prep script verifies size; redownload if mismatch |
| Bandwidth too low to download in reasonable time | Possible | Low | Can prep over multiple days; doesn't impact production |

## What success looks like

After Phase 1.b is complete:
- `nss-thinker-heavy-vllm` route serves OpenHands at ~16 tok/s for the Nigerian-context complex prompt
- `AgentStuckInLoopError` does not recur (proves the parser issue was the root cause)
- Nano Omni stays up the whole time (`nss-elite` uninterrupted)
- Total stack memory under control with measurable headroom

## What this does NOT solve

- Raw speed of complex prompts (still ~16 tok/s; agent latency dominates)
- Anthropic credit (separate billing issue)
- Minisforum outage (separate physical recovery)
- llama.cpp tensor-shape bug for the GGUF (still worth rebuilding llama.cpp later for non-tool workloads)

## Next session resume point

If anything in this runbook is unclear or needs updating, the file lives at `/Users/oluwajobamalomo/phase1b_runbook.md` and is referenced from `MEMORY.md` via `project_nemotron_super_phase1.md`.
