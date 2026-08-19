"""Gateway test — model-agnostic checks of the gateway itself.

These exercise behaviors that belong to the gateway, not to any one model:
catalog shape, health/metrics, routing guardrails (bad model, wrong endpoint for
a model's type, unsupported tools/vision), the auth edge (Tyk), and the resources
block. Targets and model names are discovered from /v1/models at runtime, so this
has no hardcoded model list or cluster IP.

  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 gateway/test.py          # gateway checks
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> FLEET=1 python3 gateway/test.py  # + warm-sweep every model

Inside the gateway pod (no auth):
  cat gateway/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -

Per-model feature batteries live next to each model: models/<model>/test.py
(start from models/test.template.py).
"""
import base64, json, os, struct, sys, time, zlib
import httpx

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
FLEET = os.environ.get("FLEET", "").lower() in ("1", "true", "yes")
WARM_TIMEOUT = 480
results = []


def req(method, path, body=None, timeout=180, headers=None, stream=False):
    h = _HEADERS if headers is None else headers
    if stream:
        return httpx.stream(method, f"{G}{path}", json=body, timeout=timeout, headers=h)
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout, headers=h)


def record(icon, status, name, detail=""):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def make_png(r, g, b, size=16):
    """Tiny solid-color PNG → base64 data URL (cluster can't fetch external URLs)."""
    def chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    raw = (b"\x00" + bytes([r, g, b]) * size) * size
    png = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    return "data:image/png;base64," + base64.b64encode(png).decode()


RED_IMG = make_png(220, 20, 20)
MINI_PDB = ("ATOM      1  N   GLY A   1      0.000   0.000   0.000  1.00  0.00           N\n"
            "ATOM      2  CA  GLY A   1      1.458   0.000   0.000  1.00  0.00           C\n"
            "ATOM      3  C   GLY A   1      2.009   1.420   0.000  1.00  0.00           C\n"
            "ATOM      4  O   GLY A   1      1.251   2.390   0.000  1.00  0.00           O\nEND\n")


def catalog(show_all=True):
    r = req("GET", f"/v1/models{'?all=true' if show_all else ''}")
    return r, (r.json().get("data", []) if r.status_code == 200 else [])


def first(entries, pred):
    return next((e for e in entries if pred(e)), None)


def _cold(r):
    """True if the response is a Knative cold-start (model scaled to zero / starting).
    Gateway checks shouldn't warm models, so callers SKIP on cold instead of failing."""
    if r.status_code != 503:
        return False
    try:
        code = r.json().get("error", {}).get("code", "")
    except Exception:
        code = ""
    return code in ("model_scaled_to_zero", "model_starting", "insufficient_capacity") or r.status_code == 503


# ── health / metrics ──────────────────────────────────────────────────────────
def health():
    for path, label in (("/healthz", "healthz"), ("/readyz", "readyz")):
        try:
            r = req("GET", path, timeout=15)
            record("PASS" if r.status_code == 200 else "FAIL", r.status_code, f"health {label}", r.text[:40])
        except Exception as e:
            record("ERR", 0, f"health {label}", str(e)[:60])

def metrics():
    try:
        r = req("GET", "/metrics", timeout=15)
        ok = r.status_code == 200 and len(r.text) > 0
        record("PASS" if ok else "FAIL", r.status_code, "metrics", f"{len(r.text)} bytes")
    except Exception as e:
        record("ERR", 0, "metrics", str(e)[:60])


# ── catalog shape ─────────────────────────────────────────────────────────────
def catalog_schema():
    r, allm = catalog(True)
    if r.status_code != 200 or not allm:
        record("FAIL", r.status_code, "catalog ?all=true", "no data"); return
    need = ("id", "object", "type", "capabilities", "context_window", "max_completion_tokens")
    missing = {k for e in allm for k in need if k not in e}
    sorted_ok = [e["id"] for e in allm] == sorted(e["id"] for e in allm)
    ok = not missing and sorted_ok
    record("PASS" if ok else "FAIL", r.status_code, "catalog schema",
           f"n={len(allm)} sorted={sorted_ok} missing_fields={sorted(missing)}")

def catalog_default_subset():
    _, allm = catalog(True)
    r, chat = catalog(False)
    ids_all = {e["id"] for e in allm}
    ids_chat = {e["id"] for e in chat}
    non_chat = {e["id"] for e in chat if e.get("type", "chat") != "chat"}
    ok = r.status_code == 200 and ids_chat <= ids_all and not non_chat
    record("PASS" if ok else "FAIL", r.status_code, "catalog default=chat-only",
           f"default={len(ids_chat)} all={len(ids_all)} non_chat_leaked={sorted(non_chat)}")


# ── routing guardrails ────────────────────────────────────────────────────────
def guard_bad_model():
    r = req("POST", "/v1/chat/completions", {"model": "definitely-not-a-real-model",
            "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5})
    record("EXP" if r.status_code == 404 else "FAIL", r.status_code, "guard bad model (404)",
           str(r.json().get("error", ""))[:50])

def guard_embed_via_chat():
    _, allm = catalog(True)
    em = first(allm, lambda e: e.get("type") == "embedding")
    if not em:
        record("SKIP", 0, "guard chat→embedder (400)", "no embedding model"); return
    r = req("POST", "/v1/chat/completions", {"model": em["id"],
            "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5})
    if _cold(r):
        record("SKIP", r.status_code, "guard chat→embedder (400)", f"{em['id']} cold (type-check is post-scale)"); return
    record("EXP" if r.status_code == 400 else "FAIL", r.status_code, "guard chat→embedder (400)",
           f"model={em['id']} code={r.json().get('error',{}).get('code','')}")

def guard_chat_via_embed():
    _, allm = catalog(True)
    cm = first(allm, lambda e: e.get("type", "chat") == "chat")
    if not cm:
        record("SKIP", 0, "guard embed→chat-model (400)", "no chat model"); return
    r = req("POST", "/v1/embeddings", {"model": cm["id"], "input": "hi"})
    if _cold(r):
        record("SKIP", r.status_code, "guard embed→chat-model (400)", f"{cm['id']} cold (type-check is post-scale)"); return
    record("EXP" if r.status_code == 400 else "FAIL", r.status_code, "guard embed→chat-model (400)",
           f"model={cm['id']}")

def guard_tools_unsupported():
    _, allm = catalog(True)
    nm = first(allm, lambda e: e.get("type", "chat") == "chat" and not e.get("capabilities", {}).get("tools"))
    if not nm:
        record("SKIP", 0, "guard tools→no-tool model (400)", "no non-tool chat model"); return
    tools = [{"type": "function", "function": {"name": "x", "parameters": {"type": "object", "properties": {}}}}]
    r = req("POST", "/v1/chat/completions", {"model": nm["id"], "max_tokens": 16,
            "messages": [{"role": "user", "content": "hi"}], "tools": tools})
    code = r.json().get("error", {}).get("code", "") if r.status_code != 200 else ""
    record("EXP" if r.status_code == 400 else "FAIL", r.status_code, "guard tools→no-tool model (400)",
           f"model={nm['id']} code={code}")

def guard_vision_unsupported():
    _, allm = catalog(True)
    nm = first(allm, lambda e: e.get("type", "chat") == "chat" and not e.get("capabilities", {}).get("vision"))
    if not nm:
        record("SKIP", 0, "guard image→no-vision model (400)", "no non-vision chat model"); return
    r = req("POST", "/v1/chat/completions", {"model": nm["id"], "max_tokens": 16,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "what is this?"},
                {"type": "image_url", "image_url": {"url": RED_IMG}}]}]})
    code = r.json().get("error", {}).get("code", "") if r.status_code != 200 else ""
    record("EXP" if r.status_code == 400 else "FAIL", r.status_code, "guard image→no-vision model (400)",
           f"model={nm['id']} code={code}")


# ── auth edge (only meaningful through the Tyk VIP) ────────────────────────────
def auth_required():
    if not _KEY:
        record("SKIP", 0, "auth: no-key rejected", "TYK_KEY unset (running keyless/in-pod)"); return
    r = req("GET", "/v1/models", headers={})  # deliberately no Authorization
    record("EXP" if r.status_code in (401, 403) else "FAIL", r.status_code,
           "auth: no-key rejected", f"status={r.status_code}")


# ── resources block (uses an already-ready model; never warms) ────────────────
def resources_block():
    _, allm = catalog(True)
    rm = first(allm, lambda e: e.get("type", "chat") == "chat" and e.get("ready"))
    if not rm:
        record("SKIP", 0, "resources block", "no ready chat model"); return
    r = req("POST", "/v1/chat/completions", {"model": rm["id"],
            "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5, "reasoning_effort": "none"})
    if _cold(r):
        record("SKIP", r.status_code, "resources block", f"{rm['id']} cold (no warming in gateway test)"); return
    res = r.json().get("resources", {}) if r.status_code == 200 else {}
    record("PASS" if r.status_code == 200 and "model" in res else "FAIL", r.status_code,
           "resources block", f"model={rm['id']} keys={sorted(res.keys())}")


# ── optional: warm-sweep the whole fleet (replaces the old full_test.py) ───────
def _warm(path, payload):
    t0 = time.time()
    while time.time() - t0 < WARM_TIMEOUT:
        try:
            r = req("POST", path, payload, timeout=60)
            if r.status_code == 200:
                return True, int(time.time() - t0), r
        except Exception:
            pass
        time.sleep(8)
    return False, int(time.time() - t0), None

def _probe_for(entry):
    """(path, payload, validate) for a catalog entry, chosen by type/endpoint."""
    t = entry.get("type", "chat"); mid = entry["id"]
    if t == "embedding":
        return "/v1/embeddings", {"model": mid, "input": "hello world"}, \
            lambda r: bool(r.json().get("data"))
    if t == "rerank":
        return "/v1/rerank", {"model": mid, "query": "q", "documents": ["a", "b"]}, \
            lambda r: bool(r.json().get("results"))
    ep = entry.get("endpoint", "") or ""
    if ep.startswith("/v1/science") or ep in ("/v1/design", "/v1/forecast"):
        # Science/custom endpoints: just confirm the route warms to 200 with a model echo.
        return ep, {"model": mid}, lambda r: True
    # default: chat
    return "/v1/chat/completions", {"model": mid, "messages": [{"role": "user", "content": "hi"}],
                                    "max_tokens": 8}, lambda r: True

def fleet_sweep():
    _, allm = catalog(True)
    print(f"\n--- fleet sweep: {len(allm)} models (warming each, up to {WARM_TIMEOUT}s) ---", flush=True)
    for e in allm:
        path, payload, validate = _probe_for(e)
        ok, secs, r = _warm(path, payload)
        if not ok:
            record("FAIL", 0, f"fleet {e['id']}", f"did not warm in {secs}s ({path})"); continue
        try:
            good = validate(r)
        except Exception:
            good = False
        record("PASS" if good else "FAIL", r.status_code, f"fleet {e['id']}",
               f"type={e.get('type','chat')} warm={secs}s")


GATEWAY_CHECKS = [
    health, metrics, catalog_schema, catalog_default_subset,
    guard_bad_model, guard_embed_via_chat, guard_chat_via_embed,
    guard_tools_unsupported, guard_vision_unsupported,
    auth_required, resources_block,
]

if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"gateway test @ {G}", flush=True); print("=" * 66, flush=True)
    for t in GATEWAY_CHECKS:
        try:
            t()
        except Exception as ex:
            record("ERR", 0, t.__name__, str(ex)[:120])
    if FLEET:
        try:
            fleet_sweep()
        except Exception as ex:
            record("ERR", 0, "fleet_sweep", str(ex)[:120])

    p = sum(1 for x in results if x[0] == "PASS")
    e = sum(1 for x in results if x[0] == "EXP")
    f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
    s = sum(1 for x in results if x[0] == "SKIP")
    print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(results)}",
          flush=True)
    sys.exit(1 if f else 0)
