"""qwen38-27b worst-case-traffic stress battery.

Built after the 2026-08-26 engine death: at gpu-mem-util 0.92 the first large
chunked-prefill batch OOM'd the engine (532MB GEMM output, 1.3GB free), EngineDead wedged
the pod for ~4h holding 2 whole L40S. This battery reproduces the killer shapes and
asserts the engine is still alive at the end.

PASS criteria: every step HTTP 200 with sane output AND zero
`OutOfMemoryError|EngineDeadError` in the pod log AND a final chat succeeds.

Run like test.py:
  GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> MODEL=qwen38-27b \
      python3 models/qwen38-27b/stress.py
  # video step needs VIDEO_B64 (small mp4, base64) or VIDEO_URL.
Pod-log check needs STRESS_SSH=1 (runs kubectl via sudo ssh to aleph1); without it the
log grep step is SKIPped.
"""
import httpx, json, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "qwen38-27b")
RED_PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
results = []


def req(method, path, body=None, timeout=600):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, name, detail):
    results.append((icon, name))
    print(f"[{icon}] {name}: {detail}", flush=True)


def chat(body, timeout=600):
    t0 = time.time()
    r = req("POST", "/v1/chat/completions", body, timeout=timeout)
    dt = time.time() - t0
    if r.status_code != 200:
        return r, dt, None
    d = r.json()
    return r, dt, (d["choices"][0]["message"] if d.get("choices") else None)


def filler_words(n_tokens):
    # ~1.3 tokens/word for this tokenizer; pad hard and let the server count.
    base = ("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi "
            "omicron pi rho sigma tau upsilon phi chi psi omega ")
    text = base * (int(n_tokens * 1.4 / len(base.split())) + 1)
    return text


def s1_baseline():
    r, dt, m = chat({"model": MODEL, "messages": [{"role": "user", "content": "Say OK"}],
                     "reasoning_effort": "none", "max_tokens": 20})
    record("PASS" if r.status_code == 200 and m else "FAIL", "s1 baseline",
           f"{r.status_code} in {dt:.1f}s content={m and (m.get('content') or '')[:20]!r}")


def s2_long_prefill():
    body = {"model": MODEL, "messages": [{"role": "user", "content":
            filler_words(15000) + "\n\nHow many Greek letter names appear above? Answer briefly."}],
            "reasoning_effort": "medium", "max_tokens": 512}
    r, dt, m = chat(body)
    ok = r.status_code == 200 and m and len(m.get("reasoning") or "") >= 0
    u = r.json().get("usage", {}) if r.status_code == 200 else {}
    record("PASS" if ok else "FAIL", "s2 long prefill ~15k tok (max chunk)",
           f"{r.status_code} in {dt:.1f}s prompt={u.get('prompt_tokens')} rc_len={m and len(m.get('reasoning') or '')}")


def s3_prefix_cache_hit():
    body = {"model": MODEL, "messages": [{"role": "user", "content":
            filler_words(15000) + "\n\nHow many Greek letter names appear above? One word."}],
            "reasoning_effort": "none", "max_tokens": 100}
    r1, dt1, _ = chat(body)
    r2, dt2, m2 = chat(body)
    ok = r1.status_code == 200 and r2.status_code == 200
    record("PASS" if ok else "FAIL", "s3 repeat long prefill (prefix-cache path)",
           f"1st {r1.status_code} {dt1:.1f}s / 2nd {r2.status_code} {dt2:.1f}s ({dt2/max(dt1,0.01):.0%} of first)")


def s4_concurrent_burst():
    import concurrent.futures as cf
    bodies = [{"model": MODEL, "messages": [{"role": "user", "content":
               filler_words(8000) + f"\n\nSummarize passage {i} in one sentence."}],
               "reasoning_effort": "none", "max_tokens": 120} for i in range(8)]
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        rs = list(ex.map(lambda b: chat(b, timeout=900), bodies))
    dt = time.time() - t0
    codes = [r.status_code for r, _, _ in rs]
    ok = all(c == 200 for c in codes)
    record("PASS" if ok else "FAIL", "s4 burst 8x ~8k-token prefills",
           f"codes={codes} wall={dt:.1f}s avg={dt/8:.1f}s")


def s5_long_plus_mm():
    prompt = filler_words(12000) + "\n\nDescribe the attached image in one word, then name letter #5 above."
    img_body = {"model": MODEL, "messages": [{"role": "user", "content": [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": RED_PNG}}]}],
        "reasoning_effort": "none", "max_tokens": 100}
    r, dt, m = chat(img_body)
    ok_img = r.status_code == 200 and m
    u = r.json().get("usage", {}) if r.status_code == 200 else {}
    record("PASS" if ok_img else "FAIL", "s5a 12k prefill + image",
           f"{r.status_code} in {dt:.1f}s prompt={u.get('prompt_tokens')}")
    vurl = os.environ.get("VIDEO_URL") or (f"data:video/mp4;base64,{os.environ['VIDEO_B64']}" if os.environ.get("VIDEO_B64") else None)
    if not vurl:
        record("SKIP", "s5b 12k prefill + video", "set VIDEO_URL or VIDEO_B64 to enable")
        return
    vid_body = {"model": MODEL, "messages": [{"role": "user", "content": [
        {"type": "text", "text": filler_words(12000) + "\n\nDescribe the video in one sentence."},
        {"type": "video_url", "video_url": {"url": vurl}}]}],
        "reasoning_effort": "none", "max_tokens": 120}
    r, dt, m = chat(vid_body, timeout=900)
    record("PASS" if r.status_code == 200 and m else "FAIL", "s5b 12k prefill + video",
           f"{r.status_code} in {dt:.1f}s")


def s6_sustained_mix():
    t0 = time.time(); bad = []
    for i in range(20):
        n = [30, 2000, 6000, 100, 10000][i % 5]
        r, dt, m = chat({"model": MODEL, "messages": [{"role": "user", "content":
                filler_words(n) + f"\n\nReply with the number {i} only."}],
                "reasoning_effort": "none", "max_tokens": 30})
        if r.status_code != 200:
            bad.append((i, n, r.status_code))
    dt = time.time() - t0
    record("PASS" if not bad else "FAIL", "s7 sustained mix x20",
           f"{20-len(bad)}/20 ok in {dt:.1f}s bad={bad}")


def s7_health_and_logs():
    r = req("GET", "/v1/models", timeout=30)
    ok = r.status_code == 200
    r2, dt, m = chat({"model": MODEL, "messages": [{"role": "user", "content": "final ping"}],
                      "reasoning_effort": "none", "max_tokens": 10})
    ok = ok and r2.status_code == 200
    record("PASS" if ok else "FAIL", "s7a engine alive after stress",
           f"models={r.status_code} chat={r2.status_code} in {dt:.1f}s")
    if os.environ.get("STRESS_SSH") != "1":
        record("SKIP", "s7b pod-log OOM/EngineDead grep", "set STRESS_SSH=1 to enable")
        return
    import subprocess
    cmd = ("sudo ssh root@172.26.92.43 \"export PATH=$PATH:/var/lib/rancher/rke2/bin; "
           "export KUBECONFIG=/etc/rancher/rke2/rke2.yaml; kubectl logs -n models "
           "-l serving.kserve.io/inferenceservice=" + MODEL + " -c kserve-container "
           "--since=30m 2>&1 | grep -cE 'OutOfMemoryError|EngineDeadError' || true\"")
    n = int(subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip() or "0")
    record("PASS" if n == 0 else "FAIL", "s7b pod-log OOM/EngineDead grep", f"{n} matches in last 30m")


print("=" * 70, flush=True); print(f"{MODEL} stress battery (worst-case traffic)", flush=True); print("=" * 70, flush=True)
for step in [s1_baseline, s2_long_prefill, s3_prefix_cache_hit, s4_concurrent_burst,
             s5_long_plus_mm, s6_sustained_mix, s7_health_and_logs]:
    try:
        step()
    except Exception as e:
        record("ERR", step.__name__, str(e)[:120])

p = sum(1 for x in results if x[0] == "PASS"); f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
s = sum(1 for x in results if x[0] == "SKIP")
print(f"\n{'=' * 70}\nStress results: {p} pass, {f} FAIL/ERR, {s} skipped of {len(results)}", flush=True)
