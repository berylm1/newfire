"""Document intake via vision model — turns a photo or scan into usable text.

This is what makes "handle it without being in the office" actually true for
paper intake: a client's photo of a document becomes the same kind of input
an agent already accepts as typed text. No separate OCR service, no cloud
vision API — this runs on the same self-hosted Ollama instance as everything
else, using a vision-capable model (qwen2.5vl, confirmed installed on the DGX).
"""

import base64
import json
import os
import urllib.request

DEFAULT_BASE_URL = "http://100.88.112.5:11434"
DEFAULT_VISION_MODEL = "qwen2.5vl:7b"

EXTRACTION_PROMPT = (
    "Extract all the text from this document image, preserving its structure "
    "(field names and their values, paragraph breaks). Output the text only — "
    "no commentary, no description of the image itself."
)


def extract_document_text(image_path: str) -> str:
    """Run a scanned/photographed document through the vision model and
    return the extracted text, ready to feed into a text-based agent the
    same way a typed email or pasted brief would be."""
    base_url = os.environ.get("OLLAMA_VISION_BASE_URL", DEFAULT_BASE_URL)
    model = os.environ.get("OLLAMA_VISION_MODEL", DEFAULT_VISION_MODEL)

    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("ascii")

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": EXTRACTION_PROMPT, "images": [image_b64]}
        ],
        "stream": False,
    }
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    return result["message"]["content"]
