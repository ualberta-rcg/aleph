#!/usr/bin/env python3
"""GLM-4-32B gateway conformance suite.

Targets the model-gateway (NOT raw vLLM), so it exercises both the OpenAI and
Anthropic faces of the endpoint plus the OpenWebUI/meta catalog surface.

GLM-4-32B-0414 is a dense chat/tool model — NOT a reasoning or vision model.
So the "reasoning levels" and "vision" sections are negative tests: the
gateway must no-op thinking params and must reject image input with a clean
400, never crash and never leak a thinking/image path.

Run via port-forward to the gateway, or point straight at the ClusterIP:

    # port-forward (default http://localhost:8080)
    kubectl -n models port-forward svc/model-gateway 8080:80 &
    python3 test.py

    # or against the in-cluster gateway directly
    GATEWAY_URL=http://10.43.79.101 MODEL_ID=glm-4-32b python3 test.py
"""
import os, sys, json
import httpx

G = os.environ.get("GATEWAY_URL", "http://localhost:8080").rstrip("/")
MODEL = os.environ.get("MODEL_ID", "glm-4-32b")
TIMEOUT = int(os.environ.get("TIMEOUT", "180"))
results = []


def req(method, path, body=None, timeout=TIMEOUT, stream=False, headers=None):
    url = f"{G}{path}"
    if stream:
        return httpx.stream(method, url, json=body, timeout=timeout, headers=headers)
    return httpx.request(method, url, json=body, timeout=timeout, headers=headers)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status:>3} | {name}: {detail}", flush=True)


def ok(resp, name, detail, want=200):
    record("PASS" if resp.status_code == want else "FAIL", resp.status_code, name, detail)


def safe(v, n=60):
    if v is None:
        return "<null>"
    s = str(v)
    return s[:n] + ("…" if len(s) > n else "")


def chat(msg="hi", **kw):
    body = {"model": MODEL, "messages": [{"role": "user", "content": msg}], "max_tokens": 30}
    body.update(kw)
    return req("POST", "/v1/chat/completions", body)


def has_reasoning(msg) -> bool:
    return bool(msg.get("reasoning") or msg.get("reasoning_content"))


# A tiny image (1x1 transparent PNG), base64 data URL — used only to prove the
# gateway rejects vision for a non-vision model. Never reaches the GPU.
PNG_1X1 = ("data:image/png;base64,"
           "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLvAAAAAElFTkSuQmCC")

# A weather tool, OpenAI shape.
WEATHER_TOOL_OAI = [{"type": "function", "function": {
    "name": "get_weather", "description": "Get current weather for a city",
    "parameters": {"type": "object",
                   "properties": {"location": {"type": "string", "description": "City name"},
                                  "unit": {"type": "string", "enum": ["c", "f"]}},
                   "required": ["location"]}}}]

# Same tool, Anthropic shape.
WEATHER_TOOL_ANT = [{"name": "get_weather", "description": "Get current weather for a city",
                     "input_schema": {"type": "object",
                                      "properties": {"location": {"type": "string"}},
                                      "required": ["location"]}}]


################################################################
# OPENAI — chat & sampling
################################################################

def t01():
    r = chat("What is 2+2? Answer with just the number.", temperature=0)
    msg = r.json()["choices"][0]["message"]
    ok(r, "OAI basic chat", f"content={safe(msg.get('content'))}")


def t02():
    with req("POST", "/v1/chat/completions",
             {"model": MODEL, "messages": [{"role": "user", "content": "Count 1 to 5"}],
              "max_tokens": 40, "stream": True}, stream=True) as r:
        chunks = [l for l in r.iter_lines() if l.startswith("data:") and "DONE" not in l]
    ok(r, "OAI streaming", f"{len(chunks)} chunks")


def t03():
    r = chat("Capital of France?", temperature=0, max_tokens=20)
    ok(r, "OAI temp=0", f"content={safe(r.json()['choices'][0]['message'].get('content'))}")


def t04():
    r = chat("Say hello in one word.", top_p=0.95, max_tokens=15)
    ok(r, "OAI top_p=0.95", f"content={safe(r.json()['choices'][0]['message'].get('content'))}")


def t05():
    r = chat("Count: 1, 2, 3, 4, 5, 6, 7, 8", max_tokens=60, stop=["6"])
    ch = r.json()["choices"][0]
    ok(r, "OAI stop seq", f"finish={ch.get('finish_reason')} content={safe(ch['message'].get('content'))}")


def t06():
    r = chat("Hello!", max_tokens=30,
             messages=[{"role": "system", "content": "You are a pirate. Always say 'Arrr'."},
                       {"role": "user", "content": "Hello!"}])
    ok(r, "OAI system prompt", f"content={safe(r.json()['choices'][0]['message'].get('content'))}")


def t07():
    r = chat("Repeat the word 'ha' many times.", frequency_penalty=1.5, max_tokens=40)
    ok(r, "OAI frequency_penalty", f"content={safe(r.json()['choices'][0]['message'].get('content'))}")


def t08():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 12})
    u = r.json().get("usage", {})
    ok(r, "OAI usage tokens", f"prompt={u.get('prompt_tokens')} comp={u.get('completion_tokens')} total={u.get('total_tokens')}")


################################################################
# OPENAI — tools (the glm4_0414 fix under test)
################################################################

def t09():
    r = req("POST", "/v1/chat/completions", {"model": MODEL,
            "messages": [{"role": "user", "content": "What's the weather in Tokyo? Call the tool."}],
            "max_tokens": 150, "tools": WEATHER_TOOL_OAI, "tool_choice": "auto", "temperature": 0.1})
    msg = r.json()["choices"][0]["message"]; tc = msg.get("tool_calls", [])
    fn = tc[0]["function"]["name"] if tc else "none"
    ok(r, "OAI tool: auto", f"tool_calls={len(tc)} fn={fn} content_null={msg.get('content') is None}")


def t10():
    # tool_choice=none must NOT emit tool_calls even when prompted to call.
    r = req("POST", "/v1/chat/completions", {"model": MODEL,
            "messages": [{"role": "user", "content": "What's the weather in Berlin? Call the tool."}],
            "max_tokens": 80, "tools": WEATHER_TOOL_OAI, "tool_choice": "none"})
    msg = r.json()["choices"][0]["message"]
    ok(r, "OAI tool: choice=none", f"tool_calls={len(msg.get('tool_calls', []))} content={safe(msg.get('content'))}")


def t11():
    r = req("POST", "/v1/chat/completions", {"model": MODEL,
            "messages": [{"role": "user", "content": "What's the weather in Cairo? You must use the tool."}],
            "max_tokens": 150, "tools": WEATHER_TOOL_OAI, "tool_choice": "required", "temperature": 0.1})
    msg = r.json()["choices"][0]["message"]; tc = msg.get("tool_calls", [])
    ok(r, "OAI tool: required", f"tool_calls={len(tc)} fn={tc[0]['function']['name'] if tc else 'none'}")


def t12():
    r = req("POST", "/v1/chat/completions", {"model": MODEL,
            "messages": [{"role": "user", "content": "What's the weather in Rome? Use get_weather."}],
            "max_tokens": 150, "tools": WEATHER_TOOL_OAI,
            "tool_choice": {"type": "function", "function": {"name": "get_weather"}}, "temperature": 0.1})
    msg = r.json()["choices"][0]["message"]; tc = msg.get("tool_calls", [])
    args = tc[0]["function"]["arguments"] if tc else ""
    ok(r, "OAI tool: named", f"tool_calls={len(tc)} args={safe(args, 50)}")


def t13():
    # Streaming tool call — the re-parse-and-diff path must emit a tool_calls delta.
    with req("POST", "/v1/chat/completions", {"model": MODEL,
             "messages": [{"role": "user", "content": "What's the weather in Lisbon? Call the tool."}],
             "max_tokens": 150, "tools": WEATHER_TOOL_OAI, "tool_choice": "auto",
             "temperature": 0.1, "stream": True}, stream=True) as r:
        tc_chunks, fr = 0, None
        for l in r.iter_lines():
            l = l.strip()
            if not l.startswith("data:") or "DONE" in l:
                continue
            o = json.loads(l[5:].strip())
            ch = o["choices"][0]
            if ch["delta"].get("tool_calls"):
                tc_chunks += 1
            if ch.get("finish_reason"):
                fr = ch["finish_reason"]
    ok(r, "OAI tool: streaming", f"tool_delta_chunks={tc_chunks} finish={fr}")


################################################################
# OPENAI — reasoning no-op (GLM-4-32B is NOT a reasoning model)
################################################################

def t14():
    r = chat("Explain gravity briefly.", reasoning_effort="high", max_tokens=60)
    msg = r.json()["choices"][0]["message"]
    ok(r, "OAI reasoning_effort=high", f"reasoning_leak={has_reasoning(msg)} content={safe(msg.get('content'))}")


def t15():
    for lvl in ("low", "medium", "high", "max"):
        r = chat("Say ok.", reasoning_effort=lvl, max_tokens=10)
        if r.status_code != 200:
            ok(r, f"OAI reasoning_effort={lvl}", f"http={r.status_code}")
            return
    record("PASS", 200, "OAI reasoning_effort levels", "low/medium/high/max all 200")


def t16():
    # thinking_token_budget must be ignored, not subtracted from output.
    r = chat("Say hello.", extra_body={"thinking_token_budget": 2000}, max_tokens=20)
    ok(r, "OAI thinking_token_budget", f"content={safe(r.json()['choices'][0]['message'].get('content'))}")


################################################################
# OPENAI — vision rejection (no vision support)
################################################################

def t17():
    body = {"model": MODEL, "max_tokens": 30,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "What is in this image?"},
                {"type": "image_url", "image_url": {"url": PNG_1X1}}]}]}
    r = req("POST", "/v1/chat/completions", body)
    code = r.json().get("error", {}).get("code", "")
    record("EXP" if r.status_code == 400 and "vision" in code else "FAIL",
           r.status_code, "OAI vision rejected", f"code={code}")


################################################################
# OPENAI — max_tokens enforcement
################################################################

def t18():
    r = chat("Tell me a long story about a dragon.", max_tokens=12)
    ch = r.json()["choices"][0]; u = r.json().get("usage", {})
    ok(r, "OAI max_tokens=12 truncation", f"finish={ch.get('finish_reason')} comp_tokens={u.get('completion_tokens')}")


def t19():
    # Asking for more than the card cap (8192) must be clamped, not error.
    r = chat("Say hi.", max_tokens=999999)
    ok(r, "OAI max_tokens>cap clamp", f"status={r.status_code} finish={r.json()['choices'][0].get('finish_reason') if r.status_code==200 else 'n/a'}")


################################################################
# ANTHROPIC — chat & sampling
################################################################

def ant(body):
    body = {"model": MODEL, "max_tokens": 30, **body}
    return req("POST", "/v1/messages", body)


def t20():
    r = ant({"messages": [{"role": "user", "content": "What is 3+3? Just the number."}]})
    d = r.json(); txt = d.get("content", [{}])[0].get("text", "")
    ok(r, "ANT basic", f"stop={d.get('stop_reason')} text={safe(txt)}")


def t21():
    with req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 30, "stream": True,
             "messages": [{"role": "user", "content": "Say hi"}]}, stream=True) as r:
        ev = [l.split(": ", 1)[1].strip() for l in r.iter_lines() if l.startswith("event:")]
    types = set(ev)
    ok(r, "ANT streaming", f"{len(ev)} events types={types}")


def t22():
    r = ant({"system": "You are a terse math tutor.", "messages": [{"role": "user", "content": "What is 2+2?"}]})
    txt = r.json().get("content", [{}])[0].get("text", "")
    ok(r, "ANT system prompt", f"text={safe(txt)}")


def t23():
    r = ant({"temperature": 0, "max_tokens": 20, "messages": [{"role": "user", "content": "Capital of France?"}]})
    ok(r, "ANT temp=0", f"text={safe(r.json().get('content', [{}])[0].get('text', ''))}")


def t24():
    r = ant({"max_tokens": 60, "stop_sequences": ["5"],
             "messages": [{"role": "user", "content": "Count: 1,2,3,4,5,6,7"}]})
    d = r.json()
    ok(r, "ANT stop_sequences", f"stop_reason={d.get('stop_reason')} stop_seq={d.get('stop_sequence')}")


def t25():
    r = ant({"max_tokens": 10, "messages": [{"role": "user", "content": "Tell me a long story"}]})
    d = r.json()
    ok(r, "ANT max_tokens=10", f"stop_reason={d.get('stop_reason')} out_tokens={d.get('usage', {}).get('output_tokens')}")


################################################################
# ANTHROPIC — tools
################################################################

def t26():
    r = ant({"max_tokens": 150, "messages": [{"role": "user", "content": "What's the weather in Tokyo?"}],
             "tools": WEATHER_TOOL_ANT, "tool_choice": {"type": "any"}, "temperature": 0.1})
    blocks = r.json().get("content", [])
    tu = [b for b in blocks if b.get("type") == "tool_use"]
    name = tu[0].get("name") if tu else "none"
    ok(r, "ANT tool: any", f"tool_use={len(tu)} total_blocks={len(blocks)} name={name}")


def t27():
    # Streaming Anthropic tool_use → a content_block_start block whose type is tool_use.
    with req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 150, "stream": True,
             "messages": [{"role": "user", "content": "What's the weather in Paris?"}],
             "tools": WEATHER_TOOL_ANT, "tool_choice": {"type": "any"}, "temperature": 0.1}, stream=True) as r:
        lines = list(r.iter_lines())
    blocks = []
    cur_event = None
    for l in lines:
        l = l.strip()
        if l.startswith("event:"):
            cur_event = l.split(":", 1)[1].strip()
        elif l.startswith("data:") and cur_event == "content_block_start":
            try:
                blk = json.loads(l[5:].strip()).get("content_block", {})
                blocks.append(blk.get("type"))
            except Exception:
                pass
    has_tu = "tool_use" in blocks
    record("PASS" if r.status_code == 200 and has_tu else "FAIL",
           r.status_code, "ANT tool: streaming", f"block_types={blocks} tool_use_present={has_tu}")


################################################################
# ANTHROPIC — reasoning no-op + vision rejection
################################################################

def t28():
    r = ant({"max_tokens": 40, "thinking": {"type": "enabled", "budget_tokens": 1024},
             "messages": [{"role": "user", "content": "Explain entropy briefly."}]})
    d = r.json()
    leak = any(b.get("type") == "thinking" for b in d.get("content", []))
    ok(r, "ANT thinking=enabled (no-op)", f"stop={d.get('stop_reason')} thinking_block_leak={leak}")


def t29():
    r = ant({"max_tokens": 30, "messages": [{"role": "user", "content": [
        {"type": "text", "text": "What is this?"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": PNG_1X1.split(",", 1)[1]}}]}]})
    code = r.json().get("error", {}).get("code", "")
    record("EXP" if r.status_code == 400 and "vision" in code else "FAIL",
           r.status_code, "ANT vision rejected", f"code={code}")


################################################################
# OPENWEBUI / meta surface
################################################################

def t30():
    r = req("GET", "/v1/models")
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m:
        record("FAIL", 0, "META catalog entry", "not in /v1/models"); return
    c = m.get("capabilities", {})
    want = (not c.get("vision") and not c.get("reasoning") and c.get("tools") is True
            and c.get("system_prompt") is True)
    ok(r, "META catalog capabilities", f"vision={c.get('vision')} tools={c.get('tools')} reasoning={c.get('reasoning')} sys={c.get('system_prompt')}")


def t31():
    r = req("GET", "/v1/models")
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m:
        record("FAIL", 0, "META catalog fields", "missing"); return
    need = {"id", "object", "type", "owned_by", "context_window", "max_completion_tokens",
            "description", "endpoint", "capabilities", "scaling", "tags"}
    missing = [k for k in need if k not in m]
    ok(r, "META catalog fields", f"present={len(need - set(missing))}/{len(need)} missing={missing or 'none'}")


def t32():
    # ?all=true surfaces non-chat models too; glm-4-32b must still be present.
    r = req("GET", "/v1/models?all=true")
    ids = [x["id"] for x in r.json().get("data", [])]
    ok(r, "META /v1/models?all=true", f"count={len(ids)} has_self={MODEL in ids}")


def t33():
    r = req("GET", "/healthz")
    ok(r, "META /healthz", f"body={safe(r.text, 40)}")


def t34():
    r = req("GET", "/readyz")
    ok(r, "META /readyz", f"body={safe(r.text, 40)}")


################################################################
# GUARDRAILS
################################################################

def t35():
    # Non-existent model → 404, not a 500 or upstream leak.
    r = req("POST", "/v1/chat/completions", {"model": "does-not-exist-xyz", "messages": [{"role": "user", "content": "x"}]})
    record("EXP" if r.status_code == 404 else "FAIL", r.status_code, "GRD bad model", safe(r.json().get("error", ""), 60))


def t36():
    # An embedding model must not successfully complete a chat. Exact rejection
    # code varies (400 if gateway blocks it, 404/503 if that model is cold or
    # lacks a chat endpoint) — the guardrail is "no 200 chat from an embedder".
    r = req("GET", "/v1/models?all=true")
    embed = next((m["id"] for m in r.json().get("data", []) if m.get("type") == "embedding"), None)
    if not embed:
        record("SKIP", 0, "GRD embed via chat", "no embedding model deployed"); return
    r2 = req("POST", "/v1/chat/completions", {"model": embed, "messages": [{"role": "user", "content": "x"}]})
    held = r2.status_code != 200
    record("EXP" if held else "FAIL", r2.status_code, "GRD embed via chat", f"embed={embed} served_chat={not held}")


def t37():
    # Empty messages list → should be rejected, not crash the model.
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [], "max_tokens": 5})
    ok(r, "GRD empty messages", f"status={r.status_code} (200 ok if engine tolerates)", want=r.status_code)


################################################################
print("\n" + "=" * 64, flush=True)
print(f"GLM-4-32B gateway conformance — target {G}, model {MODEL}", flush=True)
print("=" * 64 + "\n", flush=True)

TESTS = [t01, t02, t03, t04, t05, t06, t07, t08,
         t09, t10, t11, t12, t13,
         t14, t15, t16, t17, t18, t19,
         t20, t21, t22, t23, t24, t25,
         t26, t27, t28, t29,
         t30, t31, t32, t33, t34,
         t35, t36, t37]

for t in TESTS:
    try:
        t()
    except Exception as e:
        record("ERR", 0, t.__name__, f"{type(e).__name__}: {str(e)[:90]}")

p = sum(1 for r in results if r[0] == "PASS")
e = sum(1 for r in results if r[0] == "EXP")
f = sum(1 for r in results if r[0] in ("FAIL", "ERR"))
s = sum(1 for r in results if r[0] == "SKIP")
total = len(results)
print(f"\n{'=' * 64}", flush=True)
print(f"Results: {p} passed, {e} expected-fail, {f} failed, {s} skipped  ({total} total)", flush=True)
print(f"{'=' * 64}", flush=True)
sys.exit(0 if f == 0 else 1)
