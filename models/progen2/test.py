"""progen2 gateway test (completions-only).

ProGen2-XLarge (6.4B, custom transformers server, NOT vLLM). POST /v1/completions with an amino-acid
prompt -> continued sequence. No chat, no tools, no vision, no streaming.
NB: the gateway requires a `model` field to route (the progen2 server ignores it).

Run externally via the gateway VIP + Tyk auth:
  GW_URL=https://<GATEWAY_VIP> TYK_KEY=<key> GW_INSECURE=1 python3 models/progen2/test.py
"""
import httpx, json, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = "progen2"
AA = "ACDEFGHIKLMNPQRSTVWY"  # valid single-letter amino acids
results = []


def req(method, path, body=None, timeout=300):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def comp(prompt, max_tokens=20, temperature=0.0):
    # gateway routes on `model`; the progen2 server reads only prompt/max_tokens/temperature.
    return {"model": MODEL, "prompt": prompt, "max_tokens": max_tokens, "temperature": temperature}


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def wake():
    for attempt in range(60):
        r = req("POST", "/v1/completions", comp("MKTIIAL", 20, 0.0))
        if r.status_code == 200:
            txt = r.json()["choices"][0]["text"]
            record("PASS", 200, "WAKE + completion", f"attempts={attempt+1} out={txt[:40]!r}")
            return
        if r.status_code == 503:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + completion", f"unexpected body={r.text[:80]}")
        return
    record("FAIL", 503, "WAKE + completion", "timed out waiting for warm model")


def completion_temp():
    r = req("POST", "/v1/completions", comp("MKTAYIA", 30, 1.0))
    ok = r.status_code == 200 and bool(r.json().get("choices"))
    record("PASS" if ok else "FAIL", r.status_code, "completion temp=1.0", r.json()["choices"][0]["text"][:40] if ok else r.text[:60])


def completion_cap():
    r = req("POST", "/v1/completions", comp("MKT", 5, 0.0))
    d = r.json(); ct = len(d.get("choices", [{}])[0].get("text", ""))
    record("PASS" if r.status_code == 200 and ct > 0 else "FAIL", r.status_code, "completion max_tokens=5", f"len={ct}")


def usage_model():
    r = req("POST", "/v1/completions", comp("MKTII", 10, 0.0))
    d = r.json()
    ok = r.status_code == 200 and d.get("model") == MODEL and d.get("object") == "text_completion"
    record("PASS" if ok else "FAIL", r.status_code, "model + object echo", f"model={d.get('model')!r} object={d.get('object')!r}")


def amino_acid_output():
    r = req("POST", "/v1/completions", comp("MKTIIAL", 40, 0.0))
    d = r.json(); txt = d.get("choices", [{}])[0].get("text", "")
    tail = txt[len("MKTIIAL"):] if txt.startswith("MKTIIAL") else txt
    aa_frac = sum(c in AA for c in tail) / max(1, len(tail))
    record("PASS" if r.status_code == 200 and aa_frac > 0.8 else "FAIL", r.status_code,
           "output is amino-acid-like", f"aa_frac={aa_frac:.2f} tail={tail[:30]!r}")


def guard_chat():
    # progen2 is completions-only: a chat request must be rejected with 400.
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5})
    record("EXP" if r.status_code == 400 else "FAIL", r.status_code, "Guard: chat rejected", str(r.json().get("error", ""))[:50])


def catalog():
    # The gateway's /v1/models catalog doesn't list completions-type models (known behavior);
    # routing still works via the `model` field. Informational, not a failure.
    r = req("GET", "/v1/models")
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    record("PASS" if m else "EXP", r.status_code, "Catalog entry (completions type may not list)", f"type={m.get('type') if m else 'not-listed (ok)'}")


if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} gateway test (completions)", flush=True); print("=" * 66, flush=True)
    for t in (wake, completion_temp, completion_cap, usage_model, amino_acid_output, guard_chat, catalog):
        try:
            t()
        except Exception as e:
            record("ERR", 0, t.__name__, str(e)[:120])
    p = sum(1 for x in results if x[0] == "PASS"); e = sum(1 for x in results if x[0] == "EXP")
    f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
    print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err of {len(results)}", flush=True)
