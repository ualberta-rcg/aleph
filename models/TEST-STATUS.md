# Model Test Status -- Cluster 230

Master tracker for the per-model verification loop. Gateway ClusterIP `http://10.43.79.101:80` (in-cluster only). Source of truth: this local repo.

Test-status legend: `PENDING` (not yet verified by this loop) - `PASS` - `FIXED` (was broken, now PASS) - `FAIL` (hard fail, see note).

Cluster-state at snapshot start: **93 READY**, **58 NOT-READY**, **6 NO-ISVC** (of 157).

| Model | Type | GPU | Primary endpoint | Cluster state | Test status | Note |
|---|---|---|---|---|---|---|
| ablang2 | embedding | false | /v1/embeddings | READY | FIXED | embeddings+batch PASS; /v1/restore was broken, fixed (heavy/light pairs), now PASS |
| aeneas | structure | true | /v1/science/predict | READY | FAIL | input alphabet lacks [/# gap chars + JAX activator timeout; needs research |
| agront | embedding | true | /v1/embeddings | READY | PASS | 1500-dim DNA |
| aion | embed | false | /v1/science/embed | READY | FIXED | rewrote to real AION CodecManager API; legacy_image + photometry -> 768-dim; was non-functional |
| alphafold2 | structure-prediction | true | /v1/science/predict | READY | PASS | demo folds seq -> PDB |
| ancient-greek-bert | embedding | true | /v1/science/embed | READY | PASS | 768-dim (field: text) |
| ankh | embedding | true | /v1/embeddings | READY | FIXED | T5 fp16->fp32 NaN fix; 768-dim protein PASS |
| arcface | embedding | false | /v1/vision/face | READY | PASS | id=arcface-resnet100; face embedding |
| astroclip | embed | true | /v1/science/embed | READY | FAIL | AstroCLIP lib not installed; demo-only stub |
| astropt | embed | true | /v1/science/embed | READY | FAIL | patchify preprocessing wrong (needs 32x32x3 tokens) |
| astrosage | chat | true | /v1/chat/completions | READY | PASS | OpenAI + Anthropic endpoints both work |
| aurora | forecast | true | /v1/science/forecast | READY | PASS | full weather batch -> 6h forecast |
| bge-m3 | embedding | false | /v1/embeddings | READY | PASS | embeddings batch multilingual, dim=1024, matches card |
| bge-reranker-v2-m3 | reranker | false | /v1/rerank | READY | PASS | /v1/rerank correct ranking (panda docs top), scores OK |
| bge-small |  |  | - | READY | PENDING |  |
| biobert | embedding | true | /v1/embeddings | READY | PASS | 768-dim |
| biogpt | generate | true | /v1/completions | READY | PASS | coherent biomedical text completion |
| biolinkbert | embedding | true | /v1/embeddings | READY | PASS | 768-dim |
| biomed-roberta | embedding | true | /v1/embeddings | READY | PASS | 768-dim |
| biomedbert-large | embedding | true | /v1/science/embed | READY | PASS | 1024-dim (field: text) |
| biomedbert | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id biomedbert-110m) |
| biomedclip | embed | true | /v1/embeddings | READY | PASS | text_embeddings (texts/images) |
| biot5 | science-generate | false | /v1/science/generate | READY | FIXED | task-specific checkpoints + SELFIES; mol2text & text2mol correct (was garbage) |
| birdnet-analyzer | audio-classification | false | /v1/science/identify | READY | PASS | end-to-end OK; synthetic tone -> no detections (expected) |
| boltz-1 | structure | true | /v1/science/predict | READY | FAIL | torch runtime error during folding; needs deep-fix |
| borzoi | predict | true | /v1/science/predict | READY | PASS | genomics: 6144 tracks x 16 bins |
| brainlm | embed | true | /v1/embeddings | READY | FAIL | ViT-MAE API unpack error; needs fMRI patch fix |
| caduceus | embedding | true | /v1/embeddings | NOT-READY | FAIL | mamba_ssm/selective_scan_cuda torch-CUDA ABI mismatch |
| chem-t5 | science-generate | false | /v1/science/generate | READY | FIXED | exact GT4SD prompt templates; caption+forward_synthesis correct (was wrong) |
| chemberta | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id chemberta-125m) |
| chemgpt-19m | generate | true | /v1/science/generate | READY | PASS | SELFIES molecule generation |
| chemgpt | generate | true | /v1/science/generate | READY | PASS | id=chemgpt-1.2b; SELFIES molecule generation |
| chgnet | force-field | true | /v1/science/energy | NOT-READY | PENDING |  |
| chronos-bolt | forecast | false | /v1/forecast | READY | PASS | quantile forecast on 16-pt series |
| clap | embedding | false | /v1/embeddings | READY | PASS | text emb 512-dim + zero-shot audio classify (dog 0.73) |
| clay | embed | false | /v1/science/embed | READY | FIXED | rewrote to Clay v1.5 datacube dict API; cls embedding PASS |
| climatebert | classification | false | /v1/science/classify | READY | PASS | net-zero 0.9988 |
| climax | forecast | true | /v1/science/forecast | READY | PASS | needs valid ERA5 var names (e.g. 2m_temperature) |
| clinical-longformer | embedding | true | /v1/science/embed | NOT-READY | FAIL | hangs on CPU (gpu=true but no CUDA use); needs GPU/attention fix |
| clinicalbert | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id clinicalbert-110m) |
| command-r-7b | chat | true | /v1/chat/completions | READY | PASS | OpenAI + Anthropic |
| croma | segment | true | /v1/embeddings | READY | FIXED | dict output extraction (joint/optical/SAR GAP) |
| crysta-llm | chat | true | /v1/science/generate | READY | PASS | crystal structure gen from formula (progress-deadline fix) |
| deepseek-v2-lite-16b | chat | true | /v1/chat/completions | READY | PASS | v0.20.2 (std); gpumem 45GB + max-model-len 8192; correct answers |
| depth-anything | depth | false | /v1/vision/depth | READY | FIXED | fixed k8s_name 404 + PNG output; PASS |
| diffdock | dock | true | /v1/dock | NOT-READY | PENDING |  |
| dino-vit-b8 | embedding | false | /v1/vision/embed | READY | PASS | image embedding |
| dnabert-2 | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id dnabert-2-117m) |
| dnabert-s | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id dnabert-s) |
| dust3r | 3d | true | /v1/science/reconstruct | NOT-READY | PENDING |  |
| earthpt | embed | true | /v1/science/predict | NOT-READY | PENDING |  |
| efficientnet-b0 | classify | false | /v1/vision/classify | READY | FIXED | lite4: fixed preproc+double-softmax+labels; minibus 0.63 |
| enformer | predict | true | /v1/science/predict | NOT-READY | FAIL | isvc never deployed (READY=False 11h); needs recreate |
| ernierna | embedding | true | /v1/science/embed | NOT-READY | FAIL | isvc never deployed (READY=False 10h); needs recreate/fix |
| esm1b | embedding | true | /v1/embeddings | READY | PASS | 1280-dim protein (recreated) |
| esm2-150m | embedding | true | /v1/embeddings | READY | PASS | 640-dim protein (recreated) |
| esm2-35m | embedding | true | /v1/embeddings | READY | PASS | 480-dim protein |
| esm2-3b | embedding | true | /v1/embeddings | READY | PASS | 2560-dim protein (recreate cleared) |
| esm2-650m | embedding | true | /v1/embeddings | READY | PASS | 1280-dim protein |
| esmc-300m | embedding | true | /v1/embeddings | READY | PASS | 960-dim (recreated) |
| esmfold | structure | true | /v1/structure | READY | PASS | folds protein -> PDB |
| fengwu | forecast | true | /v1/science/forecast | NOT-READY | PENDING |  |
| finbert | classify | true | /v1/science/classify | READY | PASS | sentiment positive 0.96 |
| fourcastnet3 | forecast | true | /v1/science/forecast | NOT-READY | PENDING |  |
| galileo | classify | false | /v1/embeddings | READY | FAIL | numpy fixed; model loads as raw state_dict - needs deep fix |
| gemma-3-4b-it | chat | true | /v1/chat/completions | READY | PASS | OpenAI + Anthropic |
| gemma-4-26b-a4b | chat | true | /v1/chat/completions | READY | PASS | 26B MoE fp8 (progress-deadline fix); correct answers |
| gena-lm-large | embedding | true | /v1/science/embed | READY | FIXED | output_hidden_states (was returning vocab logits); 1024-dim |
| gena-lm | embedding | true | /v1/embeddings | READY | PASS | 768-dim DNA (recreated) |
| geneformer | embedding | true | /v1/embed | READY | PASS | needs gene_ids token IDs (recreated) |
| geogalactica | chat | true | /v1/chat/completions | NOT-READY | FAIL | gated HF repo geobrain-ai/geogalactica (403); needs access approval |
| gpt-oss-120b | chat | true | /v1/chat/completions | READY | FIXED | TP2 ~200tok/s; v0.20.2; full GPUs (no gpumem) + --disable-custom-all-reduce (HAMi custom-AR stall); CUDA_DISABLE_CONTROL removed (unneeded); reasoning+OpenAI+Anthropic |
| gpt-oss-20b | chat | true | /v1/chat/completions | READY | PASS | OpenAI + Anthropic |
| granite-geospatial-biomass | classify | true | /v1/science/predict | NOT-READY | PENDING |  |
| granite-geospatial-ocean | classify | true | /v1/science/embed | NOT-READY | PENDING |  |
| graphcast | forecast | false | /v1/science/predict | READY | PASS | demo mode (real ERA5 not via API by design) |
| hyenadna | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=256 (id hyenadna-6.5m) |
| ithaca | predict | true | /v1/science/predict | NOT-READY | PENDING |  |
| kandinsky-3 | image | true | /v1/images/generations | NO-ISVC | PENDING |  |
| labram | embed | false | /v1/science/embed | READY | FAIL | needs 128 canonical channels or ch_names - needs deep fix |
| lag-llama | forecast | true | /v1/science/forecast | READY | FIXED | torch2.6 weights_only + create_predictor(module=) API |
| leandojo | embed | true | /v1/science/retrieve | READY | PASS | premise retrieval w/ scores |
| ligandmpnn | design | false | /v1/design | READY | FIXED | checkpoints+args+optional-openfold; 1CRN design near-native PASS |
| mace-mh-1 | force-field | true | /v1/science/predict | NOT-READY | PENDING |  |
| mace-mp-0 | force-field | false | /v1/science/energy | READY | FIXED | fixed pbc-zero-cell garbage + PVC model cache; water -14.15eV PASS |
| mace-mp | force-field | true | /v1/science/predict | NOT-READY | PENDING |  |
| maskrcnn | segment | false | /v1/vision/segment | READY | PASS | id=maskrcnn-resnet50; person 0.999 + mask |
| mast3r | 3d | true | /v1/science/reconstruct | NOT-READY | PENDING |  |
| matscibert | embedding | true | /v1/science/embed | READY | PASS | 768-dim (field: text) |
| mattergen | generate | true | /v1/science/generate | NOT-READY | PENDING |  |
| mattersim | force-field | true | /v1/science/predict | NOT-READY | PENDING |  |
| medcpt-article | embedding | true | /v1/embeddings | READY | PASS | 768-dim PubMed article (recreated) |
| medcpt-query | embedding | true | /v1/embeddings | READY | PASS | 768-dim PubMed query (recreated) |
| medgemma-27b-it | chat | true | /v1/chat/completions | READY | PASS | 27B dense TP2 ~20tok/s; v0.20.2 (fixed --limit-mm-per-prompt JSON); full GPUs + --disable-custom-all-reduce; correct medical answers |
| medsam | segment | true | /v1/science/segment | READY | PASS | image as HxWx3 pixel array + boxes -> masks |
| megadetector | detect | true | /v1/detect | READY | PASS | bbox detections w/ conf |
| moirai-large | forecast | true | /v1/science/forecast | READY | PASS | mean+samples forecast |
| moirai-moe | forecast | true | /v1/forecast | NOT-READY | PENDING |  |
| moirai | forecast | true | /v1/forecast | NOT-READY | PENDING |  |
| molformer | embedding | true | /v1/science/embed | READY | PASS | 768-dim (field: smiles) |
| moment | forecast | true | /v1/forecast | READY | FIXED | output indexing (chan vs horizon); needs 512-len input; 96-step horizon |
| multilingual-e5-small | embedding | false | /v1/embeddings | READY | PASS | 384-dim text embedding |
| naturecode-earth | embed | true | /v1/science/predict | NOT-READY | PENDING |  |
| neuralgcm | forecast | false | /v1/science/predict | READY | PASS | demo mode (real ERA5 not via API by design) |
| nucleotide-transformer | embedding | true | /v1/embeddings | READY | PASS | 1024-dim DNA |
| oceangpt-30b | chat | true | /v1/chat/completions | READY | FIXED | 30B-A3B MoE TP2 ~73tok/s; v0.20.2; full GPUs + --disable-custom-all-reduce (no CUDA_DISABLE_CONTROL); OpenAI+Anthropic |
| omnigenome | embedding | false | /v1/science/predict | READY | PASS | id=omnigenome-186m; RNA embedding |
| pangu-weather | forecast | true | /v1/science/forecast | NOT-READY | PENDING |  |
| phi-4-reasoning | chat | true | /v1/chat/completions | READY | PASS | v0.20.2 (std; dropped --enable-reasoning, removed in 0.20.2); correct answers; reasoning_content not separated by deepseek_r1 parser (cosmetic) |
| presto | classify | false | /v1/embeddings | READY | FAIL | band-layout mismatch - needs correct presto format |
| prithvi-eo | embed | true | /v1/embed | NOT-READY | PENDING |  |
| prithvi-wxc | embed | true | /v1/science/forecast | NOT-READY | PENDING |  |
| progen2 | generate | true | /v1/completions | NOT-READY | FAIL | ProgressDeadlineExceeded; init download too slow, needs progress-deadline bump |
| prokbert | embedding | true | /v1/embeddings | READY | PASS | 384-dim DNA |
| prostt5 | translate | true | /v1/translate | READY | PASS | AA->3Di structural alphabet (recreated) |
| proteinmpnn | design | true | /v1/design | READY | PASS | designs sequences from PDB w/ scores |
| protgpt2 | generate | true | /v1/completions | READY | PASS | de novo protein generation (recreated) |
| pubmedbert | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id pubmedbert) |
| qwen25-vl-3b | chat | true | /v1/chat/completions | READY | PASS | v0.20.2 (std; fixed --limit-mm-per-prompt JSON); gpumem 24GB; chat OK |
| qwen25-vl-7b | chat | true | /v1/chat/completions | READY | PASS | OpenAI + Anthropic + vision (image_url) |
| qwen3-235b | chat | true | /v1/chat/completions | READY | PASS | 235B-A22B AWQ-int4 MoE TP4 ~67tok/s; v0.20.2; ported from 232 (tclf90 repo deleted -> QuantTrio); whole node (4 GPUs, no gpumem) + --disable-custom-all-reduce + awq_marlin; correct math + tool-calling (hermes) |
| qwen35-122b | chat | true | /v1/chat/completions | READY | FIXED | 122B FP8 MoE TP4 ~65tok/s; v0.20.2; whole node (4 GPUs, no gpumem) + --disable-custom-all-reduce; unpinned; reasoning-parser=qwen3; correct answers |
| retinanet | detect | false | /v1/vision/detect | READY | PASS | id=retinanet-resnet50; bus 0.95 |
| rita | embedding | false | /v1/science/generate | READY | PASS | protein generation: greedy + sampling produce valid sequences |
| rnabert | embedding | true | /v1/science/embed | READY | PASS | 120-dim RNA (recreated) |
| rnafm | embedding | true | /v1/science/embed | READY | PASS | 640-dim RNA (recreated) |
| rnamsm | embedding | true | /v1/science/embed | READY | PASS | 768-dim RNA (field: sequence) |
| sapbert | embedding | true | /v1/science/embed | READY | PASS | 768-dim biomedical |
| saprot-650m | embedding | true | /v1/embeddings | READY | PASS | 1280-dim (AA+3Di tokens; recreated) |
| satmae | embed | false | /v1/science/embed | READY | PASS | HxW RGB -> cls embedding |
| scgpt | embedding | true | /v1/embeddings | READY | FIXED | _encode needs src_key_padding_mask; 512-dim |
| scibert | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id scibert-110m) |
| science-embed | embedding | ? | - | NO-ISVC | CANCELLED | superseded by individual ESM2/NT ISVCs; not deployed |
| scincl | embedding | true | /v1/embeddings | READY | PASS | 768-dim scientific paper |
| seisbench | classify | true | /v1/science/detect | READY | PASS | phasenet runs (P/S detection) |
| speaches | standalone | true | - | NO-ISVC | PENDING |  |
| specter2 | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id specter2-110m) |
| splicebert | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id splicebert-86m) |
| stanford-deidentifier | deidentify | true | /v1/science/deidentify | READY | PASS | PHI entities (PATIENT/DATE/HOSPITAL) |
| sundial | forecast | false | /v1/science/forecast | READY | FIXED | fixed input shape + pinned transformers 4.40.2; forecast+quantiles PASS |
| surya | forecast | true | /v1/science/forecast | NOT-READY | PENDING |  |
| terramind-flood | classify | true | /v1/science/classify | NOT-READY | PENDING |  |
| thor | embed | true | /v1/science/embed | NOT-READY | FAIL | ProgressDeadlineExceeded; init too slow (+terratorch lib check) |
| time-moe | forecast | true | /v1/forecast | NOT-READY | PENDING |  |
| timer-xl-1b | forecast | true | /v1/forecast | NOT-READY | PENDING |  |
| timer | forecast | true | /v1/forecast | NOT-READY | PENDING |  |
| timesfm | forecast | true | /v1/forecast | NOT-READY | PENDING |  |
| tinyllama | chat | false | /v1/chat/completions | READY | PASS | OpenAI + Anthropic PASS; streaming 500 (gateway SSE, cross-cutting) |
| totalsegmentator | segment | true | /v1/science/segment | NOT-READY | PENDING |  |
| ttm | forecast | true | /v1/science/forecast | READY | FIXED | past_values shape [batch,time,chan]; 96-step forecast |
| uma-m | force-field | true | /v1/science/predict | NOT-READY | PENDING |  |
| xtts-v2 | tts | true | /v1/audio/speech | READY | PASS | text->WAV 155KB audio |
| yolov8n | detect | false | /v1/vision/detect | READY | PASS | person 0.89 on bus.jpg |
| yolov8s | detect | false | /v1/vision/detect | READY | PASS | person 0.91 on bus.jpg |
| zoobot | embedding | false | /v1/vision/embed | READY | PASS | id=zoobot-15m; galaxy embedding |
