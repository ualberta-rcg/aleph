import urllib.request, json, time, os

# Gateway base URL + optional Tyk auth. In-pod default is localhost:8080 (no auth).
# Externally: GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/deepseek-v2-lite-16b/test.py
G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")

def post(path, body):
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if _KEY:
        headers["Authorization"] = f"Bearer {_KEY}"
    req = urllib.request.Request(f"{G}{path}", data=data, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=120)
        return r.status, r.read().decode(), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), ""
    except Exception as e:
        return -1, str(e), ""

model = "deepseek-v2-lite-16b"
P = 0
F = 0

def check(name, code, body, ct="", expect_ok=True):
    global P, F
    ok = (code == 200) if expect_ok else (code != 200)
    sym = chr(9989) if ok else chr(10060)
    if ok: P += 1
    else: F += 1
    snippet = ""
    if code == 200 and body:
        try:
            j = json.loads(body)
            choices = j.get("choices", [])
            if choices:
                snippet = choices[0].get("message", {}).get("content", "")[:60]
            elif isinstance(j.get("content"), list):
                for blk in j["content"]:
                    snippet = blk.get("text", "")[:60]
                    break
        except:
            snippet = body[:60]
    print(f"{sym} {name}: HTTP {code} | {snippet}")

# ===== OPENAI /v1/chat/completions =====
print("=== OpenAI /v1/chat/completions ===")
check("Basic chat", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "What is 2+2? Just the number."}], "max_tokens": 50, "temperature": 0.1}))
check("System prompt", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "system", "content": "You are a pirate."}, {"role": "user", "content": "Hello"}], "max_tokens": 80}))
check("High temperature", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "Tell a joke"}], "max_tokens": 80, "temperature": 1.5}))
check("Low temperature", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "Capital of France?"}], "max_tokens": 50, "temperature": 0.0}))
check("Short max_tokens", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "About computers"}], "max_tokens": 10}))

# Streaming
print()
print("=== Streaming ===")
code, body, ct = post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "Say hi"}], "max_tokens": 20, "stream": True})
if code == 200:
    P += 1
    print(f"{chr(9989)} Streaming: HTTP 200")
else:
    F += 1
    print(f"{chr(10060)} Streaming: HTTP {code}")

# Tools rejected
print()
print("=== Tools rejected ===")
check("Tools rejected", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "Weather?"}], "tools": [{"type": "function", "function": {"name": "get_weather", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}}}}], "max_tokens": 50}), expect_ok=False)

# Vision rejected
print()
print("=== Vision rejected ===")
check("Vision rejected", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": [{"type": "text", "text": "See?"}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}}]}], "max_tokens": 50}), expect_ok=False)

# Reasoning effort ignored
print()
print("=== Reasoning effort (ignored) ===")
check("Reasoning effort", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "5+5=?"}], "max_tokens": 30, "reasoning_effort": "high"}))

# ===== ANTHROPIC /v1/messages =====
print()
print("=== Anthropic /v1/messages ===")
check("Anthropic basic", *post("/v1/messages", {"model": model, "messages": [{"role": "user", "content": "3+3=? Just number."}], "max_tokens": 50}))
check("Anthropic system", *post("/v1/messages", {"model": model, "messages": [{"role": "user", "content": "Hello"}], "system": "Be concise.", "max_tokens": 50}))

code, body, ct = post("/v1/messages", {"model": model, "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 30, "stream": True})
if code == 200:
    P += 1
    print(f"{chr(9989)} Anthropic streaming: HTTP 200")
else:
    F += 1
    print(f"{chr(10060)} Anthropic streaming: HTTP {code}")

check("Anthropic tools rejected", *post("/v1/messages", {"model": model, "messages": [{"role": "user", "content": "Weather?"}], "tools": [{"name": "get_weather", "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}}}], "max_tokens": 50}), expect_ok=False)

vis_msg = {"model": model, "messages": [{"role": "user", "content": [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}}]}], "max_tokens": 50}
check("Anthropic vision rejected", *post("/v1/messages", vis_msg), expect_ok=False)

print()
print(f"=== RESULTS: {P} passed, {F} failed ===")
