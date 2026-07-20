"""xtts-v2 Coqui TTS + voice-cloning gateway test (run inside the gateway pod).

Coqui XTTS-v2 multilingual TTS via OpenAI-style POST /v1/audio/speech -> audio/wav,
plus voice cloning via POST /v1/audio/clone (multipart + base64) and recalled saved
voices. Covers WAKE + audio (RIFF/WAV bytes), voice param, empty-input rejection,
unknown-model 404 guardrail, catalog entry, clone (base64 + multipart), saved-voice
recall, and the /v1/audio/voices listing.

Run inside the gateway pod (no auth needed):
  cat models/xtts-v2/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -

External via the gateway VIP + Tyk auth:
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/xtts-v2/test.py
"""
import os, time, io, math, struct, wave, base64
import httpx

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
MODEL = os.environ.get("MODEL", "xtts-v2")
results = []


def req(method, path, body=None, timeout=300):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS)


def tts(body, timeout=300):
    return req("POST", "/v1/audio/speech", body, timeout=timeout)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def _is_wav(b: bytes) -> bool:
    return len(b) > 1000 and b[:4] == b"RIFF" and b[8:12] == b"WAVE"


# ── 1. WAKE (retry through cold-start 503) + audio/wav ────────────────────────
def wake_audio():
    for attempt in range(72):
        r = tts({"model": MODEL, "input": "Hello, this is a quick test.", "language": "en"})
        if r.status_code == 200:
            ok = _is_wav(r.content)
            record("PASS" if ok else "FAIL", 200, "WAKE + audio/wav",
                   f"attempts={attempt+1} bytes={len(r.content)} wav={_is_wav(r.content)}")
            return
        if r.status_code == 503:
            time.sleep(5)
            continue
        record("FAIL", r.status_code, "WAKE + audio/wav", r.text[:80])
        return
    record("FAIL", 503, "WAKE + audio/wav", "timed out waiting for warm model")


def voice_param():
    r = tts({"model": MODEL, "input": "Testing the voice clone parameter.", "language": "en", "voice": "en"})
    ok = r.status_code == 200 and _is_wav(r.content)
    record("PASS" if ok else "EXP", r.status_code, "voice param",
           f"bytes={len(r.content) if r.status_code == 200 else 0}")


def long_input():
    r = tts({"model": MODEL, "input": "This is a longer sentence to synthesize. " * 5, "language": "en"})
    ok = r.status_code == 200 and _is_wav(r.content)
    record("PASS" if ok else "FAIL", r.status_code, "longer input",
           f"bytes={len(r.content) if r.status_code == 200 else 0}")


def empty_input():
    r = tts({"model": MODEL, "input": "", "language": "en"})
    record("EXP" if 400 <= r.status_code < 500 else "FAIL", r.status_code,
           "Guard: empty input", "(expect 4xx)")


def guard_badmodel():
    r = tts({"model": "fake-xyz", "input": "hi"})
    record("EXP" if r.status_code == 404 else "FAIL", r.status_code,
           "Guard: unknown model", str(r.text)[:60])


def catalog():
    r = req("GET", "/v1/models?all=true")
    m = next((x for x in r.json().get("data", []) if x.get("id") == MODEL), None)
    if not m:
        record("FAIL", 0, "Catalog entry", f"{MODEL} not found")
        return
    record("PASS" if m.get("type") == "tts" else "FAIL", r.status_code,
           "Catalog entry", f"type={m.get('type')}")


# ── reference clip for cloning (3s 440Hz tone, mono 24kHz WAV) ────────────────
def _ref_wav():
    sr, secs, freq = 24000, 3.0, 440.0
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        frames = bytearray()
        for i in range(int(sr * secs)):
            s = int(32767 * 0.4 * math.sin(2 * math.pi * freq * (i / sr)))
            frames += struct.pack("<h", s)
        w.writeframes(frames)
    return buf.getvalue()


def clone_base64():
    """Clone via JSON base64 voice_sample; model omitted to exercise the default."""
    ref = _ref_wav()
    r = httpx.request("POST", f"{G}/v1/audio/clone", timeout=300, headers=_HEADERS,
                      json={"input": "Cloning a voice from a sample.", "language": "en",
                            "voice_sample": base64.b64encode(ref).decode()})
    ok = r.status_code == 200 and _is_wav(r.content)
    record("PASS" if ok else "FAIL", r.status_code, "Clone (base64)",
           f"bytes={len(r.content) if r.status_code == 200 else 0}")


def clone_multipart_save():
    """Clone via multipart upload with save_as=clonetest; reuse the saved voice next."""
    ref = _ref_wav()
    r = httpx.request("POST", f"{G}/v1/audio/clone", timeout=300, headers=_HEADERS,
                      data={"model": MODEL, "input": "Saving a cloned voice.",
                            "language": "en", "save_as": "clonetest"},
                      files={"file": ("ref.wav", ref, "audio/wav")})
    ok = r.status_code == 200 and _is_wav(r.content)
    record("PASS" if ok else "FAIL", r.status_code, "Clone (multipart, save_as)",
           f"bytes={len(r.content) if r.status_code == 200 else 0}")


def saved_voice_recall():
    """Recall the saved clone by name via /v1/audio/speech."""
    r = tts({"model": MODEL, "input": "Recalling the saved voice.",
             "language": "en", "voice": "clonetest"})
    ok = r.status_code == 200 and _is_wav(r.content)
    record("PASS" if ok else "FAIL", r.status_code, "Saved-voice recall",
           f"bytes={len(r.content) if r.status_code == 200 else 0}")


def voices_listing():
    r = req("GET", "/v1/audio/voices")
    if r.status_code != 200:
        record("FAIL", r.status_code, "Voices listing", r.text[:80]); return
    d = r.json()
    ok = "voices" in d and "saved" in d
    record("PASS" if ok else "FAIL", r.status_code, "Voices listing",
           f"builtin={len(d.get('voices', []))} saved={d.get('saved')}")


# ── run ───────────────────────────────────────────────────────────────────────
print("=" * 66, flush=True)
print(f"{MODEL} Coqui TTS gateway test", flush=True)
print("=" * 66, flush=True)
for t in [wake_audio, voice_param, long_input, empty_input, guard_badmodel, catalog,
          clone_base64, clone_multipart_save, saved_voice_recall, voices_listing]:
    try:
        t()
    except Exception as e:
        record("ERR", 0, t.__name__, str(e)[:120])

p = sum(1 for x in results if x[0] == "PASS")
e = sum(1 for x in results if x[0] == "EXP")
f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err of {len(results)}", flush=True)
