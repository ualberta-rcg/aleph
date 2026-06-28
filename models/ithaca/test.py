"""ithaca restoration test — POST /v1/science/predict {text}.

Restores + dates + geolocates an ancient Greek inscription (50-750 chars, gaps [---]). Sanity:
response has restoration + attribution and is NOT the demo fallback (which means jax failed to load).
The Greek text is built via ASCII->Greek transliteration to avoid Cyrillic homoglyphs (ithaca's
alphabet rejects non-Greek chars -> KeyError).
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=ithaca python3 models/ithaca/test.py
"""
import httpx, os, time

G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "ithaca")
ENDPOINT = "/v1/science/predict"

# ASCII -> Greek uppercase codepoints (no Cyrillic homoglyph ambiguity).
_BETA = {"A": "Α", "B": "Β", "G": "Γ", "D": "Δ", "E": "Ε", "Z": "Ζ", "H": "Η",
         "Q": "Θ", "I": "Ι", "K": "Κ", "L": "Λ", "M": "Μ", "N": "Ν", "X": "Ξ",
         "O": "Ο", "P": "Π", "R": "Ρ", "S": "Σ", "T": "Τ", "U": "Υ", "F": "Φ",
         "C": "Χ", "Y": "Ψ", "W": "Ω", " ": " "}
# Attic decree fragment (>50 chars). Gap char is "?" (predictingthepast alphabet; NOT "[---]").
TEXT = "".join(_BETA.get(ch, ch) for ch in
               "EDOCHSEN TEI BOULEI KAI TOI DEMOI ATHENAIOI TON ??? ARXONTA KAI TOUS PAIDAS AGATHEI TYXEI")
PAYLOAD = {"model": MODEL, "text": TEXT}  # NO demo:true → real jax inference
results = []


def req(body, timeout=300):
    return httpx.post(f"{G}{ENDPOINT}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def wake():
    for attempt in range(72):
        r = req(PAYLOAD)
        if r.status_code == 200:
            record("PASS", 200, "WAKE + predict", f"attempts={attempt+1}"); return r.json()
        if r.status_code in (502, 503, 504):
            time.sleep(5); continue
        if r.status_code == 404 and attempt < 24:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + predict", f"unexpected body={r.text[:120]}"); return None
    record("FAIL", 503, "WAKE + predict", "timed out waiting for warm model"); return None


def shape(d):
    ok = {"restoration", "attribution"} <= set(d)
    record("PASS" if ok else "FAIL", 200, "SHAPE", f"keys={sorted(d.keys())}")


def sanity(d):
    # demo:true would mean the jax model failed to load (server fell back to canned output).
    demo = d.get("demo", False)
    ok = (not demo) and isinstance(d.get("restoration"), dict) and isinstance(d.get("attribution"), dict)
    record("PASS" if ok else "FAIL", 200, "SANITY (real inference, not demo)",
           f"demo={demo} restoration_keys={sorted((d.get('restoration') or {}).keys())}")


def model_echo(d):
    record("PASS" if d.get("model") == MODEL else "FAIL", 200, "MODEL-ECHO", f"model={d.get('model')!r}")


def catalog():
    r = httpx.get(f"{G}/v1/models?all=true", headers=_HEADERS, verify=_VERIFY, timeout=30)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    record("PASS" if m else "FAIL", r.status_code, "Catalog entry",
           f"type={m.get('type') if m else 'MISSING'}")


if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} restoration test ({ENDPOINT})", flush=True)
    print("=" * 66, flush=True)
    d = wake()
    if d:
        for t in (shape, sanity, model_echo, catalog):
            try:
                t(d) if t is not catalog else t()
            except Exception as e:
                record("ERR", 0, t.__name__, str(e)[:120])
    else:
        catalog()
    p = sum(1 for x in results if x[0] == "PASS"); e = sum(1 for x in results if x[0] == "EXP")
    f = sum(1 for x in results if x[0] in ("FAIL", "ERR")); s = sum(1 for x in results if x[0] == "SKIP")
    print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(results)}",
          flush=True)
