import json, urllib.request, sys

URL = "http://localhost:30001/v1/chat/completions"

payload = {
    "model": "nemotron-super-direct",
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
print("=== message.content (should be empty or short if tool_calls populated) ===")
print(repr(content[:500]))
print()
print("=== message.tool_calls ===")
if tool_calls:
    print(json.dumps(tool_calls, indent=2))
    print()
    print("VERDICT: model emitted OpenAI-format tool_calls. OpenHands-compatible.")
else:
    print("NONE")
    print()
    print("VERDICT: model did NOT emit tool_calls field.")
    print("Check if content contains a tool-call-like JSON or Qwen3-Coder-style markup.")
    print("Will likely need a chat-template patch or a switch to vLLM for tool-call support.")
