# llama.cpp Router Mode Test Kit

Source: YouTube V2t_YRsyqeI ("Llama.cpp Router Mode: Switch Models Instantly").

This kit extracts the demo into something we can run safely on the homelab's DGX Spark (ghana) without touching the existing vLLM or Ollama services.

## What it proves
One `llama-server` process can serve many GGUF models behind a single OpenAI-compatible endpoint. Clients pick a model by name in each request; the router loads it on demand and unloads idle ones.

## Why we care for NewFire
Today OpenClaw routes between Ollama (multiple resident models, each holding VRAM) and vLLM (one pinned model). Router mode collapses the Ollama side into a single endpoint with cleaner swap semantics. If the test passes, the production path is to wire OpenClaw at one new upstream and retire most of the Ollama containers.

## Files in this kit
| File | Purpose |
|---|---|
| `models.ini` | Model registry for the router. Three models picked for the test: gemma3-4b chat, qwen2.5-coder-7b coder, deepseek-r1-distill-8b reasoner. All pulled from Hugging Face on first load. |
| `setup-router-test.sh` | Verifies llama-server is recent, stops any prior test, launches router on 127.0.0.1:9094 inside a screen session. Loopback-only. |
| `smoke-test.sh` | Hits `/v1/chat/completions` against each model twice, prints wall time per call so we can see the unload+reload cost honestly. |
| `teardown.sh` | Stops the screen session, confirms the port is free, leaves the log for review. |

## Deploy (recommended path, runs on ghana)

From your Mac:

```bash
cd /Users/oluwajobamalomo/Desktop/llamacpp_router_test
scp models.ini setup-router-test.sh smoke-test.sh teardown.sh newwave-dgx@ghana:/tmp/
ssh newwave-dgx@ghana 'chmod +x /tmp/setup-router-test.sh /tmp/smoke-test.sh /tmp/teardown.sh && bash /tmp/setup-router-test.sh'
```

If setup exits with code 2, the existing llama-server is too old. The script prints the rebuild commands inline. The Phase 1 Nemotron memory already flagged this rebuild as needed, so this is a good moment to do it.

After setup succeeds:

```bash
ssh newwave-dgx@ghana 'bash /tmp/smoke-test.sh'
```

When done:

```bash
ssh newwave-dgx@ghana 'bash /tmp/teardown.sh'
```

## Security notes (per homelab posture)
- Port 9094 is bound to `127.0.0.1` only. No LAN, no Tailscale, no public. To reach it from Minisforum during testing, use an SSH port forward: `ssh -L 9094:127.0.0.1:9094 newwave-dgx@ghana`.
- No auth on the router itself, so loopback binding is the only gate during the test. Do not change `BIND=` to `0.0.0.0` without putting Cloudflare Access or a reverse proxy in front first.
- vLLM (port 8000) and Ollama (port 11434) are untouched. Only port 9094 is added.
- Model files are pulled from Hugging Face on first load and cached under `~/.cache/llama.cpp`. Bandwidth on first run is approximately 13 GB across the three models.

## Expected results
- Cold load (first hit on any model) on the DGX should land around 3 to 8 seconds.
- Same model re-hit while still resident: hundreds of milliseconds plus generation time.
- Same model re-hit AFTER a different one was used: pays cold load again, since the default keeps only one model in memory per worker.
- If you raise `--models-max 3` on the launch line, all three can stay warm at once (about 13 GB VRAM total), but that competes with vLLM's qwen3-coder-30b footprint, so test that variant deliberately.

## Decision checkpoint after testing
1. Cold-load times acceptable for agent dispatch? If yes, the router is a candidate for the OpenClaw smart-routing layer.
2. Stability over 30 minutes of sustained switching? Watch `router.log` for crashes; the multi-process design should isolate them.
3. Memory headroom alongside vLLM? If contention is bad, the production fit is router for small models + vLLM kept for the 30b coder.

## Cleanup if we abandon the test
```bash
ssh newwave-dgx@ghana 'bash /tmp/teardown.sh && sudo rm -rf /opt/llamacpp-router'
```
