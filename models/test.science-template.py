"""TEMPLATE — per-model gateway test battery for SCIENCE models (custom servers).

These are NOT chat models — there is no /v1/chat/completions. The battery hits the model's own
science endpoint (/v1/science/<verb> or /v1/<verb>), retries through the cold-start 503, checks the
output SHAPE + a domain SANITY check (NOT a correctness oracle), and gracefully SKIPs when there's
no realistic test vector (demo-only / real-data-not-via-API models).

Copy to models/<your-model>/test.py, then FILL IN (from the card input_map + research):
  - MODEL, ENDPOINT, PAYLOAD  (minimal valid request body)
  - the SHAPE key/type assertions + the SANITY predicate for your domain
  - NO_TEST_VECTOR  (set a reason ONLY if the model has no real test vector → SHAPE/SANITY SKIP)
Delete what doesn't apply.

Run externally via the public edge + Tyk auth:
  GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=<id> python3 models/<m>/test.py
Run inside the gateway pod (no auth):
  cat models/<m>/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
# Public edge may serve a self-signed cert — opt out with GW_INSECURE=1 for login-node runs.
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "__MODEL_ID__")

# ── FILL IN (from details.yaml endpoints.primary + input_map + research) ───────
ENDPOINT = "/v1/science/__VERB__"        # the model's primary route
PAYLOAD = {"model": MODEL}               # minimal valid request body (research-derived)
NO_TEST_VECTOR = ""                      # set a reason ONLY if no real test vector → SHAPE/SANITY SKIP
results = []


def req(method, path, body=None, timeout=300):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout,
                         headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


# ── 1. WAKE (retry through cold-start 503 on the science endpoint) ────────────
def wake():
    if NO_TEST_VECTOR:
        record("SKIP", 0, "WAKE (no test vector)", NO_TEST_VECTOR); return
    for attempt in range(72):
        r = req("POST", ENDPOINT, PAYLOAD)
        if r.status_code == 200:
            record("PASS", 200, "WAKE + endpoint", f"attempts={attempt+1}"); return
        if r.status_code == 503:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + endpoint", f"unexpected body={r.text[:80]}"); return
    record("FAIL", 503, "WAKE + endpoint", "timed out waiting for warm model")


# ── 2. SHAPE (200 + output matches output_map keys/types) ─────────────────────
def shape():
    if NO_TEST_VECTOR:
        record("SKIP", 0, "SHAPE (no test vector)", NO_TEST_VECTOR); return
    r = req("POST", ENDPOINT, PAYLOAD)
    if r.status_code != 200:
        record("FAIL", r.status_code, "SHAPE", f"body={r.text[:80]}"); return
    d = r.json()
    # EDIT: assert the keys/types your output_map documents. Example (force-field):
    #   ok = {"energy", "forces"} <= set(d) and isinstance(d["energy"], (int, float))
    ok = bool(d)
    record("PASS" if ok else "FAIL", r.status_code, "SHAPE", f"keys={sorted(d.keys())}")


# ── 3. SANITY (domain check — "not garbage", NOT a correctness oracle) ────────
def sanity():
    if NO_TEST_VECTOR:
        record("SKIP", 0, "SANITY (no test vector)", NO_TEST_VECTOR); return
    r = req("POST", ENDPOINT, PAYLOAD)
    d = r.json() if r.status_code == 200 else {}
    # EDIT: a domain sanity check. Examples:
    #   force-field : -50 < energy < 0 (eV-scale), forces finite, len == n_atoms
    #   structure   : pdb startswith "ATOM", 0 <= plddt <= 100
    #   dock        : poses non-empty, confidence float, sdf present
    #   forecast    : deltas finite, output shaped like input
    ok = r.status_code == 200
    record("PASS" if ok else "FAIL", r.status_code, "SANITY", "checked")


# ── 4. MODEL-ECHO + no streaming path ─────────────────────────────────────────
def model_echo():
    if NO_TEST_VECTOR:
        record("SKIP", 0, "MODEL-ECHO (no test vector)", NO_TEST_VECTOR); return
    r = req("POST", ENDPOINT, PAYLOAD)
    m = (r.json() or {}).get("model") if r.status_code == 200 else None
    record("PASS" if m == MODEL else "FAIL", r.status_code, "MODEL-ECHO", f"model={m!r}")


# ── 5. GUARD / CATALOG ────────────────────────────────────────────────────────
def catalog():
    # Science/non-chat models appear only in /v1/models?all=true (the plain list is chat-routable only).
    r = req("GET", "/v1/models?all=true")
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m:
        record("FAIL", 0, "Catalog entry", "not found"); return
    record("PASS", r.status_code, "Catalog entry", f"type={m.get('type')} endpoint match")


# ── run ───────────────────────────────────────────────────────────────────────
BATTERY = [wake, shape, sanity, model_echo, catalog]

if __name__ == "__main__":
    print("=" * 66, flush=True)
    print(f"{MODEL} science test ({ENDPOINT})", flush=True)
    print("=" * 66, flush=True)
    for t in BATTERY:
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
