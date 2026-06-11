import httpx, json, sys

G = "http://localhost:8080"
results = []

def req(method, path, body=None, timeout=180, stream=False):
    if stream:
        return httpx.stream(method, f"{G}{path}", json=body, timeout=timeout)
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout)

def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)

def safe_content(msg, maxlen=80):
    c = msg.get("content")
    return (c[:maxlen] if c else "<null>") if c is not None else "<null>"

IMAGE_URL = "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png"

################################################################
# OPENAI STYLE
################################################################

# 1. Basic chat (with thinking on by default)
def t01():
    r = req("POST", "/v1/chat/completions", {"model":"qwen36-35b-a3b","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":200,"temperature":0.6})
    d = r.json(); msg = d["choices"][0]["message"]
    has_r = bool(msg.get("reasoning") or msg.get("reasoning_content"))
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "OAI basic chat", f"content={safe_content(msg)} reasoning={'yes' if has_r else 'no'}")

# 2. Streaming chat
def t02():
    with req("POST", "/v1/chat/completions", {"model":"qwen36-35b-a3b","messages":[{"role":"user","content":"Count 1 to 3"}],"max_tokens":100,"temperature":0.6,"stream":True}, stream=True) as r:
        chunks = [l for l in r.iter_lines() if l.startswith("data:") and "DONE" not in l]
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "OAI streaming", f"{len(chunks)} chunks")

# 3. Temperature=0
def t03():
    r = req("POST", "/v1/chat/completions", {"model":"qwen36-35b-a3b","messages":[{"role":"user","content":"Capital of France?"}],"max_tokens":100,"temperature":0})
    d = r.json(); msg = d["choices"][0]["message"]
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "OAI temp=0", f"content={safe_content(msg)}")

# 4. Temperature=0.6 + top_k=20 (thinking recommended)
def t04():
    r = req("POST", "/v1/chat/completions", {"model":"qwen36-35b-a3b","messages":[{"role":"user","content":"Say hello"}],"max_tokens":100,"temperature":0.6,"top_k":20})
    d = r.json(); msg = d["choices"][0]["message"]
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "OAI temp=0.6 top_k=20", f"content={safe_content(msg)}")

# 5. Top_p sampling
def t05():
    r = req("POST", "/v1/chat/completions", {"model":"qwen36-35b-a3b","messages":[{"role":"user","content":"Say hello"}],"max_tokens":100,"temperature":0.6,"top_p":0.95})
    d = r.json(); msg = d["choices"][0]["message"]
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "OAI top_p=0.95", f"content={safe_content(msg)}")

# 6. Stop sequences
def t06():
    r = req("POST", "/v1/chat/completions", {"model":"qwen36-35b-a3b","messages":[{"role":"user","content":"Count: 1, 2, 3, 4, 5, 6, 7"}],"max_tokens":200,"stop":["5"],"temperature":0.6})
    d = r.json(); msg = d["choices"][0]["message"]; finish = d["choices"][0].get("finish_reason")
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "OAI stop sequences", f"finish={finish} content={safe_content(msg)}")

# 7. System prompt
def t07():
    r = req("POST", "/v1/chat/completions", {"model":"qwen36-35b-a3b","messages":[{"role":"system","content":"You are a pirate. Always speak like a pirate."},{"role":"user","content":"Hello!"}],"max_tokens":100,"temperature":0.6})
    d = r.json(); msg = d["choices"][0]["message"]
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "OAI system prompt", f"content={safe_content(msg)}")

# 8. Tool calling (qwen3_coder parser)
def t08():
    r = req("POST", "/v1/chat/completions", {"model":"qwen36-35b-a3b","messages":[{"role":"user","content":"What is the weather in Edmonton?"}],"tools":[{"type":"function","function":{"name":"get_weather","description":"Get weather for a city","parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}}}],"max_tokens":200,"temperature":0.6})
    d = r.json(); msg = d["choices"][0]["message"]
    tc = msg.get("tool_calls",[])
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "OAI tool calling", f"tool_calls={len(tc)} fn={tc[0]['function']['name'] if tc else 'none'}")

# 9. Vision — image description
def t09():
    r = req("POST", "/v1/chat/completions", {"model":"qwen36-35b-a3b","messages":[{"role":"user","content":[{"type":"text","text":"Describe this image in one sentence."},{"type":"image_url","image_url":{"url": IMAGE_URL}}]}],"max_tokens":200,"temperature":0.6})
    d = r.json(); msg = d["choices"][0]["message"]
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "OAI vision image", f"content={safe_content(msg)}")

# 10. Large max_tokens
def t10():
    r = req("POST", "/v1/chat/completions", {"model":"qwen36-35b-a3b","messages":[{"role":"user","content":"Say hi"}],"max_tokens":32000,"temperature":0.6})
    d = r.json(); msg = d["choices"][0]["message"]
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "OAI max_tokens=32k", f"content={safe_content(msg,40)}")

# 11. Resources block
def t11():
    r = req("POST", "/v1/chat/completions", {"model":"qwen36-35b-a3b","messages":[{"role":"user","content":"hi"}],"max_tokens":10,"temperature":0.6})
    res = r.json().get("resources",{})
    record("PASS" if r.status_code==200 and "model" in res else "FAIL", r.status_code, "OAI resources block", f"keys={sorted(res.keys())}")

# 12. Reasoning content present (with explicit enable_thinking)
def t12():
    r = req("POST", "/v1/chat/completions", {"model":"qwen36-35b-a3b","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":300,"temperature":0.6,"chat_template_kwargs":{"enable_thinking":True}})
    d = r.json(); msg = d["choices"][0]["message"]
    has_r = bool(msg.get("reasoning") or msg.get("reasoning_content"))
    record("PASS" if r.status_code==200 and has_r else "FAIL", r.status_code, "OAI reasoning present", f"reasoning={'yes' if has_r else 'no'} content={safe_content(msg)}")

################################################################
# ANTHROPIC STYLE
################################################################

# 13. Basic Anthropic message
def t13():
    r = req("POST", "/v1/messages", {"model":"qwen36-35b-a3b","max_tokens":100,"temperature":0.6,"messages":[{"role":"user","content":"What is 3+3? Just the number."}]})
    d = r.json(); content = d.get("content",[{}])[0].get("text","")
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "ANT basic message", f"type={d.get('type')} stop={d.get('stop_reason')} text={content[:60]}")

# 14. Anthropic streaming
def t14():
    with req("POST", "/v1/messages", {"model":"qwen36-35b-a3b","max_tokens":100,"stream":True,"temperature":0.6,"messages":[{"role":"user","content":"Say hi"}]}, stream=True) as r:
        events = [l for l in r.iter_lines() if l.startswith("event:")]
        etypes = set(l.split(": ",1)[1].strip() for l in events)
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "ANT streaming", f"{len(events)} events types={etypes}")

# 15. Anthropic vision
def t15():
    r = req("POST", "/v1/messages", {"model":"qwen36-35b-a3b","max_tokens":200,"messages":[{"role":"user","content":[{"type":"image","source":{"type":"url","url": IMAGE_URL}},{"type":"text","text":"What do you see in this image? Be brief."}]}]})
    d = r.json()
    content = d.get("content",[{}])[0].get("text","")
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "ANT vision image", f"text={content[:80]}")

# 16. Anthropic with system prompt
def t16():
    r = req("POST", "/v1/messages", {"model":"qwen36-35b-a3b","max_tokens":100,"temperature":0.6,"system":"You are a pirate.","messages":[{"role":"user","content":"Hello!"}]})
    d = r.json(); content = d.get("content",[{}])[0].get("text","")
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "ANT system prompt", f"text={content[:60]}")

# 17. Anthropic with temperature
def t17():
    r = req("POST", "/v1/messages", {"model":"qwen36-35b-a3b","max_tokens":50,"temperature":0,"messages":[{"role":"user","content":"Capital of France?"}]})
    d = r.json(); content = d.get("content",[{}])[0].get("text","")
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "ANT temp=0", f"text={content[:60]}")

# 18. Anthropic with tools
def t18():
    r = req("POST", "/v1/messages", {"model":"qwen36-35b-a3b","max_tokens":200,"messages":[{"role":"user","content":"Weather in Edmonton?"}],"tools":[{"name":"get_weather","description":"Get weather","input_schema":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}}]})
    d = r.json(); blocks = d.get("content",[])
    tool_blocks = [b for b in blocks if b.get("type") == "tool_use"]
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "ANT tool calling", f"tool_use_blocks={len(tool_blocks)} total_blocks={len(blocks)}")

# 19. Anthropic max_tokens truncation
def t19():
    r = req("POST", "/v1/messages", {"model":"qwen36-35b-a3b","max_tokens":10,"messages":[{"role":"user","content":"Tell me a long story"}]})
    d = r.json(); sr = d.get("stop_reason"); tokens = d.get("usage",{}).get("output_tokens")
    record("PASS" if r.status_code==200 else "FAIL", r.status_code, "ANT max_tokens=10", f"stop_reason={sr} output_tokens={tokens}")

################################################################
# GATEWAY GUARDRAILS
################################################################

# 20. Embed model via Anthropic (should reject)
def t20():
    r = req("GET", "/v1/models?all=true")
    embed = next((m["id"] for m in r.json().get("data",[]) if m.get("type") == "embedding"), None)
    if not embed:
        record("SKIP", 0, "Guard: embed via ANT", "no embed model found"); return
    r2 = req("POST", "/v1/messages", {"model":embed,"max_tokens":10,"messages":[{"role":"user","content":"test"}]})
    record("EXP" if r2.status_code==400 else "FAIL", r2.status_code, "Guard: embed via ANT", f"code={r2.json().get('error',{}).get('code','')}")

# 21. Non-existent model
def t21():
    r = req("POST", "/v1/chat/completions", {"model":"fake-xyz","messages":[{"role":"user","content":"test"}]})
    record("EXP" if r.status_code==404 else "FAIL", r.status_code, "Guard: bad model", r.json().get("error","")[:60])

# 22. Model catalog capabilities (reasoning, tools, vision)
def t22():
    r = req("GET", "/v1/models")
    m = next((x for x in r.json().get("data",[]) if x["id"]=="qwen36-35b-a3b"), None)
    if not m:
        record("FAIL", 0, "Catalog entry", "not found"); return
    c = m.get("capabilities",{})
    ok = c.get("tools") and c.get("vision") and c.get("reasoning")
    record("PASS" if ok else "FAIL", r.status_code, "Catalog capabilities", f"vision={c.get('vision')} tools={c.get('tools')} reasoning={c.get('reasoning')} ctx={m.get('context_window')} max_out={m.get('max_completion_tokens')}")

# 23. Usage/token counts present
def t23():
    r = req("POST", "/v1/chat/completions", {"model":"qwen36-35b-a3b","messages":[{"role":"user","content":"hi"}],"max_tokens":10,"temperature":0.6})
    d = r.json(); usage = d.get("usage",{})
    record("PASS" if usage.get("prompt_tokens") else "FAIL", r.status_code, "OAI usage tokens", f"prompt={usage.get('prompt_tokens')} completion={usage.get('completion_tokens')} total={usage.get('total_tokens')}")

################################################################
print("\n" + "="*60, flush=True)
print("Qwen3.6-35B-A3B Comprehensive Gateway Test", flush=True)
print("="*60 + "\n", flush=True)

for t in [t01,t02,t03,t04,t05,t06,t07,t08,t09,t10,t11,t12,
          t13,t14,t15,t16,t17,t18,t19,
          t20,t21,t22,t23]:
    try:
        t()
    except Exception as e:
        record("ERR", 0, t.__name__, str(e)[:100])

p = sum(1 for r in results if r[0]=="PASS")
e = sum(1 for r in results if r[0]=="EXP")
f = sum(1 for r in results if r[0] in ("FAIL","ERR"))
s = sum(1 for r in results if r[0]=="SKIP")
print(f"\n{'='*60}", flush=True)
print(f"Results: {p} passed, {e} expected failures, {f} failed, {s} skipped", flush=True)
print(f"{'='*60}", flush=True)
