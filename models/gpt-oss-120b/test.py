"""gpt-oss-120b thinking verification (run inside the gateway pod).

vLLM v0.20.2 emits reasoning in the `reasoning` field (NOT reasoning_content).
This barrage asserts the gateway's managed-thinking contract for the model:
  ON  (effort low/med/high, or a caller token budget) -> reasoning surfaces:
        OpenAI `reasoning` field / Anthropic `thinking` block.
  OFF (effort none / thinking disabled) -> NO reasoning anywhere, tokens capped.

Run:  cat models/gpt-oss-120b/test.py | \
      kubectl exec -i -n models deploy/model-gateway -- python3 -
"""
import httpx, json, os

G = "http://localhost:8080"
MODEL = os.environ.get("MODEL", "gpt-oss-120b")
HARD = ("A farmer has 17 sheep. All but 9 die. How many sheep are left? "
        "Take that number, multiply by 7, then subtract 4. Show your reasoning.")
results = []


def req(method, path, body=None, timeout=300, stream=False):
    if stream:
        return httpx.stream(method, f"{G}{path}", json=body, timeout=timeout)
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def _rc(msg):
    """Reasoning text regardless of vLLM field naming."""
    return msg.get("reasoning") or msg.get("reasoning_content") or ""


def oai(body):
    r = req("POST", "/v1/chat/completions", body)
    d = r.json()
    return r, d, d["choices"][0]["message"]


# ── OpenAI: thinking ON (effort) ──────────────────────────────────────────────
def on_medium():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": HARD}],
                  "reasoning_effort": "medium", "max_tokens": 16000, "temperature": 0})
    rc = _rc(m)
    ok = r.status_code == 200 and len(rc) > 0
    record("PASS" if ok else "FAIL", r.status_code, "OAI ON medium: reasoning present",
           f"rc_len={len(rc)} content_len={len(m.get('content') or '')}")


def on_high():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": HARD}],
                  "reasoning_effort": "high", "max_tokens": 16000, "temperature": 0})
    rc = _rc(m)
    ok = r.status_code == 200 and len(rc) > 0
    record("PASS" if ok else "FAIL", r.status_code, "OAI ON high: reasoning present",
           f"rc_len={len(rc)}")


# ── OpenAI: thinking OFF -> no reasoning anywhere ─────────────────────────────
def off():
    r, d, m = oai({"model": MODEL,
                   "messages": [{"role": "user", "content": "What is the capital of France?"}],
                   "reasoning_effort": "none", "max_tokens": 8000, "temperature": 0})
    rc = _rc(m)
    ct = (d.get("usage") or {}).get("completion_tokens", 0)
    ok = r.status_code == 200 and len(rc) == 0
    record("PASS" if ok else "FAIL", r.status_code, "OAI OFF: no reasoning",
           f"rc_len={len(rc)} content={(m.get('content') or '')[:40]!r} completion_tokens={ct}")


# ── OpenAI: fake token budget (effort model has no native budget) ─────────────
def budget():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": HARD}],
                  "thinking_token_budget": 2000, "max_tokens": 20000, "temperature": 0})
    rc = _rc(m)
    ct = (d.get("usage") or {}).get("completion_tokens", 0)
    # reasoning present AND total completion capped near budget + reserve (2512)
    ok = r.status_code == 200 and len(rc) > 0 and ct <= 2600
    record("PASS" if ok else "FAIL", r.status_code, "OAI fake token-budget",
           f"rc_len={len(rc)} completion_tokens={ct} (budget 2000)")


# ── OpenAI streaming ON: reasoning deltas ship to the client ──────────────────
def stream_on():
    rn = cn = 0
    with req("POST", "/v1/chat/completions",
             {"model": MODEL, "messages": [{"role": "user", "content": HARD}],
              "reasoning_effort": "medium", "max_tokens": 8000, "temperature": 0,
              "stream": True, "stream_options": {"include_usage": True}}, stream=True) as r:
        for line in r.iter_lines():
            if not line.startswith("data:") or "[DONE]" in line:
                continue
            try:
                o = json.loads(line[5:].strip())
            except Exception:
                continue
            for ch in o.get("choices", []):
                dd = ch.get("delta", {})
                if dd.get("reasoning") or dd.get("reasoning_content"):
                    rn += 1
                if dd.get("content"):
                    cn += 1
    ok = r.status_code == 200 and rn > 0
    record("PASS" if ok else "FAIL", r.status_code, "OAI stream ON: reasoning deltas",
           f"reasoning_deltas={rn} content_deltas={cn}")


# ── OpenAI basics ─────────────────────────────────────────────────────────────
def basic():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Say hi"}],
                  "reasoning_effort": "none", "max_tokens": 20, "temperature": 0})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI basic",
           (m.get("content") or "")[:40])


def tools():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Weather in Tokyo?"}],
                  "reasoning_effort": "none", "max_tokens": 300,
                  "tools": [{"type": "function", "function": {
                      "name": "get_weather", "description": "x",
                      "parameters": {"type": "object",
                                     "properties": {"location": {"type": "string"}},
                                     "required": ["location"]}}}]})
    tc = m.get("tool_calls", [])
    record("PASS" if r.status_code == 200 and tc else "FAIL", r.status_code, "OAI tools",
           f"tool_calls={len(tc)}")


# ── Anthropic: thinking ON -> thinking block ──────────────────────────────────
def ant_on():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 16000,
            "messages": [{"role": "user", "content": HARD}],
            "thinking": {"type": "enabled", "budget_tokens": 8000}})
    d = r.json(); blocks = d.get("content", [])
    has = any(b.get("type") == "thinking" for b in blocks)
    ok = r.status_code == 200 and has
    record("PASS" if ok else "FAIL", r.status_code, "ANT ON: thinking block",
           f"has_thinking={has} block_types={[b.get('type') for b in blocks]}")


# ── Anthropic: thinking OFF -> no thinking block ──────────────────────────────
def ant_off():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 8000, "temperature": 0,
            "messages": [{"role": "user", "content": "Capital of France?"}],
            "thinking": {"type": "disabled"}})
    d = r.json(); blocks = d.get("content", [])
    has = any(b.get("type") == "thinking" for b in blocks)
    ot = (d.get("usage") or {}).get("output_tokens", 0)
    ok = r.status_code == 200 and not has
    record("PASS" if ok else "FAIL", r.status_code, "ANT OFF: no thinking block",
           f"has_thinking={has} output_tokens={ot}")


def ant_basic():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 40,
            "messages": [{"role": "user", "content": "Say hi"}],
            "thinking": {"type": "disabled"}})
    d = r.json(); blocks = d.get("content", [])
    txt = next((b.get("text", "") for b in blocks if b.get("type") == "text"), "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT basic", f"text={txt[:40]!r}")


# ── run ───────────────────────────────────────────────────────────────────────
print("=" * 64, flush=True)
print(f"{MODEL} thinking verification", flush=True)
print("=" * 64, flush=True)
for t in [basic, tools, on_medium, on_high, off, budget, stream_on,
          ant_basic, ant_on, ant_off]:
    try:
        t()
    except Exception as e:
        record("ERR", 0, t.__name__, str(e)[:120])

p = sum(1 for x in results if x[0] == "PASS")
f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
print(f"\n{'=' * 64}\nResults: {p} passed, {f} failed/err of {len(results)}", flush=True)
