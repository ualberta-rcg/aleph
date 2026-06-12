import httpx, json, sys

G = "http://localhost:8080"
MODEL = "gemma-3-4b-it"
results = []

def req(method, path, body=None, timeout=120, stream=False):
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

# 1. Basic chat
def t01():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "What is 2+2?"}], "max_tokens": 20, "temperature": 0})
    d = r.json(); msg = d["choices"][0]["message"]
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI basic chat", f"content={safe_content(msg)}")

# 2. Streaming chat
def t02():
    with req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "Count 1 to 3"}], "max_tokens": 30, "stream": True}, stream=True) as r:
        chunks = [l for l in r.iter_lines() if l.startswith("data:") and "DONE" not in l]
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI streaming", f"{len(chunks)} chunks")

# 3. Temperature=0 (deterministic)
def t03():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "What is the capital of France?"}], "max_tokens": 20, "temperature": 0})
    d = r.json(); msg = d["choices"][0]["message"]
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI temp=0", f"content={safe_content(msg)}")

# 4. Temperature=1.0 + top_k=64 (Gemma 3 recommended)
def t04():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "Say hello"}], "max_tokens": 20, "temperature": 1.0, "top_k": 64})
    d = r.json(); msg = d["choices"][0]["message"]
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI temp=1 top_k=64", f"content={safe_content(msg)}")

# 5. Top_p sampling
def t05():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "Say hello"}], "max_tokens": 20, "top_p": 0.95})
    d = r.json(); msg = d["choices"][0]["message"]
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI top_p=0.95", f"content={safe_content(msg)}")

# 6. Stop sequences
def t06():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "Count: 1, 2, 3, 4, 5, 6, 7"}], "max_tokens": 50, "stop": ["5"]})
    d = r.json(); msg = d["choices"][0]["message"]; finish = d["choices"][0].get("finish_reason")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI stop sequences", f"finish={finish} content={safe_content(msg)}")

# 7. System prompt
def t07():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "system", "content": "You are a pirate. Always speak like a pirate."}, {"role": "user", "content": "Hello!"}], "max_tokens": 30})
    d = r.json(); msg = d["choices"][0]["message"]
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI system prompt", f"content={safe_content(msg)}")

# 8. Vision (image URL — model supports vision via SigLIP)
def t08():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": [{"type": "text", "text": "What do you see in this image? Describe briefly."}, {"type": "image_url", "image_url": {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png"}}]}], "max_tokens": 50}, timeout=60)
    d = r.json(); msg = d["choices"][0]["message"]
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI vision", f"content={safe_content(msg)}")

# 9. Large max_tokens
def t09():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "Say hi"}], "max_tokens": 8192})
    d = r.json(); msg = d["choices"][0]["message"]
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI max_tokens=8k", f"content={safe_content(msg, 40)}")

# 10. Usage/token counts present
def t10():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10})
    d = r.json(); usage = d.get("usage", {})
    record("PASS" if usage.get("prompt_tokens") else "FAIL", r.status_code, "OAI usage tokens", f"prompt={usage.get('prompt_tokens')} completion={usage.get('completion_tokens')} total={usage.get('total_tokens')}")

################################################################
# ANTHROPIC STYLE
################################################################

# 11. Basic Anthropic message
def t11():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 30, "messages": [{"role": "user", "content": "What is 3+3? Just the number."}]})
    d = r.json(); content = d.get("content", [{}])[0].get("text", "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT basic message", f"type={d.get('type')} stop={d.get('stop_reason')} text={content[:60]}")

# 12. Anthropic streaming
def t12():
    with req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 30, "stream": True, "messages": [{"role": "user", "content": "Say hi"}]}, stream=True) as r:
        events = [l for l in r.iter_lines() if l.startswith("event:")]
        etypes = set(l.split(": ", 1)[1].strip() for l in events)
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT streaming", f"{len(events)} events types={etypes}")

# 13. Anthropic with system prompt
def t13():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 30, "system": "You are a pirate.", "messages": [{"role": "user", "content": "Hello!"}]})
    d = r.json(); content = d.get("content", [{}])[0].get("text", "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT system prompt", f"text={content[:60]}")

# 14. Anthropic with temperature
def t14():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 20, "temperature": 0, "messages": [{"role": "user", "content": "Capital of France?"}]})
    d = r.json(); content = d.get("content", [{}])[0].get("text", "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT temp=0", f"text={content[:60]}")

# 15. Anthropic with top_p + top_k
def t15():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 20, "top_p": 0.95, "top_k": 64, "messages": [{"role": "user", "content": "Say hi"}]})
    d = r.json(); content = d.get("content", [{}])[0].get("text", "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT top_p+top_k", f"text={content[:60]}")

# 16. Anthropic with stop_sequences
def t16():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 50, "stop_sequences": ["5"], "messages": [{"role": "user", "content": "Count: 1,2,3,4,5,6,7"}]})
    d = r.json(); stop = d.get("stop_sequence"); sr = d.get("stop_reason")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT stop_sequences", f"stop_reason={sr} stop_seq={stop}")

# 17. Anthropic max_tokens truncation
def t17():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 10, "messages": [{"role": "user", "content": "Tell me a long story"}]})
    d = r.json(); sr = d.get("stop_reason"); tokens = d.get("usage", {}).get("output_tokens")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT max_tokens=10", f"stop_reason={sr} output_tokens={tokens}")

################################################################
# GATEWAY GUARDRAILS
################################################################

# 18. Embed model via Anthropic (should reject)
def t18():
    r = req("GET", "/v1/models?all=true")
    embed = next((m["id"] for m in r.json().get("data", []) if m.get("type") == "embedding"), None)
    if not embed:
        record("SKIP", 0, "Guard: embed via ANT", "no embed model found"); return
    r2 = req("POST", "/v1/messages", {"model": embed, "max_tokens": 10, "messages": [{"role": "user", "content": "test"}]})
    record("EXP" if r2.status_code == 400 else "FAIL", r2.status_code, "Guard: embed via ANT", f"code={r2.json().get('error', {}).get('code', '')}")

# 19. Non-existent model
def t19():
    r = req("POST", "/v1/chat/completions", {"model": "fake-xyz", "messages": [{"role": "user", "content": "test"}]})
    record("EXP" if r.status_code == 404 else "FAIL", r.status_code, "Guard: bad model", r.json().get("error", "")[:60])

# 20. Model catalog capabilities
def t20():
    r = req("GET", "/v1/models")
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m:
        record("FAIL", 0, "Catalog entry", "not found"); return
    c = m.get("capabilities", {})
    ok = c.get("vision") and not c.get("tools") and not c.get("reasoning")
    record("PASS" if ok else "FAIL", r.status_code, "Catalog capabilities", f"vision={c.get('vision')} tools={c.get('tools')} reasoning={c.get('reasoning')} ctx={m.get('context_window')} max_out={m.get('max_completion_tokens')}")

################################################################
print("\n" + "=" * 60, flush=True)
print("Gemma-3-4B-IT Gateway Test", flush=True)
print("=" * 60 + "\n", flush=True)

for t in [t01, t02, t03, t04, t05, t06, t07, t08, t09, t10,
          t11, t12, t13, t14, t15, t16, t17,
          t18, t19, t20]:
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
