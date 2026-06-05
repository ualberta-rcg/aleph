# Model Test Status -- Cluster 230

Master tracker for the per-model verification loop. Gateway ClusterIP `http://10.43.79.101:80` (in-cluster only). Source of truth: this local repo.

Test-status legend: `PENDING` (not yet verified by this loop) - `PASS` - `FIXED` (was broken, now PASS) - `FAIL` (hard fail, see note).

Cluster-state at snapshot start: **93 READY**, **58 NOT-READY**, **6 NO-ISVC** (of 157).

| Model | Type | GPU | Primary endpoint | Cluster state | Test status | Note |
|---|---|---|---|---|---|---|
| ablang2 | embedding | false | /v1/embeddings | READY | FIXED | embeddings+batch PASS; /v1/restore was broken, fixed (heavy/light pairs), now PASS |
| aeneas | structure | true | /v1/science/predict | READY | PENDING |  |
| agront | embedding | true | /v1/embeddings | READY | PENDING | had TEST.md (pre-loop) |
| aion | embed | false | /v1/science/embed | READY | PENDING | had TEST.md (pre-loop) |
| alphafold2 | structure-prediction | true | /v1/science/predict | READY | PENDING | had TEST.md (pre-loop) |
| ancient-greek-bert | embedding | true | /v1/science/embed | READY | PENDING |  |
| ankh | embedding | true | /v1/embeddings | READY | PENDING |  |
| arcface | face | false | /v1/vision/face | READY | PENDING | had TEST.md (pre-loop) |
| astroclip | embed | true | /v1/science/embed | READY | PENDING |  |
| astropt | embed | true | /v1/science/embed | READY | PENDING |  |
| astrosage | chat | true | /v1/chat/completions | READY | PENDING |  |
| aurora | forecast | true | /v1/science/forecast | READY | PENDING |  |
| bge-m3 | embedding | false | /v1/embeddings | READY | PASS | embeddings batch multilingual, dim=1024, matches card |
| bge-reranker-v2-m3 | reranker | false | /v1/rerank | READY | PENDING |  |
| bge-small |  |  | - | READY | PENDING |  |
| biobert | embedding | true | /v1/embeddings | READY | PENDING |  |
| biogpt | generate | true | /v1/completions | READY | PENDING |  |
| biolinkbert | embedding | true | /v1/embeddings | READY | PENDING |  |
| biomed-roberta | embedding | true | /v1/embeddings | READY | PENDING |  |
| biomedbert-large | embedding | true | /v1/science/embed | READY | PENDING |  |
| biomedbert | embedding | false | /v1/embeddings | READY | PENDING | had TEST.md (pre-loop) |
| biomedclip | embed | true | /v1/embeddings | READY | PENDING |  |
| biot5 | science-generate | false | /v1/science/generate | READY | PENDING | had TEST.md (pre-loop) |
| birdnet-analyzer | audio-classification | false | /v1/science/identify | READY | PENDING | had TEST.md (pre-loop) |
| boltz-1 | structure | true | /v1/science/predict | READY | PENDING |  |
| borzoi | predict | true | /v1/science/predict | READY | PENDING |  |
| brainlm | embed | true | /v1/embeddings | READY | PENDING |  |
| caduceus | embedding | true | /v1/embeddings | NOT-READY | PENDING |  |
| chem-t5 | science-generate | false | /v1/science/generate | READY | PENDING | had TEST.md (pre-loop) |
| chemberta | embedding | false | /v1/embeddings | READY | PENDING | had TEST.md (pre-loop) |
| chemgpt-19m | generate | true | /v1/science/generate | READY | PENDING |  |
| chemgpt | generate | true | /v1/science/generate | READY | PENDING |  |
| chgnet | force-field | true | /v1/science/energy | NOT-READY | PENDING |  |
| chronos-bolt | forecast | false | /v1/forecast | READY | PENDING | had TEST.md (pre-loop) |
| clap | embedding | false | /v1/embeddings | READY | PENDING | had TEST.md (pre-loop) |
| clay | embed | false | /v1/science/embed | READY | PENDING |  |
| climatebert | classification | false | /v1/science/classify | READY | PENDING | had TEST.md (pre-loop) |
| climax | forecast | true | /v1/science/forecast | READY | PENDING |  |
| clinical-longformer | embedding | true | /v1/science/embed | READY | PENDING |  |
| clinicalbert | embedding | false | /v1/embeddings | READY | PENDING | had TEST.md (pre-loop) |
| command-r-7b | chat | ? | /v1/chat/completions | READY | PENDING |  |
| croma | segment | true | /v1/embeddings | READY | PENDING |  |
| crysta-llm | chat | true | /v1/science/generate | NOT-READY | PENDING |  |
| deepseek-v2-lite-16b | chat | true | /v1/chat/completions | NOT-READY | PENDING |  |
| depth-anything | depth | false | /v1/vision/depth | READY | PENDING |  |
| diffdock | dock | true | /v1/dock | NOT-READY | PENDING |  |
| dino-vit-b8 | embed | false | /v1/vision/embed | READY | PENDING | had TEST.md (pre-loop) |
| dnabert-2 | embedding | false | /v1/embeddings | READY | PENDING | had TEST.md (pre-loop) |
| dnabert-s | embedding | false | /v1/embeddings | READY | PENDING | had TEST.md (pre-loop) |
| dust3r | 3d | true | /v1/science/reconstruct | NOT-READY | PENDING |  |
| earthpt | embed | true | /v1/science/predict | NOT-READY | PENDING |  |
| efficientnet-b0 | classify | false | /v1/vision/classify | READY | PENDING | had TEST.md (pre-loop) |
| enformer | predict | true | /v1/science/predict | NOT-READY | PENDING |  |
| ernierna | embedding | true | /v1/science/embed | NOT-READY | PENDING |  |
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
| galileo | classify | false | /v1/embeddings | READY | PENDING |  |
| gemma-3-4b-it | chat | ? | /v1/chat/completions | READY | PENDING |  |
| gemma-4-26b-a4b | chat | true | /v1/chat/completions | NOT-READY | PENDING |  |
| gena-lm-large | embedding | true | /v1/science/embed | NOT-READY | PENDING |  |
| gena-lm | embedding | true | /v1/embeddings | NOT-READY | PENDING |  |
| geneformer-v2 | embedding | ? | - | NO-ISVC | PENDING |  |
| geneformer | embedding | true | /v1/embed | NOT-READY | PENDING |  |
| geogalactica | chat | true | /v1/chat/completions | NOT-READY | PENDING |  |
| gpt-oss-120b | chat | true | /v1/chat/completions | NOT-READY | PENDING |  |
| gpt-oss-20b | chat | ? | /v1/chat/completions | READY | PENDING |  |
| granite-geospatial-biomass | classify | true | /v1/science/predict | NOT-READY | PENDING |  |
| granite-geospatial-ocean | classify | true | /v1/science/embed | NOT-READY | PENDING |  |
| graphcast | forecast | false | /v1/science/predict | READY | PENDING |  |
| hyenadna | embedding | false | /v1/embeddings | READY | PENDING |  |
| ithaca | predict | true | /v1/science/predict | NOT-READY | PENDING |  |
| kandinsky-3 | image | true | /v1/images/generations | NO-ISVC | PENDING |  |
| labram | embed | false | /v1/science/embed | READY | PENDING |  |
| lag-llama | forecast | true | /v1/science/forecast | READY | PENDING |  |
| leandojo | embed | true | /v1/science/retrieve | READY | PENDING |  |
| led | stub | false | - | NO-ISVC | PENDING |  |
| ligandmpnn | design | false | /v1/design | READY | PENDING |  |
| longformer | stub | false | - | NO-ISVC | PENDING |  |
| mace-mh-1 | force-field | true | /v1/science/predict | NOT-READY | PENDING |  |
| mace-mp-0 | force-field | false | /v1/science/energy | READY | PENDING |  |
| mace-mp | force-field | true | /v1/science/predict | NOT-READY | PENDING |  |
| maskrcnn | segment | false | /v1/vision/segment | READY | PENDING |  |
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
| multilingual-e5-small | embedding | false | /embed | READY | PENDING |  |
| naturecode-earth | embed | true | /v1/science/predict | NOT-READY | PENDING |  |
| neuralgcm | forecast | false | /v1/science/predict | READY | PENDING |  |
| nucleotide-transformer | embedding | true | /v1/embeddings | READY | PENDING |  |
| oceangpt-30b | chat | true | /v1/chat/completions | NOT-READY | PENDING |  |
| omnigenome | embedding | false | /v1/science/predict | READY | PENDING |  |
| pangu-weather | forecast | true | /v1/science/forecast | NOT-READY | PENDING |  |
| phi-4-reasoning | chat | true | /v1/chat/completions | NOT-READY | PENDING |  |
| presto | classify | false | /v1/embeddings | READY | PENDING |  |
| prithvi-eo | embed | true | /v1/embed | NOT-READY | PENDING |  |
| prithvi-wxc | embed | true | /v1/science/forecast | NOT-READY | PENDING |  |
| progen2 | chat | true | /v1/completions | NOT-READY | PENDING |  |
| prokbert | embedding | true | /v1/embeddings | READY | PENDING |  |
| prostt5 | embedding | true | /v1/translate | NOT-READY | PENDING |  |
| proteinmpnn | design | true | /v1/design | READY | PENDING |  |
| protgpt2 | chat | true | /v1/completions | NOT-READY | PENDING |  |
| pubmedbert | embedding | false | /v1/embeddings | READY | PENDING | had TEST.md (pre-loop) |
| qwen25-vl-3b | chat | true | /v1/chat/completions | NOT-READY | PENDING |  |
| qwen25-vl-7b | chat | ? | /v1/chat/completions | READY | PENDING |  |
| qwen35-122b | chat | ? | /v1/chat/completions | READY | PENDING |  |
| retinanet | detect | false | /v1/vision/detect | READY | PENDING |  |
| rita | embedding | false | /v1/science/generate | READY | PENDING | had TEST.md (pre-loop) |
| rnabert | embedding | true | /v1/science/embed | NOT-READY | PENDING |  |
| rnafm | embedding | true | /v1/science/embed | NOT-READY | PENDING |  |
| rnamsm | embedding | true | /v1/science/embed | READY | PENDING |  |
| sapbert | embedding | true | /v1/science/embed | READY | PENDING |  |
| saprot-650m | embedding | true | /v1/embeddings | NOT-READY | PENDING |  |
| satmae | embed | false | /v1/science/embed | READY | PENDING |  |
| scgpt | embedding | true | /v1/embeddings | NOT-READY | PENDING |  |
| scibert | embedding | false | /v1/embeddings | READY | PENDING | had TEST.md (pre-loop) |
| science-embed | embedding | ? | - | NO-ISVC | PENDING |  |
| scincl | embedding | true | /v1/embeddings | READY | PENDING |  |
| seisbench | classify | true | /v1/science/detect | READY | PENDING |  |
| speaches | standalone | true | - | NO-ISVC | PENDING |  |
| specter2 | embedding | false | /v1/embeddings | READY | PENDING | had TEST.md (pre-loop) |
| splicebert | embedding | false | /v1/embeddings | READY | PENDING |  |
| stanford-deidentifier | deidentify | true | /v1/science/deidentify | READY | PENDING |  |
| sundial | forecast | false | /v1/science/forecast | READY | PENDING |  |
| surya | forecast | true | /v1/science/forecast | NOT-READY | PENDING |  |
| terramind-flood | classify | true | /v1/science/classify | NOT-READY | PENDING |  |
| thor | forecast | true | /v1/science/embed | NOT-READY | PENDING |  |
| time-moe | forecast | true | /v1/forecast | NOT-READY | PENDING |  |
| timer-xl-1b | forecast | true | /v1/forecast | NOT-READY | PENDING |  |
| timer | forecast | true | /v1/forecast | NOT-READY | PENDING |  |
| timesfm | forecast | true | /v1/forecast | NOT-READY | PENDING |  |
| tinyllama | chat | false | /v1/chat/completions | READY | PENDING | had TEST.md (pre-loop) |
| totalsegmentator | segment | true | /v1/science/segment | NOT-READY | PENDING |  |
| ttm | forecast | true | /v1/science/forecast | READY | PENDING |  |
| uma-m | force-field | true | /v1/science/predict | NOT-READY | PENDING |  |
| xtts-v2 | tts | true | /v1/audio/speech | READY | PENDING |  |
| yolov8n | detect | false | /v1/vision/detect | READY | PENDING | had TEST.md (pre-loop) |
| yolov8s | detect | false | /v1/vision/detect | READY | PENDING | had TEST.md (pre-loop) |
| zoobot | classify | false | /v1/vision/embed | READY | PENDING |  |
