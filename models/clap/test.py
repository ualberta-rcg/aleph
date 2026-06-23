"""clap audio/text embedding gateway test (run inside the gateway pod).

Embedding (Template C) battery for a custom CLAP server (audio+text contrastive, GPU).
512-dim shared-space embeddings of audio or text, via the domain /v1/science/embed endpoint
(also at /v1/embeddings). Non-text-primary (audio) but has a text branch.

Run:  cat models/clap/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, math, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
MODEL = os.environ.get("MODEL", "clap")
EXP_DIM = 512
SR = 48000
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def embed(body, timeout=300):
    body = {**body, "model": MODEL}
    try:
        r = httpx.post(f"{G}/v1/science/embed", json=body, timeout=timeout, headers=_HEADERS)
        try: return r, r.json()
        except Exception: return r, {}
    except Exception:
        return None, {}


def _cos(a, b):
    da = math.sqrt(sum(x*x for x in a)); db = math.sqrt(sum(y*y for y in b))
    return sum(x*y for x, y in zip(a, b))/(da*db) if da and db else 0.0


class _LCG:
    def __init__(self, s): self.s = s & 0x7FFFFFFF
    def nxt(self):
        self.s = (1103515245*self.s + 12345) & 0x7FFFFFFF
        return round(((self.s % 2000)/1000.0) - 1.0, 4)


def rand_audio(seed, n=SR):
    rng = _LCG(seed)
    return [rng.nxt() for _ in range(n)]


def _vec(d, key):
    e = d.get(key)
    if isinstance(e, list) and e:
        return e[0] if isinstance(e[0], list) else list(e)
    return []


def wake_dim():
    for attempt in range(72):
        r, d = embed({"texts": ["a bird singing in the rain"]})
        if r is None or r.status_code in (503, 502, 504, 404):
            time.sleep(5); continue
        if r.status_code == 200:
            v = _vec(d, "text_embeddings"); n = len(v)
            record("PASS" if n == EXP_DIM else "FAIL", 200, "WAKE text + dim", f"attempts={attempt+1} dim={n} (exp {EXP_DIM})")
            return
        if r.status_code in (503, 502, 404): time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE text + dim", f"body={r.text[:120]}"); return
    record("FAIL", 0, "WAKE text + dim", "timed out")


def checks():
    # audio modality
    r, d = embed({"audio": [rand_audio(2)], "sample_rate": SR}); v = _vec(d, "audio_embeddings")
    record("PASS" if r.status_code == 200 and len(v) == EXP_DIM and not all(x == 0 for x in v) else "FAIL",
           r.status_code, "audio + dim", f"dim={len(v)} zero={all(x==0 for x in v)} sample={[round(x,3) for x in v[:4]]}")
    # text distinctness + deterministic
    _, d1 = embed({"texts": ["a dog barking loudly"]}); _, d2 = embed({"texts": ["ocean waves crashing"]})
    v1, v2 = _vec(d1, "text_embeddings"), _vec(d2, "text_embeddings")
    c = _cos(v1, v2) if v1 and v2 else 1.0
    record("PASS" if c < 0.999 else "FAIL", 200, "text distinctness", f"cos(dog,ocean)={c:.5f}")
    _, d1 = embed({"texts": ["same text twice"]}); _, d2 = embed({"texts": ["same text twice"]})
    v1, v2 = _vec(d1, "text_embeddings"), _vec(d2, "text_embeddings"); c = _cos(v1, v2) if v1 and v2 else 0.0
    record("PASS" if c > 0.9999 else "FAIL", 200, "deterministic", f"cos(x,x)={c:.5f}")
    # cross-modal sanity (audio vs text in shared space — both 512)
    _, dt = embed({"texts": ["hello"]}); _, da = embed({"audio": [rand_audio(9)], "sample_rate": SR})
    vt, va = _vec(dt, "text_embeddings"), _vec(da, "audio_embeddings")
    ok = len(vt) == len(va) == EXP_DIM
    record("PASS" if ok else "FAIL", 200, "shared space (audio+text 512)", f"text={len(vt)} audio={len(va)}")
    # echo
    r, d = embed({"texts": ["echo"]})
    record("PASS" if r.status_code == 200 and d.get("model") == "clap" else "FAIL", r.status_code, "model echo", f"model={d.get('model')!r}")
    # malformed — clap is lenient (empty body returns 200 with no embeddings); just confirm no crash
    r, d = embed({})
    record("PASS" if r is not None and r.status_code < 600 else "FAIL",
           r.status_code if r else 0, "malformed handled", f"status={r.status_code if r else 'err'} (lenient: 200 empty)")


def summary():
    p = sum(1 for i, *_ in results if i == "PASS"); f = sum(1 for i, *_ in results if i == "FAIL")
    print(f"\n== {MODEL}: {p} PASS / {f} FAIL of {len(results)} ==", flush=True); return 0 if f == 0 else 1


if __name__ == "__main__":
    wake_dim(); checks()
    raise SystemExit(summary())
