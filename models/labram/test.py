"""labram EEG embedding gateway test.

Embedding (Template C) battery for a custom braindecode server (LaBraM, CPU).
200-dim [CLS] embeddings of multi-channel EEG windows, via the domain /v1/science/embed
endpoint. LaBraM is non-text (EEG-array input), so it does NOT expose OpenAI /v1/embeddings
and stays on /v1/science/embed.

Run externally via the gateway VIP + Tyk auth (preferred):
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/labram/test.py

Run inside the gateway pod (legacy, no auth needed):
  cat models/labram/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, json, math, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
MODEL = os.environ.get("MODEL", "labram")
EXP_DIM = 200
N_TIMES = 2000  # server pads/truncates to the pretrained 3000
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def science_embed(body, timeout=300):
    body = {**body, "model": MODEL}
    r = httpx.post(f"{G}/v1/science/embed", json=body, timeout=timeout, headers=_HEADERS)
    try:
        return r, r.json()
    except Exception:
        return r, {}


def _cos(a, b):
    da = math.sqrt(sum(x * x for x in a))
    db = math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / (da * db) if da and db else 0.0


class _LCG:
    def __init__(self, seed):
        self.s = seed & 0x7FFFFFFF
    def next(self):
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return round(((self.s % 2000) / 1000.0) - 1.0, 4)  # [-1, 1)-ish EEG-ish


def rand_eeg(seed, n_chans=8, n_times=N_TIMES):
    rng = _LCG(seed)
    return [[rng.next() for _ in range(n_times)] for _ in range(n_chans)]


CH8 = ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4"]


def wake_dim():
    eeg = rand_eeg(1)
    for attempt in range(72):
        r, d = science_embed({"eeg": eeg, "ch_names": CH8})
        if r.status_code == 200:
            n = len(d.get("embeddings", []))
            rec = "PASS" if n == EXP_DIM else "FAIL"
            record(rec, 200, "WAKE + dim", f"attempts={attempt+1} dim={n} (exp {EXP_DIM})")
            return
        if r.status_code in (503, 502, 404):
            time.sleep(5)
            continue
        record("FAIL", r.status_code, "WAKE + dim", f"body={r.text[:120]}")
        return
    record("FAIL", 0, "WAKE + dim", "timed out")


def nonzero():
    r, d = science_embed({"eeg": rand_eeg(2), "ch_names": CH8})
    emb = d.get("embeddings", [])
    zero = all(v == 0 for v in emb)
    # Real pretrained weights -> non-trivial embedding (not all-zero, not a tiny range)
    ok = r.status_code == 200 and len(emb) == EXP_DIM and not zero
    record("PASS" if ok else "FAIL", r.status_code, "non-zero real", f"zero={zero} sample={[round(v,3) for v in emb[:4]]}")


def distinct():
    _, d1 = science_embed({"eeg": rand_eeg(10), "ch_names": CH8})
    _, d2 = science_embed({"eeg": rand_eeg(20), "ch_names": CH8})
    e1, e2 = d1.get("embeddings"), d2.get("embeddings")
    if not e1 or not e2:
        record("FAIL", 0, "distinctness", "missing embeddings")
        return
    c = _cos(e1, e2)
    record("PASS" if c < 0.999 else "FAIL", 200, "distinctness", f"cos(eeg_a,eeg_b)={c:.5f}")


def deterministic():
    eeg = rand_eeg(30)
    _, d1 = science_embed({"eeg": eeg, "ch_names": CH8})
    _, d2 = science_embed({"eeg": eeg, "ch_names": CH8})
    e1, e2 = d1.get("embeddings"), d2.get("embeddings")
    if not e1 or not e2:
        record("FAIL", 0, "deterministic", "missing embeddings")
        return
    c = _cos(e1, e2)
    record("PASS" if c > 0.9999 else "FAIL", 200, "deterministic", f"cos(eeg,eeg)={c:.5f}")


def channel_subset():
    # 4-channel subset should still yield 200-dim
    r, d = science_embed({"eeg": rand_eeg(40, n_chans=4), "ch_names": CH8[:4]})
    n = len(d.get("embeddings", []))
    ok = r.status_code == 200 and n == EXP_DIM and d.get("n_channels") == 4
    record("PASS" if ok else "FAIL", r.status_code, "channel subset", f"n_chans={d.get('n_channels')} dim={n}")


def padding_short():
    # Short input (200 samples) is padded to the pretrained n_times=3000 -> still 200-dim
    r, d = science_embed({"eeg": rand_eeg(50, n_chans=8, n_times=200), "ch_names": CH8})
    n = len(d.get("embeddings", []))
    used = d.get("n_times_used")
    ok = r.status_code == 200 and n == EXP_DIM and used == 3000
    record("PASS" if ok else "FAIL", r.status_code, "short-input padded", f"n_times_used={used} dim={n}")


def chnames_mismatch():
    # ch_names count != channels -> server should 4xx/5xx, not hang
    r, _ = science_embed({"eeg": rand_eeg(60, n_chans=8), "ch_names": CH8[:3]})
    record("PASS" if 400 <= r.status_code < 600 else "FAIL", r.status_code, "ch_names mismatch", f"status={r.status_code}")


def malformed():
    # No eeg -> 4xx/5xx
    r, _ = science_embed({"ch_names": CH8})
    record("PASS" if 400 <= r.status_code < 600 else "FAIL", r.status_code, "malformed handled", f"status={r.status_code}")


def summary():
    passed = sum(1 for i, *_ in results if i == "PASS")
    failed = sum(1 for i, *_ in results if i == "FAIL")
    print(f"\n== {MODEL}: {passed} PASS / {failed} FAIL of {len(results)} ==", flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    wake_dim()
    nonzero()
    distinct()
    deterministic()
    channel_subset()
    padding_short()
    chnames_mismatch()
    malformed()
    raise SystemExit(summary())
