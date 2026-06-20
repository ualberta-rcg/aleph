# Model Test Status -- Cluster 230

Master tracker for the per-model verification loop. Gateway ClusterIP `http://10.43.79.101:80` (in-cluster only). Source of truth: this local repo.

Test-status legend: `PENDING` (not yet verified by this loop) - `PASS` - `FIXED` (was broken, now PASS) - `FAIL` (hard fail, see note).

Cluster-state at snapshot start: **93 READY**, **58 NOT-READY**, **6 NO-ISVC** (of 157).

| Model | Type | GPU | Primary endpoint | Cluster state | Test status | Note |
|---|---|---|---|---|---|---|
| ablang2 | embedding | false | /v1/embeddings | READY | FIXED | embeddings+batch PASS; /v1/restore was broken, fixed (heavy/light pairs), now PASS |
| aeneas | structure | true | /v1/science/predict | READY | FIXED | wake-up test PASS 2026-06-08: demo PASS (restoration+dating); real inference slow (JAX) |
| agront | embedding | true | /v1/embeddings | READY | PASS | 1500-dim DNA |
| aion | embed | false | /v1/science/embed | READY | FIXED | rewrote to real AION CodecManager API; legacy_image + photometry -> 768-dim; was non-functional |
| alphafold2 | structure-prediction | true | /v1/science/predict | READY | PASS | demo folds seq -> PDB. **NIM available:** `nvcr.io/nim/deepmind/alphafold2` (build.nvidia.com/deepmind/alphafold2) |
| ancient-greek-bert | embedding | true | /v1/science/embed | READY | PASS | 768-dim (field: text) |
| ankh | embedding | true | /v1/embeddings | READY | FIXED | T5 fp16->fp32 NaN fix; 768-dim protein PASS |
| arcface | embedding | false | /v1/vision/face | READY | PASS | id=arcface-resnet100; face embedding |
| astroclip | embed | true | /v1/science/embed | READY | FIXED | Real model 2026-06-19 (was demo stub): venv-on-PVC + 1024-dim image/spectrum (not 512); fixed weights_only (PyTorch 2.6) + upstream batch<2 attentions[1] bug; 9/0 test |
| astropt | embed | true | /v1/science/embed | READY | PASS | v2 2026-06-19: venv-on-PVC conversion (was reinstalling torch every wake); 768-dim (docs said [N,512], wrong); 7/0 test |
| astrosage | chat | true | /v1/chat/completions | READY | PASS | 14/14 ✅ via gateway; custom transformers server (not vLLM); 8B Llama-3.1; vGPU slice 16GB; no_stream; vision gating added (gateway-9ade05f) |
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
| biomedclip | embed | true | /v1/embeddings | READY | PASS | text_embeddings (texts/images) |
| biot5 | science-generate | false | /v1/science/generate | READY | FIXED | task-specific checkpoints + SELFIES; mol2text & text2mol correct (was garbage) |
| birdnet-analyzer | audio-classification | false | /v1/science/identify | READY | PASS | end-to-end OK; synthetic tone -> no detections (expected) |
| boltz-1 | structure | true | /v1/science/predict | READY | PASS | Boltz-1 NIM container; protein structure prediction; Ready on cluster. **NIM:** `nvcr.io/nim/mit/boltz-2` (--checkpoint boltz1) |
| boltz-2 | structure | true | /v1/science/predict | READY | PASS | Boltz-2 NIM container (default); protein structure prediction; Ready on cluster. **NIM:** `nvcr.io/nim/mit/boltz-2` (build.nvidia.com/mit/boltz-2) |
| borzoi | predict | true | /v1/science/predict | READY | PASS | genomics: 6144 tracks x 16 bins |
| brainlm | embed | true | /v1/embeddings | READY | FIXED | wake-up test PASS 2026-06-08: 1280-dim fMRI embeddings via ViTMAE CLS token; slow model load (~10min) |
| caduceus | embedding | true | /v1/embeddings | READY | FIXED | torch 2.2.0+mamba-ssm 1.2.0 pinned, numpy<2, AutoModel RCPS 256-dim; PVC venv cached; mamba compile ~20min first deploy, 5sec after |
| chem-t5 | science-generate | false | /v1/science/generate | READY | FIXED | exact GT4SD prompt templates; caption+forward_synthesis correct (was wrong) |
| chemberta | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id chemberta-125m) |
| chemgpt-19m | generate | true | /v1/science/generate | READY | PASS | SELFIES molecule generation |
| chemgpt | generate | true | /v1/science/generate | READY | PASS | id=chemgpt-1.2b; SELFIES molecule generation |
| chgnet | force-field | true | /v1/science/energy | READY | FIXED | DEEP-FIX: ported server.py was broken (manually built CrystalGraph w/ bad kwarg) -> rewrote to model.predict_structure(); added missing server.py+kustomization (never ported); CederGroupHub/chgnet HF repo removed (404) -> non-fatal, uses chgnet bundled weights; pinned chgnet==0.3.8. water -14.79 eV + forces + stress + magmom |
| chronos-bolt | forecast | false | /v1/forecast | READY | PASS | quantile forecast on 16-pt series |
| clap | embedding | false | /v1/embeddings | READY | PASS | text emb 512-dim + zero-shot audio classify (dog 0.73) |
| clay | embed | false | /v1/science/embed | READY | PASS | v2 2026-06-19: RWO→RWX (cp); +embeddings field; 1024-dim CLS (large); 6/0 test; was parked |
| climatebert | classification | false | /v1/science/classify | READY | PASS | net-zero 0.9988 |
| climax | forecast | true | /v1/science/forecast | READY | PASS | needs valid ERA5 var names (e.g. 2m_temperature) |
| clinical-longformer | embedding | true | /v1/science/embed | READY | FIXED | wake-up test PASS 2026-06-08: 768-dim embeddings; slow on CPU (~2min inference) |
| clinicalbert | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id clinicalbert-110m) |
| command-r-7b | chat | true | /v1/chat/completions | READY | PASS | OpenAI + Anthropic |
| croma | segment | true | /v1/embeddings | READY | FIXED | dict output extraction (joint/optical/SAR GAP) |
| crysta-llm | chat | true | /v1/science/generate | READY | PASS | crystal structure gen from formula (progress-deadline fix) |
| deepseek-v2-lite-16b | chat | true | /v1/chat/completions | READY | PASS | v0.20.2 (std); gpumem 45GB + max-model-len 8192; correct answers |
| depth-anything | depth | false | /v1/vision/depth | READY | FIXED | fixed k8s_name 404 + PNG output; PASS |
| diffdock | dock | true | /v1/dock | READY | FIXED | SMILES passed direct (not .smi file); conf regex fixed; 11 poses on 1CRN+aspirin. **NIM available:** `nvcr.io/nim/mit/diffdock` (build.nvidia.com/mit/diffdock) |
| dino-vit-b8 | embedding | false | /v1/vision/embed | READY | PASS | image embedding |
| dnabert-2 | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id dnabert-2-117m) |
| dnabert-s | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id dnabert-s) |
| dust3r | 3d | true | /v1/science/reconstruct | READY | FIXED | downsample pointcloud (was 31MB>gateway); bbox+loss; 2 imgs OK |
| earthpt | embed | true | /v1/science/predict | READY | FIXED | CPU ckpt load + RAM 24Gi (was GPU+host OOM); predicts OK |
| efficientnet-b0 | classify | false | /v1/vision/classify | READY | FIXED | lite4: fixed preproc+double-softmax+labels; minibus 0.63 |
| enformer | predict | true | /v1/science/predict | READY | FIXED | dict output fix (`isinstance(out, dict)`), transformers<4.52, GPU torch, Python 3.12; human_shape [896,5313] PASS |
| ernierna | embedding | true | /v1/science/embed | READY | FIXED | GPU torch cu126 reinstall, nodeSelector gpu=on, progress-deadline 600s; 768-dim RNA embeddings PASS |
| esm1b | embedding | true | /v1/embeddings | READY | PASS | 1280-dim protein (recreated) |
| esm2-150m | embedding | true | /v1/embeddings | READY | PASS | 640-dim protein (recreated) |
| esm2-35m | embedding | true | /v1/embeddings | READY | PASS | 480-dim protein |
| esm2-3b | embedding | true | /v1/embeddings | READY | PASS | 2560-dim protein (recreate cleared) |
| esm2-650m | embedding | true | /v1/embeddings | READY | PASS | 1280-dim protein. **NIM available:** `nvcr.io/nim/meta/esm2-650m` (build.nvidia.com/meta/esm2-650m) |
| esmc-300m | embedding | true | /v1/embeddings | READY | PASS | 960-dim (recreated) |
| esmfold | structure | true | /v1/structure | READY | PASS | folds protein -> PDB. **NIM available:** `nvcr.io/nim/meta/esmfold` (build.nvidia.com/meta/esmfold) |
| fengwu | forecast | true | /v1/science/forecast | READY | FIXED | summarize grid (was 286MB>gateway); demo+real ONNX OK |
| finbert | classify | true | /v1/science/classify | READY | PASS | sentiment positive 0.96 |
| fourcastnet3 | forecast | true | /v1/science/forecast | READY | DEMO | demo OK; real FCN3 blocked (makani+torch-harmonics CUDA matrix needs dedicated image). **NIM available (FCN2):** `nvcr.io/nim/nvidia/fourcastnet` (build.nvidia.com/nvidia/fourcastnet, L40S-tested) |
| galileo | classify | false | /v1/embeddings | READY | FAIL | galileo pip package import conflicts with cloned repo; server stuck at model loading |
| gemma-3-4b-it | chat | true | /v1/chat/completions | READY | PASS | OpenAI + Anthropic |
| gemma-4-26b-a4b | chat | true | /v1/chat/completions | READY | PASS | 26B MoE fp8; managed thinking (toggle: enable_thinking, not reasoning_effort) + vision + tools; 32-check test 30/2/0 ✅ 2026-06-18. (NIM alt: nvcr.io/nim/google/gemma-4-31b-it) |
| gena-lm-large | embedding | true | /v1/science/embed | READY | FIXED | output_hidden_states (was returning vocab logits); 1024-dim |
| gena-lm | embedding | true | /v1/embeddings | READY | PASS | 768-dim DNA (recreated) |
| geneformer | embedding | true | /v1/embed | READY | PASS | needs gene_ids token IDs (recreated) |
| geogalactica | chat | true | /v1/chat/completions | READY | FIXED | 14/14 ✅ via gateway; v0.20.2 TP2; OPT 30B; context 2048 (hard limit); tools/vision rejected; prev engine core init fail resolved |
| glm-4-32b | chat | true | /v1/chat/completions | READY | PASS | org moved THUDM->zai-org; haiku ok. **NIM available:** `nvcr.io/nim/zai-org/glm-51` (GLM-5.1, build.nvidia.com/z-ai/glm-5.1) |
| glm-z1-32b | — | — | — | RETIRED | — | Removed 2026-06-18 — redundant reasoning model; reasoning not surfaceable (chat template has no enable_thinking; glm45 parser crashes). Deleted from repo + cluster. Use qwq/r1-distill/gpt-oss/qwen3 instead. |
| glm-z1-rumination-32b | — | — | — | RETIRED | — | Removed 2026-06-18 — deep-research reasoner; same surfacing issue + ignores tools/system by design. Deleted from repo + cluster. |
| gpt-oss-120b | chat | true | /v1/chat/completions | READY | PASS | TP2 ~200tok/s; v0.20.2; full GPUs (no gpumem) + --disable-custom-all-reduce; managed thinking ON (expose reasoning: effort + fake token-budget) / OFF (strip + cap) verified 30/3/0 (33-check) |
| gpt-oss-20b | chat | true | /v1/chat/completions | READY | PASS | TP1; v0.20.2; managed thinking ON/OFF verified 30/3/0 (33-check); OpenAI + Anthropic |
| granite-geospatial-biomass | classify | true | /v1/science/predict | READY | FIXED | add gcc/g++ to init (terratorch->stringzilla build); demo OK |
| granite-geospatial-ocean | classify | true | /v1/science/embed | READY | FIXED | add gcc/g++ to init; demo embeddings OK; slow cold-start |
| graphcast | forecast | false | /v1/science/predict | READY | PASS | demo mode (real ERA5 not via API by design) |
| hyenadna | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=256 (id hyenadna-6.5m) |
| ithaca | text-restore | true | /v1/science/predict | READY | FIXED | DEEP-FIX: jax[cuda12] (was CPU-fallback -> 3min); contextualize() retrieval made opt-in (req.contextualize); gap char is ? (uppercase Greek, 50-750 chars). Warm ~8s on GPU (first call ~90s JIT). Returns restoration + attribution (date/geo) |
| kandinsky-3 | text-to-image | true | /v1/images/generations | READY | PASS | RayService w/ in-tree autoscaler. Head on non-GPU kubeflow-head-node2 (proxy_location HeadOnly); GPU worker autoscales 0->3. VERIFIED: scale-up 0->1 on request, image gen ~24s (1024) PNG, scale-DOWN releases L40S after idle. Added missing download-job.yaml. 15min idle retention |
| labram | embed | false | /v1/science/embed | READY | FIXED | Real model 2026-06-19 (was untrained random): from_pretrained(local dir, offline); n_times 1600->3000; LABRAM_CHANNEL_ORDER submodule import fix; 200-dim EEG; 8/0 test |
| lag-llama | forecast | true | /v1/science/forecast | READY | FIXED | torch2.6 weights_only + create_predictor(module=) API |
| leandojo | embed | true | /v1/science/retrieve | READY | PASS | premise retrieval w/ scores |
| ligandmpnn | design | false | /v1/design | READY | FIXED | checkpoints+args+optional-openfold; 1CRN design near-native PASS |
| mace-mh-1 | force-field | true | /v1/science/predict | READY | PASS | water -14.22 eV + forces (omat_pbe head) |
| mace-mp-0 | force-field | false | /v1/science/energy | READY | FIXED | fixed pbc-zero-cell garbage + PVC model cache; water -14.15eV PASS |
| mace-mp | force-field | true | /v1/science/predict | READY | PASS | water -14.01 eV + forces; mace-mp-0 medium |
| maskrcnn | segment | false | /v1/vision/segment | READY | PASS | id=maskrcnn-resnet50; person 0.999 + mask |
| mast3r | 3d | true | /v1/science/match | READY | FIXED | use /v1/science/match; numpy (not tensor) fix; 473 matches |
| matscibert | embedding | true | /v1/science/embed | READY | PASS | 768-dim (field: text) |
| mattergen | generate | true | /v1/science/generate | NO-ISVC | FAIL | Knative rejects ISVC: timeoutSeconds 1500 > max 600; predictor never created; gateway 404 |
| mattersim | force-field | true | /v1/science/predict | READY | PASS | water -14.07 eV + forces + per-atom |
| medcpt-article | embedding | true | /v1/embeddings | READY | PASS | 768-dim PubMed article (recreated) |
| medcpt-query | embedding | true | /v1/embeddings | READY | PASS | 768-dim PubMed query (recreated) |
| medgemma-27b-it | chat | true | /v1/chat/completions | READY | PASS | 27B dense TP2 ~20tok/s; v0.20.2 (fixed --limit-mm-per-prompt JSON); full GPUs + --disable-custom-all-reduce; correct medical answers |
| medsam | segment | true | /v1/science/segment | READY | PASS | image as HxWx3 pixel array + boxes -> masks |
| megadetector | detect | true | /v1/detect | READY | PASS | bbox detections w/ conf |
| moirai-large | forecast | true | /v1/science/forecast | READY | PASS | mean+samples forecast |
| moirai-moe-1-0-r-base | forecast | true | /v1/forecast | READY | FIXED | replaced moirai-moe; rewrote to official uni2ts create_predictor() + GluonTS API; 19 quantile levels PASS |
| moirai | forecast | true | /v1/forecast | READY | PASS | Salesforce Moirai base; values+horizon -> mean/quantiles; sensible forecast |
| molformer | embedding | true | /v1/science/embed | READY | PASS | 768-dim (field: smiles) |
| moment | forecast | true | /v1/forecast | READY | FIXED | output indexing (chan vs horizon); needs 512-len input; 96-step horizon |
| multilingual-e5-small | embedding | false | /v1/embeddings | READY | PASS | 384-dim text embedding |
| naturecode-earth | embed | true | /v1/science/predict | READY | DEMO | demo OK (seg probs); weights GATED (naturecodeproject/earth 403); needs HF access |
| neuralgcm | forecast | false | /v1/science/predict | READY | PASS | demo mode (real ERA5 not via API by design) |
| nucleotide-transformer | embedding | true | /v1/embeddings | READY | PASS | 1024-dim DNA |
| oceangpt-30b | chat | true | /v1/chat/completions | READY | FIXED | 30B-A3B MoE TP2 ~73tok/s; v0.20.2; full GPUs + --disable-custom-all-reduce (no CUDA_DISABLE_CONTROL); OpenAI+Anthropic |
| openbiollm-70b | chat | true | /v1/chat/completions | READY | PASS | hemoglobin answer correct; tokenizer already Fast; vLLM v0.20.2 TP4 whole-device |
| openfold-3 | structure | true | /v1/science/predict | READY | PASS | OpenFold-3 NIM container. **NIM:** `nvcr.io/nim/openfold/openfold3` (build.nvidia.com/openfold/openfold3) |
| omnigenome | embedding | false | /v1/science/predict | READY | PASS | id=omnigenome-186m; RNA embedding |
| pangu-weather | forecast | true | /v1/science/forecast | READY | FIXED | demo+real ONNX; summarized upper/surface stats (not raw 721x1440 grids) |
| phi-4-reasoning | chat | true | /v1/chat/completions | READY | PASS | v0.20.2 whole L40S; budget mode with REDUCE-off (none→512, NOT 0 — budget 0 mishandled per vLLM#18141) + strip; ON exposes reasoning, OFF/meta return content (reasoning stripped); generous meta caps. 31-check 26/5/0 ✅ 2026-06-18 |
| presto | classify | false | /v1/embeddings | READY | FIXED | wake-up test PASS 2026-06-08: 17-band S1_S2_ERA5_SRTM satellite embeddings; pass mask/month/dynamic_world kwargs |
| prithvi-eo | embed | true | /v1/embed | READY | FIXED | BACKBONE_REGISTRY + forward_features, GDAL + libexpat1 runtime dep; 1024-dim CLS embeddings PASS |
| prithvi-wxc | embed | true | /v1/science/forecast | READY | PASS | demo forecast OK after unstop+cold-start (~6min); real MERRA-2 state not exercised |
| progen2 | generate | true | /v1/completions | READY | FIXED | sentinel + progress-deadline 600s; 6.4B protein generation PASS |
| prokbert | embedding | true | /v1/embeddings | READY | PASS | 384-dim DNA |
| prostt5 | translate | true | /v1/translate | READY | PASS | AA->3Di structural alphabet (recreated) |
| proteinmpnn | design | true | /v1/design | READY | PASS | designs sequences from PDB w/ scores. **NIM available:** `nvcr.io/nim/ipd/proteinmpnn` (build.nvidia.com/ipd/proteinmpnn) |
| protgpt2 | generate | true | /v1/completions | READY | PASS | de novo protein generation (recreated) |
| pubmedbert | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id pubmedbert) |
| qwen25-coder-32b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP2 whole-device; 32.5B dense code specialist; no reasoning parser; tools (hermes parser); 131K native ctx deployed at 32K; 22/22 gateway test ✅ 2026-06-11; cold start ~90s; vision correctly rejected |
| qwen25-vl-3b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP1 gpumem 24GB; 3B dense + ViT (36 layers, GQA 16Q/2KV); vision (dynamic-res, video, OCR, 4 img/prompt); no tools, no reasoning; 4K ctx; init container for HF download; 18/18 gateway test ✅ 2026-06-11; cold start ~120s |
| qwen25-vl-7b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP1 gpumem 32GB; 7B dense + ViT (28 layers, GQA 28Q/4KV); vision (dynamic-res, video, 20 images/prompt) + tools (hermes, forced); no reasoning; 65K ctx; init container for HF download; 22/22 gateway test ✅ 2026-06-11; cold start ~120s |
| qwen25-vl-72b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP4 whole-device; 72.2B dense VLM; vision (dynamic-res images, video, 5 img/prompt); no tools, no reasoning; 131K native ctx deployed at 32K; 22/22 gateway test ✅ 2026-06-11; cold start ~285s; limit-mm-per-prompt=5 images |
| qwen3-235b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP4 whole-device; 235B-A22B AWQ int4 MoE (22B active, 128 experts); non-thinking Instruct-2507 variant; tools (hermes parser); no reasoning parser (non-thinking); awq_marlin quantization; 131K ctx; 21/21 gateway test ✅ 2026-06-11; vision correctly rejected; ~4min cold start; **NIM available:** `nvcr.io/nim/qwen/qwen3-235b-a22b` |
| qwen3-32b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP2 whole-device; 32.8B dense; managed thinking (qwen3 parser, effort mode, enable_thinking toggle) + tools (hermes); 33-check test 30/3/0 ✅ 2026-06-18; vision rejected |
| qwen35-122b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP4 whole-node; 122B FP8 MoE (10B active); managed thinking (toggle enable_thinking) + tools (qwen3_coder); language-model-only (vision off); 131K ctx; DEPLOYED on 230 (weights on PVC); 28-check test 25/3/0 ✅ 2026-06-18 |
| qwen36-27b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP2 whole-device; Gated-DeltaNet hybrid; managed thinking (effort + enable_thinking) + vision + tools (qwen3_coder); 30-check test 28/2/0 ✅ 2026-06-18 |
| qwen36-35b-a3b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP2 whole-device; 35B MoE (3B active) hybrid Gated-DeltaNet; managed thinking (effort + enable_thinking) + tools (qwen3_coder) + vision; 64K ctx; 30-check test 28/2/0 ✅ 2026-06-18 |
| qwq-32b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP2 whole-device; 32.5B dense; managed always-on thinking (deepseek_r1) — ON exposes reasoning, OFF strips+caps; tools (hermes); 32K ctx; 21-check test 18/3/0 ✅ 2026-06-18 |
| r1-distill-llama-70b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP4 whole-node; tokenizer_class patch; managed always-on reasoning (deepseek_r1) — ON exposes, OFF strips+caps; 25-check 20/5/0 ✅ 2026-06-18 |
| r1-distill-qwen-32b | chat | true | /v1/chat/completions | READY | PASS | vLLM v0.20.2 TP2 whole-device; managed always-on reasoning (deepseek_r1) — ON exposes, OFF strips+caps; 25-check 20/5/0 ✅ 2026-06-18 |
| retinanet | detect | false | /v1/vision/detect | READY | PASS | id=retinanet-resnet50; bus 0.95 |
| rita | embedding | false | /v1/science/generate | READY | PASS | protein generation: greedy + sampling produce valid sequences |
| rnabert | embedding | true | /v1/science/embed | READY | PASS | 120-dim RNA (recreated) |
| rnafm | embedding | true | /v1/science/embed | READY | PASS | 640-dim RNA (recreated) |
| rnamsm | embedding | true | /v1/science/embed | READY | PASS | 768-dim RNA (field: sequence) |
| sapbert | embedding | true | /v1/science/embed | READY | PASS | 768-dim biomedical |
| saprot-650m | embedding | true | /v1/embeddings | READY | PASS | 1280-dim (AA+3Di tokens; recreated) |
| satmae | embed | false | /v1/science/embed | READY | PASS | v2 2026-06-19: RWO→RWX (cp-migrated); +embeddings field; 1024-dim CLS; 6/0 test; was parked (stop ann cleared) |
| scgpt | embedding | true | /v1/embeddings | READY | FIXED | _encode needs src_key_padding_mask; 512-dim |
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
| terramind-flood | classify | true | /v1/science/classify | READY | FIXED | wake-up test PASS 2026-06-08: demo PASS (flood mask); added gcc to init for stringzilla compile |
| thor | embed | true | /v1/science/embed | READY | FIXED | wake-up test PASS 2026-06-08: demo PASS (768-dim); added gcc to init for stringzilla compile |
| time-moe | forecast | true | /v1/forecast | READY | PASS | TimeMoE-50M MoE; forecast_len matches prediction_length (must be 1/96/192/336/720; 12 returns empty) |
| timer-s1 | forecast | true | /v1/forecast | READY | FIXED | replaced timer-xl-1b (gated 403); Timer-S1 bf16 dtype cast, 32Gi init RAM; 9 quantile forecasts PASS |
| timer | forecast | true | /v1/forecast | READY | FIXED | pinned transformers==4.40.2 (remote code uses DynamicCache.seen_tokens removed in >=4.41); forecast_len 96 PASS |
| timesfm | forecast | true | /v1/forecast | READY | FIXED | transformers>=4.51,<4.53 + torch>=2.5 cu126; TimesFmModelForPrediction (v2.0 500M) PASS; 128 quantile levels |
| tinyllama | chat | false | /v1/chat/completions | READY | PASS | OpenAI + Anthropic PASS; streaming 500 (gateway SSE, cross-cutting) |
| totalsegmentator | segment | true | /v1/science/segment | READY | FIXED | force-reinstall torch+torchvision cu126 after TotalSegmentator (ABI fix); 200 PASS |
| ttm | forecast | true | /v1/science/forecast | READY | FIXED | past_values shape [batch,time,chan]; 96-step forecast |
| uma-m | force-field | true | /v1/science/predict | BLOCKED | FAIL | gated repo facebook/UMA (401) - needs Meta access grant on HF token |
| xtts-v2 | tts | true | /v1/audio/speech | READY | PASS | text->WAV 155KB audio |
| yolov8n | detect | false | /v1/vision/detect | READY | PASS | person 0.89 on bus.jpg |
| yolov8s | detect | false | /v1/vision/detect | READY | PASS | person 0.91 on bus.jpg |
| zoobot | embedding | false | /v1/vision/embed | READY | PASS | id=zoobot-15m; galaxy embedding |

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
| qwen25-vl-72b | none | — | — | ✅ | v2 | 22/22 |
| qwen25-vl-72b-awq | none | — | — | ✅ | v2 | 16/18 |
| qwen25-vl-7b | none | — | hermes | ✅ | v2 | 22/22 |
| qwen25-vl-3b | none | — | — | ✅ | v2 | 18/18 |
| gemma-4-26b-a4b | toggle | gemma4 | gemma4 | ✅ | v2 | 30/2 (32) |
| gemma-3-4b-it | none | — | — | ✅ | v2 | 17/20 |
| medgemma-27b-it | none | — | — | ✅ | v2 | 17/20 |
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
