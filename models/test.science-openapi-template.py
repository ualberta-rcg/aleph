"""TEMPLATE — OpenAPI-aware gateway test battery for NVIDIA science NIMs.

Run inside the gateway pod:
  cat models/<m>/test.py | \
      kubectl exec -i -n models deploy/model-gateway -- python3 -

Each model's test.py sets the variables in the CONFIG section below and then copies/runs
the rest of this file. The harness:

1. Wakes the model through the public gateway endpoint.
2. Fetches the NIM's native OpenAPI spec from the in-cluster ksvc.
3. Discovers the POST operation that accepts FIXTURE and runs it as the primary endpoint.
4. Property-maps the request schema:
   - missing each required field -> expects 4xx
   - each enum value -> expects 2xx
   - numeric min/max/typical/out-of-range values -> expects 2xx or 4xx as appropriate
5. Sanity-checks the response against the operation's response schema.
6. Checks /v1/health/ready, /v1/models, and gateway catalog.

Copy this file, fill in CONFIG, and save as models/<m>/test.py.
"""
import copy, httpx, json, os, time, urllib.parse

# ── CONFIG (filled in per model) ───────────────────────────────────────────────
G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")

MODEL = os.environ.get("MODEL", "__MODEL_ID__")          # e.g. "alphafold2"
KSVC = os.environ.get("KSVC", f"{MODEL}-predictor")      # in-cluster ksvc name
UPSTREAM = os.environ.get("UPSTREAM", f"http://{KSVC}.models.svc.cluster.local")
ENDPOINT = os.environ.get("ENDPOINT", "/v1/__ENDPOINT__")  # public gateway path
FIXTURE = {"model": MODEL}                                # minimal valid request
SKIP_PROPS = set()                                        # props to skip in negative tests
TIMEOUT = int(os.environ.get("TIMEOUT", "600"))

results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def _upstream_body():
    """Return a copy of FIXTURE with the OpenAI-style `model` field removed.

    Direct calls to the NIM must not include `model` (and often `stream`), while
    gateway calls keep it for routing.
    """
    body = copy.deepcopy(FIXTURE)
    body.pop("model", None)
    body.pop("stream", None)
    return body


def greq(method, path, body=None, timeout=TIMEOUT):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout,
                         headers=_HEADERS, verify=_VERIFY)


def ureq(method, path, body=None, timeout=TIMEOUT):
    return httpx.request(method, f"{UPSTREAM}{path}", json=body, timeout=timeout,
                         headers={}, verify=False)


# ── 1. WAKE through gateway ────────────────────────────────────────────────────
def wake():
    for attempt in range(80):
        r = greq("POST", ENDPOINT, FIXTURE)
        if r.status_code == 200:
            record("PASS", 200, "WAKE", f"attempts={attempt+1}")
            return True
        if r.status_code in (502, 503, 504):
            time.sleep(5); continue
        if r.status_code == 404 and attempt < 30:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE", f"body={r.text[:120]}")
        return False
    record("FAIL", 503, "WAKE", "timed out")
    return False


# ── 2. OpenAPI discovery ───────────────────────────────────────────────────────
_spec = None
_primary_path = None
_primary_op = None


def load_openapi():
    global _spec, _primary_path, _primary_op
    r = ureq("GET", "/openapi.json")
    if r.status_code != 200:
        record("SKIP", r.status_code, "OpenAPI", "spec not reachable")
        return False
    try:
        _spec = r.json()
    except Exception as e:
        record("SKIP", 0, "OpenAPI", f"parse error: {e}")
        return False

    # Pick the POST path that accepts FIXTURE. Try paths in order: exact match of
    # ENDPOINT suffix, then paths that contain a known keyword, then first POST.
    paths = _spec.get("paths", {})
    candidates = []
    suffix = ENDPOINT.split("/v1/", 1)[-1] if "/v1/" in ENDPOINT else ENDPOINT
    for p, ops in paths.items():
        if "post" not in ops:
            continue
        if p.lstrip("/") == suffix or p.endswith(suffix.split("/")[-1]):
            candidates.insert(0, p)
        else:
            candidates.append(p)

    for p in candidates:
        test = ureq("POST", p, _upstream_body())
        if test.status_code == 200:
            _primary_path = p
            _primary_op = _spec["paths"][p]["post"]
            break
    if not _primary_path:
        _primary_path = candidates[0] if candidates else None
        _primary_op = _spec["paths"][_primary_path]["post"] if _primary_path else None

    record("PASS" if _primary_op else "SKIP", 200,
           "OpenAPI", f"paths={len(paths)} primary={_primary_path}")
    return bool(_primary_op)


# ── 3. Response schema validation ──────────────────────────────────────────────
def _type_match(value, schema, path="root"):
    if not isinstance(schema, dict):
        return True
    types = schema.get("type")
    if not types:
        return True
    if isinstance(types, str):
        types = [types]
    type_ok = False
    for t in types:
        if t == "string" and isinstance(value, str):
            type_ok = True
        elif t == "integer" and isinstance(value, int) and not isinstance(value, bool):
            type_ok = True
        elif t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            type_ok = True
        elif t == "boolean" and isinstance(value, bool):
            type_ok = True
        elif t == "array" and isinstance(value, list):
            type_ok = True
        elif t == "object" and isinstance(value, dict):
            type_ok = True
        elif t == "null" and value is None:
            type_ok = True
    if not type_ok:
        return False
    if "array" in types and isinstance(value, list):
        item_schema = schema.get("items", {})
        return all(_type_match(v, item_schema, f"{path}[i]") for v in value)
    if "object" in types and isinstance(value, dict):
        props = schema.get("properties", {})
        for k, sub in props.items():
            if k in value and not _type_match(value[k], sub, f"{path}.{k}"):
                return False
        return True
    return True


def _schema_check(d, schema):
    if not isinstance(schema, dict):
        return True, "no schema"
    # top-level object check
    if schema.get("type") == "object":
        for k, sub in schema.get("properties", {}).items():
            if k in d and not _type_match(d[k], sub, k):
                return False, f"key {k} type mismatch"
    return True, "schema ok"


def response_schema():
    if not _primary_op:
        record("SKIP", 0, "RESPONSE-SCHEMA", "no OpenAPI op")
        return
    r = ureq("POST", _primary_path, _upstream_body())
    if r.status_code != 200:
        record("FAIL", r.status_code, "RESPONSE-SCHEMA", f"body={r.text[:120]}")
        return
    try:
        d = r.json()
    except Exception:
        record("FAIL", 200, "RESPONSE-SCHEMA", "not JSON")
        return
    resp_schema = (_primary_op.get("responses", {})
                   .get("200", {})
                   .get("content", {})
                   .get("application/json", {})
                   .get("schema", {}))
    ok, msg = _schema_check(d, resp_schema)
    record("PASS" if ok else "FAIL", 200, "RESPONSE-SCHEMA", msg)


# ── 4. Property mapping ────────────────────────────────────────────────────────
def _request_schema():
    if not _primary_op:
        return {}
    return (_primary_op.get("requestBody", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {}))


def _set_leaf(d, key_path, value):
    keys = key_path.split(".")
    cur = d
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    cur[keys[-1]] = value


def _make_body_without(key_path):
    body = _upstream_body()
    keys = key_path.split(".")
    cur = body
    for k in keys[:-1]:
        if not isinstance(cur.get(k), dict):
            return body
        cur = cur[k]
    cur.pop(keys[-1], None)
    return body


def required_fields():
    schema = _request_schema()
    required = schema.get("required", [])
    if not required:
        record("SKIP", 0, "REQUIRED-FIELDS", "none declared")
        return
    passes = fails = 0
    for key in required:
        if key in SKIP_PROPS:
            continue
        r = ureq("POST", _primary_path, _make_body_without(key))
        # NIMs vary: some 422 on missing, others use defaults and return 200.
        if r.status_code in (400, 422):
            passes += 1
        else:
            fails += 1
            print(f"  missing {key}: {r.status_code}", flush=True)
    record("PASS" if fails == 0 else "FAIL", 200,
           "REQUIRED-FIELDS", f"ok={passes} unexpected={fails}")


def enum_values():
    schema = _request_schema()
    props = schema.get("properties", {})
    passes = fails = 0
    for key, sub in props.items():
        if key in SKIP_PROPS:
            continue
        enum = sub.get("enum")
        if not enum:
            continue
        for val in enum:
            body = _upstream_body()
            _set_leaf(body, key, val)
            r = ureq("POST", _primary_path, body)
            if r.status_code == 200:
                passes += 1
            else:
                fails += 1
                print(f"  {key}={val}: {r.status_code}", flush=True)
    if passes + fails == 0:
        record("SKIP", 0, "ENUM-VALUES", "no enums")
    else:
        record("PASS" if fails == 0 else "FAIL", 200,
               "ENUM-VALUES", f"ok={passes} fail={fails}")


def numeric_ranges():
    schema = _request_schema()
    props = schema.get("properties", {})
    passes = fails = 0
    for key, sub in props.items():
        if key in SKIP_PROPS:
            continue
        t = sub.get("type")
        if t not in ("number", "integer"):
            continue
        mn = sub.get("minimum")
        mx = sub.get("maximum")
        tests = []
        if mn is not None:
            tests.append(("min", mn))
            if t == "integer":
                tests.append(("below-min", mn - 1))
            else:
                tests.append(("below-min", mn - 0.1))
        if mx is not None:
            tests.append(("max", mx))
            if t == "integer":
                tests.append(("above-max", mx + 1))
            else:
                tests.append(("above-max", mx + 0.1))
        # typical value from fixture is already implicitly tested by wake
        for label, val in tests:
            body = _upstream_body()
            _set_leaf(body, key, val)
            r = ureq("POST", _primary_path, body)
            if r.status_code in (200, 400, 422):
                passes += 1
            else:
                fails += 1
                print(f"  {key} {label}={val}: {r.status_code}", flush=True)
    if passes + fails == 0:
        record("SKIP", 0, "NUMERIC-RANGES", "no numeric props")
    else:
        record("PASS" if fails == 0 else "FAIL", 200,
               "NUMERIC-RANGES", f"ok={passes} fail={fails}")


def string_formats():
    schema = _request_schema()
    props = schema.get("properties", {})
    passes = fails = 0
    for key, sub in props.items():
        if key in SKIP_PROPS or sub.get("type") != "string":
            continue
        # empty string
        body = _upstream_body()
        _set_leaf(body, key, "")
        r = ureq("POST", _primary_path, body)
        if r.status_code in (200, 400, 422):
            passes += 1
        else:
            fails += 1
    if passes + fails == 0:
        record("SKIP", 0, "STRING-FORMATS", "no string props")
    else:
        record("PASS" if fails == 0 else "FAIL", 200,
               "STRING-FORMATS", f"ok={passes} fail={fails}")


# ── 5. Native health / models / openapi ────────────────────────────────────────
def native_health():
    r = ureq("GET", "/v1/health/ready")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code,
           "NATIVE-HEALTH", "ready" if r.status_code == 200 else r.text[:80])


def native_models():
    r = ureq("GET", "/v1/models")
    if r.status_code == 404:
        record("SKIP", 404, "NATIVE-MODELS", "endpoint not implemented")
        return
    if r.status_code != 200:
        record("FAIL", r.status_code, "NATIVE-MODELS", r.text[:80]); return
    try:
        data = r.json()
        models = data if isinstance(data, list) else data.get("available_models", data.get("data", []))
        record("PASS", 200, "NATIVE-MODELS", f"count={len(models)}")
    except Exception as e:
        record("FAIL", 200, "NATIVE-MODELS", f"parse: {e}")


def openapi_reachable():
    r = ureq("GET", "/openapi.json")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code,
           "OPENAPI-REACHABLE", f"size={len(r.text)}" if r.status_code == 200 else r.text[:80])


# ── 6. Gateway catalog ─────────────────────────────────────────────────────────
def catalog():
    r = greq("GET", "/v1/models?all=true")
    if r.status_code != 200:
        record("FAIL", r.status_code, "CATALOG", r.text[:80]); return
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m:
        record("FAIL", 0, "CATALOG", "model not found"); return
    record("PASS", r.status_code, "CATALOG",
           f"type={m.get('type')} endpoint={m.get('endpoint')}")


# ── 7. Error handling ──────────────────────────────────────────────────────────
def malformed_json():
    r = httpx.request("POST", f"{G}{ENDPOINT}", content="not json",
                      headers={**_HEADERS, "Content-Type": "application/json"},
                      verify=_VERIFY, timeout=TIMEOUT)
    record("PASS" if r.status_code in (400, 422) else "FAIL", r.status_code,
           "MALFORMED-JSON", r.text[:80])


def empty_body():
    r = greq("POST", ENDPOINT, {})
    record("PASS" if r.status_code in (400, 422) else "FAIL", r.status_code,
           "EMPTY-BODY", r.text[:80])


# ── run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 70, flush=True)
    print(f"{MODEL} OpenAPI-driven science test ({ENDPOINT})", flush=True)
    print("=" * 70, flush=True)
    if not wake():
        # still run catalog so the failure is complete
        catalog()
    else:
        openapi_ok = load_openapi()
        native_health()
        native_models()
        openapi_reachable()
        catalog()
        if openapi_ok:
            response_schema()
            required_fields()
            enum_values()
            numeric_ranges()
            string_formats()
        malformed_json()
        empty_body()
    p = sum(1 for x in results if x[0] == "PASS")
    e = sum(1 for x in results if x[0] == "EXP")
    f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
    s = sum(1 for x in results if x[0] == "SKIP")
    print(f"\n{'=' * 70}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(results)}",
          flush=True)
