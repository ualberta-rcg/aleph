import urllib.request, json, time

def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"http://localhost:8080{path}", data=data, headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=120)
        return r.status, r.read().decode(), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), ""
    except Exception as e:
        return -1, str(e), ""

model = "geogalactica"
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
                snippet = choices[0].get("message", {}).get("content", "")[:80]
            elif isinstance(j.get("content"), list):
                for blk in j["content"]:
                    snippet = blk.get("text", "")[:80]
                    break
        except:
            snippet = body[:80]
    print(f"{sym} {name}: HTTP {code} | {snippet}")

# ===== OPENAI /v1/chat/completions =====
print("=== OpenAI /v1/chat/completions ===")
check("Basic chat", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "What is the Mohs hardness scale? Brief answer."}], "max_tokens": 80, "temperature": 0.1}))

check("System prompt", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "system", "content": "You are a geology expert."}, {"role": "user", "content": "What is granite?"}], "max_tokens": 80, "temperature": 0.7}))

check("High temperature", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "Describe a volcanic eruption"}], "max_tokens": 80, "temperature": 1.5}))

check("Low temperature", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "2+2? Just the number."}], "max_tokens": 20, "temperature": 0.0}))

check("Short max_tokens", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "Tell me about plate tectonics"}], "max_tokens": 10}))

# Streaming
print()
print("=== Streaming ===")
code, body, ct = post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "Say hi"}], "max_tokens": 20, "stream": True})
if code == 200:
    if "event-stream" in ct or body.startswith("data:"):
        P += 1
        print(f"{chr(9989)} Streaming SSE works")
    else:
        P += 1
        print(f"{chr(9989)} Streaming returned JSON (also fine)")
else:
    F += 1
    print(f"{chr(10060)} Streaming: HTTP {code}")

# Tools - should be rejected
print()
print("=== Tools (should be rejected) ===")
check("Tools rejected", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "Weather?"}], "tools": [{"type": "function", "function": {"name": "get_weather", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}}}}], "max_tokens": 50}), expect_ok=False)

# Vision - should be rejected
print()
print("=== Vision (should be rejected) ===")
check("Vision rejected", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": [{"type": "text", "text": "See?"}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}}]}], "max_tokens": 50}), expect_ok=False)

# Reasoning effort - should be ignored
print()
print("=== Reasoning effort (ignored) ===")
check("Reasoning effort", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "5+5=?"}], "max_tokens": 30, "reasoning_effort": "high"}))

# ===== ANTHROPIC /v1/messages =====
print()
print("=== Anthropic /v1/messages ===")
check("Anthropic basic", *post("/v1/messages", {"model": model, "messages": [{"role": "user", "content": "What is the Richter scale? Brief answer."}], "max_tokens": 60}))

check("Anthropic system", *post("/v1/messages", {"model": model, "messages": [{"role": "user", "content": "Hello"}], "system": "Be concise.", "max_tokens": 50}))

# Anthropic streaming
code, body, ct = post("/v1/messages", {"model": model, "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 30, "stream": True})
if code == 200:
    P += 1
    print(f"{chr(9989)} Anthropic streaming: HTTP {code}")
else:
    F += 1
    print(f"{chr(10060)} Anthropic streaming: HTTP {code}")

# Anthropic tools rejected
check("Anthropic tools rejected", *post("/v1/messages", {"model": model, "messages": [{"role": "user", "content": "Weather?"}], "tools": [{"name": "get_weather", "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}}}], "max_tokens": 50}), expect_ok=False)

# Anthropic vision rejected
vis_msg = {"model": model, "messages": [{"role": "user", "content": [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}}]}], "max_tokens": 50}
check("Anthropic vision rejected", *post("/v1/messages", vis_msg), expect_ok=False)

print()
print(f"=== RESULTS: {P} passed, {F} failed ===")
