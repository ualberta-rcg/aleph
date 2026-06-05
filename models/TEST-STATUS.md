# Model Test Status -- Cluster 230

Master tracker for the per-model verification loop. Gateway ClusterIP `http://10.43.79.101:80` (in-cluster only). Source of truth: this local repo.

Test-status legend: `PENDING` (not yet verified by this loop) - `PASS` - `FIXED` (was broken, now PASS) - `FAIL` (hard fail, see note).

Cluster-state at snapshot start: **93 READY**, **58 NOT-READY**, **6 NO-ISVC** (of 157).

| Model | Type | GPU | Primary endpoint | Cluster state | Test status | Note |
|---|---|---|---|---|---|---|
| ablang2 | embedding | false | /v1/embeddings | READY | FIXED | embeddings+batch PASS; /v1/restore was broken, fixed (heavy/light pairs), now PASS |
| aeneas | structure | true | /v1/science/predict | READY | PENDING |  |
| agront | embedding | true | /v1/embeddings | READY | PASS | 1500-dim DNA |
| aion | embed | false | /v1/science/embed | READY | FIXED | rewrote to real AION CodecManager API; legacy_image + photometry -> 768-dim; was non-functional |
| alphafold2 | structure-prediction | true | /v1/science/predict | READY | PENDING | had TEST.md (pre-loop) |
| ancient-greek-bert | embedding | true | /v1/science/embed | READY | PASS | 768-dim (field: text) |
| ankh | embedding | true | /v1/embeddings | READY | FIXED | T5 fp16->fp32 NaN fix; 768-dim protein PASS |
| arcface | embedding | false | /v1/vision/face | READY | PASS | id=arcface-resnet100; face embedding |
| astroclip | embed | true | /v1/science/embed | READY | PENDING |  |
| astropt | embed | true | /v1/science/embed | READY | PENDING |  |
| astrosage | chat | true | /v1/chat/completions | READY | PENDING |  |
| aurora | forecast | true | /v1/science/forecast | READY | PENDING |  |
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
| boltz-1 | structure | true | /v1/science/predict | READY | PENDING |  |
| borzoi | predict | true | /v1/science/predict | READY | PENDING |  |
| brainlm | embed | true | /v1/embeddings | READY | PENDING |  |
| caduceus | embedding | true | /v1/embeddings | NOT-READY | PENDING |  |
| chem-t5 | science-generate | false | /v1/science/generate | READY | FIXED | exact GT4SD prompt templates; caption+forward_synthesis correct (was wrong) |
| chemberta | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id chemberta-125m) |
| chemgpt-19m | generate | true | /v1/science/generate | READY | PASS | SELFIES molecule generation |
| chemgpt | generate | true | /v1/science/generate | READY | PASS | id=chemgpt-1.2b; SELFIES molecule generation |
| chgnet | force-field | true | /v1/science/energy | NOT-READY | PENDING |  |
| chronos-bolt | forecast | false | /v1/forecast | READY | PASS | quantile forecast on 16-pt series |
| clap | embedding | false | /v1/embeddings | READY | PASS | text emb 512-dim + zero-shot audio classify (dog 0.73) |
| clay | embed | false | /v1/science/embed | READY | FIXED | rewrote to Clay v1.5 datacube dict API; cls embedding PASS |
| climatebert | classification | false | /v1/science/classify | READY | PASS | net-zero 0.9988 |
| climax | forecast | true | /v1/science/forecast | READY | PENDING |  |
| clinical-longformer | embedding | true | /v1/science/embed | NOT-READY | FAIL | hangs on CPU (gpu=true but no CUDA use); needs GPU/attention fix |
| clinicalbert | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id clinicalbert-110m) |
| command-r-7b | chat | ? | /v1/chat/completions | READY | PENDING |  |
| croma | segment | true | /v1/embeddings | READY | PENDING |  |
| crysta-llm | chat | true | /v1/science/generate | NOT-READY | PENDING |  |
| deepseek-v2-lite-16b | chat | true | /v1/chat/completions | NOT-READY | PENDING |  |
| depth-anything | depth | false | /v1/vision/depth | READY | FIXED | fixed k8s_name 404 + PNG output; PASS |
| diffdock | dock | true | /v1/dock | NOT-READY | PENDING |  |
| dino-vit-b8 | embedding | false | /v1/vision/embed | READY | PASS | image embedding |
| dnabert-2 | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id dnabert-2-117m) |
| dnabert-s | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id dnabert-s) |
| dust3r | 3d | true | /v1/science/reconstruct | NOT-READY | PENDING |  |
| earthpt | embed | true | /v1/science/predict | NOT-READY | PENDING |  |
| efficientnet-b0 | classify | false | /v1/vision/classify | READY | FIXED | lite4: fixed preproc+double-softmax+labels; minibus 0.63 |
| enformer | predict | true | /v1/science/predict | NOT-READY | PENDING |  |
| ernierna | embedding | true | /v1/science/embed | NOT-READY | FAIL | isvc never deployed (READY=False 10h); needs recreate/fix |
| esm1b | embedding | true | /v1/embeddings | NOT-READY | PENDING |  |
| esm2-150m | embedding | true | /v1/embeddings | NOT-READY | PENDING |  |
| esm2-35m | embedding | true | /v1/embeddings | READY | PENDING |  |
| esm2-3b | embedding | true | /v1/embeddings | NOT-READY | PENDING |  |
| esm2-650m | embedding | true | /v1/embeddings | READY | PENDING |  |
| esmc-300m | embedding | true | /v1/embeddings | NOT-READY | PENDING |  |
| esmfold | structure | true | /v1/structure | NOT-READY | PENDING |  |
| fengwu | forecast | true | /v1/science/forecast | NOT-READY | PENDING |  |
| finbert | classify | true | /v1/science/classify | READY | PENDING |  |
| fourcastnet3 | forecast | true | /v1/science/forecast | NOT-READY | PENDING |  |
| galileo | classify | false | /v1/embeddings | READY | FAIL | numpy fixed; model loads as raw state_dict - needs deep fix |
| gemma-3-4b-it | chat | ? | /v1/chat/completions | READY | PENDING |  |
| gemma-4-26b-a4b | chat | true | /v1/chat/completions | NOT-READY | PENDING |  |
| gena-lm-large | embedding | true | /v1/science/embed | NOT-READY | PENDING |  |
| gena-lm | embedding | true | /v1/embeddings | NOT-READY | PENDING |  |
| geneformer | embedding | true | /v1/embed | NOT-READY | PENDING |  |
| geogalactica | chat | true | /v1/chat/completions | NOT-READY | PENDING |  |
| gpt-oss-120b | chat | true | /v1/chat/completions | NOT-READY | PENDING |  |
| gpt-oss-20b | chat | ? | /v1/chat/completions | READY | PENDING |  |
| granite-geospatial-biomass | classify | true | /v1/science/predict | NOT-READY | PENDING |  |
| granite-geospatial-ocean | classify | true | /v1/science/embed | NOT-READY | PENDING |  |
| graphcast | forecast | false | /v1/science/predict | READY | PASS | demo mode (real ERA5 not via API by design) |
| hyenadna | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=256 (id hyenadna-6.5m) |
| ithaca | predict | true | /v1/science/predict | NOT-READY | PENDING |  |
| kandinsky-3 | image | true | /v1/images/generations | NO-ISVC | PENDING |  |
| labram | embed | false | /v1/science/embed | READY | FAIL | needs 128 canonical channels or ch_names - needs deep fix |
| lag-llama | forecast | true | /v1/science/forecast | READY | PENDING |  |
| leandojo | embed | true | /v1/science/retrieve | READY | PENDING |  |
| ligandmpnn | design | false | /v1/design | READY | FIXED | checkpoints+args+optional-openfold; 1CRN design near-native PASS |
| mace-mh-1 | force-field | true | /v1/science/predict | NOT-READY | PENDING |  |
| mace-mp-0 | force-field | false | /v1/science/energy | READY | FIXED | fixed pbc-zero-cell garbage + PVC model cache; water -14.15eV PASS |
| mace-mp | force-field | true | /v1/science/predict | NOT-READY | PENDING |  |
| maskrcnn | segment | false | /v1/vision/segment | READY | PASS | id=maskrcnn-resnet50; person 0.999 + mask |
| mast3r | 3d | true | /v1/science/reconstruct | NOT-READY | PENDING |  |
| matscibert | embedding | true | /v1/science/embed | READY | PENDING |  |
| mattergen | generate | true | /v1/science/generate | NOT-READY | PENDING |  |
| mattersim | force-field | true | /v1/science/predict | NOT-READY | PENDING |  |
| medcpt-article | embedding | true | /v1/embeddings | NOT-READY | PENDING |  |
| medcpt-query | embedding | true | /v1/embeddings | NOT-READY | PENDING |  |
| medgemma-27b-it | chat | true | /v1/chat/completions | NOT-READY | PENDING |  |
| medsam | segment | true | /v1/science/segment | READY | PENDING |  |
| megadetector | detect | true | /v1/detect | READY | PENDING |  |
| moirai-large | forecast | true | /v1/science/forecast | READY | PENDING |  |
| moirai-moe | forecast | true | /v1/forecast | NOT-READY | PENDING |  |
| moirai | forecast | true | /v1/forecast | NOT-READY | PENDING |  |
| molformer | embedding | true | /v1/science/embed | READY | PENDING |  |
| moment | forecast | true | /v1/forecast | READY | PENDING |  |
| multilingual-e5-small | embedding | false | /v1/embeddings | READY | PASS | 384-dim text embedding |
| naturecode-earth | embed | true | /v1/science/predict | NOT-READY | PENDING |  |
| neuralgcm | forecast | false | /v1/science/predict | READY | PASS | demo mode (real ERA5 not via API by design) |
| nucleotide-transformer | embedding | true | /v1/embeddings | READY | PENDING |  |
| oceangpt-30b | chat | true | /v1/chat/completions | NOT-READY | PENDING |  |
| omnigenome | embedding | false | /v1/science/predict | READY | PASS | id=omnigenome-186m; RNA embedding |
| pangu-weather | forecast | true | /v1/science/forecast | NOT-READY | PENDING |  |
| phi-4-reasoning | chat | true | /v1/chat/completions | NOT-READY | PENDING |  |
| presto | classify | false | /v1/embeddings | READY | FAIL | band-layout mismatch - needs correct presto format |
| prithvi-eo | embed | true | /v1/embed | NOT-READY | PENDING |  |
| prithvi-wxc | embed | true | /v1/science/forecast | NOT-READY | PENDING |  |
| progen2 | chat | true | /v1/completions | NOT-READY | PENDING |  |
| prokbert | embedding | true | /v1/embeddings | READY | PENDING |  |
| prostt5 | embedding | true | /v1/translate | NOT-READY | PENDING |  |
| proteinmpnn | design | true | /v1/design | READY | PENDING |  |
| protgpt2 | chat | true | /v1/completions | NOT-READY | PENDING |  |
| pubmedbert | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id pubmedbert) |
| qwen25-vl-3b | chat | true | /v1/chat/completions | NOT-READY | PENDING |  |
| qwen25-vl-7b | chat | ? | /v1/chat/completions | READY | PENDING |  |
| qwen35-122b | chat | ? | /v1/chat/completions | READY | PENDING |  |
| retinanet | detect | false | /v1/vision/detect | READY | PASS | id=retinanet-resnet50; bus 0.95 |
| rita | embedding | false | /v1/science/generate | READY | PASS | protein generation: greedy + sampling produce valid sequences |
| rnabert | embedding | true | /v1/science/embed | NOT-READY | PENDING |  |
| rnafm | embedding | true | /v1/science/embed | NOT-READY | PENDING |  |
| rnamsm | embedding | true | /v1/science/embed | READY | PENDING |  |
| sapbert | embedding | true | /v1/science/embed | READY | PENDING |  |
| saprot-650m | embedding | true | /v1/embeddings | NOT-READY | PENDING |  |
| satmae | embed | false | /v1/science/embed | READY | PASS | HxW RGB -> cls embedding |
| scgpt | embedding | true | /v1/embeddings | NOT-READY | PENDING |  |
| scibert | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id scibert-110m) |
| science-embed | embedding | ? | - | NO-ISVC | CANCELLED | superseded by individual ESM2/NT ISVCs; not deployed |
| scincl | embedding | true | /v1/embeddings | READY | PENDING |  |
| seisbench | classify | true | /v1/science/detect | READY | PENDING |  |
| speaches | standalone | true | - | NO-ISVC | PENDING |  |
| specter2 | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id specter2-110m) |
| splicebert | embedding | false | /v1/embeddings | READY | PASS | embeddings PASS dim=768 (id splicebert-86m) |
| stanford-deidentifier | deidentify | true | /v1/science/deidentify | READY | PENDING |  |
| sundial | forecast | false | /v1/science/forecast | READY | FIXED | fixed input shape + pinned transformers 4.40.2; forecast+quantiles PASS |
| surya | forecast | true | /v1/science/forecast | NOT-READY | PENDING |  |
| terramind-flood | classify | true | /v1/science/classify | NOT-READY | PENDING |  |
| thor | forecast | true | /v1/science/embed | NOT-READY | PENDING |  |
| time-moe | forecast | true | /v1/forecast | NOT-READY | PENDING |  |
| timer-xl-1b | forecast | true | /v1/forecast | NOT-READY | PENDING |  |
| timer | forecast | true | /v1/forecast | NOT-READY | PENDING |  |
| timesfm | forecast | true | /v1/forecast | NOT-READY | PENDING |  |
| tinyllama | chat | false | /v1/chat/completions | READY | PASS | OpenAI + Anthropic PASS; streaming 500 (gateway SSE, cross-cutting) |
| totalsegmentator | segment | true | /v1/science/segment | NOT-READY | PENDING |  |
| ttm | forecast | true | /v1/science/forecast | READY | PENDING |  |
| uma-m | force-field | true | /v1/science/predict | NOT-READY | PENDING |  |
| xtts-v2 | tts | true | /v1/audio/speech | READY | PENDING |  |
| yolov8n | detect | false | /v1/vision/detect | READY | PASS | person 0.89 on bus.jpg |
| yolov8s | detect | false | /v1/vision/detect | READY | PASS | person 0.91 on bus.jpg |
| zoobot | embedding | false | /v1/vision/embed | READY | PASS | id=zoobot-15m; galaxy embedding |
