import httpx, json, sys

G = "http://localhost:8080"
MODEL = "glm-z1-rumination-32b"
results = []

def req(method, path, body=None, timeout=300, stream=False):
    if stream:
        return httpx.stream(method, f"{G}{path}", json=body, timeout=timeout)
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout)

def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)

def safe_content(msg, maxlen=80):
    c = msg.get("content")
    return (c[:maxlen] if c else "<null>") if c is not None else "<null>"

################################################################
# OPENAI STYLE
################################################################

# 1. Basic chat (thinking on by default)
def t01():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "What is 2+2? Answer with just the number."}], "max_tokens": 100, "temperature": 0.6})
    d = r.json(); msg = d["choices"][0]["message"]
    rc = bool(msg.get("reasoning_content"))
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI basic chat", f"content={safe_content(msg)} reasoning={'yes' if rc else 'no'}")

# 2. Streaming chat
def t02():
    with req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "Say hello"}], "max_tokens": 100, "stream": True}, stream=True) as r:
        chunks = [l for l in r.iter_lines() if l.startswith("data:") and "DONE" not in l]
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI streaming", f"{len(chunks)} chunks")

# 3. Thinking ON (default)
def t03():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "What is 15*17?"}], "max_tokens": 200, "thinking": True}, timeout=180)
    d = r.json(); msg = d["choices"][0]["message"]
    rc = msg.get("reasoning_content", "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI thinking ON", f"content={safe_content(msg)} reasoning={'yes' if rc else 'no'}")

# 4. Thinking OFF
def t04():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "Say hello"}], "max_tokens": 50, "thinking": False})
    d = r.json(); msg = d["choices"][0]["message"]
    rc = msg.get("reasoning_content", "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI thinking OFF", f"content={safe_content(msg)} reasoning={'yes' if rc else 'no'}")

# 5. Temperature=0 (no thinking)
def t05():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "Capital of France?"}], "max_tokens": 30, "temperature": 0, "thinking": False})
    d = r.json(); msg = d["choices"][0]["message"]
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI temp=0", f"content={safe_content(msg)}")

# 6. Stop sequences
def t06():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "Count: 1, 2, 3, 4, 5, 6, 7"}], "max_tokens": 50, "stop": ["5"], "thinking": False})
    d = r.json(); msg = d["choices"][0]["message"]; finish = d["choices"][0].get("finish_reason")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI stop sequences", f"finish={finish} content={safe_content(msg)}")

# 7. System prompt (ignored by rumination template — but should still return 200)
def t07():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "system", "content": "You are a helpful math tutor."}, {"role": "user", "content": "What is 3+4?"}], "max_tokens": 100, "thinking": False})
    d = r.json(); msg = d["choices"][0]["message"]
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI system prompt (ignored)", f"content={safe_content(msg)}")

# 8. No tools (custom tools ignored by rumination template)
def t08():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "What's the weather?"}], "max_tokens": 100, "tools": [{"type": "function", "function": {"name": "get_weather", "description": "Get current weather", "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}}}], "thinking": False})
    d = r.json(); msg = d["choices"][0]["message"]
    tc = msg.get("tool_calls", [])
    # Tools should be ignored — expect no tool calls, just text response
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI tools ignored", f"tool_calls={len(tc)} content={safe_content(msg)}")

# 9. Usage/token counts
def t09():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10, "thinking": False})
    d = r.json(); usage = d.get("usage", {})
    record("PASS" if usage.get("prompt_tokens") else "FAIL", r.status_code, "OAI usage tokens", f"prompt={usage.get('prompt_tokens')} completion={usage.get('completion_tokens')} total={usage.get('total_tokens')}")

################################################################
# ANTHROPIC STYLE
################################################################

# 10. Basic Anthropic message
def t10():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 50, "messages": [{"role": "user", "content": "What is 3+3? Just the number."}]})
    d = r.json(); content = d.get("content", [{}])[0].get("text", "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT basic message", f"type={d.get('type')} stop={d.get('stop_reason')} text={content[:60]}")

# 11. Anthropic streaming
def t11():
    with req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 50, "stream": True, "messages": [{"role": "user", "content": "Say hi"}]}, stream=True) as r:
        events = [l for l in r.iter_lines() if l.startswith("event:")]
        etypes = set(l.split(": ", 1)[1].strip() for l in events)
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT streaming", f"{len(events)} events types={etypes}")

# 12. Anthropic thinking disabled
def t12():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 30, "temperature": 0, "messages": [{"role": "user", "content": "Say hello"}], "thinking": {"type": "disabled"}})
    d = r.json(); content = d.get("content", [{}])[0].get("text", "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT thinking disabled", f"stop={d.get('stop_reason')} text={content[:60]}")

# 13. Anthropic with temperature
def t13():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 20, "temperature": 0, "messages": [{"role": "user", "content": "Capital of France?"}], "thinking": {"type": "disabled"}})
    d = r.json(); content = d.get("content", [{}])[0].get("text", "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT temp=0", f"text={content[:60]}")

# 14. Anthropic with stop_sequences
def t14():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 50, "stop_sequences": ["5"], "messages": [{"role": "user", "content": "Count: 1,2,3,4,5,6,7"}], "thinking": {"type": "disabled"}})
    d = r.json(); stop = d.get("stop_sequence"); sr = d.get("stop_reason")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT stop_sequences", f"stop_reason={sr} stop_seq={stop}")

# 15. Anthropic max_tokens truncation
def t15():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 10, "messages": [{"role": "user", "content": "Tell me a long story"}], "thinking": {"type": "disabled"}})
    d = r.json(); sr = d.get("stop_reason"); tokens = d.get("usage", {}).get("output_tokens")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT max_tokens=10", f"stop_reason={sr} output_tokens={tokens}")

# 16. Anthropic thinking enabled
def t16():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 200, "messages": [{"role": "user", "content": "What is 8*9?"}], "thinking": {"type": "enabled", "budget_tokens": 4096}}, timeout=180)
    d = r.json()
    content = d.get("content", [])
    has_thinking = any(b.get("type") == "thinking" for b in content)
    text = next((b.get("text", "")[:60] for b in content if b.get("type") == "text"), "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT thinking enabled", f"has_thinking={has_thinking} text={text}")

################################################################
# GATEWAY GUARDRAILS
################################################################

# 17. Embed model via Anthropic (should reject)
def t17():
    r = req("GET", "/v1/models?all=true")
    embed = next((m["id"] for m in r.json().get("data", []) if m.get("type") == "embedding"), None)
    if not embed:
        record("SKIP", 0, "Guard: embed via ANT", "no embed model found"); return
    r2 = req("POST", "/v1/messages", {"model": embed, "max_tokens": 10, "messages": [{"role": "user", "content": "test"}]})
    record("EXP" if r2.status_code == 400 else "FAIL", r2.status_code, "Guard: embed via ANT", f"code={r2.json().get('error', {}).get('code', '')}")

# 18. Model catalog capabilities
def t18():
    r = req("GET", "/v1/models")
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m:
        record("FAIL", 0, "Catalog entry", "not found"); return
    c = m.get("capabilities", {})
    ok = not c.get("vision") and not c.get("tools") and c.get("reasoning")
    record("PASS" if ok else "FAIL", r.status_code, "Catalog capabilities", f"vision={c.get('vision')} tools={c.get('tools')} reasoning={c.get('reasoning')} ctx={m.get('context_window')} max_out={m.get('max_completion_tokens')}")

################################################################
print("\n" + "=" * 60, flush=True)
print("GLM-Z1-Rumination-32B Gateway Test", flush=True)
print("=" * 60 + "\n", flush=True)

for t in [t01, t02, t03, t04, t05, t06, t07, t08, t09,
          t10, t11, t12, t13, t14, t15, t16,
          t17, t18]:
    try:
        t()
    except Exception as e:
        record("ERR", 0, t.__name__, str(e)[:100])

p = sum(1 for r in results if r[0] == "PASS")
e = sum(1 for r in results if r[0] == "EXP")
f = sum(1 for r in results if r[0] in ("FAIL", "ERR"))
s = sum(1 for r in results if r[0] == "SKIP")
print(f"\n{'=' * 60}", flush=True)
print(f"Results: {p} passed, {e} expected failures, {f} failed, {s} skipped", flush=True)
print(f"{'=' * 60}", flush=True)
