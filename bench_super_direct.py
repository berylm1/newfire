import json, time, urllib.request, sys

URL = "http://localhost:30001/v1/chat/completions"

P = {
    "model": "nemotron-super-direct",
    "messages": [
        {"role": "user",
         "content": "Explain how a Mixture of Experts model routes tokens. Be precise. 200 words."}
    ],
    "max_tokens": 400,
    "temperature": 0,
    "stream": False,
}

req = urllib.request.Request(
    URL,
    data=json.dumps(P).encode(),
    headers={"Content-Type": "application/json"},
)

t0 = time.time()
try:
    body = json.loads(urllib.request.urlopen(req, timeout=900).read())
except Exception as exc:
    print("REQUEST FAILED:", exc)
    sys.exit(1)
t1 = time.time()

u = body.get("usage", {})
c = u.get("completion_tokens", 0)
p = u.get("prompt_tokens", 0)
el = t1 - t0
tps = c / el if el > 0 else 0

print(f"endpoint: {URL}")
print(f"elapsed_seconds: {el:.2f}")
print(f"prompt_tokens: {p}")
print(f"completion_tokens: {c}")
print(f"tokens_per_second: {tps:.2f}")

if "choices" in body:
    txt = body["choices"][0].get("message", {}).get("content", "")
    print(f"sample_output: {txt[:200]!r}")
else:
    print(f"raw_preview: {json.dumps(body)[:400]}")
