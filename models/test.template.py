"""TEMPLATE — per-model gateway test battery (reference example).

Copy this to `models/<your-model>/test.py`, set MODEL, and KEEP THE SECTIONS THAT
APPLY to your model — delete the rest. This file deliberately pretends the model
supports *everything* (chat + vision + tools + reasoning + meta-tasks + the
Anthropic surface, plus an embeddings/rerank block at the bottom) so it works as
a menu you pick from, not an auto-detecting harness.

How to specialize:
  - Text-only chat model  → drop vision(), vision_multi_image().
  - No tool support       → drop tools_oai(), ant_tools() (or assert a clean 400).
  - Non-reasoning model   → drop the Thinking section + ant_think_*; keep think_off
                            only if you want to prove no reasoning leaks.
  - Embedding / rerank    → delete the chat battery and use the EMBEDDINGS block.
  - Update HARD / prompts / expected answers to suit the model.

Run externally via the gateway VIP + Tyk auth (preferred):
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> MODEL=<model-id> python3 models/<m>/test.py

Run inside the gateway pod (no auth needed):
  cat models/<m>/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, json, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
MODEL = os.environ.get("MODEL", "__MODEL_ID__")
# A reasoning prompt with a definite answer (sheep: 9 → ×7=63 → −4=59).
HARD = ("A farmer has 17 sheep. All but 9 die. How many sheep are left? "
        "Take that number, multiply by 7, then subtract 4. Show your reasoning.")
# 1x1 red PNG (base64) — the cluster can't fetch external URLs, so inline data.
RED_PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
results = []


def req(method, path, body=None, timeout=300, stream=False):
    if stream:
        return httpx.stream(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS)
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def _rc(msg):
    return msg.get("reasoning") or msg.get("reasoning_content") or ""


def oai(body):
    r = req("POST", "/v1/chat/completions", body)
    d = r.json()
    return r, d, d["choices"][0]["message"]


def safe(m, n=60):
    c = m.get("content") or ""
    return (c[:n] + "…") if len(c) > n else c


TOOLS = [{"type": "function", "function": {
    "name": "get_weather", "description": "Get weather for a city",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}},
                   "required": ["city"]}}}]
ANT_TOOLS = [{"name": "get_weather", "description": "Get weather",
              "input_schema": {"type": "object",
                               "properties": {"city": {"type": "string"}},
                               "required": ["city"]}}]


# ── 1. WAKE (retry through cold-start 503) + basic chat ───────────────────────
def wake():
    body = {"model": MODEL, "messages": [{"role": "user", "content": "Say hi"}],
            "reasoning_effort": "none", "max_tokens": 20, "temperature": 0}
    for attempt in range(72):
        r = req("POST", "/v1/chat/completions", body)
        if r.status_code == 200:
            m = r.json()["choices"][0]["message"]
            record("PASS", 200, "WAKE + OAI basic", f"attempts={attempt+1} content={safe(m,30)!r}")
            return
        if r.status_code == 503:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + OAI basic", f"unexpected status body={r.text[:80]}")
        return
    record("FAIL", 503, "WAKE + OAI basic", "timed out waiting for warm model")


# ── OpenAI feature battery ────────────────────────────────────────────────────
def stream():
    with req("POST", "/v1/chat/completions", {"model": MODEL,
             "messages": [{"role": "user", "content": "Count 1 to 3"}], "max_tokens": 30,
             "reasoning_effort": "none", "stream": True}, stream=True) as r:
        n = len([l for l in r.iter_lines() if l.startswith("data:") and "DONE" not in l])
    record("PASS" if r.status_code == 200 and n > 0 else "FAIL", r.status_code, "OAI streaming", f"{n} chunks")

def temp0():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Capital of France? One word."}],
                  "reasoning_effort": "none", "max_tokens": 20, "temperature": 0})
    ok = r.status_code == 200 and "paris" in (m.get("content") or "").lower()
    record("PASS" if ok else "FAIL", r.status_code, "OAI temp=0 + answer", safe(m))

def temp_topk():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Say hello"}],
                  "reasoning_effort": "none", "max_tokens": 20, "temperature": 1.0, "top_k": 64})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI temp+top_k", safe(m))

def top_p():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Say hello"}],
                  "reasoning_effort": "none", "max_tokens": 20, "top_p": 0.95})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI top_p", safe(m))

def stop_seq():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Continue this count: 1, 2, 3, 4,"}],
                  "reasoning_effort": "none", "max_tokens": 100, "stop": ["5"]})
    fin = d["choices"][0].get("finish_reason")
    ok = r.status_code == 200 and fin == "stop"
    record("PASS" if ok else "FAIL", r.status_code, "OAI stop sequences", f"finish={fin} {safe(m)}")

def system():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "system", "content": "You are a pirate. Speak like a pirate."},
                  {"role": "user", "content": "Hello!"}], "reasoning_effort": "none", "max_tokens": 30})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI system prompt", safe(m))

# DROP for models without tool support (or flip to assert a clean 400).
def tools_oai():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Weather in Edmonton?"}],
                  "reasoning_effort": "none", "max_tokens": 200, "tools": TOOLS})
    tc = m.get("tool_calls", [])
    name = tc[0]["function"]["name"] if tc else ""
    ok = r.status_code == 200 and tc and name == "get_weather"
    record("PASS" if ok else "FAIL", r.status_code, "OAI tools",
           f"tool_calls={len(tc)} name={name!r}")

# DROP for text-only models.
def vision():
    r, d, m = oai({"model": MODEL, "max_tokens": 60, "reasoning_effort": "none",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "What color is this image? One word."},
                {"type": "image_url", "image_url": {"url": RED_PNG}}]}]})
    ok = r.status_code == 200 and len(m.get("content") or "") > 0
    record("PASS" if ok else "FAIL", r.status_code, "OAI vision (image works)", safe(m, 40))

# DROP for text-only models.
def vision_multi_image():
    r, d, m = oai({"model": MODEL, "max_tokens": 40, "reasoning_effort": "none",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "How many images do you see? Just the number."},
                {"type": "image_url", "image_url": {"url": RED_PNG}},
                {"type": "image_url", "image_url": {"url": RED_PNG}}]}]})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI vision multi-image", safe(m, 40))

def max_tokens():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Say hi"}],
                  "reasoning_effort": "none", "max_tokens": 8192})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI max_tokens=8k", safe(m, 30))

def truncation():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Tell me a very long story."}],
                  "reasoning_effort": "none", "max_tokens": 5})
    fin = d["choices"][0].get("finish_reason"); ct = (d.get("usage") or {}).get("completion_tokens", 0)
    ok = r.status_code == 200 and fin == "length" and ct <= 8
    record("PASS" if ok else "FAIL", r.status_code, "OAI truncation max_tokens=5",
           f"finish={fin} completion_tokens={ct}")

def usage():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "hi"}],
                  "reasoning_effort": "none", "max_tokens": 10})
    u = d.get("usage", {})
    ok = u.get("prompt_tokens") and MODEL in (d.get("model") or "")
    record("PASS" if ok else "FAIL", r.status_code, "OAI usage + model echo",
           f"prompt={u.get('prompt_tokens')} completion={u.get('completion_tokens')} model={d.get('model')!r}")

def resources():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "hi"}],
                  "reasoning_effort": "none", "max_tokens": 10})
    res = d.get("resources", {})
    record("PASS" if r.status_code == 200 and "model" in res else "FAIL", r.status_code,
           "OAI resources block", f"keys={sorted(res.keys())}")

# ── Thinking (DROP this whole section for non-reasoning models) ────────────────
def think_on_medium():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": HARD}],
                  "reasoning_effort": "medium", "max_tokens": 4096, "temperature": 1.0, "top_p": 0.95})
    rc = _rc(m)
    record("PASS" if r.status_code == 200 and rc else "FAIL", r.status_code,
           "OAI think ON medium", f"rc_len={len(rc)} content_len={len(m.get('content') or '')}")

def think_on_high():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": HARD}],
                  "reasoning_effort": "high", "max_tokens": 4096, "temperature": 1.0, "top_p": 0.95})
    rc = _rc(m)
    record("PASS" if r.status_code == 200 and rc else "FAIL", r.status_code,
           "OAI think ON high", f"rc_len={len(rc)}")

# Keep this even for non-reasoning models if you want to prove no reasoning leaks.
def think_off():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Capital of France?"}],
                  "reasoning_effort": "none", "max_tokens": 8000, "temperature": 0})
    rc = _rc(m); ct = (d.get("usage") or {}).get("completion_tokens", 0)
    record("PASS" if r.status_code == 200 and not rc else "FAIL", r.status_code,
           "OAI think OFF", f"rc_len={len(rc)} {safe(m,30)!r} completion_tokens={ct}")

def think_budget():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": HARD}],
                  "thinking_token_budget": 2000, "max_tokens": 20000, "temperature": 1.0})
    rc = _rc(m); ct = (d.get("usage") or {}).get("completion_tokens", 0)
    record("PASS" if r.status_code == 200 and rc and ct <= 2600 else "FAIL", r.status_code,
           "OAI token-budget", f"rc_len={len(rc)} completion_tokens={ct} (budget 2000)")

def think_stream():
    rn = cn = 0
    with req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": HARD}],
             "reasoning_effort": "medium", "max_tokens": 4096, "temperature": 1.0, "top_p": 0.95,
             "stream": True, "stream_options": {"include_usage": True}}, stream=True) as r:
        for line in r.iter_lines():
            if not line.startswith("data:") or "[DONE]" in line:
                continue
            try: o = json.loads(line[5:].strip())
            except Exception: continue
            for ch in o.get("choices", []):
                dd = ch.get("delta", {})
                if dd.get("reasoning") or dd.get("reasoning_content"): rn += 1
                if dd.get("content"): cn += 1
    record("PASS" if r.status_code == 200 and rn > 0 else "FAIL", r.status_code,
           "OAI stream think ON", f"reasoning_deltas={rn} content_deltas={cn}")

# ── Meta-tasks (chat-UI title/tags/followups; must not leak reasoning) ─────────
def _meta(signal, name, cap):
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user",
                  "content": f"{signal} for: The quick brown fox jumps over the lazy dog."}],
                  "max_tokens": 512, "temperature": 0})
    rc = _rc(m); ct = (d.get("usage") or {}).get("completion_tokens", 0)
    ok = r.status_code == 200 and not rc and ct <= cap
    record("PASS" if ok else "FAIL", r.status_code, f"OAI meta {name}",
           f"rc_len={len(rc)} completion_tokens={ct} (cap {cap}) {safe(m,30)!r}")

def meta_title():   _meta("Generate a concise, 3-5 word title", "title", 80)
def meta_tags():    _meta("Generate 1-3 broad tags", "tags", 60)
def meta_followups(): _meta("Suggest 3-5 relevant follow-up questions", "followups", 220)

# ── Anthropic feature battery ─────────────────────────────────────────────────
def ant_basic():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 30, "temperature": 0,
            "thinking": {"type": "disabled"},
            "messages": [{"role": "user", "content": "What is 3+3? Just the number."}]})
    d = r.json(); t = next((b.get("text", "") for b in d.get("content", []) if b.get("type") == "text"), "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT basic", f"{t[:50]!r}")

def ant_stream():
    with req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 30, "stream": True,
             "thinking": {"type": "disabled"}, "messages": [{"role": "user", "content": "Say hi"}]},
             stream=True) as r:
        etypes = set(l.split(": ", 1)[1].strip() for l in r.iter_lines() if l.startswith("event:"))
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT streaming", f"types={etypes}")

def ant_system():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 30, "thinking": {"type": "disabled"},
            "system": "You are a pirate.", "messages": [{"role": "user", "content": "Hello!"}]})
    d = r.json(); t = next((b.get("text", "") for b in d.get("content", []) if b.get("type") == "text"), "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT system", f"{t[:50]!r}")

def ant_temp0():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 20, "temperature": 0,
            "thinking": {"type": "disabled"}, "messages": [{"role": "user", "content": "Capital of France?"}]})
    d = r.json(); t = next((b.get("text", "") for b in d.get("content", []) if b.get("type") == "text"), "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT temp=0", f"{t[:50]!r}")

def ant_topk():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 20, "top_p": 0.95, "top_k": 64,
            "thinking": {"type": "disabled"}, "messages": [{"role": "user", "content": "Say hi"}]})
    d = r.json(); t = next((b.get("text", "") for b in d.get("content", []) if b.get("type") == "text"), "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT top_p+top_k", f"{t[:50]!r}")

def ant_stop():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 50, "stop_sequences": ["5"],
            "thinking": {"type": "disabled"}, "messages": [{"role": "user", "content": "Count: 1,2,3,4,5,6,7"}]})
    d = r.json()
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT stop_sequences",
           f"stop_reason={d.get('stop_reason')} stop_seq={d.get('stop_sequence')}")

# DROP for models without tool support.
def ant_tools():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 200, "thinking": {"type": "disabled"},
            "messages": [{"role": "user", "content": "Weather in Edmonton?"}], "tools": ANT_TOOLS})
    d = r.json(); blocks = d.get("content", [])
    tub = [b for b in blocks if b.get("type") == "tool_use"]
    record("PASS" if r.status_code == 200 and tub else "FAIL", r.status_code, "ANT tools",
           f"tool_use_blocks={len(tub)}")

# DROP for non-reasoning models.
def ant_think_on():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 4096,
            "messages": [{"role": "user", "content": HARD}],
            "thinking": {"type": "enabled", "budget_tokens": 4096}})
    d = r.json(); blocks = d.get("content", [])
    has = any(b.get("type") == "thinking" for b in blocks)
    record("PASS" if r.status_code == 200 and has else "FAIL", r.status_code, "ANT think ON",
           f"has_thinking={has} types={[b.get('type') for b in blocks]}")

def ant_think_off():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 8000, "temperature": 0,
            "thinking": {"type": "disabled"}, "messages": [{"role": "user", "content": "Capital of France?"}]})
    d = r.json(); blocks = d.get("content", [])
    has = any(b.get("type") == "thinking" for b in blocks)
    record("PASS" if r.status_code == 200 and not has else "FAIL", r.status_code, "ANT think OFF",
           f"has_thinking={has} output_tokens={d.get('usage',{}).get('output_tokens')}")

# ── Guardrails / catalog ──────────────────────────────────────────────────────
def guard_badmodel():
    r = req("POST", "/v1/chat/completions", {"model": "fake-xyz",
            "messages": [{"role": "user", "content": "test"}]})
    record("EXP" if r.status_code == 404 else "FAIL", r.status_code, "Guard: bad model",
           str(r.json().get("error", ""))[:50])

def catalog():
    r = req("GET", "/v1/models")
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m:
        record("FAIL", 0, "Catalog entry", "not found"); return
    c = m.get("capabilities", {})
    # EDIT the expectation to match this model's real capabilities.
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "Catalog capabilities",
           f"vision={c.get('vision')} tools={c.get('tools')} reasoning={c.get('reasoning')} "
           f"ctx={m.get('context_window')} max_out={m.get('max_completion_tokens')}")

# ── EMBEDDINGS / RERANK (for type=embedding|rerank models) ─────────────────────
# Delete the chat battery above and run these instead for an embedder/reranker.
def embed_single():
    r = req("POST", "/v1/embeddings", {"model": MODEL, "input": "Hello world, a test sentence."})
    d = r.json(); dim = len(d["data"][0]["embedding"]) if r.status_code == 200 and d.get("data") else 0
    # EDIT: assert dim == the card's embedding_dimensions.
    record("PASS" if dim > 0 else "FAIL", r.status_code, "EMB single", f"dim={dim}")

def embed_batch():
    r = req("POST", "/v1/embeddings", {"model": MODEL, "input": ["one", "two", "three"]})
    d = r.json(); n = len(d.get("data", [])) if r.status_code == 200 else 0
    record("PASS" if n == 3 else "FAIL", r.status_code, "EMB batch", f"n={n}")

def embed_base64():
    r = req("POST", "/v1/embeddings", {"model": MODEL, "input": "test", "encoding_format": "base64"})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "EMB base64", "encoding_format=base64")

def rerank():
    r = req("POST", "/v1/rerank", {"model": MODEL, "query": "What is deep learning?",
            "documents": ["Deep learning uses neural networks.", "Bananas are yellow.",
                          "Many-layer neural nets power deep learning."]})
    d = r.json(); res = d.get("results") if r.status_code == 200 else None
    top = res[0]["index"] if res else None
    record("PASS" if res and top == 0 else "FAIL", r.status_code, "RERANK", f"n={len(res) if res else 0} top_idx={top}")

def guard_embed_via_chat():
    # An embed-only model must reject a chat request with 400.
    r = req("POST", "/v1/chat/completions", {"model": MODEL,
            "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5})
    record("EXP" if r.status_code == 400 else "FAIL", r.status_code, "Guard: chat to embedder",
           f"code={r.json().get('error',{}).get('code','')}")

# ── run ───────────────────────────────────────────────────────────────────────
# CHAT battery (default). For an embedder/reranker, replace this list with:
#   [wake_embed?, embed_single, embed_batch, embed_base64, rerank, guard_embed_via_chat, catalog]
CHAT_BATTERY = [
    wake, stream, temp0, temp_topk, top_p, stop_seq, system, tools_oai,
    vision, vision_multi_image, max_tokens, truncation, usage, resources,
    think_on_medium, think_on_high, think_off, think_budget, think_stream,
    meta_title, meta_tags, meta_followups,
    ant_basic, ant_stream, ant_system, ant_temp0, ant_topk, ant_stop, ant_tools,
    ant_think_on, ant_think_off, guard_badmodel, catalog,
]

if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} gateway test", flush=True)
    print("=" * 66, flush=True)
    for t in CHAT_BATTERY:
        try:
            t()
        except Exception as e:
            record("ERR", 0, t.__name__, str(e)[:120])

    p = sum(1 for x in results if x[0] == "PASS")
    e = sum(1 for x in results if x[0] == "EXP")
    f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
    s = sum(1 for x in results if x[0] == "SKIP")
    print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(results)}",
          flush=True)
