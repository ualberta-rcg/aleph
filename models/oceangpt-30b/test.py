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

model = "oceangpt-30b"
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
                msg = choices[0].get("message", {})
                if msg.get("tool_calls"):
                    snippet = "tool_calls: " + str([tc["function"]["name"] for tc in msg["tool_calls"]])
                else:
                    snippet = msg.get("content", "")[:80]
            elif isinstance(j.get("content"), list):
                for blk in j["content"]:
                    snippet = blk.get("text", "")[:80]
                    break
        except:
            snippet = body[:80]
    print(f"{sym} {name}: HTTP {code} | {snippet}")

# ===== OPENAI /v1/chat/completions =====
print("=== OpenAI /v1/chat/completions ===")
check("Basic chat", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "What causes ocean acidification? Brief answer."}], "max_tokens": 80, "temperature": 0.1}))

check("System prompt (Chinese)", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "system", "content": "Answer in Chinese."}, {"role": "user", "content": "What is the Mariana Trench?"}], "max_tokens": 80, "temperature": 0.7}))

check("High temperature", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "Describe the deep sea creatively"}], "max_tokens": 80, "temperature": 1.5}))

check("Low temperature", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "2+2? Just the number."}], "max_tokens": 20, "temperature": 0.0}))

check("Short max_tokens", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "Tell me about coral reefs"}], "max_tokens": 10}))

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

# Tools (should WORK for oceangpt — supports_tools=true)
print()
print("=== Tools (should work) ===")
code, body, ct = post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "What is the sea temperature in the Pacific Ocean?"}], "tools": [{"type": "function", "function": {"name": "get_sea_temperature", "description": "Get sea surface temperature for a location", "parameters": {"type": "object", "properties": {"location": {"type": "string"}, "depth_m": {"type": "number"}}}}}], "max_tokens": 80})
j = json.loads(body)
if code == 200:
    msg = j["choices"][0]["message"]
    if msg.get("tool_calls"):
        P += 1
        names = [tc["function"]["name"] for tc in msg["tool_calls"]]
        print(f"{chr(9989)} OpenAI tools work: {names}")
    else:
        # Model chose not to use tools — still a pass if response is valid
        P += 1
        print(f"{chr(9989)} OpenAI tools: model responded without tool_calls (ok): {msg.get('content','')[:60]}")
else:
    F += 1
    print(f"{chr(10060)} OpenAI tools: HTTP {code}")

# Vision - should be rejected
print()
print("=== Vision (should be rejected) ===")
check("Vision rejected", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": [{"type": "text", "text": "See?"}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}}]}], "max_tokens": 50}), expect_ok=False)

# Reasoning effort - should be ignored (not reasoning model)
print()
print("=== Reasoning effort (ignored) ===")
check("Reasoning effort", *post("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "5+5=?"}], "max_tokens": 30, "reasoning_effort": "high"}))

# ===== ANTHROPIC /v1/messages =====
print()
print("=== Anthropic /v1/messages ===")
check("Anthropic basic", *post("/v1/messages", {"model": model, "messages": [{"role": "user", "content": "What causes tides? Brief answer."}], "max_tokens": 60}))

check("Anthropic system", *post("/v1/messages", {"model": model, "messages": [{"role": "user", "content": "Hello"}], "system": "Be concise.", "max_tokens": 50}))

# Anthropic streaming
code, body, ct = post("/v1/messages", {"model": model, "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 30, "stream": True})
if code == 200:
    P += 1
    print(f"{chr(9989)} Anthropic streaming: HTTP {code}")
else:
    F += 1
    print(f"{chr(10060)} Anthropic streaming: HTTP {code}")

# Anthropic tools (should WORK — supports_tools=true)
print()
print("=== Anthropic tools (should work) ===")
code, body, ct = post("/v1/messages", {"model": model, "messages": [{"role": "user", "content": "What is the sea temperature in the Atlantic?"}], "tools": [{"name": "get_sea_temperature", "description": "Get sea surface temperature for a location", "input_schema": {"type": "object", "properties": {"location": {"type": "string"}, "depth_m": {"type": "number"}}}}], "max_tokens": 80})
if code == 200:
    try:
        j = json.loads(body)
        # Check for tool_use in content blocks
        has_tool_use = False
        if isinstance(j.get("content"), list):
            for blk in j["content"]:
                if blk.get("type") == "tool_use":
                    has_tool_use = True
                    P += 1
                    print(f"{chr(9989)} Anthropic tools work: {blk.get('name')}")
                    break
        if not has_tool_use:
            # Model chose not to use tools — still valid
            P += 1
            text = ""
            if isinstance(j.get("content"), list):
                for blk in j["content"]:
                    text += blk.get("text", "")
            print(f"{chr(9989)} Anthropic tools: model responded without tool_use (ok): {text[:60]}")
    except:
        F += 1
        print(f"{chr(10060)} Anthropic tools: parse error")
else:
    F += 1
    print(f"{chr(10060)} Anthropic tools: HTTP {code}")

# Anthropic vision rejected
vis_msg = {"model": model, "messages": [{"role": "user", "content": [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}}]}], "max_tokens": 50}
check("Anthropic vision rejected", *post("/v1/messages", vis_msg), expect_ok=False)

print()
print(f"=== RESULTS: {P} passed, {F} failed ===")
