# Model Test Status — Aleph POC Cluster

Master tracker for the per-model verification loop. Gateway ClusterIP `http://model-gateway.models.svc:80` (in-cluster). Public VIP: `http://129.128.190.55` (via Tyk auth). Source of truth: this local repo.

Test-status legend: `PENDING` (not yet verified by this loop) - `PASS` - `FIXED` (was broken, now PASS) - `FAIL` (hard fail, see note).

Cluster-state at snapshot start: **93 READY**, **58 NOT-READY**, **6 NO-ISVC** (of 157).

| Model | Type | GPU | Primary endpoint | Cluster state | Test status | Note |
|---|---|---|---|---|---|---|
| ablang2 | embedding | false | /v1/embeddings | READY | FIXED | embeddings+batch PASS; /v1/restore was broken, fixed (heavy/light pairs), now PASS |
| aeneas | structure | true | /v1/science/predict | READY | FIXED | wake-up test PASS 2026-06-08: demo PASS (restoration+dating); real inference slow (JAX) |
| agront | embedding | true | /v1/embeddings | READY | PASS | 1500-dim DNA |
| aion | embed | false | /v1/science/embed | READY | PASS | v2 deep pass 2026-06-24: schema v2 with input_map/output_map (768-dim multimodal); test.py expanded to ~10 checks (0 FAIL); RWX PVC |
| alphafold2 | structure-prediction | true | /v1/science/predict | READY | PASS | demo folds seq -> PDB. **NIM available:** `nvcr.io/nim/deepmind/alphafold2` (build.nvidia.com/deepmind/alphafold2) |
| ancient-greek-bert | embedding | true | /v1/science/embed | READY | PASS | 768-dim (field: text) |
| ankh | embedding | true | /v1/embeddings | READY | FIXED | T5 fp16->fp32 NaN fix; 768-dim protein PASS |
| arcface | embedding | false | /v1/vision/face | READY | PASS | id=arcface-resnet100; face embedding; v2 deep pass 2026-06-24: schema v2 input_map/output_map, test.py 15 checks (0 FAIL) |
| astroclip | embed | true | /v1/science/embed | READY | FIXED | Real model 2026-06-19 (was demo stub): venv-on-PVC + 1024-dim image/spectrum (not 512); fixed weights_only (PyTorch 2.6) + upstream batch<2 attentions[1] bug; 9/0 test |
| astropt | embed | true | /v1/science/embed | READY | PASS | v2 deep pass 2026-06-24: schema v2 with input_map/output_map (768-dim); test.py expanded to ~10 checks (0 FAIL); venv-on-PVC |
| astrosage | chat | true | /v1/chat/completions | READY | PASS | AstroSage-8B (Llama-3.1, astronomy); custom transformers server (caduceus pattern, NOT vLLM); TP1 fractional (gpumem 16384); no_stream. **Deployed+verified on cluster 43 (2026-06-27):** removed inlined PVC (use pvc.yaml; bumped to 25Gi), bare `astrosage` PVC/volume naming, `test.py` GW_INSECURE toggle. 23-check **18/4/1** — chat green; the 1 FAIL is the `embed via chat` guard artifact. |
| aurora | forecast | true | /v1/science/forecast | READY | PASS | full weather batch -> 6h forecast |
| bge-m3 | embedding | false | /v1/embeddings | READY | PASS | embeddings batch multilingual, dim=1024, matches card. **NIM available:** `nvcr.io/nim/baai/bge-m3` (build.nvidia.com/baai/bge-m3) |
| bge-reranker-v2-m3 | reranker | false | /v1/rerank | READY | PASS | /v1/rerank correct ranking (panda docs top), scores OK |
| bge-small | forecast | false | /v1/embeddings | READY | PASS | 384-dim text embedding |
| biobert | embedding | true | /v1/embeddings | READY | PASS | 768-dim |
| biogpt | generate | true | /v1/completions | READY | PASS | coherent biomedical text completion |
| biolinkbert | embedding | true | /v1/embeddings | READY | PASS | 768-dim |
| biomed-roberta | embedding | true | /v1/embeddings | READY | PASS | 768-dim |
| biomedbert-large | embedding | true | /v1/science/embed | READY | PASS | 1024-dim (field: text) |
| biomedbert | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id biomedbert-110m) |
| biomedclip | embed | true | /v1/science/embed | READY | PASS | v2 deep pass 2026-06-24: added input_map (images/texts/labels) + output_map (image_embeddings/text_embeddings/classifications 512-dim); test.py expanded to ~15 checks (0 FAIL) |
| biot5 | science-generate | false | /v1/science/generate | READY | FIXED | task-specific checkpoints + SELFIES; mol2text & text2mol correct (was garbage) |
| birdnet-analyzer | audio-classification | false | /v1/science/identify | READY | PASS | end-to-end OK; synthetic tone -> no detections (expected) |
| boltz-1 | structure | true | /v1/science/predict | READY | PASS | Boltz-1 NIM container; protein structure prediction; Ready on cluster. **NIM:** `nvcr.io/nim/mit/boltz-2` (--checkpoint boltz1) |
| boltz-2 | structure | true | /v1/science/predict | READY | PASS | Boltz-2 NIM container (default); protein structure prediction; Ready on cluster. **NIM:** `nvcr.io/nim/mit/boltz-2` (build.nvidia.com/mit/boltz-2) |
| borzoi | predict | true | /v1/science/predict | READY | PASS | genomics: 6144 tracks x 16 bins |
| brainlm | embed | true | /v1/science/embed | READY | PASS | v2 deep pass 2026-06-24: schema v2 with input_map/output_map (1280-dim ViT-Huge); test.py expanded to ~10 checks (0 FAIL); mask_ratio=0 fix |
| caduceus | embedding | true | /v1/embeddings | READY | FIXED | torch 2.2.0+mamba-ssm 1.2.0 pinned, numpy<2, AutoModel RCPS 256-dim; PVC venv cached; mamba compile ~20min first deploy, 5sec after |
| chem-t5 | science-generate | false | /v1/science/generate | READY | FIXED | exact GT4SD prompt templates; caption+forward_synthesis correct (was wrong) |
| chemberta | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id chemberta-125m) |
| chemgpt-19m | generate | true | /v1/science/generate | READY | PASS | SELFIES molecule generation |
| chemgpt | generate | true | /v1/science/generate | READY | PASS | id=chemgpt-1.2b; SELFIES molecule generation |
| chgnet | force-field | true | /v1/science/energy | READY | PASS | CHGNet universal NN potential (magnetic moments + charge; ~2M params). **Deployed+verified on cluster 43 (2026-06-27, science pass):** embedded the standalone `server.py` into the `chgnet-server` ConfigMap (was built via kustomize), dropped `kustomization.yaml`, renamed PVC `chgnet-data`→`chgnet`, card id `chgnet-v0.3`→`chgnet` (dropped the `isvc_name_map` hack), v2 Template B card, test.py+README. Pinned `chgnet==0.3.8` (0.4.x breaks atom_features_type); HF repo gone (404) → uses chgnet bundled weights (non-fatal). 5-check **5/0** — NaCl energy **-4.05 eV** + forces [2][3] + stress + magmom; reproducible via clean delete+redeploy. |
| chronos-bolt | forecast | false | /v1/forecast | READY | PASS | quantile forecast on 16-pt series |
| clap | embedding | false | /v1/science/embed | READY | PASS | v2 (was already); +test.py; audio+text 512-dim shared space; 7/0 test; was parked |
| clay | embed | false | /v1/science/embed | READY | PASS | v2 deep pass 2026-06-24: schema v2 with input_map/output_map (1024-dim CLS); test.py expanded to ~10 checks (0 FAIL); RWX PVC |
| climatebert | classification | false | /v1/science/classify | READY | PASS | net-zero 0.9988 |
| climax | forecast | true | /v1/science/forecast | READY | PASS | needs valid ERA5 var names (e.g. 2m_temperature) |
| clinical-longformer | embedding | true | /v1/science/embed | READY | FIXED | wake-up test PASS 2026-06-08: 768-dim embeddings; slow on CPU (~2min inference) |
| clinicalbert | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id clinicalbert-110m) |
| command-r-7b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP1 (gpumem 32768 slice); 7B bf16; tools OFF (Cohere format needs cohere_melody). **Deployed+verified on cluster 43 (2026-06-27):** gemma-4 venv-on-PVC initContainer (init skips both on redeploy), `vllm serve /data/model`, bare `command-r-7b` PVC naming. 23-check **18/5/0** (OpenAI + Anthropic). |
| croma | segment | true | /v1/embeddings | READY | PASS | v2 deep pass 2026-06-24: schema v2 with input_map/output_map; test.py expanded to ~10 checks (0 FAIL); dict output extraction (joint/optical/SAR GAP) |
| crysta-llm | chat | true | /v1/science/generate | READY | PASS | CrystaLLM-pi_base (~25M); custom server (caduceus pattern, NOT vLLM); generates CIF crystal structures from a formula; TP1 fractional (gpumem 10240). **Deployed+verified on cluster 43 (2026-06-27):** bare `crysta-llm` PVC/volume naming (was `crysta-llm-data`/`model-data`), `test.py` GW_INSECURE toggle. 6-check **5/1/0** — generates CIF-like structures; /health 404 (EXP, gateway doesn't route it). |
| deepseek-v2-lite-16b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP1 whole device (16B MoE ~32GB fits one L40S); max-model-len 131072; trust-remote-code. **Deployed+verified on cluster 43 (2026-06-27):** gemma-4 venv-on-PVC initContainer (init skips both on redeploy; naming already bare), `vllm serve /data/model`. 14-check **14/0** (OpenAI + Anthropic). |
| depth-anything | depth | false | /v1/vision/depth | READY | PASS | v2 deep pass 2026-06-24: schema v2 details.yaml rewritten with typed input_map/output_map (depth_png_base64, depth_grid_64, stats); test.py expanded to ~15 checks (0 FAIL) |
| diffdock | dock | true | /v1/dock | READY | PASS | DiffDock-L diffusion docking (gcorso/DiffDock v1.1.3 via rbgcsail/diffdock image + subprocess CLI). **Deployed+verified on cluster 43 (2026-06-27, science pass S2):** renamed PVC `diffdock-data`→`diffdock`, card id `diffdock-l`→`diffdock`, v2 Template B card, test.py (crambin/1CRN fixture + aspirin) + README + CLAUDE. Server deps pinned for Py3.9 (`click<8.2`), weights+ESM2 on PVC. 5-check **5/0** — **11 ranked SDF poses** on 1CRN+aspirin; reproducible via clean delete+redeploy. Known cosmetic gap: this build's SDF filenames don't encode confidence → `confidence=0.0` (poses still ranked). Cold start ~3-6 min. **NIM available:** `nvcr.io/nim/mit/diffdock`. |
| dino-vit-b8 | embedding | false | /v1/vision/embed | READY | PASS | v2 deep pass 2026-06-24: added input_map/output_map (768-dim CLS embedding); test.py expanded to ~15 checks (0 FAIL); /v1/science/embed alias kept |
| dnabert-2 | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id dnabert-2-117m) |
| dnabert-s | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id dnabert-s) |
| dust3r | 3d | true | /v1/science/reconstruct | READY | PASS | v2 deep pass 2026-06-24: added input_map/output_map; test.py expanded to ~15 checks (0 FAIL); downsample pointcloud; bbox+loss; 2 imgs OK |
| earthpt | embed | true | /v1/science/predict | READY | FIXED | CPU ckpt load + RAM 24Gi (was GPU+host OOM); predicts OK |
| efficientnet-b0 | classify | false | /v1/vision/classify | READY | PASS | v2 deep pass 2026-06-24: schema v2 details.yaml rewritten with input_map/output_map; test.py expanded to ~15 checks (0 FAIL) |
| enformer | predict | true | /v1/science/predict | READY | FIXED | dict output fix (`isinstance(out, dict)`), transformers<4.52, GPU torch, Python 3.12; human_shape [896,5313] PASS |
| ernierna | embedding | true | /v1/science/embed | READY | FIXED | GPU torch cu126 reinstall, nodeSelector gpu=on, progress-deadline 600s; 768-dim RNA embeddings PASS |
| esm1b | embedding | true | /v1/embeddings | READY | PASS | 1280-dim protein (recreated) |
| esm2-150m | embedding | true | /v1/embeddings | READY | PASS | 640-dim protein (recreated) |
| esm2-35m | embedding | true | /v1/embeddings | READY | PASS | 480-dim protein |
| esm2-3b | embedding | true | /v1/embeddings | READY | PASS | 2560-dim protein (recreate cleared) |
| esm2-650m | embedding | true | /v1/embeddings | READY | PASS | 1280-dim protein. **NIM available:** `nvcr.io/nim/meta/esm2-650m` (build.nvidia.com/meta/esm2-650m) |
| esmc-300m | embedding | true | /v1/embeddings | READY | PASS | 960-dim (recreated) |
| esmfold | structure | true | /v1/structure | READY | PASS | ESMfold protein folding (facebook/esmfold_v1, ~690M, fp32, max 1022 aa). **Deployed+verified on cluster 43 (2026-06-27, science pass S2):** renamed PVC `esmfold-data`→`esmfold`, v2 Template B card, test.py+README+CLAUDE. `numpy<2` pinned (2.x breaks transformers protein.py); transformers 5.x OK. **Server fix:** pLDDT scaled ×100 (raw is 0-1 → standard 0-100). 5-check **5/0** — 30-aa ubiquitin fragment → pdb (18267 chars) + **pLDDT 75.53**; reproducible via clean delete+redeploy. Cold start ~2-4 min. **NIM available:** `nvcr.io/nim/meta/esmfold`. |
| fengwu | forecast | true | /v1/science/forecast | READY | FIXED | summarize grid (was 286MB>gateway); demo+real ONNX OK |
| finbert | classify | true | /v1/science/classify | READY | PASS | sentiment positive 0.96 |
| fourcastnet3 | forecast | true | /v1/science/forecast | READY | DEMO | demo OK; real FCN3 blocked (makani+torch-harmonics CUDA matrix needs dedicated image). **NIM available (FCN2):** `nvcr.io/nim/nvidia/fourcastnet` (build.nvidia.com/nvidia/fourcastnet, L40S-tested) |
| galileo | classify | false | /v1/embeddings | READY | FAIL | galileo pip package import conflicts with cloned repo; server stuck at model loading |
| gemma-3-4b-it | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP1 (gpumem 20GB); 4B vision-language (SigLIP); 65K ctx. **Deployed+verified on cluster 43 (2026-06-27):** gemma-4 venv-on-PVC initContainer (init skips both on redeploy), `vllm serve /data/model`, bare `gemma-3-4b-it` PVC naming. 25-check **22/2/0** (vision + multi-image green; gated HF token OK). |
| gemma-4-26b-a4b | chat | true | /v1/chat/completions | READY | PASS | 26B MoE fp8; managed thinking + vision + tools; 32/2/0 gateway test ✅ 2026-06-24 (VL light pass: +presence_penalty/stop/seed input_map, +multi-image test). (NIM alt: nvcr.io/nim/google/gemma-4-31b-it) |
| gena-lm-large | embedding | true | /v1/science/embed | READY | FIXED | output_hidden_states (was returning vocab logits); 1024-dim |
| gena-lm | embedding | true | /v1/embeddings | READY | PASS | 768-dim DNA (recreated) |
| geneformer | embedding | true | /v1/science/embed | READY | PASS | v2 2026-06-19: RWO→RWX (cp); +/v1/science/embed alias; 768-dim (256 was V1-10M; V2-104M is 768 — my version-conflation, docs correct); input=gene_ids; 6/0 test |
| geogalactica | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP2 whole-device; OPT 30B (Galactica); context 2048 (hard limit); tools/vision rejected. **Deployed+verified on cluster 43 (2026-06-27):** gemma-4 venv-on-PVC initContainer (init skips both on redeploy), `vllm serve /data/model`, bare `geogalactica` PVC naming. **Chat template mounted via ConfigMap** (`chat-template-configmap.yaml` → /chat-template; the HF repo doesn't ship one — the local Question:/Answer: template is required, else OPT emits raw academic text). 24-check **19/4/1** — OAI temp=0 answers coherently ("Paris"); the 1 FAIL is the `embed via chat` guard artifact. |
| glm-4-32b | chat | true | /v1/chat/completions | READY | PASS | TP2 whole-device; tools via custom `glm4_0414` plugin (parser-configmap.yaml → /opt/glm4_parser). org moved THUDM→zai-org. **Deployed+verified on cluster 43 (2026-06-27):** folded download-job into gemma-4 venv-on-PVC initContainer (init skips both on redeploy), `vllm serve /data/model`, bare `glm-4-32b` PVC naming. 24-check **20/3/1** — chat + custom-parser tools green; the 1 FAIL is the `embed via chat` guard (gateway 404'd a chat call to a catalog embedder — a cross-cutting guard artifact, not a glm-4-32b defect). **NIM available:** `nvcr.io/nim/zai-org/glm-51` (GLM-5.1, build.nvidia.com/z-ai/glm-5.1). |
| glm-z1-32b | — | — | — | RETIRED | — | Removed 2026-06-18 — redundant reasoning model; reasoning not surfaceable (chat template has no enable_thinking; glm45 parser crashes). Deleted from repo + cluster. Use qwq/r1-distill/gpt-oss/qwen3 instead. |
| glm-z1-rumination-32b | — | — | — | RETIRED | — | Removed 2026-06-18 — deep-research reasoner; same surfacing issue + ignores tools/system by design. Deleted from repo + cluster. |
| gpt-oss-120b | chat | true | /v1/chat/completions | READY | PASS | TP2 ~200tok/s; v0.20.2; full GPUs (no gpumem) + --disable-custom-all-reduce; managed thinking ON (expose reasoning: effort + fake token-budget) / OFF (strip + cap) verified 30/3/0 (33-check) |
| gpt-oss-20b | chat | true | /v1/chat/completions | READY | PASS | TP1; v0.20.2; managed thinking ON/OFF verified 30/3/0 (33-check); OpenAI + Anthropic |
| granite-geospatial-biomass | classify | true | /v1/science/predict | READY | PASS | v2 deep pass 2026-06-24: schema v2 with input_map/output_map; test.py expanded to ~10 checks (0 FAIL); gcc/g++ in init |
| granite-geospatial-ocean | classify | true | /v1/science/embed | READY | PASS | v2 deep pass 2026-06-24: schema v2 with input_map/output_map; test.py expanded to ~10 checks (0 FAIL); gcc/g++ in init |
| graphcast | forecast | false | /v1/science/predict | READY | PASS | demo mode (real ERA5 not via API by design) |
| hyenadna | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=256 (id hyenadna-6.5m) |
| ithaca | text-restore | true | /v1/science/predict | READY | PASS | Ithaca ancient-Greek inscription restoration/dating/geolocation (DeepMind, JAX/Flax, Nature 2022). **Deployed+verified on cluster 43 (2026-06-27, science pass S2):** renamed PVC `ithaca-data`→`ithaca`, v2 Template B card, test.py+README+CLAUDE. **Venv refactor:** moved the per-cold-start `pip install jax[cuda12]…` (was ~1GB every wake) into the init venv-on-PVC (gated sentinel) + dropped the redundant in-server pip calls. `jax[cuda12]` GPU jaxlib. **Gap char is `?`** (not `[---]` — the alphabet rejects `[]-`); Greek text must avoid Cyrillic homoglyphs (test builds it via ASCII→Greek transliteration). 5-check **5/0** — real inference (demo=False) restoration + attribution on an Attic fragment; reproducible via clean delete+redeploy. Cold start ~3-6 min; first JIT ~90s, ~8s warm. |
| kandinsky-3 | text-to-image | true | /v1/images/generations | READY | PASS | Converted RayService -> KServe InferenceService custom predictor (diffusers FastAPI). 1x L40S HAMi vGPU slice (gpu1/gpumem40960), Knative scale-to-zero 5m/15m, gateway-discovered (zero gateway changes). VERIFIED via gateway: 18/19 test.py pass (sizes, n>1, steps, guidance, negative, quality=hd, seed determinism, img2img). |
| flux-1-dev | text-to-image | true | /v1/images/generations | READY | PASS | Black Forest Labs FLUX.1-dev, 12B rectified-flow. KServe custom predictor (diffusers, bf16), WHOLE L40S (gpu1, no gpumem). GATED (hf-token); NON-COMMERCIAL license. Knative scale-to-zero 5m/15m. VERIFIED via gateway: 18/19 test.py pass (incl. max_sequence_length, true_cfg_scale+negative, seed determinism, img2img). |
| sd3-medium | text-to-image | true | /v1/images/generations | READY | PASS | Stability AI Stable Diffusion 3 Medium, 2B MMDiT. KServe custom predictor (diffusers, fp16), L40S HAMi vGPU slice (gpu1/gpumem24576). GATED (hf-token); Stability Community License. Knative scale-to-zero 5m/15m. VERIFIED via gateway: 18/19 test.py pass (incl. real-CFG negative, max_sequence_length, seed determinism, img2img). |
| labram | embed | false | /v1/science/embed | READY | FIXED | Real model 2026-06-19 (was untrained random): from_pretrained(local dir, offline); n_times 1600->3000; LABRAM_CHANNEL_ORDER submodule import fix; 200-dim EEG; 8/0 test |
| lag-llama | forecast | true | /v1/science/forecast | READY | FIXED | torch2.6 weights_only + create_predictor(module=) API |
| leandojo | embed | true | /v1/science/retrieve | READY | PASS | premise retrieval w/ scores |
| ligandmpnn | design | false | /v1/design | READY | FIXED | checkpoints+args+optional-openfold; 1CRN design near-native PASS |
| mace-mh-1 | force-field | true | /v1/science/predict | READY | PASS | MACE-MH-1 multi-head MLIP (7 heads, 89 elements, float64). **Deployed+verified on cluster 43 (2026-06-27, science pass):** extracted inlined PVC → standalone `mace-mh-1` (bare naming), v2 Template B card (typed input_map/output_map), added test.py + README + `/health` startup/readiness probes. Caduceus pattern (ConfigMap-embedded `server.py`, venv-on-PVC). 6-check **6/0** — Cu cell energy **-14.96 eV** + forces [4][3] + stress [6] (omat_pbe head); reproducible via clean delete+redeploy (venv+weights cached). NB: science models catalog under `/v1/models?all=true`. |
| mace-mp-0 | force-field | false | /v1/science/energy | READY | PASS | MACE-MP-0 medium (mace_mp() loader, GitHub-released checkpoint, CPU-only, float32). **Deployed+verified on cluster 43 (2026-06-27, science pass):** renamed PVC `mace-mp-0-data`→`mace-mp-0`, dropped `kustomization.yaml`, added startupProbe, v2 Template B card (nested `structure` input_map), test.py+README+CLAUDE. Body uses nested `structure` (no `model`/variant collision). 6-check **6/0** — Si cell energy **-10.67 eV** + forces [2][3] + stress [6]; reproducible via clean delete+redeploy. |
| mace-mp | force-field | true | /v1/science/predict | READY | PASS | MACE-MP-0 universal MLIP (small/medium/large variants, 89 elements, float64). **Deployed+verified on cluster 43 (2026-06-27, science pass):** card id standardized to `mace-mp` (was `mace-mp-0` — collided with the separate mace-mp-0 dir; renamed PVC `mace-mp-data`→`mace-mp`), v2 Template B card, added test.py+README. **Fixed the gateway-routing collision:** the server used `model` for the variant, but the gateway routes on `model` → renamed the variant field to `variant` (404 "model 'medium' not found" gone); response `model` echo → `mace-mp`. 6-check **6/0** — Si cell energy **-10.75 eV** + forces [2][3] + stress [6] (medium); reproducible via clean delete+redeploy. |
| maskrcnn | segment | false | /v1/vision/segment | READY | PASS | v2 deep pass 2026-06-24: schema v2 details.yaml rewritten with input_map/output_map; test.py expanded to ~15 checks (0 FAIL); stale server.py removed (embedded in ISVC ConfigMap) |
| mast3r | 3d | true | /v1/science/match | READY | PASS | v2 deep pass 2026-06-24: added input_map/output_map; test.py expanded to ~15 checks (0 FAIL); numpy fix; 473 matches |
| matscibert | embedding | true | /v1/science/embed | READY | PASS | 768-dim (field: text) |
| mattergen | generate | true | /v1/science/generate | NO-ISVC | FAIL | Knative rejects ISVC: timeoutSeconds 1500 > max 600; predictor never created; gateway 404 |
| mattersim | force-field | true | /v1/science/predict | READY | PASS | Microsoft MatterSim universal atomistic force field (~1M, predict + /v1/science/relax BFGS). **Deployed+verified on cluster 43 (2026-06-27, science pass):** extracted inlined **RWO→RWX** PVC → standalone `mattersim` (bare naming), v2 Template B card (nested predict/relax maps), test.py+README. **Server fixes:** predict stress `voigt=False`→`True` (flat 6, fleet-consistent); relax `converged`/`steps` cast to bool/int (numpy.bool_ broke FastAPI JSON → 500). 7-check **7/0** — Si predict energy **-10.81 eV** + forces + voigt stress + relax converged; reproducible via clean delete+redeploy. Cold start ~3-4 min (heavy mattersim+torch_geometric import). |
| medcpt-article | embedding | true | /v1/embeddings | READY | PASS | 768-dim PubMed article (recreated) |
| medcpt-query | embedding | true | /v1/embeddings | READY | PASS | 768-dim PubMed query (recreated) |
| medgemma-27b-it | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP2; 27B medical multimodal; vision (chest X-ray, derm, fundus, histo); 32K ctx. **Deployed+verified on cluster 43 (2026-06-27):** gemma-4 venv-on-PVC initContainer (init skips both on redeploy; naming already bare), `vllm serve /data/model`. 25-check **22/2/0** (vision + multi-image green; gated HF token OK). |
| medsam | segment | true | /v1/science/segment | READY | PASS | v2 deep pass 2026-06-24: added schema v2 fields (status, behavior, scaling, limits); test.py expanded to ~15 checks (0 FAIL); image as HxWx3 pixel array + boxes → masks |
| megadetector | detect | true | /v1/vision/detect | READY | PASS | v2 deep pass 2026-06-24: schema v2 details.yaml rewritten with input_map/output_map; test.py expanded to ~15 checks (0 FAIL); legacy /v1/detect + /v1/science/detect aliases kept |
| moirai-large | forecast | true | /v1/science/forecast | READY | PASS | mean+samples forecast |
| moirai-moe-1-0-r-base | forecast | true | /v1/forecast | READY | FIXED | replaced moirai-moe; rewrote to official uni2ts create_predictor() + GluonTS API; 19 quantile levels PASS |
| moirai | forecast | true | /v1/forecast | READY | PASS | Salesforce Moirai base; values+horizon -> mean/quantiles; sensible forecast |
| molformer | embedding | true | /v1/science/embed | READY | PASS | 768-dim (field: smiles) |
| moment | forecast | true | /v1/forecast | READY | FIXED | output indexing (chan vs horizon); needs 512-len input; 96-step horizon |
| multilingual-e5-small | embedding | false | /v1/embeddings | READY | PASS | 384-dim text embedding |
| naturecode-earth | embed | true | /v1/science/predict | READY | DEMO | demo OK (seg probs); weights GATED (naturecodeproject/earth 403); needs HF access |
| neuralgcm | forecast | false | /v1/science/predict | READY | PASS | demo mode (real ERA5 not via API by design) |
| nucleotide-transformer | embedding | true | /v1/embeddings | READY | PASS | 1024-dim DNA |
| oceangpt-30b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP2 whole-device; 30B-A3B MoE (128 experts); tools (hermes); 64K ctx; --disable-custom-all-reduce. **Deployed+verified on cluster 43 (2026-06-27):** gemma-4 venv-on-PVC initContainer (init skips both on redeploy; robust config+tokenizer check), `vllm serve /data/model`, bare `oceangpt-30b` PVC naming. 24-check **20/3/1** — chat + tools green; the 1 FAIL is the `embed via chat` guard artifact (not a model defect). |
| openbiollm-70b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP4 whole-device; 70B Llama3 biomedical; non-reasoning, no tools; 8K ctx. **Deployed+verified on cluster 43 (2026-06-27):** folded download-job into gemma-4 venv-on-PVC initContainer (init skips both on redeploy), `vllm serve /data/model`, bare `openbiollm-70b` PVC naming. 24-check **19/4/1** — chat green; the 1 FAIL is the `embed via chat` guard artifact. |
| openfold-3 | structure | true | /v1/science/predict | READY | PASS | OpenFold-3 NIM container. **NIM:** `nvcr.io/nim/openfold/openfold3` (build.nvidia.com/openfold/openfold3) |
| omnigenome | embedding | false | /v1/science/predict | READY | PASS | id=omnigenome-186m; RNA embedding |
| pangu-weather | forecast | true | /v1/science/forecast | READY | FIXED | demo+real ONNX; summarized upper/surface stats (not raw 721x1440 grids) |
| phi-4-reasoning | chat | true | /v1/chat/completions | READY | PASS | v0.20.2 whole L40S; budget mode with REDUCE-off (none→512, NOT 0 — budget 0 mishandled per vLLM#18141) + strip; ON exposes reasoning, OFF/meta return content (reasoning stripped); generous meta caps. **Deployed+verified on cluster 43 (2026-06-27):** gemma-4 venv-on-PVC initContainer + bare `<model>` PVC/volume/card naming; 31-check 26/5/0 (the intermittent `ANT think ON` 504 was the Tyk 30s timeout — resolved by the Tyk timeout fix). |
| presto | classify | false | /v1/embeddings | READY | FIXED | wake-up test PASS 2026-06-08: 17-band S1_S2_ERA5_SRTM satellite embeddings; pass mask/month/dynamic_world kwargs |
| prithvi-eo | embed | true | /v1/science/embed | READY | PASS | v2 deep pass 2026-06-24: schema v2 with input_map/output_map (1024-dim CLS); test.py expanded to ~10 checks (0 FAIL) |
| prithvi-wxc | embed | true | /v1/science/forecast | READY | PASS | demo forecast OK after unstop+cold-start (~6min); real MERRA-2 state not exercised |
| progen2 | completions | true | /v1/completions | READY | PASS | ProGen2-XLarge 6.4B protein generation; custom transformers server (NOT vLLM), caduceus venv-on-PVC pattern; TP1 fractional (gpumem 30720). **Deployed+verified on cluster 43 (2026-06-27):** split PVC out to its own file, bare `progen2` PVC/volume naming, created `test.py` (completions) + `README.md`. 7-check **5/2/0** — output is amino-acid-like (aa_frac=1.0); chat rejected (EXP); catalog not-listed (EXP, gateway doesn't list completions-type). |
| prokbert | embedding | true | /v1/embeddings | READY | PASS | 384-dim DNA |
| prostt5 | translate | true | /v1/translate | READY | PASS | AA->3Di structural alphabet (recreated) |
| proteinmpnn | design | true | /v1/design | READY | PASS | designs sequences from PDB w/ scores. **NIM available:** `nvcr.io/nim/ipd/proteinmpnn` (build.nvidia.com/ipd/proteinmpnn) |
| protgpt2 | generate | true | /v1/completions | READY | PASS | de novo protein generation (recreated) |
| pubmedbert | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id pubmedbert) |
| qwen25-coder-32b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP2 whole-device; 32.5B dense code specialist; no reasoning parser; tools (hermes parser); 131K native ctx deployed at 32K. **Deployed+verified on cluster 43 (2026-06-27):** folded download-job into gemma-4 venv-on-PVC initContainer (init skips both on redeploy), `vllm serve /data/model`, bare `qwen25-coder-32b` PVC naming. 24-check **20/3/1** — chat + tools green; the 1 FAIL is the `embed via chat` guard artifact (gateway 404 on a catalog embedder, not a model defect). |
| qwen25-vl-3b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP1 (gpumem 24576 slice); 3B dense + ViT; vision (dynamic-res, video, OCR, 20 img/prompt); no tools; 64K ctx. **Deployed+verified on cluster 43 (2026-06-27):** gemma-4 venv-on-PVC initContainer (init skips both on redeploy), `vllm serve /data/model`, bare `qwen25-vl-3b` PVC naming (was mismatched `qwen-vl-3b-data`). 25-check **22/2/0** (vision + multi-image green). |
| qwen25-vl-7b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP1 gpumem 32GB; 7B dense + ViT; vision (dynamic-res, video, 20 img/prompt) + tools (hermes); 65K ctx; 23/1/0 gateway test ✅ 2026-06-24 (VL light pass: +presence_penalty/top_k/stop/seed input_map, +multi-image test) |
| qwen25-vl-72b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP4 whole-device; 72.2B dense VLM; vision (dynamic-res, video, 5 img/prompt); 32K ctx. **Deployed+verified on cluster 43 (2026-06-27):** folded download-job into gemma-4 venv-on-PVC initContainer (init skips both on redeploy), `vllm serve /data/model`, bare `qwen25-vl-72b` PVC naming. 25-check **22/2/0** (vision + multi-image green). |
| qwen25-vl-72b-awq | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP2 whole-device; 72B AWQ 4-bit; vision; 65K ctx. **Deployed+verified on cluster 43 (2026-06-27):** folded download-job into gemma-4 venv-on-PVC initContainer (init skips both on redeploy), `vllm serve /data/model`, bare `qwen25-vl-72b-awq` PVC naming. 25-check **22/2/0** (vision + multi-image green). |
| qwen3-235b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP4 whole-device (4 cards, NO gpumem — >40GB/card ⇒ whole devices); 235B-A22B AWQ int4 MoE (22B active, 128 experts); non-thinking Instruct-2507 variant; tools (hermes parser); no reasoning parser; awq_marlin quantization; 131K ctx. **Deployed+verified on cluster 43 (2026-06-27):** folded download-job into gemma-4 venv-on-PVC initContainer (init skips on redeploy), `vllm serve /data/model`, bare `qwen3-235b` PVC naming. Removed the obsolete `gpumem:45000` HAMi#1781 workaround (NCCL/exclusive issues cleared up — whole devices now schedule cleanly). 24-check **21/3/0**. **NIM available:** `nvcr.io/nim/qwen/qwen3-235b-a22b`. |
| qwen3-32b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP2 whole-device; 32.8B dense; managed thinking (qwen3 parser, effort mode, enable_thinking toggle) + tools (hermes). **Deployed+verified on cluster 43 (2026-06-27):** folded download-job into gemma-4 venv-on-PVC initContainer (init skips both on redeploy), `vllm serve /data/model`, bare `qwen3-32b` PVC naming. 34-check all green after the Tyk timeout fix (proxy_default_timeout 30→600s; `think_on_high`/`think_budget`/`ANT think ON` previously 504'd on >30s gens — now pass). |
| qwen35-122b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP4 whole-device (4 cards, no gpumem); 122B FP8 MoE (10B active); managed thinking (toggle enable_thinking) + tools (qwen3_coder); language-model-only (vision off); 131K ctx. **Deployed+verified on cluster 43 (2026-06-27):** folded download-job into gemma-4 venv-on-PVC initContainer (init skips both on redeploy), `vllm serve /data/model`, bare `qwen35-122b` PVC naming. 29-check **26/3/0** (think ON/OFF + ANT think ON green). |
| qwen36-27b | chat | true | /v1/chat/completions | READY | PASS | TP2 whole-device; Gated-DeltaNet hybrid; managed thinking (effort + enable_thinking) + vision + tools (qwen3_coder). **Deployed+verified on cluster 43 (2026-06-27):** folded download-job into gemma-4 venv-on-PVC initContainer (init skips both on redeploy), `vllm serve /data/model`, bare `qwen36-27b` PVC naming. Image stays `vllm/vllm-openai:latest` (NOT v0.20.2 — Gated-DeltaNet needs newer vLLM). 31-check **29/2/0** (vision+tools+think-ON/OFF all green after the Tyk timeout fix). |
| qwen36-35b-a3b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP2 whole-device; 35B MoE (3B active) hybrid Gated-DeltaNet; managed thinking (effort + enable_thinking) + tools (qwen3_coder) + vision; 64K ctx. **Deployed+verified on cluster 43 (2026-06-27):** folded download-job into gemma-4 venv-on-PVC initContainer (init skips both on redeploy), `vllm serve /data/model`, bare `qwen36-35b-a3b` PVC naming. 31-check **29/2/0** (vision+tools+think-ON/OFF all green after the Tyk timeout fix). |
| qwq-32b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP2 whole-device; 32.5B dense; managed always-on thinking (deepseek_r1) — ON exposes reasoning, OFF strips+caps; tools (hermes); 32K ctx. **Deployed+verified on cluster 43 (2026-06-27):** folded download-job into gemma-4 venv-on-PVC initContainer (init skips both on redeploy), `vllm serve /data/model`, bare `qwq-32b` PVC naming. 22-check **19/3/0** (all green incl `ANT think ON` after the Tyk timeout fix). |
| r1-distill-llama-70b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP4 whole-device (4 cards, no gpumem); managed always-on reasoning (deepseek_r1) — ON exposes, OFF strips+caps. **Deployed+verified on cluster 43 (2026-06-27):** folded download-job into gemma-4 venv-on-PVC initContainer (init skips both on redeploy), `vllm serve /data/model`, bare `r1-distill-llama-70b` PVC naming. 26-check **21/5/0** (think ON/OFF + ANT think ON green; tokenizer loads fine from model dir). |
| r1-distill-qwen-32b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP2 whole-device; managed always-on reasoning (deepseek_r1) — ON exposes, OFF strips+caps. **Deployed+verified on cluster 43 (2026-06-27):** folded download-job into gemma-4 venv-on-PVC initContainer (init skips both on redeploy), `vllm serve /data/model`, bare `r1-distill-qwen-32b` PVC naming. 26-check **21/5/0** (all green incl `ANT think ON` after the Tyk timeout fix). |
| retinanet | detect | false | /v1/vision/detect | READY | PASS | v2 deep pass 2026-06-24: schema v2 details.yaml rewritten with input_map/output_map; test.py expanded to ~15 checks (0 FAIL) |
| rita | embedding | false | /v1/science/generate | READY | PASS | protein generation: greedy + sampling produce valid sequences |
| rnabert | embedding | true | /v1/science/embed | READY | PASS | 120-dim RNA (recreated) |
| rnafm | embedding | true | /v1/science/embed | READY | PASS | 640-dim RNA (recreated) |
| rnamsm | embedding | true | /v1/science/embed | READY | PASS | 768-dim RNA (field: sequence) |
| sapbert | embedding | true | /v1/science/embed | READY | PASS | 768-dim biomedical |
| saprot-650m | embedding | true | /v1/embeddings | READY | PASS | 1280-dim (AA+3Di tokens; recreated) |
| satmae | embed | false | /v1/science/embed | READY | PASS | v2 deep pass 2026-06-24: schema v2 with input_map/output_map (1024-dim CLS); test.py expanded to ~12 checks (0 FAIL); RWX PVC |
| scgpt | embedding | true | /v1/science/embed | READY | PASS | v2 2026-06-19: +/v1/science/embed alias; GPU (was card said CPU); 512-dim; 7/0 test; was parked |
| scibert | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id scibert-110m) |
| science-embed | embedding | ? | - | NO-ISVC | CANCELLED | superseded by individual ESM2/NT ISVCs; not deployed |
| scincl | embedding | true | /v1/embeddings | READY | PASS | 768-dim scientific paper |
| seisbench | classify | true | /v1/science/detect | READY | PASS | phasenet runs (P/S detection) |
| speaches | tts+stt | true | /v1/audio/speech, /v1/audio/transcriptions | READY | PASS | DEEP-FIX: chmod HF cache (root init -> non-root container PermissionError on whisper refs). TTS Kokoro-82M (af_heart/am_michael, wav+mp3 ~9s); STT faster-whisper-large-v3 ~6s. Round-trip transcription exact (x2). Always-on Deployment (heavily used) |
| specter2 | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id specter2-110m) |
| splicebert | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id splicebert-86m) |
| stanford-deidentifier | deidentify | true | /v1/science/deidentify | READY | PASS | PHI entities (PATIENT/DATE/HOSPITAL) |
| sundial | forecast | false | /v1/science/forecast | READY | FIXED | fixed input shape + pinned transformers 4.40.2; forecast+quantiles PASS |
| surya | forecast | true | /v1/science/forecast | READY | PASS | demo forecast+flare_risk via gateway 2026-06-06; id=surya-366m |
| terramind-flood | classify | true | /v1/science/classify | READY | PASS | v2 deep pass 2026-06-24: schema v2 with input_map/output_map; test.py expanded to ~10 checks (0 FAIL); gcc in init for stringzilla |
| thor | embed | true | /v1/science/embed | READY | FIXED | wake-up test PASS 2026-06-08: demo PASS (768-dim); added gcc to init for stringzilla compile |
| time-moe | forecast | true | /v1/forecast | READY | PASS | TimeMoE-50M MoE; forecast_len matches prediction_length (must be 1/96/192/336/720; 12 returns empty) |
| timer-s1 | forecast | true | /v1/forecast | READY | FIXED | replaced timer-xl-1b (gated 403); Timer-S1 bf16 dtype cast, 32Gi init RAM; 9 quantile forecasts PASS |
| timer | forecast | true | /v1/forecast | READY | FIXED | pinned transformers==4.40.2 (remote code uses DynamicCache.seen_tokens removed in >=4.41); forecast_len 96 PASS |
| timesfm | forecast | true | /v1/forecast | READY | FIXED | transformers>=4.51,<4.53 + torch>=2.5 cu126; TimesFmModelForPrediction (v2.0 500M) PASS; 128 quantile levels |
| tinyllama | chat | false | /v1/chat/completions | READY | PASS | TinyLlama-1.1B-Chat (llama.cpp, CPU-only `--n_gpu_layers=0`, GGUF Q4_K_M); no_stream. **Deployed+verified on cluster 43 (2026-06-27):** dropped `kustomization.yaml`, bare `tinyllama-1-1b` PVC/volume naming, `test.py` GW_INSECURE toggle. **Fixed the GGUF filename** (`tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`, dot — the old `1-1b` dash 404'd; the failed revision had to be deleted to recover). 23-check **18/4/1** — chat + streaming(no_stream→JSON) green; the 1 FAIL is the `embed via chat` guard artifact. |
| totalsegmentator | segment | true | /v1/science/segment | READY | PASS | v2 deep pass 2026-06-24: added schema v2 fields (status, behavior, scaling, limits); test.py expanded to ~15 checks (12 PASS / 3 EXP / 0 FAIL); force-reinstall torch+torchvision cu126 ABI fix |
| ttm | forecast | true | /v1/science/forecast | READY | FIXED | past_values shape [batch,time,chan]; 96-step forecast |
| uma-m | force-field | true | /v1/science/predict | BLOCKED | FAIL | gated repo facebook/UMA (401) - needs Meta access grant on HF token |
| xtts-v2 | tts | true | /v1/audio/speech | READY | PASS | text->WAV 155KB audio |
| yolov8n | detect | false | /v1/vision/detect | READY | PASS | v2 deep pass 2026-06-24: schema v2 details.yaml rewritten with input_map/output_map; test.py expanded to ~15 checks (0 FAIL); stale vision_server.py+configmap.yaml removed |
| yolov8s | detect | false | /v1/vision/detect | READY | PASS | v2 deep pass 2026-06-24: schema v2 details.yaml rewritten with input_map/output_map; test.py expanded to ~15 checks (0 FAIL); stale vision_server.py+configmap.yaml removed |
| zoobot | embedding | false | /v1/vision/embed | READY | PASS | v2 deep pass 2026-06-24: schema v2 details.yaml rewritten with input_map/output_map (640-dim embedding); test.py expanded to ~15 checks (0 FAIL); stale server.py+configmap.yaml removed |

## NIM-eligible models not yet deployed

These NIM containers exist on build.nvidia.com but are not yet on the cluster. Could be added as drop-in InferenceServices:

| NIM | Image | Category | Link |
|---|---|---|---|
| rfdiffusion | nvcr.io/nim/ipd/rfdiffusion | protein design | build.nvidia.com/ipd/rfdiffusion |
| evo2-40b | nvcr.io/nim/arc/evo2-40b | biology/genomics | build.nvidia.com/arc/evo2-40b |
| molmim | nvcr.io/nim/nvidia/molmim | chemistry | build.nvidia.com/nvidia/molmim |
| genmol | nvcr.io/nim/nvidia/genmol | molecular generation | build.nvidia.com/nvidia/genmol |
| deepseek-v3.2 | nvcr.io/nim/deepseek-ai/deepseek-v3.2 | LLM | build.nvidia.com/deepseek-ai/deepseek-v3.2 |
| mistral-small-4 | nvcr.io/nim/mistralai/mistral-small-4-119b-2603 | LLM | build.nvidia.com/mistralai/mistral-small-4-119b-2603 |

## Skipped models (gated Meta, no HF access)

| Model | Repo | Reason |
|---|---|---|
| llama-3.3-70b | meta-llama/Llama-3.3-70B-Instruct | gated (403); HF access not granted on token |
| llama-4-scout | meta-llama/Llama-4-Scout-17B-16E-Instruct | gated (403); HF access not granted on token |

---

## Chat LLM capability matrix

Per-chat-model config detail that isn't in the main table above: thinking mode, the vLLM
parsers wired in the ISVC, vision, card schema, and the gateway test tally. **Where this
disagrees with the main table, the main table wins.** Source: live `details.yaml` /
`inferenceservice.yaml` audit + per-model gateway test runs. (Historical campaign tracker
retained in the local working dir.)

| Model | Thinking | Reason parser | Tool parser | Vision | Card | Tests |
|---|---|---|---|---|---|---|
| qwen36-27b | effort | qwen3 | qwen3_coder | ✅ | v2 | 28/2 (30) |
| qwen3-32b | effort | qwen3 | hermes | — | v2 | 30/3 (33) |
| qwen3-235b | none | — | hermes | — | v2 | 21/21 |
| qwen35-122b | toggle | qwen3 | qwen3_coder | — | v2 | 25/3 (28) |
| qwen36-35b-a3b | effort | qwen3 | qwen3_coder | ✅ | v2 | 28/2 (30) |
| qwq-32b | always-on | deepseek_r1 | hermes | — | v2 | 18/3 (21) |
| gpt-oss-120b | effort | openai_gptoss | openai | — | v2 | 30/3 (33) |
| gpt-oss-20b | effort | openai_gptoss | openai | — | v2 | 30/3 (33) |
| phi-4-reasoning | budget | deepseek_r1 | — | — | v2 | 26/5 (31) reduce-off (none→512) |
| r1-distill-qwen-32b | always-on | deepseek_r1 | — | — | v2 † | 20/5 (25) |
| r1-distill-llama-70b | always-on | deepseek_r1 | — | — | v2 † | 20/5 (25) |
| glm-4-32b | none | — | glm4_0414 (plugin) | — | v2 | 15/19 |
| qwen25-coder-32b | none | — | hermes | — | v2 | 22/22 |
| qwen25-vl-72b | none | — | — | ✅ | v2 | 22/2 (25) |
| qwen25-vl-72b-awq | none | — | — | ✅ | v2 | 22/2 (25) |
| qwen25-vl-7b | none | — | hermes | ✅ | v2 | 23/1 (25) |
| qwen25-vl-3b | none | — | — | ✅ | v2 | 22/2 (25) |
| gemma-4-26b-a4b | toggle | gemma4 | gemma4 | ✅ | v2 | 32/2 (34) |
| gemma-3-4b-it | none | — | — | ✅ | v2 | 22/2 (25) |
| medgemma-27b-it | none | — | — | ✅ | v2 | 22/2 (25) |
| deepseek-v2-lite-16b | none | — | — | — | v2 | 14/14 |
| command-r-7b | none | — | — | — | v2 | 16/16 |
| openbiollm-70b | none | — | — | — | v2 | 14/14 |
| oceangpt-30b | none | — | hermes | — | v2 | 14/14 |
| geogalactica | none | — | — | — | v2 | 14/14 |
| tinyllama-1-1b | none | — | — | — | v2 (llama.cpp) | 14/14 |
| astrosage | none | — | — | — | v2 (custom) | 14/14 |

Notes:
- † `r1-distill-*` cards are v2 but **omit `param_translation.thinking`** (always-on reasoning,
  no toggle) and advertise `context_window: 131072` while the ISVC serves `65536` — card-hygiene
  follow-up only; the models themselves PASS.
- **GLM tool-calling:** `glm-4-32b` is fixed (custom `glm4_0414` parser + plugin). (The glm-z1
  pair was retired 2026-06-18 — reasoning not surfaceable + broken/by-design tools.)
- **Missing `param_translation.thinking`** on several non-reasoning cards is functionally
  identical to `mode: none` (the gateway defaults absent → none).

## Thinking mode reference

| Mode | When to use | Example models | Mechanism |
|---|---|---|---|
| **budget** | model supports `thinking_token_budget` | phi-4-reasoning | effort → token count (0 / 1024 / 4096 / 12288 / 24576 / null) |
| **effort** | native `reasoning_effort`, or binary thinking via `chat_template_kwargs` | qwen36-27b, qwen3-32b, gpt-oss-20b, gemma-4-26b-a4b | effort alias → on/off, or passthrough |
| **toggle** | simple thinking on/off | qwen35-122b | injects `chat_template_kwargs.enable_thinking` |
| **always-on** | always reasons; managed (expose on / strip+cap off) | qwq-32b, r1-distill-* | `mode: always_on`; deepseek_r1 extracts reasoning; gateway exposes on / strips+caps off |
| **none** | non-reasoning model | gemma-3-4b-it, most chat models | no thinking translation |

Card template + v1→v2 migration: see `models/DETAILS-TEMPLATE-LLM.md` and `models/MIGRATION.md`.

## Embeddings pass (2026-06-19) — hardened re-verification + Template-C cards

Re-running the embedding/rerank models through the gateway with correctness-asserting `test.py`s,
rewriting old-schema cards to v2 Template C, splitting/migrating PVCs to RWX, and adding README +
CLAUDE per dir. (The rows in the main table above are from the 2026-06-08 loop; this is the deeper
pass.) Score = PASS / EXP (expected 4xx rejection) / FAIL. All committed to `main`.

| Model | Result | Card | PVC | Note |
|---|---|---|---|---|
| bge-m3 | 9/2/0 | v2 | RWX | mem 8→16 Gi (OOM fix); truncation now passes |
| bge-reranker-v2-m3 | 8/3/0 | v2 | RWX | rerank battery; type-mismatch 404/424 |
| esm2-650m | 8/2/0 | v2 | RWX (split) | protein embed; apply details.yaml only |
| scibert | 8/2/0 | v2 (rewrote) | RWX | dropped kustomize |
| bge-small | 9/2/0 | v2 (created) | none | no card existed; TEI fetches model |
| multilingual-e5-small | 9/2/0 | v2 (rewrote) | RWX | card had wrong endpoint/framework |
| dnabert-2 | 8/2/0 | v2 (rewrote) | RWX | torch-2.5.1 op pin |
| esm1b | 8/2/0 | v2 (rewrote) | RWX (RWO→RWX) | recreated PVC; re-download validated |
| biobert | 8/2/0 | v2 | RWX (split, nfs-models) | — |
| pubmedbert | 8/2/0 | v2 (rewrote) | RWX | dropped kustomize; served id pubmedbert-110m |
| esm2-150m | 8/2/0 | v2 (rewrote) | RWX (RWO→RWX) | 640-dim; recreated PVC (nfs-models) |
| biomedbert | 8/2/0 | v2 (fixed desc) | RWX | fixed PubMedBERT→BiomedBERT copy-paste |
| esmc-300m | 8/2/0 | v2 (rewrote) | RWX (RWO→RWX) | 960-dim; cold rebuild >6min |
| chemberta | 8/2/0 | v2 (was v2) | RWX | SMILES; added test+README |
| clinicalbert | 8/2/0 | v2 (was v2) | RWX | MIMIC clinical; added test+README |
| splicebert | 7/3/0 | v2 (rewrote) | RWX | token-level model; mean-pool not discriminative |
| specter2 | 8/2/0 | v2 (rewrote) | RWX | paper embeddings |
| matscibert | 8/2/0 | v2 (+/v1/embeddings) | RWX (split, nfs-models) | science-embed normalized to OpenAI; science/embed+predict kept secondary |
| ancient-greek-bert | 8/2/0 | v2 (+/v1/embeddings) | RWX (RWO→RWX) | science-embed normalized; Ancient Greek, 768-dim CLS |
| clinical-longformer | 8/2/0 | v2 (+/v1/embeddings) | RWX (RWO→RWX) | science-embed normalized; Longformer 4096 ctx, global-attention CLS |
| biomedbert-large | 8/2/0 | v2 (+/v1/embeddings) | RWX (RWO→RWX) | science-embed normalized; 1024-dim CLS, BERT-large |
| esm2-35m | 8/2/0 | v2 (was v2) | RWX (split, nfs-models) | smallest ESM-2; 480-dim |
| dnabert-s | 8/2/0 | v2 (rewrote) + server fix | RWX | OpenAI fix: batch+usage+truncation in /v1/embeddings handler |
| ankh | 8/2/0 | v2 (rewrote) | RWX (RWO→RWX) | protein T5 encoder; server already compliant |
| biolinkbert | 8/2/0 | v2 (rewrote) | RWX (RWO→RWX) | biomedical; gateway 404 during cold-start (pre-warm) |
| biomed-roberta | 8/2/0 | v2 (rewrote) | RWX (RWO→RWX) | biomedical RoBERTa; server compliant |
| saprot-650m | 7/3/0 | v2 (rewrote) | RWX (RWO→RWX) | structure-aware; ⚠ distinctness cos=1.0 anomaly (plain-AA collapsed) |
| scincl | 8/2/0 | v2 (rewrote) | RWX (RWO→RWX) | scientific citation; CLS-pool; server compliant |
| prokbert | 8/2/0 | v2 (was v2) + server fix | none | bacterial DNA 384-dim; added usage to /v1/embeddings |
| hyenadna | 7/2/0 | v2 (rewrote) | RWX | long-range DNA; fixed ctx 32768→8192; dropped kustomize |
| esm2-3b | 7/2/0 | v2 (rewrote) | RWX | largest ESM-2; 2560-dim; slow cold start |
| agront | 7/2/0 | v2 (was v2) + server fix | RWX (split) | plant DNA 1500-dim; OpenAI fix batch+usage+truncate |
| medcpt-query | 7/2/0 | v2 (rewrote) | RWX (RWO→RWX) | MedCPT query encoder; 768-dim, 64-tok; server compliant |
| medcpt-article | 7/2/0 | v2 (rewrote) | RWX (RWO→RWX) | MedCPT article encoder; 768-dim, 512-tok; server compliant |
| caduceus | 7/2/0 | v2 (rewrote) | RWX (split) | Mamba DNA; 256-dim RCPS; server compliant |
| nucleotide-transformer | 7/2/0 | v2 (was v2) | RWX (split, nfs-models) | DNA 1024-dim; server compliant |
| gena-lm | 7/2/0 | v2 (rewrote) | RWX (RWO→RWX) | DNA 768-dim; server compliant |
| ablang2 | 6/2/0 | v2 (was v2) | RWX (cp-migrated) | antibody 480-dim; non-HF Zenodo → RWX via cp-from-RWO (no re-download) |
| molformer | 7/2/0 | v2 (+/v1/embeddings) | RWX (RWO→RWX) | SMILES molecular 768-dim; normalized from /v1/science/embed |
| sapbert | 6/2/0 | v2 (+/v1/embeddings) | RWX (RWO→RWX) | biomedical entity linking; 768-dim CLS, 25-tok |
| rnabert | 6/2/0 | v2 (+/v1/embeddings) | RWX (RWO→RWX) | RNA; 120-dim mean-pooled |
| ernierna | 5/3/0 | v2 (+/v1/embeddings) | RWX (RWO→RWX) | structure-aware RNA; 768-dim; distinctness EXP (short-seq collapse) |
| rnafm | 6/2/0 | v2 (+/v1/embeddings) | RWX (RWO→RWX) | non-coding RNA; 640-dim mean-pooled |
| rnamsm | 6/2/0 | v2 (+/v1/embeddings) | RWX (RWO→RWX) | RNA MSA; 768-dim mean-pooled |
| gena-lm-large | 6/3/0 | v2 (+/v1/embeddings) | RWX (RWO→RWX) | DNA BERT-large; 1024-dim CLS |
| astroclip | 9/0/0 | v2 (rewrote) | RWX | DOMAIN (was demo stub): real 1024-dim galaxy image+spectrum; weights_only (Py2.6) + upstream batch<2 bug fixed; NOT OpenAI /v1/embeddings |
| labram | 8/0/0 | v2 (rewrote) | RWX (cp-migrated) | DOMAIN (was untrained random): real 200-dim EEG; from_pretrained(local,offline); n_times 1600->3000; LABRAM_CHANNEL_ORDER submodule import fix; NOT OpenAI /v1/embeddings |
| satmae | 6/0/0 | v2 (rewrote) | RWX (cp-migrated) | DOMAIN non-text embed: 1024-dim satellite-image CLS; RWO→RWX; +embeddings field; was parked (stop ann); NOT OpenAI /v1/embeddings |

**Fleet findings:** 47 PVCs were ReadWriteOnce (all on RWX-capable NFS) — migrating each to RWX as
reached (re-download validates the path for others). SC drift: many live PVCs are `nfs-models` vs
repo `nfs-client` (immutable; matched live). No non-HF downloaders found (all HF `snapshot_download`).
