# Aleph Model Catalog

Deployment status, capabilities, and operational notes for each model in the Aleph catalog.

| Model | Type | Runtime | Status | Test | Endpoint |
| --- | --- | --- | --- | --- | --- |
| `ablang2` | Embedding | ablang2 + torch | READY | FIXED | `/v1/embeddings` |
| `aeneas` | Structure | JAX + FastAPI | READY | FAIL | `/v1/science/predict` |
| `agront` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/embeddings` |
| `aion` | Embed | Transformers + PyTorch | READY | FIXED | `/v1/science/embed` |
| `alphafold2` | Structure-prediction | JAX + FastAPI | READY | PASS | `/v1/science/predict` |
| `ancient-greek-bert` | Embedding | pytorch | READY | PASS | `/v1/science/embed` |
| `ankh` | Embedding | Transformers + PyTorch | READY | FIXED | `/v1/embeddings` |
| `arcface` | Face | ONNX Runtime | READY | PASS | `/v1/vision/face` |
| `astroclip` | Embed | Lightning + PyTorch | READY | FAIL | `/v1/science/embed` |
| `astropt` | Embed | astropt + PyTorch | READY | FAIL | `/v1/science/embed` |
| `astrosage` | Chat | Transformers + PyTorch | READY | PASS | `/v1/chat/completions` |
| `aurora` | Forecast | microsoft-aurora + PyTorch | READY | PASS | `/v1/science/forecast` |
| `bge-m3` | Embedding | TEI (CPU) | READY | PASS | `/v1/embeddings` |
| `bge-reranker-v2-m3` | Reranker | TEI (CPU) | READY | PASS | `/v1/rerank` |
| `bge-small` | Embedding | TEI (CPU) | READY | PASS | `/v1/embeddings` |
| `biobert` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/embeddings` |
| `biogpt` | Generate | pytorch | READY | PASS | `/v1/completions` |
| `biolinkbert` | Embedding | pytorch | READY | PASS | `/v1/embeddings` |
| `biomed-roberta` | Embedding | pytorch | READY | PASS | `/v1/embeddings` |
| `biomedbert` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/embeddings` |
| `biomedbert-large` | Embedding | pytorch | READY | PASS | `/v1/science/embed` |
| `biomedclip` | Embed | custom | READY | PASS | `/v1/embeddings` |
| `biot5` | Science-generate | Transformers + PyTorch | READY | FIXED | `/v1/science/generate` |
| `birdnet-analyzer` | Audio-classification | tensorflow | READY | PASS | `/v1/science/identify` |
| `boltz-1` | Structure | boltz + torch | READY | FAIL | `/v1/science/predict` |
| `borzoi` | Predict | Transformers + PyTorch | READY | PASS | `/v1/science/predict` |
| `brainlm` | Embed | Transformers + PyTorch | READY | FAIL | `/v1/embeddings` |
| `caduceus` | Embedding | Transformers + PyTorch | NOT-READY | FAIL | `/v1/embeddings` |
| `chem-t5` | Science-generate | Transformers + PyTorch | READY | FIXED | `/v1/science/generate` |
| `chemberta` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/embeddings` |
| `chemgpt` | Generate | pytorch | READY | PASS | `/v1/science/generate` |
| `chemgpt-19m` | Generate | Transformers + PyTorch | READY | PASS | `/v1/science/generate` |
| `chgnet` | Force-field | chgnet + ASE + PyTorch | READY | FIXED | `/v1/science/energy` |
| `chronos-bolt` | Forecast | chronos-forecasting | READY | PASS | `/v1/forecast` |
| `clap` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/embeddings` |
| `clay` | Embed | lightning + claymodel + einops | READY | FIXED | `/v1/science/embed` |
| `climatebert` | Classification | Transformers + PyTorch | READY | PASS | `/v1/science/classify` |
| `climax` | Forecast | PyTorch + timm 0.6.13 | READY | PASS | `/v1/science/forecast` |
| `clinical-longformer` | Embedding | pytorch | NOT-READY | FAIL | `/v1/science/embed` |
| `clinicalbert` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/embeddings` |
| `command-r-7b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `croma` | Segment | PyTorch + CROMA repo | READY | FIXED | `/v1/embeddings` |
| `crysta-llm` | Science-generate | Transformers + PyTorch | READY | PASS | `/v1/science/generate` |
| `deepseek-v2-lite-16b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `depth-anything` | Depth | ONNX Runtime | READY | FIXED | `/v1/vision/depth` |
| `diffdock` | Dock | custom | READY | FIXED | `/v1/dock` |
| `dino-vit-b8` | Embed | ONNX Runtime | READY | PASS | `/v1/vision/embed` |
| `dnabert-2` | Embedding | pytorch | READY | PASS | `/v1/embeddings` |
| `dnabert-s` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/embeddings` |
| `dust3r` | 3D | dust3r (custom) + PyTorch | READY | FIXED | `/v1/science/reconstruct` |
| `earthpt` | Embed | PyTorch (custom nanoGPT implementation) | READY | FIXED | `/v1/science/predict` |
| `efficientnet-b0` | Classify | ONNX Runtime | READY | FIXED | `/v1/vision/classify` |
| `enformer` | Predict | enformer-pytorch + torch | NOT-READY | FAIL | `/v1/science/predict` |
| `ernierna` | Embedding | Transformers + PyTorch | NOT-READY | FAIL | `/v1/science/embed` |
| `esm1b` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/embeddings` |
| `esm2-150m` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/embeddings` |
| `esm2-35m` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/embeddings` |
| `esm2-3b` | Embedding | custom | READY | PASS | `/v1/embeddings` |
| `esm2-650m` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/embeddings` |
| `esmc-300m` | Embedding | esm SDK + torch | READY | PASS | `/v1/embeddings` |
| `esmfold` | Structure | custom | READY | PASS | `/v1/structure` |
| `fengwu` | Forecast | ONNX Runtime | READY | FIXED | `/v1/science/forecast` |
| `finbert` | Classify | Transformers + PyTorch | READY | PASS | `/v1/science/classify` |
| `fourcastnet3` | Forecast | earth2studio + PyTorch | READY | DEMO | `/v1/science/forecast` |
| `galileo` | Classify | PyTorch + galileo repo | READY | FAIL | `/v1/embeddings` |
| `gemma-3-4b-it` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `gemma-4-26b-a4b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `gena-lm` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/embeddings` |
| `gena-lm-large` | Embedding | Transformers + PyTorch | READY | FIXED | `/v1/science/embed` |
| `geneformer` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/embed` |
| `geogalactica` | Chat | vLLM | NOT-READY | FAIL | `/v1/chat/completions` |
| `glm-4-32b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `glm-z1-32b` | Chat | vLLM | READY | FIXED | `/v1/chat/completions` |
| `glm-z1-rumination-32b` | Chat | vLLM | READY | FIXED | `/v1/chat/completions` |
| `gpt-oss-120b` | Chat | vLLM | READY | FIXED | `/v1/chat/completions` |
| `gpt-oss-20b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `granite-geospatial-biomass` | Classify | terratorch + LightningInferenceModel | READY | FIXED | `/v1/science/predict` |
| `granite-geospatial-ocean` | Classify | terratorch + PyTorch | READY | FIXED | `/v1/science/embed` |
| `graphcast` | Forecast | Ray Serve | READY | PASS | `/v1/science/predict` |
| `hyenadna` | Embedding | pytorch | READY | PASS | `/v1/embeddings` |
| `ithaca` | Predict | JAX + FastAPI | READY | FIXED | `/v1/science/predict` |

| `kandinsky-3` | Image | Ray Serve | READY | PASS | `/v1/images/generations` |
| `labram` | Embed | braindecode + PyTorch | READY | FAIL | `/v1/science/embed` |
| `lag-llama` | Forecast | lag-llama + GluonTS + PyTorch | READY | FIXED | `/v1/science/forecast` |
| `leandojo` | Embed | Transformers + PyTorch | READY | PASS | `/v1/science/retrieve` |
| `ligandmpnn` | Design | LigandMPNN CLI + torch | READY | FIXED | `/v1/design` |
| `mace-mh-1` | Force-field | mace-torch + ASE + PyTorch | READY | PASS | `/v1/science/predict` |
| `mace-mp` | Force-field | mace-torch + ASE + PyTorch | READY | PASS | `/v1/science/predict` |
| `mace-mp-0` | Force-field | mace-torch + ASE + PyTorch (CPU) | READY | FIXED | `/v1/science/energy` |
| `maskrcnn` | Segment | pytorch | READY | PASS | `/v1/vision/segment` |
| `mast3r` | 3D | mast3r + dust3r (custom) + PyTorch | READY | FIXED | `/v1/science/match` |
| `matscibert` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/science/embed` |
| `mattergen` | Generate | mattergen-generate CLI + PyTorch Lightning + PyG | NO-ISVC | FAIL | `/v1/science/generate` |
| `mattersim` | Force-field | mattersim + ASE + PyTorch + PyG | READY | PASS | `/v1/science/predict` |
| `medcpt-article` | Embedding | pytorch | READY | PASS | `/v1/embeddings` |
| `medcpt-query` | Embedding | pytorch | READY | PASS | `/v1/embeddings` |
| `medgemma-27b-it` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `medsam` | Segment | Transformers + PyTorch | READY | PASS | `/v1/science/segment` |
| `megadetector` | Detect | megadetector + PyTorch | READY | PASS | `/v1/detect` |
| `moirai` | Forecast | uni2ts + PyTorch + GluonTS | READY | PASS | `/v1/forecast` |
| `moirai-large` | Forecast | uni2ts + PyTorch | READY | PASS | `/v1/science/forecast` |
| `moirai-moe` | Forecast | uni2ts + PyTorch | READY | FAIL | `/v1/forecast` |
| `molformer` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/science/embed` |
| `moment` | Forecast | momentfm + PyTorch | READY | FIXED | `/v1/forecast` |
| `multilingual-e5-small` | Embedding | TEI (CPU) | READY | PASS | `/v1/embeddings` |
| `naturecode-earth` | Embed | forestfm + PyTorch | READY | DEMO | `/v1/science/predict` |
| `neuralgcm` | Forecast | JAX + FastAPI | READY | PASS | `/v1/science/predict` |
| `nucleotide-transformer` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/embeddings` |
| `oceangpt-30b` | Chat | vLLM | READY | FIXED | `/v1/chat/completions` |
| `omnigenome` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/science/predict` |
| `openbiollm-70b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `pangu-weather` | Forecast | ONNX Runtime | READY | FIXED | `/v1/science/forecast` |
| `phi-4-reasoning` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `presto` | Classify | custom | READY | FAIL | `/v1/embeddings` |
| `prithvi-eo` | Embed | terratorch + PyTorch | NOT-READY | FAIL | `/v1/embed` |
| `prithvi-wxc` | Embed | PrithviWxC + PyTorch | READY | PASS | `/v1/science/forecast` |
| `progen2` | Generate | Transformers + PyTorch | NOT-READY | FAIL | `/v1/completions` |
| `prokbert` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/embeddings` |
| `prostt5` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/translate` |
| `proteinmpnn` | Design | pytorch | READY | PASS | `/v1/design` |
| `protgpt2` | Generate | Transformers + PyTorch | READY | PASS | `/v1/completions` |
| `pubmedbert` | Embedding | pytorch | READY | PASS | `/v1/embeddings` |
| `qwen25-coder-32b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `qwen25-vl-3b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `qwen25-vl-72b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `qwen25-vl-7b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `qwen3-235b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `qwen3-32b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `qwen35-122b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `qwen36-27b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `qwen36-35b-a3b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `qwq-32b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `r1-distill-llama-70b` | Chat | vLLM | READY | FIXED | `/v1/chat/completions` |
| `r1-distill-qwen-32b` | Chat | vLLM | READY | PASS | `/v1/chat/completions` |
| `retinanet` | Detect | pytorch | READY | PASS | `/v1/vision/detect` |
| `rita` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/science/generate` |
| `rnabert` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/science/embed` |
| `rnafm` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/science/embed` |
| `rnamsm` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/science/embed` |
| `sapbert` | Embedding | pytorch | READY | PASS | `/v1/science/embed` |
| `saprot-650m` | Embedding | Transformers + PyTorch | READY | PASS | `/v1/embeddings` |
| `satmae` | Embed | PyTorch + timm + safetensors | READY | PASS | `/v1/science/embed` |
| `scgpt` | Embedding | custom | READY | FIXED | `/v1/embeddings` |
| `scibert` | Embedding | pytorch | READY | PASS | `/v1/embeddings` |
| `science-embed` | Embedding | Transformers + PyTorch | NO-ISVC | CANCELLED | `/v1/embeddings` |
| `scincl` | Embedding | pytorch | READY | PASS | `/v1/embeddings` |
| `seisbench` | Classify | seisbench + PyTorch | READY | PASS | `/v1/science/detect` |
| `speaches` | Standalone | standalone | READY | PASS | `/v1/audio/speech, /v1/audio/transcriptions` |
| `specter2` | Embedding | pytorch | READY | PASS | `/v1/embeddings` |
| `splicebert` | Embedding | pytorch | READY | PASS | `/v1/embeddings` |
| `stanford-deidentifier` | Deidentify | pytorch | READY | PASS | `/v1/science/deidentify` |
| `sundial` | Forecast | pytorch | READY | FIXED | `/v1/science/forecast` |
| `surya` | Forecast | pytorch | READY | PASS | `/v1/science/forecast` |
| `terramind-flood` | Classify | terratorch 1.2.1 + PyTorch | NOT-READY | FAIL | `/v1/science/classify` |
| `thor` | Forecast | terratorch + thor_terratorch_ext | NOT-READY | FAIL | `/v1/science/embed` |
| `time-moe` | Forecast | Transformers + PyTorch | READY | PASS | `/v1/forecast` |
| `timer` | Forecast | Transformers + PyTorch | READY | FIXED | `/v1/forecast` |
| `timer-xl-1b` | Forecast | Transformers + PyTorch | NOT-READY | FAIL | `/v1/forecast` |
| `timesfm` | Forecast | custom | NOT-READY | FAIL | `/v1/forecast` |
| `tinyllama` | Chat | llama.cpp | READY | PASS | `/v1/chat/completions` |
| `totalsegmentator` | Segment | totalsegmentator + nnU-Net + PyTorch | READY | FAIL | `/v1/science/segment` |
| `ttm` | Forecast | tsfm_public + PyTorch | READY | FIXED | `/v1/science/forecast` |
| `uma-m` | Force-field | fairchem-core + ASE + torch | BLOCKED | FAIL | `/v1/science/predict` |
| `xtts-v2` | TTS | coqui-tts | READY | PASS | `/v1/audio/speech` |
| `yolov8n` | Detect | ONNX Runtime | READY | PASS | `/v1/vision/detect` |
| `yolov8s` | Detect | ONNX Runtime | READY | PASS | `/v1/vision/detect` |
| `zoobot` | Classify | pytorch | READY | PASS | `/v1/vision/embed` |

## `ablang2`

**Antibody language model (embeddings + CDR restore)**

Best for antibody chain embeddings and CDR restoration. Not general protein LM, chat, vision.

**Status:** READY **Test:** FIXED **Type:** Embedding **Runtime:** ablang2 + torch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/ablang2/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ablang2` | `oxpig/AbLang2` | 48M | fp32 | MIT | proteomics | antibody chain embeddings and CDR restoration | general protein LM, chat, vision |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | 480-dim |
| Restore | yes | /v1/restore |
| Sequence restore | yes | `/v1/restore`; mask with `*` |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| ablang2 + torch | no | CPU | scale-to-zero | 1-2 minutes |

### Notes

- Use `model_to_use='ablang2-paired'`; weights cached on first init (~5 min).
- **Verified 2026-06-05:** embeddings + restore PASS after heavy/light pair fix.
- Gateway `GET /v1/models` is chat-only; use `?all=true` for embedding models.

## `aeneas`

**Generative neural network for contextualising Latin inscriptions (DeepMind Nature 2025)**

Best for Latin inscription restoration, dating, and geographic attribution. Not chat, non-Latin text, production until FAIL fixed.

**Status:** READY **Test:** FAIL **Type:** Structure **Runtime:** JAX + FastAPI  
**Primary endpoint:** `/v1/science/predict` **Model path:** `models/aeneas/`

**Context window:** 750 chars

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `aeneas` | `google-deepmind/predictingthepast` | ~200M | float32 | Apache-2.0 | proteomics | Latin inscription restoration, dating, and geograp | chat, non-Latin text, production until F |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Structure predict | yes | PDB/structure output |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| JAX + FastAPI | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- Input: Latin uppercase, 50–750 chars, `#` for unknown gaps.
- **FAIL:** alphabet lacks `[`/`#` gap handling + JAX activator timeout on GPU cold start.
- Compare with **ithaca** (Greek, `?` gaps) which passed after JAX CUDA fix.

## `agront`

**AgroNT 1B plant-genome DNA language model (embeddings)**

Best for genomics embeddings (1500-dim). Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/agront/`

**Context window:** 1,024 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `agront` | `InstaDeepAI/agro-nucleotide-transformer-1b` | 1B | fp32 | Apache-2.0 | genomics | genomics embeddings (1500-dim) | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | 1500-dim |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 2-4 minutes |

### Notes

- 1500-dim DNA

## `aion`

**AION-base 300M astronomical multimodal foundation model. 39 data types from DESI, SDSS, Gaia, HSC.**

Best for astronomy embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** FIXED **Type:** Embed **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/aion/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `aion` | `polymathic-ai/aion-base` | 300M | fp32 | MIT | astronomy | astronomy embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | no | CPU | scale-to-zero | 1–3 min |

### Notes

- rewrote to real AION CodecManager API; legacy_image + photometry -> 768-dim; was non-functional

## `alphafold2`

**AlphaFold2 protein structure prediction (via ColabFold)**

Best for protein/structure prediction. Not chat, fast approximate folds at scale.

**Status:** READY **Test:** PASS **Type:** Structure-prediction **Runtime:** JAX + FastAPI  
**Primary endpoint:** `/v1/science/predict` **Model path:** `models/alphafold2/`

**Context window:** 1,000 aa

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `alphafold2` | `sokrypton/ColabFold (alphafold2_ptm)` | AF2 (93M weights) | fp32 | Apache-2.0 / MIT (ColabFold) | proteomics | protein/structure prediction | chat, fast approximate folds at scale |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Structure predict | yes | PDB/structure output |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| JAX + FastAPI | yes | HAMi GPU slice | scale-to-zero | 10-15 minutes (first ever); ~1-2 min warm |

### Notes

- demo folds seq -> PDB

## `ancient-greek-bert`

**Ancient Greek BERT — embeddings for Ancient and Byzantine Greek (768-dim)**

Best for scientific-nlp embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** pytorch  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/ancient-greek-bert/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ancient-greek-bert` | `pranaydeeps/Ancient-Greek-BERT` | 110M | fp32 | MIT | scientific-nlp | scientific-nlp embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | yes | HAMi GPU slice | scale-to-zero | ~30s |

### Notes

- 768-dim (field: text)

## `ankh`

**T5-based protein language model from ElnaggarLab (TUM, 113M params)**

Best for proteomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** FIXED **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/ankh/`

**Context window:** 1,024 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ankh` | `ElnaggarLab/ankh-base` | 113M | float16 (GPU) / float32 (CPU) | Apache-2.0 | proteomics | proteomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- T5 fp16->fp32 NaN fix; 768-dim protein PASS

## `arcface`

**ArcFace ResNet-100 — face recognition embeddings (512-dim)**

Best for face verification embeddings (512-dim L2-normalized). Not general vision, non-face images.

**Status:** READY **Test:** PASS **Type:** Face **Runtime:** ONNX Runtime  
**Primary endpoint:** `/v1/vision/face` **Model path:** `models/arcface/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `arcface-resnet100` | `onnx-community/arcface-onnx` | 65M | onnx-fp32 | MIT | computer-vision | face verification embeddings (512-dim L2-normalize | general vision, non-face images |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | 512-dim |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| ONNX Runtime | no | CPU | scale-to-zero | 1-2 minutes |

### Notes

- id=arcface-resnet100; face embedding
- Gateway id `arcface-resnet100` (directory `arcface`).

## `astroclip`

**AstroCLIP cross-modal CLIP for galaxy images and optical spectra. 512-dim joint embedding space.**

Best for astronomy embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** FAIL **Type:** Embed **Runtime:** Lightning + PyTorch  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/astroclip/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `astroclip` | `polymathic-ai/astroclip` | N/A | fp32 | MIT | astronomy | astronomy embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Lightning + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- AstroCLIP lib not installed; demo-only stub

## `astropt`

**AstroPT v2.0 95M autoregressive galaxy image transformer. 8.6M galaxies from SDSS/DESI.**

Best for astronomy embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** FAIL **Type:** Embed **Runtime:** astropt + PyTorch  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/astropt/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `astropt` | `Smith42/astroPT_v2.0` | 95M | fp32 | MIT | astronomy | astronomy embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| astropt + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- patchify preprocessing wrong (needs 32x32x3 tokens)

## `astrosage`

**AstroSage-8B, astronomy/astrophysics LLM**

Best for instruction-following chat in science domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/astrosage/`

**Context window:** 8,192 tokens **Max output:** 8,192 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `astrosage` | `AstroMLab/AstroSage-8B` | 8B | bfloat16 | Llama-3.1-Community-License | science | instruction-following chat in science domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | ~300s |

### Notes

- OpenAI + Anthropic endpoints both work

## `aurora`

**Microsoft Aurora 1.3B atmospheric foundation model for global weather forecasting at 0.25-degree resolution.**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** PASS **Type:** Forecast **Runtime:** microsoft-aurora + PyTorch  
**Primary endpoint:** `/v1/science/forecast` **Model path:** `models/aurora/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `aurora` | `microsoft/aurora` | 1.3B | fp32 | MIT | weather-climate | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| microsoft-aurora + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- full weather batch -> 6h forecast

## `bge-m3`

**BAAI bge-m3 multilingual embeddings, 8K ctx (TEI, CPU)**

Best for nlp embeddings (1024-dim). Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** TEI (CPU)  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/bge-m3/`

**Context window:** 8,192 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `bge-m3` | `BAAI/bge-m3` | 568M | fp32 | MIT | nlp | nlp embeddings (1024-dim) | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | 1024-dim |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| TEI (CPU) | no | CPU | always-on | 30-60 seconds |

### Notes

- embeddings batch multilingual, dim=1024, matches card

## `bge-reranker-v2-m3`

**BAAI bge-reranker-v2-m3 multilingual cross-encoder (TEI, CPU)**

Best for passage reranking for RAG. Not generation or raw embedding.

**Status:** READY **Test:** PASS **Type:** Reranker **Runtime:** TEI (CPU)  
**Primary endpoint:** `/v1/rerank` **Model path:** `models/bge-reranker-v2-m3/`

**Context window:** 8,192 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `bge-reranker-v2-m3` | `BAAI/bge-reranker-v2-m3` | 568M | onnx-fp32 | MIT | nlp | passage reranking for RAG | generation or raw embedding |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Reranking | yes | scores + ordering |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| TEI (CPU) | no | CPU | always-on | 30-60 seconds |

### Notes

- /v1/rerank correct ranking (panda docs top), scores OK

## `bge-small`

**BAAI bge-small-en-v1.5 — lightweight English text embeddings (384-dim, TEI CPU)**

Best for compact English text embeddings for RAG/semantic search. Not multilingual long-context (use bge-m3), chat.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** TEI (CPU)  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/bge-small/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `bge-small` | `BAAI/bge-small-en-v1.5` | 33M | fp32 | MIT | nlp | compact English text embeddings for RAG/semantic s | multilingual long-context (use bge-m3),  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | 384-dim |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| TEI (CPU) | no | CPU | always-on | 30-60 seconds |

### Notes

- 384-dim text embedding

## `biobert`

**BioBERT base (v1.**

Best for biomedical embeddings (768-dim). Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/biobert/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `biobert` | `dmis-lab/biobert-base-cased-v1.1` | 110M | fp32 | Apache-2.0 | biomedical | biomedical embeddings (768-dim) | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | 768-dim |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1-2 minutes |

### Notes

- 768-dim

## `biogpt`

**BioGPT — biomedical text generation from Microsoft**

Best for biomedical-specific generation. Not general chat or unrelated tasks.

**Status:** READY **Test:** PASS **Type:** Generate **Runtime:** pytorch  
**Primary endpoint:** `/v1/completions` **Model path:** `models/biogpt/`

**Context window:** 1,024 tokens **Max output:** 100 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `biogpt` | `microsoft/biogpt` | 347M | fp32 | MIT | biomedical | biomedical-specific generation | general chat or unrelated tasks |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Generation | yes | /v1/completions |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | yes | HAMi GPU slice | scale-to-zero | ~30s |

### Notes

- coherent biomedical text completion

## `biolinkbert`

**BioLinkBERT — biomedical link prediction embeddings (768-dim)**

Best for biomedical embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** pytorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/biolinkbert/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `biolinkbert` | `michiyasunaga/BioLinkBERT-base` | 110M | fp32 | MIT | biomedical | biomedical embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | yes | HAMi GPU slice | scale-to-zero | ~30s |

### Notes

- 768-dim

## `biomed-roberta`

**BioMed-RoBERTa — biomedical text embeddings from Allen AI (768-dim)**

Best for biomedical embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** pytorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/biomed-roberta/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `biomed-roberta` | `allenai/biomed_roberta_base` | 110M | fp32 | Apache-2.0 | biomedical | biomedical embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | yes | HAMi GPU slice | scale-to-zero | ~30s |

### Notes

- 768-dim

## `biomedbert`

**BiomedBERT — biomedical text embeddings (768-dim)**

Best for biomedical embeddings (768-dim). Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/biomedbert/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `biomedbert-110m` | `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract` | 110M | fp32 | MIT | biomedical | biomedical embeddings (768-dim) | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | 768-dim |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | no | CPU | scale-to-zero | 1-2 minutes |

### Notes

- embeddings PASS dim=768 (id biomedbert-110m)
- Gateway id `biomedbert-110m` (directory `biomedbert`).

## `biomedbert-large`

**BiomedBERT-large — large PubMed BERT embeddings (340M, 1024-dim)**

Best for biomedical embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** pytorch  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/biomedbert-large/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `biomedbert-large` | `microsoft/BiomedNLP-BiomedBERT-large-uncased-abstract` | 340M | fp32 | MIT | biomedical | biomedical embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | yes | HAMi GPU slice | scale-to-zero | ~30s |

### Notes

- 1024-dim (field: text)

## `biomedclip`

**BiomedCLIP biomedical vision-language model**

Best for biomedical embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embed **Runtime:** custom  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/biomedclip/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `biomedclip` | `microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224` | ~400M | fp32 | Apache-2.0 | biomedical | biomedical embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |
| Image embed | yes | `text_embeddings` with images |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| custom | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- text_embeddings (texts/images)

## `biot5`

**BioT5 — cross-modal biology+chemistry T5 (SELFIES)**

Best for biochemistry-specific generation. Not general chat or unrelated tasks.

**Status:** READY **Test:** FIXED **Type:** Science-generate **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/generate` **Model path:** `models/biot5/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `biot5` | `QizhiPei/biot5-base` | 0.3B | fp32 | MIT | biochemistry | biochemistry-specific generation | general chat or unrelated tasks |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Generation | yes | /v1/science/generate |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | no | CPU | scale-to-zero | 1-2 minutes |

### Notes

- task-specific checkpoints + SELFIES; mol2text & text2mol correct (was garbage)

## `birdnet-analyzer`

**BirdNET-Analyzer — bird species ID from audio (6000+ species)**

Best for BirdNET-Analyzer — bird species ID from audio (6000+ species). Not unrelated modalities or production if FAIL.

**Status:** READY **Test:** PASS **Type:** Audio-classification **Runtime:** tensorflow  
**Primary endpoint:** `/v1/science/identify` **Model path:** `models/birdnet-analyzer/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `birdnet-analyzer` | `birdnetlib (BirdNET-Analyzer)` | BirdNET v2.4 | fp32 | CC-BY-NC-SA-4.0 | bioacoustics | BirdNET-Analyzer — bird species ID from audio (600 | unrelated modalities or production if FA |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Audio ID | yes | species/event detect |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| tensorflow | no | CPU | scale-to-zero | 3-5 minutes |

### Notes

- end-to-end OK; synthetic tone -> no detections (expected)

## `boltz-1`

**Open-source biomolecular structure prediction (protein/RNA/DNA/ligand, MIT)**

Best for protein/structure prediction. Not chat, fast approximate folds at scale.

**Status:** READY **Test:** FAIL **Type:** Structure **Runtime:** boltz + torch  
**Primary endpoint:** `/v1/science/predict` **Model path:** `models/boltz-1/`

**Context window:** 2,048 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `boltz-1` | `boltz-community/boltz-1` | ~8B | float32 | MIT | proteomics | protein/structure prediction | chat, fast approximate folds at scale |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Structure predict | yes | PDB/structure output |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| boltz + torch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- torch runtime error during folding; needs deep-fix

## `borzoi`

**RNA-seq prediction from 524kb genomic sequences (Calico, ~500M)**

Best for RNA-seq prediction from 524kb genomic sequences (Calico, ~500M). Not unrelated modalities or production if FAIL.

**Status:** READY **Test:** PASS **Type:** Predict **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/predict` **Model path:** `models/borzoi/`

**Context window:** 524,288 bp

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `borzoi` | `johahi/borzoi-replicate-0` | ~500M | float32 | CC-BY-4.0 | genomics | RNA-seq prediction from 524kb genomic sequences (C | unrelated modalities or production if FA |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Prediction | yes | /v1/science/predict |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- genomics: 6144 tracks x 16 bins

## `brainlm`

**BrainLM 650M fMRI foundation model (ViT-MAE) for brain activity embeddings from 424 ROI time-series.**

Best for neuroscience embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** FAIL **Type:** Embed **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/brainlm/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `brainlm` | `vandijklab/BrainLM` | 650M | float32 | MIT | neuroscience | neuroscience embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- ViT-MAE API unpack error; needs fMRI patch fix

## `caduceus`

**Bidirectional Mamba DNA model with 131k context (Cornell/Kuleshov)**

Best for genomics embeddings. Not chat, generation, or unrelated modalities.
**Cluster state: NOT-READY.**

**Status:** NOT-READY **Test:** FAIL **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/caduceus/`

**Context window:** 8,192 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `caduceus` | `kuleshov-group/caduceus-ps_seqlen-131k_d_model-256_n_layer-16` | ~45M | float16 (GPU) / float32 (CPU) | Apache-2.0 | genomics | genomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- mamba_ssm/selective_scan_cuda torch-CUDA ABI mismatch

## `chem-t5`

**Chem-T5 — multitask text+chemistry T5 (IBM GT4SD)**

Best for chemistry-specific generation. Not general chat or unrelated tasks.

**Status:** READY **Test:** FIXED **Type:** Science-generate **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/generate` **Model path:** `models/chem-t5/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `chem-t5` | `GT4SD/multitask-text-and-chemistry-t5-base-standard` | 220M | fp32 | MIT | chemistry | chemistry-specific generation | general chat or unrelated tasks |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Generation | yes | /v1/science/generate |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | no | CPU | scale-to-zero | 1-2 minutes |

### Notes

- exact GT4SD prompt templates; caption+forward_synthesis correct (was wrong)

## `chemberta`

**ChemBERTa — SMILES/chemistry embeddings**

Best for chemistry embeddings (768-dim). Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/chemberta/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `chemberta-125m` | `seyonec/ChemBERTa-zinc-base-v1` | 125M | fp32 | MIT | chemistry | chemistry embeddings (768-dim) | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | 768-dim |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | no | CPU | scale-to-zero | 1-2 minutes |

### Notes

- embeddings PASS dim=768 (id chemberta-125m)
- Gateway id `chemberta-125m` (directory `chemberta`).

## `chemgpt`

**ChemGPT-1.2B — autoregressive SMILES molecule generation**

Best for chemistry-specific generation. Not general chat or unrelated tasks.

**Status:** READY **Test:** PASS **Type:** Generate **Runtime:** pytorch  
**Primary endpoint:** `/v1/science/generate` **Model path:** `models/chemgpt/`

**Context window:** 512 tokens **Max output:** 500 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `chemgpt-1.2b` | `ncfrey/ChemGPT-1.2B` | 1.2B | fp32 | MIT | chemistry | chemistry-specific generation | general chat or unrelated tasks |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Generation | yes | /v1/science/generate |
| Secondary | yes | /v1/science/embed |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | yes | HAMi GPU slice | scale-to-zero | ~60s |

### Notes

- id=chemgpt-1.2b; SELFIES molecule generation
- Gateway id `chemgpt-1.2b` (directory `chemgpt`).

## `chemgpt-19m`

**ChemGPT-19M, a lightweight GPT-Neo style model trained on SMILES for de-novo molecule generation.**

Best for chemistry-specific generation. Not general chat or unrelated tasks.

**Status:** READY **Test:** PASS **Type:** Generate **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/generate` **Model path:** `models/chemgpt-19m/`

**Context window:** 2,048 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `chemgpt-19m` | `ncfrey/ChemGPT-19M` | 19M | fp32 | MIT | chemistry | chemistry-specific generation | general chat or unrelated tasks |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Generation | yes | /v1/science/generate |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1-2 minutes |

### Notes

- SELFIES molecule generation

## `chgnet`

**CHGNet universal neural network potential with magnetic moments and charge distribution for materials simulation.**

Best for molecular energy/force prediction. Not NLP or vision.

**Status:** READY **Test:** FIXED **Type:** Force-field **Runtime:** chgnet + ASE + PyTorch  
**Primary endpoint:** `/v1/science/energy` **Model path:** `models/chgnet/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `chgnet-v0.3` | `CederGroupHub/chgnet` | ~2M | float32 | MIT | materials-science | molecular energy/force prediction | NLP or vision |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Energy/forces | yes | eV, stress, magmom |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| chgnet + ASE + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- DEEP-FIX: ported server.py was broken (manually built CrystalGraph w/ bad kwarg) -> rewrote to model.predict_structure(); added missing server.py+kustomization (never ported); CederGroupHub/chgnet HF repo removed (404) -> non-fatal, uses chgnet bundled weights; pinned chgnet==0.3.8. water -14.79...
- Gateway id `chgnet-v0.3` (directory `chgnet`).

## `chronos-bolt`

**Chronos-Bolt zero-shot time-series forecasting (CPU)**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** PASS **Type:** Forecast **Runtime:** chronos-forecasting  
**Primary endpoint:** `/v1/forecast` **Model path:** `models/chronos-bolt/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `chronos-bolt` | `amazon/chronos-bolt-base` | 205M | fp32 | Apache-2.0 | time-series | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| chronos-forecasting | no | CPU | scale-to-zero | 1-2 minutes |

### Notes

- quantile forecast on 16-pt series

## `clap`

**CLAP — audio/text contrastive embeddings + zero-shot audio classify**

Best for audio embeddings (512-dim). Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/clap/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `clap` | `laion/larger_clap_general` | ~190M | fp32 | Apache-2.0 | audio | audio embeddings (512-dim) | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | 512-dim |
| Classify | yes | /v1/classify |
| Zero-shot audio | yes | text→audio classify |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | no | CPU | scale-to-zero | 2-3 minutes |

### Notes

- text emb 512-dim + zero-shot audio classify (dog 0.73)

## `clay`

**Clay Foundation Model ~330M geospatial MAE embeddings from satellite imagery. Apache 2.0.**

Best for earth-observation embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** FIXED **Type:** Embed **Runtime:** lightning + claymodel + einops  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/clay/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `clay` | `made-with-clay/Clay` | ~330M | fp32 | Apache-2.0 | earth-observation | earth-observation embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| lightning + claymodel + einops | no | CPU | scale-to-zero | 1–3 min |

### Notes

- rewrote to Clay v1.5 datacube dict API; cls embedding PASS

## `climatebert`

**ClimateBERT — climate text detection / net-zero classification**

Best for climate classification. Not generation or embedding-only pipelines.

**Status:** READY **Test:** PASS **Type:** Classification **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/classify` **Model path:** `models/climatebert/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `climatebert` | `climatebert/distilroberta-base-climate-f` | 82M (x3 heads) | fp32 | MIT | climate | climate classification | generation or embedding-only pipelines |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Classification | yes | label + confidence |
| Embeddings | yes | /v1/embeddings |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | no | CPU | scale-to-zero | 1-2 minutes |

### Notes

- net-zero 0.9988

## `climax`

**Microsoft ClimaX 108M climate/weather foundation model pre-trained on CMIP6, fine-tuned on ERA5.**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** PASS **Type:** Forecast **Runtime:** PyTorch + timm 0.6.13  
**Primary endpoint:** `/v1/science/forecast` **Model path:** `models/climax/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `climax` | `microsoft/ClimaX` | 108M | fp32 | MIT | weather-climate | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| PyTorch + timm 0.6.13 | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- needs valid ERA5 var names (e.g. 2m_temperature)

## `clinical-longformer`

**Clinical-Longformer — long clinical document embeddings (4096 tokens)**

Best for clinical embeddings. Not chat, generation, or unrelated modalities.
**Cluster state: NOT-READY.**

**Status:** NOT-READY **Test:** FAIL **Type:** Embedding **Runtime:** pytorch  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/clinical-longformer/`

**Context window:** 4,096 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `clinical-longformer` | `yikuan8/Clinical-Longformer` | 149M | fp32 | Apache-2.0 | clinical | clinical embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | yes | HAMi GPU slice | scale-to-zero | ~30s |

### Notes

- hangs on CPU (gpu=true but no CUDA use); needs GPU/attention fix

## `clinicalbert`

**Bio_ClinicalBERT — clinical text embeddings (768-dim)**

Best for biomedical embeddings (768-dim). Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/clinicalbert/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `clinicalbert-110m` | `emilyalsentzer/Bio_ClinicalBERT` | 110M | fp32 | MIT | biomedical | biomedical embeddings (768-dim) | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | 768-dim |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | no | CPU | scale-to-zero | 1-2 minutes |

### Notes

- embeddings PASS dim=768 (id clinicalbert-110m)
- Gateway id `clinicalbert-110m` (directory `clinicalbert`).

## `command-r-7b`

**Cohere Command R 7B, RAG-optimized chat (multilingual)**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/command-r-7b/`

**Context window:** 65,536 tokens **Max output:** 8,192 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `command-r-7b` | `CohereForAI/c4ai-command-r7b-12-2024` | 7B | bfloat16 | CC-BY-NC | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | always-on | 30-60 seconds |

### Notes

- OpenAI + Anthropic

## `croma`

**CROMA cross-modal remote sensing foundation model. SAR + optical paired satellite imagery. ~300M.**

Best for image/medical segmentation. Not text generation.

**Status:** READY **Test:** FIXED **Type:** Segment **Runtime:** PyTorch + CROMA repo  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/croma/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `croma` | `antofuller/CROMA` | ~300M | fp32 | MIT | earth-observation | image/medical segmentation | text generation |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Segmentation | yes | masks/regions |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| PyTorch + CROMA repo | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- dict output extraction (joint/optical/SAR GAP)

## `crysta-llm`

**CrystaLLM GPT-2-based crystal structure generation model that outputs CIF-format structures from formula prompts.**

Best for crystal structure generation from chemical formulas (CIF output). Not chat, general NLP, protein folding.

**Status:** READY **Test:** PASS **Type:** Science-generate **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/generate` **Model path:** `models/crysta-llm/`

**Context window:** 1,024 tokens **Max output:** 1,024 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `crysta-llm` | `c-bone/CrystaLLM-pi_base` | ~25M | float16 (GPU) / float32 (CPU) | MIT | materials-science | crystal structure generation from chemical formula | chat, general NLP, protein folding |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Generation | yes | /v1/science/generate |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- crystal structure gen from formula (progress-deadline fix)

## `deepseek-v2-lite-16b`

**DeepSeek V2 Lite 16B MoE (2.4B active), MLA attention**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/deepseek-v2-lite-16b/`

**Context window:** 8,192 tokens (served; card 24,000) **Max output:** 8,000 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `deepseek-v2-lite-16b` | `deepseek-ai/DeepSeek-V2-Lite-Chat` | 16B MoE (2.4B active) | bfloat16 | MIT (code), Model License (weights) | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | always-on | ~180s |

### Notes

- v0.20.2 (std); gpumem 45GB + max-model-len 8192; correct answers

## `depth-anything`

**Depth Anything V2 Small — monocular depth estimation**

Best for Depth Anything V2 Small — monocular depth estimation. Not unrelated modalities or production if FAIL.

**Status:** READY **Test:** FIXED **Type:** Depth **Runtime:** ONNX Runtime  
**Primary endpoint:** `/v1/vision/depth` **Model path:** `models/depth-anything/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `depth-anything-v2` | `onnx-community/depth-anything-v2-small` | 24.8M | onnx-fp32 | Apache-2.0 | computer-vision | Depth Anything V2 Small — monocular depth estimati | unrelated modalities or production if FA |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Depth estimation | yes | depth map |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| ONNX Runtime | no | CPU | scale-to-zero | ~20s |

### Notes

- fixed k8s_name 404 + PNG output; PASS
- Gateway id `depth-anything-v2` (directory `depth-anything`).

## `diffdock`

**DiffDock-L diffusion-based protein-ligand docking**

Best for DiffDock-L diffusion-based protein-ligand docking. Not unrelated modalities or production if FAIL.

**Status:** READY **Test:** FIXED **Type:** Dock **Runtime:** custom  
**Primary endpoint:** `/v1/dock` **Model path:** `models/diffdock/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `diffdock-l` | `gcorso/DiffDock` | 20M | fp32 | MIT | structural-biology | DiffDock-L diffusion-based protein-ligand docking | unrelated modalities or production if FA |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Docking | yes | poses + scores |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| custom | yes | HAMi GPU slice | scale-to-zero | ~240s |

### Notes

- SMILES passed direct (not .smi file); conf regex fixed; 11 poses on 1CRN+aspirin
- Gateway id `diffdock-l` (directory `diffdock`).

## `dino-vit-b8`

**DINO ViT-B/8 — self-supervised visual embeddings (768-dim)**

Best for computer-vision embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embed **Runtime:** ONNX Runtime  
**Primary endpoint:** `/v1/vision/embed` **Model path:** `models/dino-vit-b8/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dino-vit-b8` | `onnx-community/vit_base_patch8_224.dino-ONNX` | 86M | onnx-fp32 | Apache-2.0 | computer-vision | computer-vision embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| ONNX Runtime | no | CPU | scale-to-zero | ~20s |

### Notes

- image embedding

## `dnabert-2`

**DNABERT-2 — multi-species DNA foundation model (768-dim)**

Best for genomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** pytorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/dnabert-2/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dnabert-2-117m` | `zhihan1996/DNABERT-2-117M` | 117M | fp32 | Apache-2.0 | genomics | genomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | no | CPU | scale-to-zero | ~30s |

### Notes

- embeddings PASS dim=768 (id dnabert-2-117m)
- Gateway id `dnabert-2-117m` (directory `dnabert-2`).

## `dnabert-s`

**Species-aware genome foundation model with contrastive learning**

Best for genomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/dnabert-s/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dnabert-s` | `zhihan1996/DNABERT-S` | 117M | float32 (CPU) | MIT | genomics | genomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |
| Science | yes | /v1/science/predict |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | no | CPU | scale-to-zero | 1–3 min |

### Notes

- embeddings PASS dim=768 (id dnabert-s)

## `dust3r`

**DUSt3R (CVPR 2024): unconstrained 3D reconstruction from 2+ uncalibrated images without known camera intrinsics.**

Best for DUSt3R (CVPR 2024): unconstrained 3D reconstruction from 2+ uncalibrated images . Not unrelated modalities or production if FAIL.

**Status:** READY **Test:** FIXED **Type:** 3D **Runtime:** dust3r (custom) + PyTorch  
**Primary endpoint:** `/v1/science/reconstruct` **Model path:** `models/dust3r/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dust3r` | `naver/DUSt3R_ViTLarge_BaseDecoder_512_dpt` | ~300M | float32 | CC-BY-NC-4.0 | 3d-vision | DUSt3R (CVPR 2024): unconstrained 3D reconstructio | unrelated modalities or production if FA |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| 3D reconstruction | yes | pointcloud/match |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| dust3r (custom) + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- downsample pointcloud (was 31MB>gateway); bbox+loss; 2 imgs OK

## `earthpt`

**EarthPT 700M EO time-series autoregressive foundation model. 18-channel pixel time-series prediction.**

Best for earth-observation embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** FIXED **Type:** Embed **Runtime:** PyTorch (custom nanoGPT implementation)  
**Primary endpoint:** `/v1/science/predict` **Model path:** `models/earthpt/`

**Context window:** 256 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `earthpt` | `Smith42/EarthPT` | 700M | fp16 (GPU), fp32 (CPU) | MIT | earth-observation | earth-observation embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| PyTorch (custom nanoGPT implementation) | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- CPU ckpt load + RAM 24Gi (was GPU+host OOM); predicts OK

## `efficientnet-b0`

**EfficientNet-B0 ImageNet classifier (1000 classes)**

Best for computer-vision classification. Not generation or embedding-only pipelines.

**Status:** READY **Test:** FIXED **Type:** Classify **Runtime:** ONNX Runtime  
**Primary endpoint:** `/v1/vision/classify` **Model path:** `models/efficientnet-b0/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `efficientnet-b0` | `onnx/EfficientNet-Lite4` | 13M | onnx-fp32 | Apache-2.0 | computer-vision | computer-vision classification | generation or embedding-only pipelines |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Classification | yes | label + confidence |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| ONNX Runtime | no | CPU | scale-to-zero | ~20s |

### Notes

- lite4: fixed preproc+double-softmax+labels; minibus 0.63

## `enformer`

**Gene expression prediction from 196kb DNA sequences (DeepMind/EleutherAI)**

Best for Gene expression prediction from 196kb DNA sequences (DeepMind/EleutherAI). Not unrelated modalities or production if FAIL.
**Cluster state: NOT-READY.**

**Status:** NOT-READY **Test:** FAIL **Type:** Predict **Runtime:** enformer-pytorch + torch  
**Primary endpoint:** `/v1/science/predict` **Model path:** `models/enformer/`

**Context window:** 196,608 bp

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `enformer` | `EleutherAI/enformer-official-rough` | ~500M | float32 | CC-BY-4.0 | genomics | Gene expression prediction from 196kb DNA sequence | unrelated modalities or production if FA |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Prediction | yes | /v1/science/predict |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| enformer-pytorch + torch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- isvc never deployed (READY=False 11h); needs recreate

## `ernierna`

**Structure-aware RNA foundation model from Baidu/multimolecule (~86M)**

Best for genomics embeddings. Not chat, generation, or unrelated modalities.
**Cluster state: NOT-READY.**

**Status:** NOT-READY **Test:** FAIL **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/ernierna/`

**Context window:** 1,024 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ernierna` | `multimolecule/ernierna` | ~86M | float32 | AGPL-3.0 | genomics | genomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- isvc never deployed (READY=False 10h); needs recreate/fix

## `esm1b`

**ESM-1b 650M protein language model from Meta**

Best for proteomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/esm1b/`

**Context window:** 1,024 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `esm1b` | `facebook/esm1b_t33_650M_UR50S` | 650M | float16 (GPU) / float32 (CPU) | MIT | proteomics | proteomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- 1280-dim protein (recreated)

## `esm2-150m`

**ESM2 150M compact protein encoder from Meta**

Best for proteomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/esm2-150m/`

**Context window:** 1,024 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `esm2-150m` | `facebook/esm2_t30_150M_UR50D` | 150M | float16 (GPU) / float32 (CPU) | MIT | proteomics | proteomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- 640-dim protein (recreated)

## `esm2-35m`

**Meta ESM-2 35M, the smallest ESM-2 protein encoder.**

Best for proteomics embeddings (480-dim). Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/esm2-35m/`

**Context window:** 1,024 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `esm2-35m` | `facebook/esm2_t12_35M_UR50D` | 35M | fp16 | MIT | proteomics | proteomics embeddings (480-dim) | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | 480-dim |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1-2 minutes |

### Notes

- 480-dim protein

## `esm2-3b`

**ESM-2 3B protein language model embeddings**

Best for proteomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** custom  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/esm2-3b/`

**Context window:** 1,022 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `esm2-3b` | `facebook/esm2_t36_3B_UR50D` | 3B | fp16 | MIT | proteomics | proteomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| custom | yes | HAMi GPU slice | scale-to-zero | ~300s |

### Notes

- 2560-dim protein (recreate cleared)

## `esm2-650m`

**ESM-2 650M protein language model (per-protein embeddings)**

Best for proteomics embeddings (1280-dim). Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/esm2-650m/`

**Context window:** 1,022 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `esm2-650m` | `facebook/esm2_t33_650M_UR50D` | 650M | fp16 | MIT | proteomics | proteomics embeddings (1280-dim) | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | 1280-dim |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1-2 minutes |

### Notes

- 1280-dim protein

## `esmc-300m`

**ESM Cambrian 300M next-gen protein LM from EvolutionaryScale**

Best for proteomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** esm SDK + torch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/esmc-300m/`

**Context window:** 2,048 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `esmc-300m` | `EvolutionaryScale/esmc-300m-2024-12` | 300M | float32 | MIT | proteomics | proteomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| esm SDK + torch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- 960-dim (recreated)

## `esmfold`

**ESMfold protein structure prediction from sequence**

Best for protein/structure prediction. Not chat, fast approximate folds at scale.

**Status:** READY **Test:** PASS **Type:** Structure **Runtime:** custom  
**Primary endpoint:** `/v1/structure` **Model path:** `models/esmfold/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `esmfold` | `facebook/esmfold_v1` | ~690M | fp32 | MIT | proteomics | protein/structure prediction | chat, fast approximate folds at scale |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Structure predict | yes | PDB/structure output |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| custom | yes | HAMi GPU slice | scale-to-zero | ~180s |

### Notes

- folds protein -> PDB

## `fengwu`

**Shanghai AI Lab FengWu v2 global weather forecast model. ONNX, 0.25-degree, 83 ERA5 variables.**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** FIXED **Type:** Forecast **Runtime:** ONNX Runtime  
**Primary endpoint:** `/v1/science/forecast` **Model path:** `models/fengwu/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `fengwu` | `OpenEarthLab/FengWu` | N/A (ONNX) | fp32 | Apache-2.0 | weather-climate | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| ONNX Runtime | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- summarize grid (was 286MB>gateway); demo+real ONNX OK

## `finbert`

**FinBERT financial sentiment classification (positive/negative/neutral)**

Best for finance classification. Not generation or embedding-only pipelines.

**Status:** READY **Test:** PASS **Type:** Classify **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/classify` **Model path:** `models/finbert/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `finbert` | `ProsusAI/finbert` | 110M | fp32 | Apache-2.0 | finance | finance classification | generation or embedding-only pipelines |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Classification | yes | label + confidence |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1-2 minutes |

### Notes

- sentiment positive 0.96

## `fourcastnet3`

**NVIDIA FourCastNet3 Spherical Fourier Neural Operator for global weather. 73 ERA5 variables, 0.25-degree.**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** DEMO **Type:** Forecast **Runtime:** earth2studio + PyTorch  
**Primary endpoint:** `/v1/science/forecast` **Model path:** `models/fourcastnet3/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `fourcastnet3` | `nvidia/fourcastnet3` | N/A (NGC) | fp32 | NVIDIA Software License | weather-climate | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |
| Demo mode | yes | synthetic input |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| earth2studio + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- demo OK; real FCN3 blocked (makani+torch-harmonics CUDA matrix needs dedicated image)
- Demo mode verified; full real-input path may need gated weights or large payloads.

## `galileo`

**NASA Harvest Galileo ~90M agricultural monitoring model. Multi-spectral Sentinel-2 time-series.**

Best for earth-observation classification. Not generation or embedding-only pipelines.

**Status:** READY **Test:** FAIL **Type:** Classify **Runtime:** PyTorch + galileo repo  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/galileo/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `galileo` | `nasaharvest/galileo` | ~90M | fp32 | MIT | earth-observation | earth-observation classification | generation or embedding-only pipelines |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Classification | yes | label + confidence |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| PyTorch + galileo repo | no | CPU | scale-to-zero | 1–3 min |

### Notes

- numpy fixed; model loads as raw state_dict - needs deep fix

## `gemma-3-4b-it`

**Google Gemma 3 4B instruction-tuned, multimodal (text + image, multilingual)**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/gemma-3-4b-it/`

**Context window:** 65,536 tokens **Max output:** 8,192 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gemma-3-4b-it` | `google/gemma-3-4b-it` | 4B | bfloat16 | gemma | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | scale-to-zero | 1-2 minutes |

### Notes

- OpenAI + Anthropic

## `gemma-4-26b-a4b`

**Google Gemma 4 26B A4B MoE, reasoning + vision, FP8**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/gemma-4-26b-a4b/`

**Context window:** 131,072 bp **Max output:** 8,000 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gemma-4-26b-a4b` | `google/gemma-4-26B-A4B-it` | 25.2B MoE (3.8B active) | fp8 | Apache-2.0 | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | always-on | ~180s |

### Notes

- 26B MoE fp8 (progress-deadline fix); correct answers

## `gena-lm`

**BERT-style DNA language model trained on T2T human genome (AIRI)**

Best for genomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/gena-lm/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gena-lm` | `AIRI-Institute/gena-lm-bert-base-t2t` | 110M | float16 (GPU) / float32 (CPU) | Apache-2.0 | genomics | genomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- 768-dim DNA (recreated)

## `gena-lm-large`

**Large DNA BERT for long genomic sequences (340M, AIRI)**

Best for genomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** FIXED **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/gena-lm-large/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gena-lm-large` | `AIRI-Institute/gena-lm-bert-large-t2t` | 340M | float32 | Apache-2.0 | genomics | genomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- output_hidden_states (was returning vocab logits); 1024-dim

## `geneformer`

**Single-cell gene expression foundation model from NIH NCI (104M)**

Best for genomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embed` **Model path:** `models/geneformer/`

**Context window:** 4,096 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `geneformer` | `ctheodoris/Geneformer` | 104M | float32 | BSD-2-Clause | genomics | genomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- needs gene_ids token IDs (recreated)

## `geogalactica`

**GeoGalactica 30B geoscience LLM — OPT-style decoder-only fine-tuned on 65B geoscience tokens.**

Best for instruction-following chat in earth-science domain. Not embedding-only workloads, batch offline inference without chat API.
**Cluster state: NOT-READY.**

**Status:** NOT-READY **Test:** FAIL **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/geogalactica/`

**Context window:** 2,048 tokens **Max output:** 2,048 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `geogalactica` | `geobrain-ai/geogalactica` | 30B | bfloat16 | Apache-2.0 | earth-science | instruction-following chat in earth-science domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- gated HF repo geobrain-ai/geogalactica (403); needs access approval

## `glm-4-32b`

**GLM-4-32B-0414 instruct: strong function calling + agentic workflows.**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/glm-4-32b/`

**Context window:** 32,768 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `glm-4-32b` | `zai-org/GLM-4-32B-0414` | TP2 | — | — | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Tool calling | yes | function_call support |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- org moved THUDM->zai-org; haiku ok

## `glm-z1-32b`

**GLM-Z1-32B-0414 reasoning variant: R1-style thinking, distinct lineage.**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** FIXED **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/glm-z1-32b/`

**Context window:** 32,768 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `glm-z1-32b` | `zai-org/GLM-Z1-32B-0414` | TP2 | — | — | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Reasoning | yes | configurable effort |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- dropped deepseek_r1 parser (no <think> special tokens); 8!=40320

## `glm-z1-rumination-32b`

**GLM-Z1-Rumination-32B deep-research model: multi-step synthesis.**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** FIXED **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/glm-z1-rumination-32b/`

**Context window:** 32,768 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `glm-z1-rumination-32b` | `zai-org/GLM-Z1-Rumination-32B-0414` | TP2 | — | — | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Reasoning | yes | configurable effort |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- dropped deepseek_r1 parser; agentic finish-call format; Tokyo ok

## `gpt-oss-120b`

**OpenAI GPT-OSS 120B MoE, configurable reasoning + native tool calling**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** FIXED **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/gpt-oss-120b/`

**Context window:** 65,536 tokens **Max output:** 16,000 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gpt-oss-120b` | `openai/gpt-oss-120b` | 117B MoE (5.1B active) | mxfp4 | Apache-2.0 | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Reasoning | yes | configurable effort |
| Tool calling | yes | function_call support |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | scale-to-zero | ~90s |

### Notes

- TP2 ~200tok/s; whole GPUs + `--disable-custom-all-reduce` (HAMi custom-AR stall fix).
- Reasoning effort + OpenAI + Anthropic verified.

## `gpt-oss-20b`

**OpenAI GPT-OSS 20B MoE, configurable reasoning + native tools (lightweight)**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/gpt-oss-20b/`

**Context window:** 131,072 bp **Max output:** 32,768 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gpt-oss-20b` | `openai/gpt-oss-20b` | 21B MoE (3.6B active) | mxfp4 | Apache-2.0 | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Reasoning | yes | configurable effort |
| Tool calling | yes | function_call support |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | scale-to-zero | 1-2 minutes |

### Notes

- OpenAI + Anthropic

## `granite-geospatial-biomass`

**IBM Granite Geospatial Biomass — above-ground biomass estimation from HLS imagery. Swin-B + UPerNet.**

Best for earth-observation classification. Not generation or embedding-only pipelines.

**Status:** READY **Test:** FIXED **Type:** Classify **Runtime:** terratorch + LightningInferenceModel  
**Primary endpoint:** `/v1/science/predict` **Model path:** `models/granite-geospatial-biomass/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `granite-geospatial-biomass` | `ibm-granite/granite-geospatial-biomass` | ~350MB checkpoint | fp32 | Apache-2.0 | earth-observation | earth-observation classification | generation or embedding-only pipelines |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Classification | yes | label + confidence |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| terratorch + LightningInferenceModel | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- add gcc/g++ to init (terratorch->stringzilla build); demo OK

## `granite-geospatial-ocean`

**IBM Granite Geospatial Ocean — Sentinel-3 ocean color foundation model. 16 bands, ViT MAE.**

Best for earth-observation classification. Not generation or embedding-only pipelines.

**Status:** READY **Test:** FIXED **Type:** Classify **Runtime:** terratorch + PyTorch  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/granite-geospatial-ocean/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `granite-geospatial-ocean` | `ibm-granite/granite-geospatial-ocean` | N/A (ViT-Base scale) | fp32 | Apache-2.0 | earth-observation | earth-observation classification | generation or embedding-only pipelines |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Classification | yes | label + confidence |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| terratorch + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- add gcc/g++ to init; demo embeddings OK; slow cold-start

## `graphcast`

**DeepMind GraphCast-Small weather model. 1-degree resolution, 13 pressure levels, JAX-based.**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** PASS **Type:** Forecast **Runtime:** Ray Serve  
**Primary endpoint:** `/v1/science/predict` **Model path:** `models/graphcast/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `graphcast` | `shermansiu/dm_graphcast_small` | N/A | fp32 | CC-BY-NC-SA-4.0 | weather-climate | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |
| Demo mode | yes | synthetic input |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Ray Serve | no | CPU | scale-to-zero | 1–3 min |

### Notes

- demo mode (real ERA5 not via API by design)

## `hyenadna`

**HyenaDNA — long-range DNA embeddings (256-dim, up to 160K bp)**

Best for genomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** pytorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/hyenadna/`

**Context window:** 32,768 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `hyenadna-6.5m` | `LongSafari/hyenadna-medium-160k-seqlen-hf` | 6.5M | fp32 | MIT | genomics | genomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | no | CPU | scale-to-zero | ~30s |

### Notes

- embeddings PASS dim=256 (id hyenadna-6.5m)
- Gateway id `hyenadna-6.5m` (directory `hyenadna`).

## `ithaca`

**Ithaca — ancient Greek inscription restoration, dating, and geolocation**

Best for Ithaca — ancient Greek inscription restoration, dating, and geolocation. Not unrelated modalities or production if FAIL.

**Status:** READY **Test:** FIXED **Type:** Predict **Runtime:** JAX + FastAPI  
**Primary endpoint:** `/v1/science/predict` **Model path:** `models/ithaca/`

**Context window:** 750 chars

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ithaca` | `google-deepmind/predictingthepast` | N/A (JAX/Flax) | fp32 | Apache-2.0 | scientific-nlp | Ithaca — ancient Greek inscription restoration, da | unrelated modalities or production if FA |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Prediction | yes | /v1/science/predict |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| JAX + FastAPI | yes | HAMi GPU slice | scale-to-zero | ~120s |

### Notes

- DEEP-FIX: jax[cuda12] (was CPU-fallback -> 3min); contextualize() retrieval made opt-in (req.contextualize); gap char is ? (uppercase Greek, 50-750 chars). Warm ~8s on GPU (first call ~90s JIT). Returns restoration + attribution (date/geo)

## `kandinsky-3`

**Kandinsky 3 text-to-image and image-to-image generation**

Best for text-to-image and image edit at 1024px. Not chat, vision understanding, low-latency without Ray cold start.

**Status:** READY **Test:** PASS **Type:** Image **Runtime:** Ray Serve  
**Primary endpoint:** `/v1/images/generations` **Model path:** `models/kandinsky-3/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `kandinsky-3` | `ai-forever/Kandinsky-3` | ~5B | fp16 | Apache-2.0 | image-generation | text-to-image and image edit at 1024px | chat, vision understanding, low-latency  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Image generation | yes | PNG output |
| Edit | yes | /v1/images/edits |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Ray Serve | yes | HAMi GPU slice | always-on | ~180s |

### Notes

- RayService with in-tree autoscaler; head pinned to CPU node, GPU workers scale 0→3.
- Verified: scale-up on request, ~24s PNG at 1024, scale-down releases L40S after idle.

## `labram`

**LaBraM Large Brain Model for EEG signals. BSD-3-Clause, braindecode/Tsinghua.**

Best for neuroscience embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** FAIL **Type:** Embed **Runtime:** braindecode + PyTorch  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/labram/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `labram` | `braindecode/labram-pretrained` | N/A | fp32 | BSD-3-Clause | neuroscience | neuroscience embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| braindecode + PyTorch | no | CPU | scale-to-zero | 1–3 min |

### Notes

- needs 128 canonical channels or ch_names - needs deep fix

## `lag-llama`

**Lag-Llama probabilistic time-series foundation model (~30M params) for zero-shot forecasting with lag features.**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** FIXED **Type:** Forecast **Runtime:** lag-llama + GluonTS + PyTorch  
**Primary endpoint:** `/v1/science/forecast` **Model path:** `models/lag-llama/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `lag-llama` | `time-series-foundation-models/lag-llama` | ~30M | float32 | Apache-2.0 | time-series | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| lag-llama + GluonTS + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- torch2.6 weights_only + create_predictor(module=) API

## `leandojo`

**LeanDojo Lean 4 premise retriever (ByT5-small, 125M) for retrieval-augmented automated theorem proving.**

Best for mathematics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embed **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/retrieve` **Model path:** `models/leandojo/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `leandojo` | `kaiyuy/leandojo-lean4-retriever-byt5-small` | 125M | float32 | Apache-2.0 | mathematics | mathematics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- premise retrieval w/ scores

## `ligandmpnn`

**Ligand-aware protein sequence design from Baker Lab (UW)**

Best for Ligand-aware protein sequence design from Baker Lab (UW). Not unrelated modalities or production if FAIL.

**Status:** READY **Test:** FIXED **Type:** Design **Runtime:** LigandMPNN CLI + torch  
**Primary endpoint:** `/v1/design` **Model path:** `models/ligandmpnn/`

**Context window:** 1,024 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ligandmpnn` | `dauparas/LigandMPNN` | ~1.7M | float32 | MIT | proteomics | Ligand-aware protein sequence design from Baker La | unrelated modalities or production if FA |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Design | yes | sequences/structures |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| LigandMPNN CLI + torch | no | CPU | scale-to-zero | 1–3 min |

### Notes

- checkpoints+args+optional-openfold; 1CRN design near-native PASS

## `mace-mh-1`

**MACE-MH-1 multi-head foundation force field for cross-domain atomistic simulation (inorganic, molecular, surfaces, reactive chemistry).**

Best for molecular energy/force prediction. Not NLP or vision.

**Status:** READY **Test:** PASS **Type:** Force-field **Runtime:** mace-torch + ASE + PyTorch  
**Primary endpoint:** `/v1/science/predict` **Model path:** `models/mace-mh-1/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `mace-mh-1` | `mace-foundations/mace-mh-1` | ~50M | float64 | ASL (academic/non-commercial) | materials-science | molecular energy/force prediction | NLP or vision |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Energy/forces | yes | eV, stress, magmom |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| mace-torch + ASE + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- water -14.22 eV + forces (omat_pbe head)

## `mace-mp`

**MACE-MP-0 universal ML interatomic potential covering 89 elements with small/medium/large model variants.**

Best for molecular energy/force prediction. Not NLP or vision.

**Status:** READY **Test:** PASS **Type:** Force-field **Runtime:** mace-torch + ASE + PyTorch  
**Primary endpoint:** `/v1/science/predict` **Model path:** `models/mace-mp/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `mace-mp-0` | `ACEsuit/mace-mp-0` | ~10M (medium) | float64 | MIT | materials-science | molecular energy/force prediction | NLP or vision |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Energy/forces | yes | eV, stress, magmom |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| mace-torch + ASE + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- water -14.01 eV + forces; mace-mp-0 medium
- Gateway id `mace-mp-0` (directory `mace-mp`).

## `mace-mp-0`

**MACE-MP-0 universal ML force field (medium variant) for materials energy/forces/stress prediction.**

Best for molecular energy/force prediction. Not NLP or vision.

**Status:** READY **Test:** FIXED **Type:** Force-field **Runtime:** mace-torch + ASE + PyTorch (CPU)  
**Primary endpoint:** `/v1/science/energy` **Model path:** `models/mace-mp-0/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `mace-mp-0` | `ACEsuit/mace-mp-0` | ~10M (medium) | float32 | MIT | materials-science | molecular energy/force prediction | NLP or vision |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Energy/forces | yes | eV, stress, magmom |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| mace-torch + ASE + PyTorch (CPU) | no | CPU | scale-to-zero | 1–3 min |

### Notes

- fixed pbc-zero-cell garbage + PVC model cache; water -14.15eV PASS

## `maskrcnn`

**Mask R-CNN ResNet-50 FPN v2 — instance segmentation (80 COCO classes)**

Best for image/medical segmentation. Not text generation.

**Status:** READY **Test:** PASS **Type:** Segment **Runtime:** pytorch  
**Primary endpoint:** `/v1/vision/segment` **Model path:** `models/maskrcnn/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `maskrcnn-resnet50` | `torchvision.models.detection.maskrcnn_resnet50_fpn_v2` | 46.4M | fp32 | BSD-3-Clause | computer-vision | image/medical segmentation | text generation |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Segmentation | yes | masks/regions |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | no | CPU | scale-to-zero | ~60s |

### Notes

- id=maskrcnn-resnet50; person 0.999 + mask
- Gateway id `maskrcnn-resnet50` (directory `maskrcnn`).

## `mast3r`

**MASt3R (ECCV 2024): grounding image matching in 3D with metric depth and feature matching for visual localization.**

Best for MASt3R (ECCV 2024): grounding image matching in 3D with metric depth and feature. Not unrelated modalities or production if FAIL.

**Status:** READY **Test:** FIXED **Type:** 3D **Runtime:** mast3r + dust3r (custom) + PyTorch  
**Primary endpoint:** `/v1/science/match` **Model path:** `models/mast3r/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `mast3r` | `naver/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric` | ~300M | float32 | CC-BY-NC-4.0 | 3d-vision | MASt3R (ECCV 2024): grounding image matching in 3D | unrelated modalities or production if FA |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| 3D reconstruction | yes | pointcloud/match |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| mast3r + dust3r (custom) + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- use /v1/science/match; numpy (not tensor) fix; 473 matches

## `matscibert`

**MatSciBERT, BERT pre-trained on materials-science literature.**

Best for materials-science embeddings (768-dim). Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/matscibert/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `matscibert` | `m3rg-iitd/matscibert` | 110M | fp32 | MIT | materials-science | materials-science embeddings (768-dim) | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | 768-dim |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1-2 minutes |

### Notes

- 768-dim (field: text)

## `mattergen`

**Microsoft MatterGen diffusion model for generating novel crystal structures conditioned on composition or properties.**

Best for materials-science-specific generation. Not general chat or unrelated tasks.
**Cluster state: NO-ISVC.**

**Status:** NO-ISVC **Test:** FAIL **Type:** Generate **Runtime:** mattergen-generate CLI + PyTorch Lightning + PyG  
**Primary endpoint:** `/v1/science/generate` **Model path:** `models/mattergen/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `mattergen` | `microsoft/mattergen` | 45M | float32 | MIT | materials-science | materials-science-specific generation | general chat or unrelated tasks |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Generation | yes | /v1/science/generate |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| mattergen-generate CLI + PyTorch Lightning + PyG | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- Knative rejects ISVC: timeoutSeconds 1500 > max 600; predictor never created; gateway 404
- No InferenceService deployed; not routable via gateway.

## `mattersim`

**Microsoft MatterSim universal atomistic ML force field for energy/forces/stress prediction and structure relaxation.**

Best for molecular energy/force prediction. Not NLP or vision.

**Status:** READY **Test:** PASS **Type:** Force-field **Runtime:** mattersim + ASE + PyTorch + PyG  
**Primary endpoint:** `/v1/science/predict` **Model path:** `models/mattersim/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `mattersim` | `microsoft/mattersim` | ~1M | float32 | MIT | materials-science | molecular energy/force prediction | NLP or vision |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Energy/forces | yes | eV, stress, magmom |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| mattersim + ASE + PyTorch + PyG | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- water -14.07 eV + forces + per-atom

## `medcpt-article`

**MedCPT Article Encoder — medical document embeddings from NCBI (768-dim)**

Best for biomedical embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** pytorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/medcpt-article/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `medcpt-article` | `ncbi/MedCPT-Article-Encoder` | 110M | fp32 | MIT | biomedical | biomedical embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | yes | HAMi GPU slice | scale-to-zero | ~30s |

### Notes

- 768-dim PubMed article (recreated)

## `medcpt-query`

**MedCPT Query Encoder — medical query embeddings from NCBI (768-dim)**

Best for biomedical embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** pytorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/medcpt-query/`

**Context window:** 64 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `medcpt-query` | `ncbi/MedCPT-Query-Encoder` | 110M | fp32 | MIT | biomedical | biomedical embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | yes | HAMi GPU slice | scale-to-zero | ~30s |

### Notes

- 768-dim PubMed query (recreated)

## `medgemma-27b-it`

**Google MedGemma 27B, medical multimodal (text + radiology images)**

Best for instruction-following chat in biomedical domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/medgemma-27b-it/`

**Context window:** 8,192 tokens (served; card 120,000) **Max output:** 8,000 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `medgemma-27b-it` | `google/medgemma-27b-it` | 27B | bfloat16 | Health AI Developer Foundations Terms of Use | biomedical | instruction-following chat in biomedical domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | scale-to-zero | ~300s |

### Notes

- 27B dense TP2 ~20tok/s; v0.20.2 (fixed --limit-mm-per-prompt JSON); full GPUs + --disable-custom-all-reduce; correct medical answers

## `medsam`

**MedSAM medical image segmentation model (SAM-based) for segmenting structures from bounding box prompts.**

Best for image/medical segmentation. Not text generation.

**Status:** READY **Test:** PASS **Type:** Segment **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/segment` **Model path:** `models/medsam/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `medsam` | `flaviagiammarino/medsam-vit-base` | ~375M | float32 | Apache-2.0 | medical-imaging | image/medical segmentation | text generation |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Segmentation | yes | masks/regions |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- image as HxWx3 pixel array + boxes -> masks

## `megadetector`

**Microsoft MegaDetector v5 wildlife camera trap detector for animals, humans, and vehicles.**

Best for object detection in images. Not text/NLP tasks.

**Status:** READY **Test:** PASS **Type:** Detect **Runtime:** megadetector + PyTorch  
**Primary endpoint:** `/v1/detect` **Model path:** `models/megadetector/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `megadetector` | `microsoft/MegaDetector` | ~87M | float32 | MIT | ecology | object detection in images | text/NLP tasks |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Detection | yes | bbox + confidence |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| megadetector + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- bbox detections w/ conf

## `moirai`

**Salesforce Moirai base universal time-series forecasting model with zero-shot capabilities.**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** PASS **Type:** Forecast **Runtime:** uni2ts + PyTorch + GluonTS  
**Primary endpoint:** `/v1/forecast` **Model path:** `models/moirai/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `moirai` | `Salesforce/moirai-1.0-R-base` | ~91M | float32 | Apache-2.0 | time-series | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| uni2ts + PyTorch + GluonTS | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- Salesforce Moirai base; values+horizon -> mean/quantiles; sensible forecast

## `moirai-large`

**Salesforce Moirai 1.1-R-Large (311M) universal zero-shot time-series forecasting model.**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** PASS **Type:** Forecast **Runtime:** uni2ts + PyTorch  
**Primary endpoint:** `/v1/science/forecast` **Model path:** `models/moirai-large/`

**Context window:** 4,096 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `moirai-large` | `Salesforce/moirai-1.1-R-large` | 311M | float32 | Apache-2.0 | time-series | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| uni2ts + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- mean+samples forecast

## `moirai-moe`

**Salesforce Moirai-MoE mixture-of-experts universal time-series forecasting model.**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** FAIL **Type:** Forecast **Runtime:** uni2ts + PyTorch  
**Primary endpoint:** `/v1/forecast` **Model path:** `models/moirai-moe/`

**Context window:** 200 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `moirai-moe` | `Salesforce/moirai-moe-1.0-R-base` | ~150M | float32 | CC-BY-NC-4.0 | time-series | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| uni2ts + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- handler bug: MoiraiMoEForecast.forward() missing past_observed_target/past_is_pad args - needs handler fix

## `molformer`

**MoLFormer-XL molecular embeddings from SMILES (chemistry)**

Best for chemistry embeddings (768-dim). Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/molformer/`

**Context window:** 202 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `molformer` | `ibm-research/MoLFormer-XL-both-10pct` | 110M | fp32 | Apache-2.0 | chemistry | chemistry embeddings (768-dim) | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | 768-dim |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1-2 minutes |

### Notes

- 768-dim (field: smiles)

## `moment`

**MOMENT-1-large (385M) open time-series foundation model from CMU for forecasting, classification, and anomaly detection.**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** FIXED **Type:** Forecast **Runtime:** momentfm + PyTorch  
**Primary endpoint:** `/v1/forecast` **Model path:** `models/moment/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `moment` | `AutonLab/MOMENT-1-large` | 385M | float32 | Apache-2.0 | time-series | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| momentfm + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- output indexing (chan vs horizon); needs 512-len input; 96-step horizon

## `multilingual-e5-small`

**Multilingual E5 Small 100-language text embeddings**

Best for nlp embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** TEI (CPU)  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/multilingual-e5-small/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `multilingual-e5-small` | `intfloat/multilingual-e5-small` | 117M | float32 | Apache-2.0 | nlp | nlp embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| TEI (CPU) | no | CPU | always-on | ~30s |

### Notes

- 384-dim text embedding

## `naturecode-earth`

**Naturecode Earth 10.9M forest monitoring model. Sentinel-2 time-series, forest segmentation + biomass + soil.**

Best for earth-observation embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** DEMO **Type:** Embed **Runtime:** forestfm + PyTorch  
**Primary endpoint:** `/v1/science/predict` **Model path:** `models/naturecode-earth/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `naturecode-earth` | `naturecodeproject/earth` | 10.9M | fp32 | Apache-2.0 | earth-observation | earth-observation embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| forestfm + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- demo OK (seg probs); weights GATED (naturecodeproject/earth 403); needs HF access
- Demo mode verified; full real-input path may need gated weights or large payloads.

## `neuralgcm`

**Google DeepMind NeuralGCM hybrid physics/ML atmospheric model. 2.8-degree deterministic.**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** PASS **Type:** Forecast **Runtime:** JAX + FastAPI  
**Primary endpoint:** `/v1/science/predict` **Model path:** `models/neuralgcm/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `neuralgcm` | `google-deepmind/neuralgcm` | N/A | fp32 | CC-BY-SA-4.0 | weather-climate | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |
| Demo mode | yes | synthetic input |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| JAX + FastAPI | no | CPU | scale-to-zero | 1–3 min |

### Notes

- demo mode (real ERA5 not via API by design)

## `nucleotide-transformer`

**InstaDeep Nucleotide Transformer v2 (500M), a DNA foundation model trained on 3,200+ genomes across multiple species.**

Best for genomics embeddings (1024-dim). Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/nucleotide-transformer/`

**Context window:** 2,048 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `nucleotide-transformer` | `InstaDeepAI/nucleotide-transformer-v2-500m-multi-species` | 500M | fp32 | Apache-2.0 | genomics | genomics embeddings (1024-dim) | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | 1024-dim |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1-2 minutes |

### Notes

- 1024-dim DNA

## `oceangpt-30b`

**OceanGPT 30B MoE, ocean science (marine biology, oceanography)**

Best for instruction-following chat in science domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** FIXED **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/oceangpt-30b/`

**Context window:** 8,192 tokens **Max output:** 8,000 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `oceangpt-30b` | `zjunlp/OceanGPT-basic-30B-A3B-Instruct` | 30.5B MoE (3B active) | bfloat16 | Apache-2.0 | science | instruction-following chat in science domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | scale-to-zero | ~300s |

### Notes

- 30B-A3B MoE TP2 ~73tok/s; v0.20.2; full GPUs + --disable-custom-all-reduce (no CUDA_DISABLE_CONTROL); OpenAI+Anthropic

## `omnigenome`

**RNA foundation model with sequence-structure alignment (186M)**

Best for genomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/predict` **Model path:** `models/omnigenome/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `omnigenome-186m` | `yangheng/OmniGenome-186M` | 186M | float32 (CPU) | MIT | genomics | genomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |
| Embeddings | yes | /v1/embeddings |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | no | CPU | scale-to-zero | 1–3 min |

### Notes

- id=omnigenome-186m; RNA embedding
- Gateway id `omnigenome-186m` (directory `omnigenome`).

## `openbiollm-70b`

**Llama3-OpenBioLLM-70B biomedical fine-tune. Strong on bio benchmarks.**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/openbiollm-70b/`

**Context window:** 8,192 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `openbiollm-70b` | `aaditya/Llama3-OpenBioLLM-70B` | TP4 | — | — | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- hemoglobin answer correct; tokenizer already Fast

## `pangu-weather`

**Huawei Pangu-Weather 3D neural network for global medium-range weather forecasting. ONNX, 0.25-degree.**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** FIXED **Type:** Forecast **Runtime:** ONNX Runtime  
**Primary endpoint:** `/v1/science/forecast` **Model path:** `models/pangu-weather/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `pangu-weather` | `huawei-weather/pangu-weather` | N/A (ONNX) | fp32 | BY-NC-SA-4.0 | weather-climate | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| ONNX Runtime | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- demo+real ONNX; summarized upper/surface stats (not raw 721x1440 grids)

## `phi-4-reasoning`

**Microsoft Phi-4 Reasoning 14B, chain-of-thought math/science/code**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/phi-4-reasoning/`

**Context window:** 32,768 tokens **Max output:** 16,000 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `phi-4-reasoning` | `microsoft/Phi-4-reasoning` | 14B | bfloat16 | MIT | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Reasoning | yes | configurable effort |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | scale-to-zero | 3-5 minutes (14B BF16 load; progress-deadline 2400s) |

### Notes

- Gateway budget mode maps effort→`thinking_token_budget` (0=skip CoT).
- v0.20.2 whole L40S; verified 2026-06-06.

## `presto`

**Presto NASA Harvest crop mapping model**

Best for earth-observation classification. Not generation or embedding-only pipelines.

**Status:** READY **Test:** FAIL **Type:** Classify **Runtime:** custom  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/presto/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `presto` | `nasaharvest/presto` | ~400K | fp32 | Apache-2.0 | earth-observation | earth-observation classification | generation or embedding-only pipelines |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Classification | yes | label + confidence |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| custom | no | CPU | scale-to-zero | 1–3 min |

### Notes

- band-layout mismatch - needs correct presto format

## `prithvi-eo`

**IBM/NASA Prithvi-EO-2.0-300M earth observation foundation model. 6-band HLS, 3D ViT MAE.**

Best for earth-observation embeddings. Not chat, generation, or unrelated modalities.
**Cluster state: NOT-READY.**

**Status:** NOT-READY **Test:** FAIL **Type:** Embed **Runtime:** terratorch + PyTorch  
**Primary endpoint:** `/v1/embed` **Model path:** `models/prithvi-eo/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `prithvi-eo` | `ibm-nasa-geospatial/Prithvi-EO-2.0-300M` | 300M | fp32 | Apache-2.0 | earth-observation | earth-observation embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| terratorch + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- ISVC BlockedByFailedLoad; revision ProgressDeadlineExceeded; never scales (terratorch init)

## `prithvi-wxc`

**NASA-IBM Prithvi-WxC 2.3B weather-climate foundation model. MERRA-2, 160 variables, 0.5-degree.**

Best for weather-climate embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embed **Runtime:** PrithviWxC + PyTorch  
**Primary endpoint:** `/v1/science/forecast` **Model path:** `models/prithvi-wxc/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `prithvi-wxc` | `ibm-nasa-geospatial/Prithvi-WxC-1.0-2300M-rollout` | 2.3B | fp16 (GPU), fp32 (CPU) | Apache-2.0 | weather-climate | weather-climate embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| PrithviWxC + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- demo forecast OK after unstop+cold-start (~6min); real MERRA-2 state not exercised

## `progen2`

**ProGen2-XLarge (6.4B) protein sequence generation model from Salesforce Research.**

Best for biology-specific generation. Not general chat or unrelated tasks.
**Cluster state: NOT-READY.**

**Status:** NOT-READY **Test:** FAIL **Type:** Generate **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/completions` **Model path:** `models/progen2/`

**Context window:** 2,048 tokens **Max output:** 1,024 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `progen2` | `hugohrban/progen2-xlarge` | 6.4B | float16 (GPU) / float32 (CPU) | BSD-3-Clause | biology | biology-specific generation | general chat or unrelated tasks |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Generation | yes | /v1/completions |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- ProgressDeadlineExceeded; init download too slow, needs progress-deadline bump

## `prokbert`

**ProkBERT-mini, a compact prokaryotic DNA language model for bacterial/phage genomics.**

Best for genomics embeddings (384-dim). Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/prokbert/`

**Context window:** 1,024 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `prokbert` | `neuralbioinfo/prokbert-mini` | 20.6M | fp32 | MIT | genomics | genomics embeddings (384-dim) | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | 384-dim |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1-2 minutes |

### Notes

- 384-dim DNA

## `prostt5`

**Protein sequence to 3Di structure token translation (Rostlab)**

Best for proteomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/translate` **Model path:** `models/prostt5/`

**Context window:** 512 tokens **Max output:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `prostt5` | `Rostlab/ProstT5` | ~800M | float16 (GPU) / float32 (CPU) | MIT | proteomics | proteomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- AA->3Di structural alphabet (recreated)

## `proteinmpnn`

**ProteinMPNN fixed-backbone protein sequence design (Baker Lab, Science 2022)**

Best for ProteinMPNN fixed-backbone protein sequence design (Baker Lab, Science 2022). Not unrelated modalities or production if FAIL.

**Status:** READY **Test:** PASS **Type:** Design **Runtime:** pytorch  
**Primary endpoint:** `/v1/design` **Model path:** `models/proteinmpnn/`

**Context window:** 200,000 bp

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `proteinmpnn` | `dauparas/ProteinMPNN` | 1.7M | fp32 | MIT | proteomics | ProteinMPNN fixed-backbone protein sequence design | unrelated modalities or production if FA |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Design | yes | sequences/structures |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | yes | HAMi GPU slice | scale-to-zero | 1-2 minutes |

### Notes

- designs sequences from PDB w/ scores

## `protgpt2`

**ProtGPT2 protein sequence generation model — generates novel protein sequences from scratch.**

Best for biology-specific generation. Not general chat or unrelated tasks.

**Status:** READY **Test:** PASS **Type:** Generate **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/completions` **Model path:** `models/protgpt2/`

**Context window:** 1,024 tokens **Max output:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `protgpt2` | `nferruz/ProtGPT2` | ~1.5B | float16 (GPU) / float32 (CPU) | MIT | biology | biology-specific generation | general chat or unrelated tasks |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Generation | yes | /v1/completions |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- de novo protein generation (recreated)

## `pubmedbert`

**PubMedBERT — biomedical text embeddings from Microsoft (768-dim)**

Best for biomedical embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** pytorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/pubmedbert/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `pubmedbert` | `microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract` | 110M | fp32 | MIT | biomedical | biomedical embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | no | CPU | scale-to-zero | ~30s |

### Notes

- embeddings PASS dim=768 (id pubmedbert)

## `qwen25-coder-32b`

**Qwen2.5-Coder-32B-Instruct — code generation, reasoning & repair specialist with tool calling.**

State-of-the-art open-source codeLLM matching GPT-4o on coding benchmarks. Trained on 5.5T tokens of source code, text-code grounding, and synthetic data.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/qwen25-coder-32b/`

**Context window:** 32,768 tokens (131K native with YaRN) **Max output:** 32,768 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen25-coder-32b` | `Qwen/Qwen2.5-Coder-32B-Instruct` | 32.5B dense | fp16 | Apache-2.0 | nlp | code generation, code reasoning, code fixing, code agents | vision tasks, reasoning/thinking mode |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Tool calling | yes | hermes parser (`--tool-call-parser=hermes`) |
| Streaming | yes | SSE chunked |
| System prompt | yes | — |
| Reasoning/thinking | no | Non-reasoning model, no thinking blocks |
| Vision | no | Text-only, correctly rejected with 400 |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM v0.20.2 | 2× L40S (48 GB) | whole-device (`nvidia.com/gpu: "2"`) | scale-to-zero 15m | ~90s |

### Sampling Recommendations

| Use case | temperature | top_p | top_k |
| --- | --- | --- | --- |
| Code generation | 0.2 | 0.8 | 20 |
| General chat | 0.7 | 0.8 | 20 |

### Test Results (2026-06-11)

**22/22 passed, 3 expected failures, 0 failed**

- ✅ Basic chat, streaming, temp/top_p/top_k, stop sequences, system prompt
- ✅ Code generation (produces valid Python with `def` keyword)
- ✅ Tool calling (hermes parser active)
- ✅ max_tokens=32k accepted
- ✅ No reasoning content (correct for non-reasoning model)
- ✅ Anthropic /v1/messages (all endpoints)
- ✅ Vision correctly rejected (400), catalog correct

## `qwen25-vl-3b`

**Qwen2.5-VL-3B-Instruct — compact vision-language for images, video, OCR & docs.**

3B dense + ViT, dynamic resolution images, video, OCR, chart/document parsing. Fits on a single HAMi GPU slice.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/qwen25-vl-3b/`

**Context window:** 4,096 tokens **Max output:** 2,048 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen25-vl-3b` | `Qwen/Qwen2.5-VL-3B-Instruct` | 3B (+ ViT) | bfloat16 | Apache-2.0 | nlp | image analysis, OCR, document parsing | tool calling, reasoning, long context |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Vision | yes | dynamic resolution, video, up to 4 images/prompt |
| Streaming | yes | SSE chunked |
| Tool calling | no | visual grounding only |
| Reasoning/thinking | no | Non-reasoning model |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM v0.20.2 | 1× GPU | HAMi vGPU slice (24 GB gpumem) | scale-to-zero | ~120s |

### Test Results (2026-06-11)

**18/18 passed, 2 expected failures, 0 failed**

- ✅ Basic chat, streaming, temp/top_p, stop sequences, system prompt
- ✅ Vision (OAI + ANT) — correctly describes images and identifies content
- ✅ No reasoning content (correct)
- ✅ Catalog: vision=True, tools=False, reasoning=False, ctx=4096, max_out=2048

## `qwen25-vl-72b`

**Qwen2.5-VL-72B-Instruct — large vision-language model for images, video & visual grounding.**

72.2B dense VLM with dynamic-resolution images, video up to 1+ hour, and up to 5 images per prompt.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/qwen25-vl-72b/`

**Context window:** 32,768 tokens (131K with YaRN, not recommended for VL tasks) **Max output:** 32,768 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen25-vl-72b` | `Qwen/Qwen2.5-VL-72B-Instruct` | 72.2B dense | bf16 | Qwen License | nlp | image analysis, video understanding, visual grounding | tool calling, reasoning/thinking mode |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Vision | yes | dynamic resolution, video, up to 5 images/prompt |
| Streaming | yes | SSE chunked |
| System prompt | yes | — |
| Tool calling | no | visual grounding only, no structured function calling |
| Reasoning/thinking | no | Non-reasoning model |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM v0.20.2 | 4× L40S (48 GB) | whole-device (`nvidia.com/gpu: "4"`) | scale-to-zero 15m | ~285s |

### Sampling Recommendations

| Use case | temperature | top_p | repetition_penalty |
| --- | --- | --- | --- |
| Vision analysis (deterministic) | 0.1 | 0.001 | 1.05 |
| General chat | 0.7 | 0.8 | 1.0 |

### Test Results (2026-06-11)

**22/22 passed, 2 expected failures, 0 failed**

- ✅ Basic chat, streaming, temp/top_p/top_k, stop sequences, system prompt
- ✅ Vision (OAI image_url) — correctly describes images and colors
- ✅ Vision (ANT image block) — correctly describes image content
- ✅ No reasoning content (correct for non-reasoning model)
- ✅ Anthropic /v1/messages (all endpoints including vision)
- ✅ Catalog: vision=True, tools=False, reasoning=False, ctx=32768, max_out=32768

## `qwen25-vl-7b`

**Qwen2.5-VL-7B-Instruct — compact vision-language model with tool calling, images + video.**

7B dense + ViT, dynamic resolution images, video up to 1+ hour, OCR, chart/document parsing. Fits on a single HAMi GPU slice.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/qwen25-vl-7b/`

**Context window:** 65,536 tokens **Max output:** 16,384 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen25-vl-7b` | `Qwen/Qwen2.5-VL-7B-Instruct` | 7B (+ ViT) | bfloat16 | Apache-2.0 | nlp | image analysis, video, OCR, visual grounding | reasoning/thinking mode |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Vision | yes | dynamic resolution, video, up to 20 images/prompt |
| Tool calling | yes | hermes parser (forced, conservative on tool_choice='auto') |
| Streaming | yes | SSE chunked |
| System prompt | yes | — |
| Reasoning/thinking | no | Non-reasoning model |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM v0.20.2 | 1× GPU | HAMi vGPU slice (32 GB gpumem) | scale-to-zero | ~120s |

### Test Results (2026-06-11)

**22/22 passed, 2 expected failures, 0 failed**

- ✅ Basic chat, streaming, temp/top_p, stop sequences, system prompt
- ✅ Vision (OAI + ANT) — correctly describes images and colors
- ✅ Tool calling (hermes parser active, conservative on auto)
- ✅ max_tokens=16k accepted, resources block with vram_mib
- ✅ No reasoning content (correct)
- ✅ Catalog: vision=True, tools=True, reasoning=False, ctx=65536, max_out=16384

## `qwen3-235b`

**Qwen3 235B A22B MoE (AWQ int4), tools + multilingual (4x L40S)**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/qwen3-235b/`

**Context window:** 131,072 bp **Max output:** 32,768 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen3-235b` | `QuantTrio/Qwen3-235B-A22B-Instruct-2507-AWQ` | 235B total / 22B active | awq-int4 | Apache-2.0 | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Tool calling | yes | hermes parser |
| Streaming | yes | — |
| Vision | no | text-only model |
| Reasoning/thinking | no | non-thinking Instruct-2507 variant |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM v0.20.2 | 4× L40S | whole-device (nvidia.com/gpu:4) | scale-to-zero 30m | ~4 minutes (116 GB AWQ int4 over NFS) |

### Notes

- 235B-A22B AWQ-int4 MoE (128 experts, 8 activated, 22B active); non-thinking Instruct-2507 variant — no reasoning mode, no `<think` blocks
- v0.20.2; ported from 232 (tclf90 repo deleted -> QuantTrio); whole node (4 GPUs) + --disable-custom-all-reduce + awq_marlin
- Tool calling via hermes parser; no vision; HF recommends temp=0.7/top_p=0.8/top_k=20
- 21/21 gateway test ✅ 2026-06-11; vision correctly rejected
- Cannot run simultaneously with other TP4 models (takes all GPUs on a node)

## `qwen3-32b`

**Qwen3-32B dense flagship: thinking mode, tool calling, 100+ languages, 40K context.**

Best for reasoning-intensive chat, agentic tool-calling workflows, multilingual dialogue. Not vision tasks, embedding-only workloads.

**Status:** READY **Test:** PASS (23/25 ✅) **Type:** Chat **Runtime:** vLLM v0.20.2
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/qwen3-32b/`

**Context window:** 40,960 tokens **Max completion:** 32,768 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen3-32b` | `Qwen/Qwen3-32B` | 32.8B dense, TP2 | bf16 auto | Apache-2.0 | nlp | reasoning chat, tool calling, multilingual | vision, embedding-only |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Reasoning | yes | effort mode (binary enable_thinking via chat_template_kwargs) |
| Tool calling | yes | hermes parser + enable-auto-tool-choice |
| Streaming | yes | SSE chunks |
| Vision | no | correctly rejected by gateway (400) |
| System prompt | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM v0.20.2 | 2× L40S | whole-device (nvidia.com/gpu:2) | scale-to-zero 15m | 3–4 min |

### Notes

- 32.8B dense (64 layers, GQA 64Q/8KV); vLLM reasoning-parser=qwen3, tool-call-parser=hermes
- Thinking: binary enable_thinking switch, on by default. Best sampling: ON → temp=0.6/topP=0.95; OFF → temp=0.7/topP=0.8/topK=20
- Gateway maps reasoning_effort: none/low → off, medium/high/max → on
- 23/25 gateway test passed 2026-06-11 (2 expected failures: embed guard, bad model guard)

## `qwen35-122b`

**Qwen3.5 122B MoE FP8, toggleable thinking + native tools (4x L40S)**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/qwen35-122b/`

**Context window:** 131,072 tokens **Max output:** 32,768 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen35-122b` | `Qwen/Qwen3.5-122B-A10B-FP8` | 122B total / 10B active | fp8 | Apache-2.0 | nlp | reasoning, tool-calling, instruction-following | vision, embedding-only, batch offline |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Reasoning | yes | toggle mode via `enable_thinking` (qwen3 parser) |
| Tool calling | yes | qwen3_coder parser, native tool support |
| Streaming | yes | — |
| Vision | no | language-model-only (vision encoder disabled) |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM v0.20.2 | 4× L40S | whole-device (nvidia.com/gpu:4) | scale-to-zero 30m | ~5 min |

### Notes

- 122B FP8 MoE (256 experts, 8 routed + 1 shared), 10B active params, ~65 tok/s
- Thinking toggle mode: `chat_template_kwargs.enable_thinking` binary on/off
- TRITON_ATTN_VLLM_V1 required on L40S (SM89); disable-custom-all-reduce for TP4 on HAMi
- 23/23 gateway test ✅ 2026-06-11

## `qwen36-27b`

**Qwen3.6-27B dense, novel Gated-DeltaNet hybrid arch (needs newer vLLM).**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/qwen36-27b/`

**Context window:** 32,768 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen36-27b` | `Qwen/Qwen3.6-27B` | TP2 | — | — | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- Jupiter+Ganymede; Gated-DeltaNet on vllm:latest

## `qwen36-35b-a3b`

**Qwen3.6-35B-A3B MoE (3B active), Gated-DeltaNet hybrid (needs newer vLLM).**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/qwen36-35b-a3b/`

**Context window:** 32,768 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen36-35b-a3b` | `Qwen/Qwen3.6-35B-A3B` | TP2 | — | — | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- s[::-1]; MoE Gated-DeltaNet on vllm:latest

## `qwq-32b`

**QwQ-32B — Qwen's dedicated reasoning model with always-on chain-of-thought and tool calling (2x L40S).**

Best for reasoning-intensive tasks: math, STEM, multi-step problem solving. Not for vision tasks, embedding workloads.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/qwq-32b/`

**Context window:** 32,768 tokens **Max output:** 32,768 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwq-32b` | `Qwen/QwQ-32B` | 32.5B dense | fp16 | Apache-2.0 | nlp | reasoning, STEM, tool calling | vision, embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Reasoning | yes | always-on CoT (deepseek_r1 parser, no toggle) |
| Tool calling | yes | hermes parser |
| Streaming | yes | — |
| Vision | no | correctly rejected (400) |
| System prompt | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM v0.20.2 | 2x L40S | whole-device (TP2) | scale-to-zero 15m | ~2 min |

### Sampling (HF recommended)

- `temperature=0.6`, `top_p=0.95`, `top_k=20-40`
- Do NOT use greedy decoding (causes endless repetitions)
- `presence_penalty` 0-2 to reduce repetition

### Notes

- Always-on reasoning — no thinking toggle. Model always generates `<think/>` blocks.
- deepseek_r1 parser handles thinking content in API responses.
- 131K native context, deployed at 32K (TP2 memory constraint).
- 21/21 gateway test passed 2026-06-11.
- **NIM available:** `nvcr.io/nim/qwen/qwq-32b`


## `r1-distill-llama-70b`

**DeepSeek-R1 reasoning distilled into Llama-70B. Strong open chain-of-thought.**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** FIXED **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/r1-distill-llama-70b/`

**Context window:** 65,536 tokens (served; card 131,072)

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `r1-distill-llama-70b` | `deepseek-ai/DeepSeek-R1-Distill-Llama-70B` | TP4 | — | — | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Reasoning | yes | configurable effort |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- tokenizer_class patch (was Ġ/Ċ garbled); 40km/h correct; max-len 65536

## `r1-distill-qwen-32b`

**DeepSeek-R1 reasoning distilled into Qwen-32B. Faster R1-grade reasoning.**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** vLLM  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/r1-distill-qwen-32b/`

**Context window:** 65,536 tokens (served; card 131,072)

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `r1-distill-qwen-32b` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` | TP2 | — | — | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Reasoning | yes | configurable effort |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| vLLM | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- 12^2=144; deepseek_r1 parser; max-len 65536 (KV fit)

## `retinanet`

**RetinaNet ResNet-50 FPN v2 — single-stage COCO detector (80 classes)**

Best for object detection in images. Not text/NLP tasks.

**Status:** READY **Test:** PASS **Type:** Detect **Runtime:** pytorch  
**Primary endpoint:** `/v1/vision/detect` **Model path:** `models/retinanet/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `retinanet-resnet50` | `torchvision.models.detection.retinanet_resnet50_fpn_v2` | 37.7M | fp32 | BSD-3-Clause | computer-vision | object detection in images | text/NLP tasks |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Detection | yes | bbox + confidence |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | no | CPU | scale-to-zero | ~60s |

### Notes

- id=retinanet-resnet50; bus 0.95
- Gateway id `retinanet-resnet50` (directory `retinanet`).

## `rita`

**Protein generative language model (1.2B) from LightOn**

Best for proteomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/generate` **Model path:** `models/rita/`

**Context window:** 1,024 tokens **Max output:** 200 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `rita-xl` | `lightonai/RITA_xl` | 1.2B | float32 | Apache-2.0 | proteomics | proteomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | no | CPU | scale-to-zero | 1–3 min |

### Notes

- protein generation: greedy + sampling produce valid sequences
- Gateway id `rita-xl` (directory `rita`).

## `rnabert`

**RNA BERT pre-trained on structured alignments from Rfam (~86M)**

Best for genomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/rnabert/`

**Context window:** 440 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `rnabert` | `multimolecule/rnabert` | ~86M | float32 | AGPL-3.0 | genomics | genomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- 120-dim RNA (recreated)

## `rnafm`

**RNA foundation model for non-coding RNA (100M, RNAcentral)**

Best for genomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/rnafm/`

**Context window:** 1,024 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `rnafm` | `multimolecule/rnafm` | 100M | float32 | RNA-FM License (non-commercial) | genomics | genomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- 640-dim RNA (recreated)

## `rnamsm`

**RNA MSA transformer for secondary structure prediction (~96M)**

Best for genomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/rnamsm/`

**Context window:** 1,024 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `rnamsm` | `multimolecule/rnamsm` | ~96M | float32 | AGPL-3.0 | genomics | genomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- 768-dim RNA (field: sequence)

## `sapbert`

**SapBERT — biomedical entity linking embeddings (768-dim)**

Best for biomedical embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** pytorch  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/sapbert/`

**Context window:** 25 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `sapbert` | `cambridgeltl/SapBERT-from-PubMedBERT-fulltext` | 110M | fp32 | MIT | biomedical | biomedical embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | yes | HAMi GPU slice | scale-to-zero | ~30s |

### Notes

- 768-dim biomedical

## `saprot-650m`

**Structure-aware protein LM combining amino acids and 3Di tokens (Westlake)**

Best for proteomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/saprot-650m/`

**Context window:** 1,024 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `saprot-650m` | `westlake-repl/SaProt_650M_AF2` | 650M | float16 (GPU) / float32 (CPU) | MIT | proteomics | proteomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- 1280-dim (AA+3Di tokens; recreated)

## `satmae`

**SatMAE ViT-Large masked autoencoder pretrained on fMoW satellite imagery. Apache 2.0.**

Best for earth-observation embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embed **Runtime:** PyTorch + timm + safetensors  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/satmae/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `satmae` | `MVRL/satmae-vitlarge-fmow-pretrain-800` | ~300M (ViT-Large) | fp32 | Apache-2.0 | earth-observation | earth-observation embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| PyTorch + timm + safetensors | no | CPU | scale-to-zero | 1–3 min |

### Notes

- HxW RGB -> cls embedding

## `scgpt`

**scGPT single-cell gene expression embeddings**

Best for transcriptomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** FIXED **Type:** Embedding **Runtime:** custom  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/scgpt/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `scgpt` | `bowang-lab/scGPT` | 50M | fp32 | MIT | transcriptomics | transcriptomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| custom | yes | HAMi GPU slice | scale-to-zero | ~180s |

### Notes

- _encode needs src_key_padding_mask; 512-dim

## `scibert`

**SciBERT — scientific text embeddings (768-dim)**

Best for nlp embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** pytorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/scibert/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `scibert-110m` | `allenai/scibert_scivocab_uncased` | 110M | fp32 | Apache-2.0 | nlp | nlp embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | no | CPU | scale-to-zero | ~30s |

### Notes

- embeddings PASS dim=768 (id scibert-110m)
- Gateway id `scibert-110m` (directory `scibert`).

## `science-embed`

**Legacy shared embedding backend (ESM2/NT); superseded by per-model ISVCs — not deployed**

Best for internal multi-model embed backend (historical). Not any client use — use esm2-*/nucleotide-transformer ISVCs directly.
**Cluster state: NO-ISVC.**

**Status:** NO-ISVC **Test:** CANCELLED **Type:** Embedding **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/science-embed/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `science-embed` | `multiple` | multiple | float32 (CPU) / float16 (GPU) | various | shared-infrastructure | internal multi-model embed backend (historical) | any client use — use esm2-*/nucleotide-t |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | ? | CPU | scale-to-zero | 1–3 min |

### Notes

- CANCELLED — superseded by individual esm2-*/nucleotide-transformer ISVCs.
- Was shared Deployment (not ISVC); not routable via gateway.
- No InferenceService deployed; not routable via gateway.

## `scincl`

**ScINCL — scientific citation embeddings via incl-training (768-dim)**

Best for scientific-nlp embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** pytorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/scincl/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `scincl` | `malteos/scincl` | 110M | fp32 | MIT | scientific-nlp | scientific-nlp embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | yes | HAMi GPU slice | scale-to-zero | ~30s |

### Notes

- 768-dim scientific paper

## `seisbench`

**SeisBench PhaseNet seismic phase detection for P/S wave arrival identification in earthquake seismology.**

Best for ecology classification. Not generation or embedding-only pipelines.

**Status:** READY **Test:** PASS **Type:** Classify **Runtime:** seisbench + PyTorch  
**Primary endpoint:** `/v1/science/detect` **Model path:** `models/seisbench/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `seisbench` | `seisbench/PhaseNet` | ~1M | float32 | GPL-3.0 | ecology | ecology classification | generation or embedding-only pipelines |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Classification | yes | label + confidence |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| seisbench + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- phasenet runs (P/S detection)

## `speaches`

**Speaches: STT (Whisper Large v3) + TTS (Kokoro-82M) combined deployment**

Best for Speaches: STT (Whisper Large v3) + TTS (Kokoro-82M) combined deployment. Not unrelated modalities or production if FAIL.

**Status:** READY **Test:** PASS **Type:** Standalone **Runtime:** standalone  
**Primary endpoint:** `/v1/audio/speech, /v1/audio/transcriptions` **Model path:** `models/speaches/`

**Context window:** 448 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `speaches` | `speaches-ai/speaches` | whisper: 1.5B + kokoro: 82M | fp16 (faster-whisper) / fp16 (Kokoro ONNX) | MIT | audio | Speaches: STT (Whisper Large v3) + TTS (Kokoro-82M | unrelated modalities or production if FA |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Primary API | yes | /v1/audio/speech, /v1/audio/transcriptions |
| Stt | yes | /v1/audio/transcriptions |
| Tts | yes | /v1/audio/speech |
| Transcription | yes | `/v1/audio/transcriptions` |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| standalone | yes | HAMi GPU slice | always-on | ~120s |

### Notes

- DEEP-FIX: chmod HF cache (root init -> non-root container PermissionError on whisper refs). TTS Kokoro-82M (af_heart/am_michael, wav+mp3 ~9s); STT faster-whisper-large-v3 ~6s. Round-trip transcription exact (x2). Always-on Deployment (heavily used)

## `specter2`

**SPECTER2 — scientific paper embeddings (768-dim)**

Best for nlp embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** pytorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/specter2/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `specter2-110m` | `allenai/specter2_base` | 110M | fp32 | Apache-2.0 | nlp | nlp embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | no | CPU | scale-to-zero | ~30s |

### Notes

- embeddings PASS dim=768 (id specter2-110m)
- Gateway id `specter2-110m` (directory `specter2`).

## `splicebert`

**SpliceBERT — RNA splice-site embeddings (768-dim)**

Best for genomics embeddings. Not chat, generation, or unrelated modalities.

**Status:** READY **Test:** PASS **Type:** Embedding **Runtime:** pytorch  
**Primary endpoint:** `/v1/embeddings` **Model path:** `models/splicebert/`

**Context window:** 510 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `splicebert-86m` | `zhihan1996/DNA_bert_6` | 86M | fp32 | Apache-2.0 | genomics | genomics embeddings | chat, generation, or unrelated modalitie |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Embeddings | yes | vectors |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | no | CPU | scale-to-zero | ~30s |

### Notes

- embeddings PASS dim=768 (id splicebert-86m)
- Gateway id `splicebert-86m` (directory `splicebert`).

## `stanford-deidentifier`

**Stanford Deidentifier — clinical PHI removal via NER**

Best for Stanford Deidentifier — clinical PHI removal via NER. Not unrelated modalities or production if FAIL.

**Status:** READY **Test:** PASS **Type:** Deidentify **Runtime:** pytorch  
**Primary endpoint:** `/v1/science/deidentify` **Model path:** `models/stanford-deidentifier/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `stanford-deidentifier` | `StanfordAIMI/stanford-deidentifier-base` | 110M | fp32 | Apache-2.0 | clinical | Stanford Deidentifier — clinical PHI removal via N | unrelated modalities or production if FA |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| PHI de-identification | yes | entity spans |
| Secondary | yes | /v1/science/embed |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | yes | HAMi GPU slice | scale-to-zero | ~30s |

### Notes

- PHI entities (PATIENT/DATE/HOSPITAL)

## `sundial`

**Sundial — generative time series foundation model (128M, CPU)**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** FIXED **Type:** Forecast **Runtime:** pytorch  
**Primary endpoint:** `/v1/science/forecast` **Model path:** `models/sundial/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `sundial` | `thuml/sundial-base-128m` | 128M | fp32 | Apache-2.0 | scientific-nlp | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | no | CPU | scale-to-zero | ~60s |

### Notes

- fixed input shape + pinned transformers 4.40.2; forecast+quantiles PASS

## `surya`

**Surya 1.0 — NASA-IBM heliophysics foundation model (366M, GPU)**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** PASS **Type:** Forecast **Runtime:** pytorch  
**Primary endpoint:** `/v1/science/forecast` **Model path:** `models/surya/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `surya-366m` | `nasa-ibm-ai4science/Surya-1.0` | 366M | fp32 | Apache-2.0 | scientific-nlp | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | yes | HAMi GPU slice | scale-to-zero | ~180s |

### Notes

- demo forecast+flare_risk via gateway 2026-06-06; id=surya-366m
- Gateway id `surya-366m` (directory `surya`).

## `terramind-flood`

**IBM/ESA TerraMind-base-Flood multi-sensor flood detection. Sentinel-1 + Sentinel-2 + DEM, 256x256.**

Best for earth-observation classification. Not generation or embedding-only pipelines.
**Cluster state: NOT-READY.**

**Status:** NOT-READY **Test:** FAIL **Type:** Classify **Runtime:** terratorch 1.2.1 + PyTorch  
**Primary endpoint:** `/v1/science/classify` **Model path:** `models/terramind-flood/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `terramind-flood` | `ibm-esa-geospatial/TerraMind-base-Flood` | N/A (TerraMind-1.0-base scale) | fp32 | Apache-2.0 | earth-observation | earth-observation classification | generation or embedding-only pipelines |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Classification | yes | label + confidence |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| terratorch 1.2.1 + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- revision ProgressDeadlineExceeded; initial scale never achieved

## `thor`

**Norwegian Computing Center THOR 1.0-base multi-sensor geospatial foundation model. FlexiViT-Base.**

Best for time-series / weather forecasting. Not chat, static embeddings.
**Cluster state: NOT-READY.**

**Status:** NOT-READY **Test:** FAIL **Type:** Forecast **Runtime:** terratorch + thor_terratorch_ext  
**Primary endpoint:** `/v1/science/embed` **Model path:** `models/thor/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `thor` | `FM4CS/THOR-1.0-base` | ~86M (FlexiViT-Base) | fp32 | Apache-2.0 | earth-observation | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| terratorch + thor_terratorch_ext | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- ProgressDeadlineExceeded; init too slow (+terratorch lib check)

## `time-moe`

**TimeMoE-50M mixture-of-experts universal time-series forecasting model from Tsinghua.**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** PASS **Type:** Forecast **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/forecast` **Model path:** `models/time-moe/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `time-moe` | `Maple728/TimeMoE-50M` | 50M | bfloat16 (GPU) / float32 (CPU) | Apache-2.0 | time-series | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- TimeMoE-50M MoE; forecast_len matches prediction_length (must be 1/96/192/336/720; 12 returns empty)

## `timer`

**Timer-base-84M universal time-series forecasting model (Tsinghua THUML, decoder-only transformer).**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** FIXED **Type:** Forecast **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/forecast` **Model path:** `models/timer/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `timer` | `thuml/timer-base-84m` | 84M | float16 (GPU) / float32 (CPU) | Apache-2.0 | time-series | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- pinned transformers==4.40.2 (remote code uses DynamicCache.seen_tokens removed in >=4.41); forecast_len 96 PASS

## `timer-xl-1b`

**Timer-XL-1B large universal time-series forecasting model (Tsinghua THUML, 1B params).**

Best for time-series / weather forecasting. Not chat, static embeddings.
**Cluster state: NOT-READY.**

**Status:** NOT-READY **Test:** FAIL **Type:** Forecast **Runtime:** Transformers + PyTorch  
**Primary endpoint:** `/v1/forecast` **Model path:** `models/timer-xl-1b/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `timer-xl-1b` | `thuml/Timer-XL-1B` | 1B | float16 (GPU) / float32 (CPU) | Apache-2.0 | time-series | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| Transformers + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- repo thuml/Timer-XL-1B 404 (wrong id); needs correct repo

## `timesfm`

**TimesFM 2.0 500M zero-shot time series forecasting**

Best for time-series / weather forecasting. Not chat, static embeddings.
**Cluster state: NOT-READY.**

**Status:** NOT-READY **Test:** FAIL **Type:** Forecast **Runtime:** custom  
**Primary endpoint:** `/v1/forecast` **Model path:** `models/timesfm/`

**Context window:** 2,048 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `timesfm-500m` | `google/timesfm-2.0-500m-pytorch` | 500M | fp32 | Apache-2.0 | time-series | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| custom | yes | HAMi GPU slice | scale-to-zero | ~180s |

### Notes

- TimesFmModelForPrediction not importable; transformers lacks TimesFm support - needs version pin/upgrade
- Gateway id `timesfm-500m` (directory `timesfm`).

## `tinyllama`

**TinyLlama 1.1B GGUF Q4_K_M, CPU inference via llama.cpp**

Best for instruction-following chat in nlp domain. Not embedding-only workloads, batch offline inference without chat API.

**Status:** READY **Test:** PASS **Type:** Chat **Runtime:** llama.cpp  
**Primary endpoint:** `/v1/chat/completions` **Model path:** `models/tinyllama/`

**Context window:** 4,096 tokens **Max output:** 1,800 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `tinyllama-1.1b` | `TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF` | 1.1B | gguf-q4-km | Apache-2.0 | nlp | instruction-following chat in nlp domain | embedding-only workloads, batch offline  |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Chat completions | yes | OpenAI + Anthropic routes |
| Streaming | yes | — |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| llama.cpp | no | CPU | always-on | ~30s |

### Notes

- OpenAI + Anthropic PASS; streaming 500 (gateway SSE, cross-cutting)
- Gateway id `tinyllama-1.1b` (directory `tinyllama`).

## `totalsegmentator`

**TotalSegmentator: automated segmentation of 117 anatomical structures in CT scans.**

Best for image/medical segmentation. Not text generation.

**Status:** READY **Test:** FAIL **Type:** Segment **Runtime:** totalsegmentator + nnU-Net + PyTorch  
**Primary endpoint:** `/v1/science/segment` **Model path:** `models/totalsegmentator/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `totalsegmentator` | `wasserth/TotalSegmentator` | ~31M | float32 | Apache-2.0 | medical-imaging | image/medical segmentation | text generation |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Segmentation | yes | masks/regions |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| totalsegmentator + nnU-Net + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- pod runs; POST 16³ CT → 500 `operator torchvision::nms does not exist` (torch/torchvision ABI)

## `ttm`

**IBM TinyTimeMixer (TTM-R2) lightweight multi-variate time-series forecasting model (1-5M params).**

Best for time-series / weather forecasting. Not chat, static embeddings.

**Status:** READY **Test:** FIXED **Type:** Forecast **Runtime:** tsfm_public + PyTorch  
**Primary endpoint:** `/v1/science/forecast` **Model path:** `models/ttm/`

**Context window:** 512 tokens

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ttm` | `ibm-granite/granite-timeseries-ttm-r2` | 1-5M | float32 | Apache-2.0 | time-series | time-series / weather forecasting | chat, static embeddings |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Forecast | yes | quantiles/mean where supported |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| tsfm_public + PyTorch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- past_values shape [batch,time,chan]; 96-step forecast

## `uma-m`

**Universal Materials Architecture from Meta FAIR (EquiformerV2, ~1.1B params)**

Best for molecular energy/force prediction. Not NLP or vision.
**Cluster state: BLOCKED.**

**Status:** BLOCKED **Test:** FAIL **Type:** Force-field **Runtime:** fairchem-core + ASE + torch  
**Primary endpoint:** `/v1/science/predict` **Model path:** `models/uma-m/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `uma-m` | `facebook/UMA` | ~1.1B | float32 | Meta Research License (non-commercial) | materials | molecular energy/force prediction | NLP or vision |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Energy/forces | yes | eV, stress, magmom |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| fairchem-core + ASE + torch | yes | HAMi GPU slice | scale-to-zero | 1–3 min |

### Notes

- gated repo facebook/UMA (401) - needs Meta access grant on HF token

## `xtts-v2`

**Coqui XTTS-v2 multilingual TTS + voice cloning (17 langs, GPU)**

Best for speech synthesis/transcription. Not text-only chat.

**Status:** READY **Test:** PASS **Type:** TTS **Runtime:** coqui-tts  
**Primary endpoint:** `/v1/audio/speech` **Model path:** `models/xtts-v2/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `xtts-v2` | `coqui/XTTS-v2` | ~1.8B | fp32 | CPML | audio | speech synthesis/transcription | text-only chat |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Speech synthesis | yes | WAV/MP3 |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| coqui-tts | yes | HAMi GPU slice | always-on | 1-2 minutes |

### Notes

- text->WAV 155KB audio

## `yolov8n`

**YOLOv8 Nano — fastest COCO object detector (80 classes)**

Best for object detection in images. Not text/NLP tasks.

**Status:** READY **Test:** PASS **Type:** Detect **Runtime:** ONNX Runtime  
**Primary endpoint:** `/v1/vision/detect` **Model path:** `models/yolov8n/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `yolov8n` | `https://github.com/ultralytics/ultralytics` | 3.2M | onnx-fp32 | AGPL-3.0 | computer-vision | object detection in images | text/NLP tasks |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Detection | yes | bbox + confidence |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| ONNX Runtime | no | CPU | scale-to-zero | ~30s |

### Notes

- person 0.89 on bus.jpg

## `yolov8s`

**YOLOv8 Small — balanced speed/accuracy COCO detector (80 classes)**

Best for object detection in images. Not text/NLP tasks.

**Status:** READY **Test:** PASS **Type:** Detect **Runtime:** ONNX Runtime  
**Primary endpoint:** `/v1/vision/detect` **Model path:** `models/yolov8s/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `yolov8s` | `https://github.com/ultralytics/ultralytics` | 11.2M | onnx-fp32 | AGPL-3.0 | computer-vision | object detection in images | text/NLP tasks |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Detection | yes | bbox + confidence |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| ONNX Runtime | no | CPU | scale-to-zero | ~30s |

### Notes

- person 0.91 on bus.jpg

## `zoobot`

**Zoobot galaxy morphology encoder (ConvNext-Nano, 640-dim)**

Best for astronomy classification. Not generation or embedding-only pipelines.

**Status:** READY **Test:** PASS **Type:** Classify **Runtime:** pytorch  
**Primary endpoint:** `/v1/vision/embed` **Model path:** `models/zoobot/`

### Overview

| Gateway id | Upstream | Parameters | Precision | License | Domain | Best for | Not for |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `zoobot-15m` | `mwalmsley/zoobot-encoder-convnext_nano` | 15M | fp32 | Apache-2.0 | astronomy | astronomy classification | generation or embedding-only pipelines |

### Capabilities

| Capability | Supported | Notes |
| --- | ---: | --- |
| Classification | yes | label + confidence |

### Serving

| Engine | GPU | Allocation | Scale | Cold start |
| --- | --- | --- | --- | --- |
| pytorch | no | CPU | scale-to-zero | ~60s |

### Notes

- id=zoobot-15m; galaxy embedding
- Gateway id `zoobot-15m` (directory `zoobot`).
