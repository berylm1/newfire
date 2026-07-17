"""
NSS auto-router for LiteLLM.

Intercepts requests addressed to model 'nss-auto' and rewrites them to either
'nss-flash' (Qwen3.5-35B-A3B-NVFP4) or 'nss-nano-omni' (Nemotron-3-Nano-Omni
Reasoning NVFP4) based on whether the user's last message looks reasoning-heavy.

Activated via litellm-config.yaml:
  litellm_settings:
    callbacks: ["nss_auto_router.NssAutoRouter"]

The file must be mounted into the litellm container at a path on PYTHONPATH.
"""
from typing import Any, Optional
from litellm.integrations.custom_logger import CustomLogger


REASONING_KEYWORDS = frozenset({
    'reason', 'reasoning', 'think through', 'think step', 'thinking',
    'analyze', 'analysis', 'analyse',
    'explain', 'explanation', 'why does', 'why is', 'why are',
    'how does', 'how do', 'how would', 'how could',
    'step by step', 'step-by-step', 'walk through', 'walk me through',
    'break down', 'break it down', 'in detail',
    'derive', 'prove', 'show that', 'demonstrate',
    'complex', 'detailed', 'thorough', 'deep dive',
    'compare and contrast', 'pros and cons', 'tradeoff', 'trade-off',
    'design', 'architect', 'plan',
    'strategy', 'strategic',
})


class NssAutoRouter(CustomLogger):
    """Rewrites model='nss-auto' to nss-nano-omni (reasoning) or nss-flash (default)."""

    def _classify(self, messages: list) -> str:
        last_user = ""
        for m in reversed(messages or []):
            if m.get("role") == "user":
                content = m.get("content", "")
                if isinstance(content, list):
                    content = " ".join(
                        p.get("text", "") for p in content if isinstance(p, dict)
                    )
                last_user = str(content).lower()
                break

        if any(kw in last_user for kw in REASONING_KEYWORDS):
            return "nss-nano-omni"

        if len(last_user) > 600:
            return "nss-nano-omni"

        return "nss-flash"

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict,
        call_type: str,
    ) -> Optional[dict]:
        if data.get("model") != "nss-auto":
            return data
        target = self._classify(data.get("messages", []))
        data["model"] = target
        try:
            print(f"[nss-auto-router] route -> {target}", flush=True)
        except Exception:
            pass
        return data
