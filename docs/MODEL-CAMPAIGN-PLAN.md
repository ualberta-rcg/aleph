# Model Campaign Plan — Chat LLMs + Embeddings

> **STATUS (2026-06-19): chat LLMs (29) + reasoning (13) DONE + committed. The active
> phase is the ~64 embedding/rerank dirs — see §11.**
>
> Working plan for the per-model sweep over the **29 chat LLMs** and the **~64
> embedding / rerank** models. Lives in the local dir (not aleph). Source-of-truth
> trackers: `aleph/models/MODEL-STATUS.md` (committed) + this dir's
> `LLM-MODEL-TRACKER.md` (campaign notes). Scope chosen 2026-06-17: **chat +
> embeddings together**.

## What this campaign actually is

**Testing + artifact authoring — not reconfiguration.** The models already work
(almost all PASS already). For each model we: **deploy it as-is, test it, and only
then write the card / README / CLAUDE / test to match what we observed.** We are not
rebuilding or re-tuning services.

Deliverables per model dir (ensure all four exist and match the working model):
- `details.yaml` — the **card** (current schema; matches observed behavior)
- `README.md` — model overview (**create in every dir that lacks one**)
- `CLAUDE.md` — model context / working notes (**create in every dir that lacks one**)
- `test.py` (or `.sh`) — the saved per-model **test barrage** (**create where missing**)

## Hard rules (every model, no exceptions)

- **Test before any change.** Deploy + run the barrage as-is first. Never pre-align the
  card/ISVC before you've seen it work.
- **No changes to the service / ISVC** unless testing shows a **startup need or
  something small**. The models work — we document them, we don't reconfigure them.
  Anything bigger → skip-and-note (§6).
- **Never eager.** `minReplicas: 0` on every ISVC; leave it at 0 when done. Don't-touch
  exceptions: `speaches` (always-on Deployment).
- **vLLM `vllm/vllm-openai:v0.20.2`** where applicable; no `--enforce-eager`.
- **Fix-only, don't remake.** Skip-and-note anything complicated.
- **Single branch.** Commit straight to `main` in `aleph` — never create a branch.
- **Changelog-first.** Every commit that changes code/config gets a dated `CHANGELOG.md`
  entry in the same commit.
- **"Cards"** — don't call them "v2" in commits/docs.
- **Secrets stay in `.env`** (gitignored). Names ok in aleph, values never.
- **Web-search the model before authoring its card.** Read its HuggingFace repo page
  (+ paper / vLLM / TEI usage notes) to fill card fields accurately — embedding dim,
  max input tokens, pooling, params, precision, license, framework, domain. This is *why*
  search is part of every model: richer, correct cards. Cite `catalog.source_url`.
- **Dir layout = flat files (the `gpt-oss-20b` standard).** Every model dir holds exactly
  `details.yaml`, `pvc.yaml`, `inferenceservice.yaml`, `test.py`, `README.md`, `CLAUDE.md`
  (+ optional `download-job.yaml`). No `kustomization.yaml`.
- **PVC is its own file, and it must be `ReadWriteMany`.** If a dir inlines the PVC inside
  `inferenceservice.yaml` (65 dirs do) or has no `pvc.yaml` at all (57 of those), extract it
  to a standalone `pvc.yaml` with `accessModes: [ReadWriteMany]`, `storageClassName: nfs-client`.
  RWX is required — NFS-backed weights are shared across scale-from-zero cold starts; `RWO`
  breaks reuse across pods.

---

## Gateway state — managed thinking is LIVE (2026-06-18)

The gateway **exposes reasoning when thinking is ON and strips+caps when OFF** for every
**managed-thinking** model (`param_translation.thinking.mode` in `budget`/`effort`/`toggle`):
- **ON** (`reasoning_effort: medium|high`, Anthropic `thinking: enabled`) → OpenAI ships the
  `reasoning` field; Anthropic emits a `thinking` content block (non-stream + SSE); streaming
  ships reasoning deltas.
- **OFF** (`reasoning_effort: none|disabled`, Anthropic `thinking: disabled`) → strip reasoning
  everywhere **and** cap `max_tokens` (`off_max_tokens`, default 2048). Effort models fake a
  token budget via a caller `thinking_token_budget` → `max_tokens` cap.
- This is **fleet-wide**: qwen3\*, phi-4-reasoning, gemma-4, qwen36\*, etc. now expose reasoning
  where they used to strip it. **Every reasoning card + test must be re-verified** (Phase 1).
- vLLM v0.20.2 emits reasoning in **`reasoning`** (not `reasoning_content`); tests/cards read either.

**Reference exemplars (DONE — copy these):** `gpt-oss-120b` + `gpt-oss-20b` — correct v2 cards
(`strips_thinking: false`, `off_max_tokens: 2048`, effort mode), 33-check `test.py` (30/3/0),
README + CLAUDE. Deploy path: commit → GH Actions builds `rkhoja/aleph:latest` (+ immutable
`gateway-<sha>`) → `kubectl rollout restart deploy/model-gateway -n models` (manifest pins
`:latest` + `imagePullPolicy: Always`, so the restart pulls the new build).
Cards hot-reload via the ConfigMap watch (no gateway restart).

---

## 1. The canonical per-model working process

For each model, in this order:

| # | Step | Done when |
|---|------|-----------|
| 1 | **Read the model dir** — `CLAUDE.md`/`details.yaml`/`inferenceservice.yaml`/`test.py` (whichever exist) | current state understood |
| 2 | **Deploy + wake as-is** — `kubectl apply -k` (if needed) + wake via gateway; **no edits** | `Ready=True`, pod up |
| 3 | **Run the test barrage** — the per-model `test.py` (or build one), as-is | results captured |
| 4 | **If broken → small fix only** — startup tweak or minor ISVC arg, then retest. Hard? → skip-and-note (§6) | PASS / expected-fails only |
| 5 | **Author/align the card** (`details.yaml`) to match what we just observed working | card == reality |
| 6 | **Ensure `README.md`** exists — create if missing; matches working settings | present + accurate |
| 7 | **Ensure `CLAUDE.md`** exists — create if missing; model context, deploy/test notes | present + accurate |
| 8 | **Ensure `test.py`/`test.sh`** exists — the saved barrage from step 3 | one per dir |
| 9 | **Record** — `MODEL-STATUS.md` row (aleph) + local tracker notes | updated |
| 10 | **Commit** (changelog-first) to `aleph` `main` | pushed |
| 11 | **Scale to 0 + verify it stays down** | 0 pods ×2, Stopped |

> Steps 5–8 are **authoring to match the working model** — they happen *after* the test
> passes, never before. If the model already PASSes, steps 4 is skipped and 5–8 are pure
> documentation work.

### Step 2 — deploy + wake (scale-to-zero native, no edits)
```bash
# Model dir = has inferenceservice.yaml (167/169). NO kustomize — flat yaml dir.
kubectl apply --server-side --force-conflicts -f models/<name>/   # ISVC + details + pvc (+ download-job, self-skips if weights staged)
# wake via the gateway (preferred — exercises the real path). Remove stop annotation if present:
kubectl annotate isvc <name> -n models serving.kserve.io/stop- --overwrite
# then curl the gateway; pod scales 0->1 (first call may 503-with-ETA, then succeed)
# OR spin one up explicitly for testing:
kubectl patch isvc <name> -n models --type merge -p '{"spec":{"predictor":{"minReplicas":1}}}'
kubectl get isvc <name> -n models -w   # Ready=True
```

### Step 3 — where the test barrage runs (Phase 0 finding)
The card-driven gateway is `deploy/model-gateway` (ns `models`, 2/2 containers, has
`httpx 0.28.1`). Inside that pod, `localhost:8080` **is** the gateway. So a model's
`test.py` runs **inside the gateway pod** — no Python on the Vulcan login node:

```bash
cat models/<name>/test.py | sudo ssh root@172.26.92.43 \
  'export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml;
   kubectl exec -i -n models deploy/model-gateway -- python3 -'
```

Each `test.py` hardcodes its own `MODEL`, so stdin-run needs no edit/copy. The first call
may 503-with-ETA while the model pod cold-starts, then PASS.

### Step 4 — "small fix only" boundary
Touch the ISVC only if the test fails on something like: missing `--reasoning-parser`/
`--tool-call-parser`, wrong `--max-model-len`, a startup crash, or `minReplicas` left >0.
**Do not** re-architect, change TP/GPU strategy, swap images, or "improve" args. If the
fix isn't small → skip-and-note (§6) and leave the service as-is.

**Research hard cases first.** When a model's thinking/behavior is wrong (parser crash,
empty content, wrong field), **web-search the model's upstream vLLM + HuggingFace usage +
known issues** (e.g. `vllm#18141`) before deciding fix vs skip. The latest vLLM/HF threads
usually have the real config (e.g. phi-4 needs REDUCE-off `none→512` not `0`; gemma-4 needs
`enable_thinking` not `reasoning_effort`; GLM-Z1 emits CoT in-content, no `<think>` field).
Cite the issue/doc in the card note.

### Step 11 — scale to 0 + verify it STAYS down
Steady state = `minReplicas: 0` + **no** stop annotation + 0 pods (wake-on-demand). That
**alone scales to zero** after the idle window — proven on gpt-oss (was 0 pods with
minReplicas 0, no stop). The `scale-to-zero-pod-retention-period` (15m) only lingers the
last pod ~N after the last request.

```bash
kubectl patch isvc <name> -n models --type merge -p '{"spec":{"predictor":{"minReplicas":0}}}'
# leave NO stop annotation (wake-on-demand). Pod lingers up to the retention period, then 0:
kubectl get pods -n models -l serving.kserve.io/inferenceservice=<name>   # -> 0 after idle
# To force it down NOW (mid-campaign), set stop=true, verify 0, then remove it so it stays
# wake-on-demand:
kubectl annotate isvc <name> -n models serving.kserve.io/stop=true --overwrite   # force 0 now
# (later) kubectl annotate isvc <name> -n models serving.kserve.io/stop- --overwrite
```
**"Stays down" =** minReplicas 0, no stop, 0 pods after the idle window. If pods return with
no traffic, a leftover minReplicas>0 is reviving it — fix the cause. (Patch JSON needs 3
closing braces when shell-escaped; single-quoted form above is clean.)

---

## 2. Phase 0 — cross-cutting prep (do ONCE, before any model)

Phase 0 findings (2026-06-17):

- [x] **15-min idle-down knob — RESOLVED.** Mechanism is the per-ISVC annotation
      **`autoscaling.knative.dev/scale-to-zero-pod-retention-period`** (NOT `window`).
      Live: `gpt-oss-120b`=15m, `qwen3-235b`=30m. Global default `0s`,
      `scale-to-zero-grace-period` 30s, `stable-window` 60s → pod lingers ~N after the last
      request. **The card's `scaling.idle_retention` is the doc mirror of this annotation —
      they must match.** Already enforced on the models checked; nothing to build. When
      authoring a card, set `idle_retention` = the ISVC's retention-period value.
- [x] **Test-exec method — RESOLVED.** Run a model's `test.py` inside `deploy/model-gateway`
      (ns `models`; has httpx 0.28.1; `localhost:8080` = the gateway). No Python on the
      login node. See §1 Step 3.
- [x] **Model-dir marker — RESOLVED.** A model dir = has `inferenceservice.yaml` (167/169).
      NO kustomize (only 35 have `kustomization.yaml`; we don't want it). Deploy = `apply -f`.
- [ ] **Confirm never-eager exceptions** (`speaches` always-on Deployment, `kandinsky-3`
      RayService) — leave alone (verify their replica counts).
- [ ] **First-stage cleanup — `TEST.md` → `README.md`.** 47 dirs have a stale `TEST.md`
      (2026-06-04..06). Fold into that model's `README.md`, then delete `TEST.md`.
- [ ] **Per-model test filename** = `test.py` (one per dir; start from
      `models/test.template.py`). Gateway-level checks live in `gateway/test.py`; the
      ops driver is `models/test-model.sh`.
- [x] **Gaps enumerated** (marker = `inferenceservice.yaml`, 167 dirs):
      - missing **README**: 146 · missing **CLAUDE**: 23 · missing **test.\***: 141
      - The 29 chat LLMs are mostly complete; the gaps concentrate in the ~140
        embeddings/science/audio dirs. Chat LLMs still missing **CLAUDE**: glm-4-32b,
        glm-z1-32b, glm-z1-rumination-32b, qwen36-27b, r1-distill-llama-70b,
        r1-distill-qwen-32b. Chat LLMs missing **README**: gpt-oss-120b, gpt-oss-20b,
        gemma-4-26b-a4b, glm-4-32b, phi-4-reasoning, qwen25-vl-72b-awq, qwen36-27b, r1-distill-*.
      - **Reference exemplars (DONE):** `gpt-oss-120b` + `gpt-oss-20b` — working managed-thinking
        models, correct v2 cards, 33-check tests (30/3/0), README + CLAUDE. **Copy these for any
        reasoning model.** Layout exemplar for a non-reasoning dir: `qwen3-235b` (complete flat dir).

---

## 3. Phase 1 — reasoning chat (13 models, full feature test)

Re-verify each against the **live managed-thinking gateway** (see "Gateway state" above):
ON must expose reasoning, OFF must strip+cap. Use the 33-check battery (§7) — copy from
`gpt-oss-120b/test.py` / `gpt-oss-20b/test.py` and trim per model (vision/tools/effort mode).
Each reasoning card needs `strips_thinking: false` + `off_max_tokens` (add if missing).

✅ **gpt-oss-120b, gpt-oss-20b — DONE** (30/3/0; reference exemplars). **11 remain:**

| Model | Thinking | Reason parser | Tool parser | Note |
|---|---|---|---|---|
| qwen36-27b | effort | qwen3 | qwen3_coder | — |
| qwen3-32b | effort | qwen3 | hermes | — |
| qwen36-35b-a3b | effort | qwen3 | qwen3_coder | verify card claims (vision/tools) |
| qwen35-122b | toggle | qwen3 | qwen3_coder | — |
| gemma-4-26b-a4b | effort | gemma4 | gemma4 | vision-URL fails in-cluster (expected) |
| phi-4-reasoning | budget | deepseek_r1 | — | small max_tokens → empty (expected) |
| qwq-32b | always-on | deepseek_r1 | hermes | — |
| r1-distill-qwen-32b | always-on | deepseek_r1 | — | card ctx 131072 vs ISVC 65536 |
| r1-distill-llama-70b | always-on | deepseek_r1 | — | card ctx 131072 vs ISVC 65536 |
| glm-z1-32b | toggle | — (template) | glm45 ⚠️ | tool parser broken — note, don't force-fix |
| glm-z1-rumination-32b | toggle | — (template) | — (by design) | ignores tools/sysprompt by design |

**always-on note:** qwq / r1-distill / glm-z1 reason in-template; `param_translation.thinking`
absent ≡ `none`. Correct — don't add a thinking block to them.

---

## 4. Phase 2 — remaining chat (16 models, lighter test)

Non-reasoning. Test set = basic chat + Anthropic + streaming + vision/tools where the
card claims them. Most already PASS — mostly re-verify + ensure README/CLAUDE/test exist.

Models: astrosage, command-r-7b, crysta-llm, gemma-3-4b-it, geogalactica, glm-4-32b,
medgemma-27b-it, oceangpt-30b, openbiollm-70b, protgpt2, qwen25-coder-32b, qwen25-vl-3b,
qwen25-vl-7b, qwen25-vl-72b, qwen25-vl-72b-awq, tinyllama (tinyllama-1-1b).

Vision models (qwen25-vl-*, gemma-3-4b-it, medgemma-27b-it): image-input test uses
base64, not URL (cluster can't fetch external URLs).

---

## 5. Phase 3 — embeddings / rerank (~64 models)

All share **template C**. Don't deep-test all 64 — **sample-deep + spot-check:**

**Deep-test** (end-to-end `/v1/embeddings` + `/v1/rerank`): bge-m3, bge-reranker-v2-m3,
esm2-650m, scibert, dnabert-2, multilingual-e5-small, bge-small. Covers text / protein /
science / rerank / small-dim.

**Spot-check the rest:** returns documented embedding dim + right `type`/endpoint; card
on current schema. Embedding test shape:
```bash
curl -s $GW/v1/embeddings -d '{"model":"bge-m3","input":"hello world"}' | jq '.data[0].embedding | length'
```

**Authoring:** many embed cards are old-schema → write the template-C card to match.
Ensure every embed dir has README + CLAUDE + test. Skip-and-note the hard ones (§6).

---

## 6. Skip-and-note (do NOT fix — one-line note each)

| Model | Reason |
|---|---|
| astroclip | demo-only stub (lib not installed) |
| galileo | pip import conflict, stuck at load |
| labram | `ModuleNotFoundError: no models module` |
| uma-m | Meta-gated repo (401) — needs HF grant |
| mattergen | NO-ISVC — Knative rejects 1500s timeout (>600 max) |
| fourcastnet3 | demo only; real mode needs dedicated image |
| naturecode-earth | weights gated (403) |

---

## 7. Test barrage template (comprehensive — copy from `models/gpt-oss-120b/test.py`)

One `test.py` per model dir, run **inside the gateway pod** (§1 Step 3). The reference
battery is **33 checks** (gpt-oss: 30 PASS / 3 EXP / 0 FAIL). Trim per model:

- **WAKE** (1): first request retries through the gateway's `503 model_starting` cold-start
  (run with the model at scale-0 to exercise the wake path).
- **OpenAI** (~11): basic · streaming · temp=0 · temp+top_k · top_p · stop · system · tools ·
  large max_tokens · usage · resources.
- **Thinking** (reasoning models, 5–6): ON medium/high → `reasoning` field present; OFF
  (`reasoning_effort: none`) → absent + `completion_tokens` ≤ `off_max_tokens`; fake
  `thinking_token_budget` → reasoning present + capped; stream ON → reasoning deltas.
- **Meta-tasks** (3): OpenWebUI signals `"Generate a concise, 3-5 word title"` /
  `"Generate 1-3 broad tags"` / `"Suggest 3-5 relevant follow-up questions"` → short, no reasoning.
- **Vision guard** (text-only): image input → `400 vision_unsupported`.
- **Anthropic** (~10): basic · streaming · system · temp=0 · top_p+top_k · stop_sequences ·
  tools · max_tokens truncation · thinking ON (→ `thinking` block) / OFF (none).
- **Guardrails** (3): embed-via-Anthropic → `400`; bad model → `404`; catalog capabilities match card.

**Reasoning field:** read `reasoning` **or** `reasoning_content` (vLLM v0.20.2 uses `reasoning`).
**Scoring:** `PASS` / `EXP` / `FAIL` / `SKIP` / `ERR`. Done = only PASS + EXP remain.

---

## 8. Reasoning-card checklist (gateway thinking is LIVE)

The gateway now exposes/strips reasoning per-request (see "Gateway state"). For a managed-
thinking card, ensure:
- [ ] `param_translation.thinking.mode` = `budget` | `effort` | `toggle` (managed). always-on
      models (qwq/r1-distill) → `none` (reason in-template; not managed).
- [ ] `behavior.strips_thinking: false` (managed models expose reasoning when ON).
- [ ] `param_translation.thinking.off_max_tokens` set (default 2048) — the OFF token cap.
- [ ] `effort_aliases` + `default_effort`; `on`/`off` maps (effort) or `effort_map` (budget).
- [ ] `defaults.meta_tasks.*.thinking.enabled: false` — meta-tasks never burn thinking.
- [ ] Tests assert: ON → `reasoning` present (OpenAI) / `thinking` block (Anthropic);
      OFF → absent + `completion_tokens` ≤ `off_max_tokens`.

**Effort vs budget:** budget = native `thinking_token_budget` (phi-4); effort =
`reasoning_effort` (gpt-oss/qwen3/gemma-4); the gateway fakes a budget for effort models via
`thinking_token_budget` → `max_tokens` cap. See `gpt-oss-120b` (effort) + `phi-4-reasoning` (budget).

**Embeddings dual-protocol:** Anthropic has **no** embeddings API — embeddings are
OpenAI `/v1/embeddings` only. Dual OpenAI+Anthropic = chat only.

---

## 9. Tracking — what goes where

| File | Where | Holds |
|---|---|---|
| `aleph/models/MODEL-STATUS.md` | git | per-model status rows + chat matrix (source of truth) |
| `~/hami-cluster-test/LLM-MODEL-TRACKER.md` | local | campaign notes, research, gotchas |
| `aleph/CHANGELOG.md` | git | dated entry per model commit |
| `aleph/models/<m>/CLAUDE.md` + `README.md` | git | model context matching deploy |
| `aleph/models/<m>/test.py` | git | the saved per-model test plan |

---

## 10. Suggested order

1. **Phase 0** (§2) — done: knob, test-exec, marker, gaps enumerated. Remaining: `TEST.md`→`README` cleanup.
2. **Phase 1** — reasoning chat. ✅ gpt-oss-120b/20b DONE (reference). Next: qwen3-32b,
   qwen36-27b, gemma-4-26b-a4b, phi-4-reasoning, qwq-32b, … (11 remain) — re-verify against
   the live thinking gateway, align cards (`strips_thinking:false` + `off_max_tokens`), comprehensive test.
3. **Phase 2** — remaining chat (16).
4. **Phase 3** — embeddings (sample-deep 7, spot-check rest, author template-C cards).

Per model: **test as-is → (small fix only if needed) → author card/README/CLAUDE/test →
record → changelog → commit to main → scale to 0 (minReplicas 0, no stop).**

---

## 11. Embeddings pass — ACTIVE (2026-06-19)

Chat (29) + reasoning (13) are DONE + committed. This phase = the **~64 embedding/rerank**
dirs. **The models are already deployed and were tested when stood up** ("we got them
started") — this pass is **artifact authoring + dir cleanup + card enrichment + a verify
test**, NOT reconfiguration. Same posture as the chat sweep (§1): test/verify → author to
match → record → commit.

### Ground truth (recon 2026-06-19)
- 167 model dirs total. JSON `type` breakdown: **embedding 50 + embed 14 = 64**, reranker 1,
  classify 9, chat 29, forecast 21, segment 4, generate 4, detect 4, predict 3, … . **This
  phase = the 64 + the 1 reranker** (`bge-reranker-v2-m3`).
- **Template C lives inside `models/DETAILS-TEMPLATE-LLM.md`** (the file is misnamed — it
  holds A+B+C). Embedding card = Template C. Exemplar `bge-m3/details.yaml` is correct but
  **minimal** (omits `input_map`/`output_map`/`defaults`) — copy it, then **enrich**.
- **65 dirs inline a `PersistentVolumeClaim` inside `inferenceservice.yaml`; 57 of those have
  no `pvc.yaml` at all.** → all extract to a standalone RWX `pvc.yaml` (the "PVC mixed into
  the ISVC" cleanup; concentrated in embedding/science dirs).
- Embedding dirs almost universally **lack `test.py`/`README.md`/`CLAUDE.md`** → greenfield.

### The 64 dirs (sorted)
ablang2 · agront · aion · ancient-greek-bert · ankh · astroclip · astropt · bge-m3 ·
bge-small · biobert · biolinkbert · biomedbert · biomedbert-large · biomedclip ·
biomed-roberta · brainlm · caduceus · chemberta · clap · clay · clinicalbert ·
clinical-longformer · dino-vit-b8 · dnabert-2 · dnabert-s · earthpt · ernierna · esm1b ·
esm2-150m · esm2-35m · esm2-3b · esm2-650m · esmc-300m · gena-lm · gena-lm-large ·
geneformer · hyenadna · labram · leandojo · matscibert · medcpt-article · medcpt-query ·
molformer · multilingual-e5-small · naturecode-earth · nucleotide-transformer · omnigenome ·
prithvi-eo · prithvi-wxc · prokbert · prostt5 · pubmedbert · rita · rnabert · rnafm · rnamsm ·
sapbert · saprot-650m · satmae · scgpt · scibert · science-embed · scincl · specter2 ·
splicebert.  **Reranker:** bge-reranker-v2-m3.
(Some are vision/geospatial embeds — dino-vit-b8, prithvi-eo/wxc, satmae, biomedclip, clay,
astropt; `astroclip` is a demo-only stub → skip-and-note §6.)

### Per-model deliverables (embeddings)
1. **Verify** it serves through the gateway (wake-on-demand; first call may 503+ETA, retry).
   NOTE: embed models served by **TEI** may be intentionally always-on (`minReplicas: 1`,
   e.g. bge-m3) — **leave them as-is**; the `minReplicas: 0` rule is for scale-to-zero vLLM
   chat models, not TEI always-on embedders.
2. **Dir cleanup → flat files.** Ensure `details.yaml` · `pvc.yaml` · `inferenceservice.yaml` ·
   `test.py` · `README.md` · `CLAUDE.md`. **Split any inlined PVC** into `pvc.yaml`
   (`accessModes: [ReadWriteMany]`, `storageClassName: nfs-client`).
3. **Card from Template C — as many fields as possible.** Web-search the HF repo page → fill
   `catalog` (embedding_dimensions, max_input_tokens, pooling, params, precision, license,
   framework, domain, subdomain, tags) + `limits` (context_window, max_input_tokens) +
   `input_map`/`output_map` accurately. No leftover `CHANGEME`. Cite `source_url`.
4. **`test.py`** — the embed battery (below). One per dir, runs inside the gateway pod.
5. **`README.md` + `CLAUDE.md`** — overview + deploy/test notes.
6. **Record** (`MODEL-STATUS.md` row) + **commit** (changelog-first) to `main`.

### Embedding test battery (Template C)
Runs inside `deploy/model-gateway` (same pattern as chat, §1 Step 3). **Embedding** model:
- **dim** — `POST /v1/embeddings {model, input:"hello world"}` → `data[0].embedding` length
  == card `embedding_dimensions`; every element is a float.
- **batch** — `input: ["a","b","c"]` → 3 vectors, same dim, `usage.prompt_tokens` > 0.
- **model-echo** — response `.model` == served name (or `upstream_model_id`).
- **encoding_format** — `encoding_format:"base64"` → decodes to the right dim (skip if unsupported).
- **truncation** — input longer than `max_input_tokens` → truncated cleanly (no 500) or the
  documented behavior.
- **guardrails** — unknown model → 404; a chat request to an embed-only model → 400.
**Reranker:** `POST /v1/rerank {query, documents:[...], top_n}` → sorted `results` with
relevance scores, `len(results) == top_n`.

### Order (1-by-1, no subagents)
Exemplar first: **bge-m3** (TEI/CPU, known-good) — establish the card-enrichment + test +
dir/PVC pattern. Then deep-test: bge-reranker-v2-m3, esm2-650m, scibert, dnabert-2,
multilingual-e5-small, bge-small. Then spot-check the rest (dim + `type` + card-on-schema +
README/CLAUDE/test exist). Skip-and-note the hard ones (§6) + any NO-ISVC.
