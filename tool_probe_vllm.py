import json, urllib.request, sys

URL = "http://127.0.0.1:30002/v1/chat/completions"

payload = {
    "model": "nemotron-super-vllm",
    "messages": [
        {"role": "user",
         "content": "What is the weather in Tokyo? Use the get_weather tool."}
    ],
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a city.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "City name"}
                    },
                    "required": ["city"],
                },
            },
        }
    ],
    "tool_choice": "auto",
    "max_tokens": 200,
    "temperature": 0,
    "stream": False,
}

req = urllib.request.Request(
    URL,
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)

try:
    body = json.loads(urllib.request.urlopen(req, timeout=300).read())
except Exception as exc:
    print("REQUEST FAILED:", exc)
    sys.exit(1)

choice = body.get("choices", [{}])[0]
msg = choice.get("message", {})
finish = choice.get("finish_reason")
content = msg.get("content", "")
tool_calls = msg.get("tool_calls")

print("=== finish_reason ===")
print(finish)
print()
print("=== message.content ===")
print(repr((content or "")[:500]))
print()
print("=== message.tool_calls ===")
if tool_calls:
    print(json.dumps(tool_calls, indent=2))
    print()
    print("VERDICT: vLLM emitted OpenAI-format tool_calls via qwen3_coder parser.")
    print("OpenHands-compatible. Safe to wire into LiteLLM.")
else:
    print("NONE")
    print()
    print("VERDICT: no tool_calls field. Either the qwen3_coder parser is not")
    print("recognizing the model's output, or the model did not emit a tool call.")
    print("Inspect content[] for embedded JSON or qwen3-style markup.")
    print("Check vLLM container logs for parser warnings:")
    print("  docker logs vllm-super-nvfp4 2>&1 | grep -i 'parser\\|tool' | tail -20")
