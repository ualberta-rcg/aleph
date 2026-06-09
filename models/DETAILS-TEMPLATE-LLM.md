# details.yaml Templates

Three patterns cover every model on the cluster. Copy the right one, fill in the `CHANGEME` fields.

- **Template A — vLLM chat/embedding LLM** (gemma-4, qwen, deepseek, etc.)
- **Template B — Custom science server** (diffdock, aurora, esmfold, etc.)
- **Template C — Embedding-only** (bge, scibert, dnabert, etc.)

## Exemplars (real production details.yaml to study)

| Pattern | Best example | Lines |
|---|---|---|
| vLLM LLM | `gemma-4-26b-a4b/details.yaml` | 106 |
| vLLM LLM (complex) | `gpt-oss-120b/details.yaml` | 155 |
| vLLM LLM (reasoning) | `phi-4-reasoning/details.yaml` | 98 |
| Science/custom | `diffdock/details.yaml` | 100 |
| Science/custom (weather) | `aurora/details.yaml` | 91 |
| Embedding | `bge-m3/details.yaml` | — |

---

## Template A — vLLM Chat/Embedding LLM

For models served by `vllm/vllm-openai` (chat, completions, embeddings via vLLM).

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: CHANGEME-details
  namespace: models
  labels:
    model-details: "true"
data:
  details.json: |
    {
      "id": "CHANGEME",
      "status": "production",
      "type": "chat",
      "description_short": "ONE LINE — what it is, who made it, key features",
      "description": "2-4 sentences. Architecture, parameter count, quantization, context window, notable capabilities (reasoning, vision, tools). License.",
      "context_window": CHANGEME,
      "max_completion_tokens": CHANGEME,
      "endpoints": {
        "primary": "/v1/chat/completions",
        "health": "/v1/models"
      },
      "owned_by": "CHANGEME-org",
      "source": "CHANGEME-org/CHANGEME-model",
      "source_url": "https://huggingface.co/CHANGEME-org/CHANGEME-model",
      "license": "CHANGEME",
      "parameters": "CHANGEME (e.g. 32B dense or 25.2B MoE / 3.8B active)",
      "parameter_count": CHANGEME,
      "precision": "CHANGEME (bfloat16, fp8, awq_int4, etc.)",
      "architecture": "CHANGEME (e.g. gemma-4-moe, Qwen2ForCausalLM)",
      "framework": "vllm",
      "deployment": {
        "gpu": true,
        "gpu_count": CHANGEME,
        "gpu_type": "L40S",
        "min_replicas": 0,
        "max_replicas": 3,
        "startup_seconds": CHANGEME,
        "container_image": "vllm/vllm-openai:v0.20.2",
        "served_model_name": "CHANGEME",
        "node": "any-L40S",
        "timeout": 300,
        "model_path": "/data"
      },
      "routing": {
        "path_prefix": "/v1/",
        "serialize": false,
        "no_stream": false,
        "deployment_mode": "Knative"
      },
      "compatibility": {
        "supports_streaming": true,
        "supports_vision": false,
        "supports_video": false,
        "supports_tools": false,
        "supports_system_prompt": true,
        "reasoning_model": false,
        "needs_json_fixing": false,
        "strips_thinking": false
      },
      "domain": "nlp",
      "subdomain": "large-language-model",
      "tags": ["chat", "llm", "CHANGEME-extra-tags"],
      "content_types": ["text"],
      "languages": ["multilingual"],
      "tier": "production",
      "server_config": {
        "cli_args": [
          "--served-model-name", "CHANGEME",
          "--port", "8080",
          "--tensor-parallel-size", "CHANGEME",
          "--max-model-len", "CHANGEME",
          "--gpu-memory-utilization", "0.92"
        ],
        "model_path": "/data",
        "shared_memory": "CHANGEME (8Gi for TP1, 16Gi for TP2+)",
        "vllm_version": "0.20.2"
      }
    }
```

### Optional blocks (add inside the JSON when applicable)

**Reasoning model** — add to `compatibility` and add `param_translation`:
```json
"reasoning_model": true,
"strips_thinking": true,
```

See `phi-4-reasoning/details.yaml` for the full `param_translation.thinking` block with effort maps.

**Tool calling** — add to `compatibility` and `server_config.cli_args`:
```json
"supports_tools": true,
```
```json
"--enable-auto-tool-choice",
"--tool-call-parser", "CHANGEME (hermes, qwen, gemma4, etc.)"
```

**Vision/multimodal** — add to `compatibility` and `server_config.cli_args`:
```json
"supports_vision": true,
```
```json
"--limit-mm-per-prompt", "{\"image\": CHANGEME}",
"--trust-remote-code"
```

**Multi-GPU (TP≥2)** — set gpu_count, add shared_memory, add `--disable-custom-all-reduce`:
```json
"gpu_count": 2,
```
```json
"--tensor-parallel-size", "2",
"--disable-custom-all-reduce",
```
**Always set `"shared_memory": "16Gi"` for TP≥2.**

**Whole-device GPU (TP≥2)** — do NOT use `nvidia.com/gpumem`. Use `nvidia.com/gpu: "N"`.

---

## Template B — Custom Science Server

For models with a custom FastAPI/Flask server (not vLLM). Biology, chemistry, weather, physics, etc.

### Shell (copy and fill in)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: CHANGEME-details
  namespace: models
  labels:
    model-details: "true"
data:
  details.json: |
    {
      "id": "CHANGEME",
      "status": "production",
      "type": "CHANGEME (predict, forecast, dock, embed, segment, classify, etc.)",
      "description_short": "ONE LINE — what it does, what domain",
      "description": "2-4 sentences. What the model predicts/classifies/generates. Input format. Key architecture details. Paper reference if notable.",
      "context_window": 0,
      "max_completion_tokens": 0,
      "endpoints": {
        "primary": "/v1/science/CHANGEME",
        "health": "/health"
      },
      "owned_by": "CHANGEME-org",
      "source": "CHANGEME-org/CHANGEME-model",
      "source_url": "https://huggingface.co/CHANGEME-org/CHANGEME-model",
      "license": "CHANGEME",
      "parameters": "CHANGEME",
      "precision": "CHANGEME",
      "architecture": "CHANGEME",
      "framework": "custom",
      "deployment": {
        "gpu": CHANGEME,
        "gpu_count": CHANGEME,
        "gpu_type": "CHANGEME (L40S or L40S-SHARED)",
        "cpu_request": "CHANGEME",
        "memory_request": "CHANGEME",
        "min_replicas": 0,
        "max_replicas": 3,
        "startup_seconds": CHANGEME,
        "container_image": "CHANGEME (python:3.11-slim or custom)",
        "timeout": CHANGEME,
        "pvc": "CHANGEME-data (CHANGEME Gi, NFS)",
        "venv": CHANGEME
      },
      "routing": {
        "kserve_custom": true,
        "k8s_name": "CHANGEME",
        "api_name": "CHANGEME",
        "gateway_type": "CHANGEME"
      },
      "compatibility": {
        "openai_compatible": false,
        "streaming": false
      },
      "domain": "CHANGEME (structural-biology, weather-climate, genomics, etc.)",
      "subdomain": "CHANGEME (molecular-docking, forecasting, etc.)",
      "tags": ["science", "CHANGEME-domain-tags", "gpu"],
      "content_types": ["application/json"],
      "input_map": {SEE INPUT_MAP PATTERNS BELOW},
      "output_map": {SEE OUTPUT_MAP PATTERNS BELOW},
      "server_config": {
        "port": 8080,
        "health_path": "/health",
        "model_path": "/data/model"
      }
    }
```

### Science-specific notes

- `context_window` and `max_completion_tokens` are `0` for non-LLM science models (they don't use token-based context).
- `type` should match the gateway endpoint pattern: `predict`, `forecast`, `dock`, `embed`, `segment`, `classify`, `design`, `generate`, `detect`, `translate`, `3d`, `depth`, `tts`, `audio-classification`, etc.
- `gpu_type` is `"L40S"` for whole-device or `"L40S-SHARED"` for HAMi vGPU split.
- `venv: true` if the init container builds a Python venv on PVC (common for science models with complex deps).

### input_map / output_map patterns

Science models have wildly different I/O. **The input_map must document exactly what the server's POST body expects**, and output_map must document what it returns. There is no single schema — match the pattern to the model's actual FastAPI server code.

Here are the 5 real patterns used on this cluster. Pick the one that matches your model:

#### Pattern 1 — Typed params with required/optional (most common)

Used by: diffdock, ligandmpnn, seisbench, esmfold, most prediction models.

```json
"input_map": {
  "protein_pdb": {
    "type": "string",
    "required": true,
    "description": "Protein structure in PDB format"
  },
  "ligand_smiles": {
    "type": "string",
    "required": true,
    "description": "Ligand as SMILES string (e.g. CC(=O)Oc1ccccc1C(=O)O)"
  },
  "num_poses": {
    "type": "integer",
    "required": false,
    "default": 10,
    "description": "Number of docked poses to generate"
  },
  "inference_steps": {
    "type": "integer",
    "required": false,
    "default": 20,
    "description": "Number of diffusion inference steps"
  }
},
"output_map": {
  "model": {"type": "string", "description": "Model name"},
  "poses": {"type": "array", "description": "Ranked poses with rank, confidence, and SDF content"}
}
```

#### Pattern 2 — Nested objects with description strings (weather/climate)

Used by: aurora, graphcast, pangu-weather, climax, neuralgcm.

```json
"input_map": {
  "surf_vars": {
    "2t": "2m temperature (K), shape [lat, lon]",
    "10u": "10m u-wind (m/s), shape [lat, lon]",
    "msl": "mean sea-level pressure (Pa), shape [lat, lon]"
  },
  "atmos_vars": {
    "t": "temperature at pressure levels, shape [level, lat, lon]",
    "z": "geopotential at pressure levels, shape [level, lat, lon]"
  },
  "lat": "[90, ..., -90] float array",
  "lon": "[0, ..., 359.75] float array",
  "time": "ISO datetime string e.g. 2024-01-01T00:00:00",
  "atmos_levels": "[50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 850, 925, 1000]"
},
"output_map": {
  "surf_vars": "same structure as input, 6h ahead",
  "atmos_vars": "same structure as input, 6h ahead",
  "step": "6h"
}
```

#### Pattern 3 — Crystal/material structure (chemistry, physics)

Used by: chgnet, mace-mp, mace-mp-0, mace-mh-1, mattersim.

```json
"input_map": {
  "structure": {
    "elements": "array of element symbols e.g. [\"Li\", \"Fe\", \"P\", \"O\"]",
    "positions": "array of [x,y,z] positions in Angstroms",
    "cell": "3x3 cell vectors",
    "pbc": "[bool, bool, bool] periodic boundary conditions"
  }
},
"output_map": {
  "energy_eV": "total potential energy in eV",
  "forces_eV_A": "per-atom forces in eV/Angstrom",
  "stress_eV_A3": "Voigt stress tensor"
}
```

For structure prediction/relaxation, add a second input mode:

```json
"input_map": {
  "predict": {
    "structure": "same as above, single-point energy prediction"
  },
  "relax": {
    "structure": "same as above, runs geometry optimization",
    "fmax": "force convergence threshold in eV/A (default: 0.1)",
    "steps": "max relaxation steps (default: 300)"
  }
}
```

#### Pattern 4 — Binary/image inputs (vision, 3D reconstruction)

Used by: dust3r, mast3r, medsam, totalsegmentator, depth-anything.

```json
"input_map": {
  "images": "array of 2+ base64-encoded JPEG/PNG images",
  "output_format": "\"pointcloud\" (default) or \"depth\""
},
"output_map": {
  "pointclouds": [
    {"pts3d": "[[x,y,z], ...]", "confidence": "[float, ...]"}
  ],
  "model": "dust3r"
}
```

For medical segmentation (totalsegmentator, medsam):

```json
"input_map": {
  "ct_array": "3D numpy array shape [D, H, W] in Hounsfield Unit values",
  "spacing": "voxel spacing in mm [z, y, x] (default: [1.5, 1.5, 1.5])",
  "fast": "boolean, use fast mode (default: true)"
},
"output_map": {
  "segmentation": "3D label array with integer labels for 117 structures",
  "structures": "list of anatomical structure names found"
}
```

#### Pattern 5 — Text/sequence input (restoration, classification, generation)

Used by: ithaca, climberbert, finbert, scgpt, most text-based science models.

```json
"input_map": {
  "text": {
    "type": "string",
    "required": true,
    "description": "Ancient Greek text with ? for missing characters (50-750 chars, uppercase)"
  },
  "demo": {
    "type": "boolean",
    "required": false,
    "default": true,
    "description": "Use demo input instead of custom text"
  }
},
"output_map": {
  "restoration": "restored text with predictions for gaps",
  "date": "attributed date range (mean ± std)",
  "location": "attributed geographic region"
}
```

### server_config patterns for science models

Science models often have more complex server configs than LLMs. Add what applies:

```json
"server_config": {
  "port": 8080,
  "health_path": "/health",
  "model_path": "/data/model",
  "checkpoint": "CHANGEME.ckpt (if model loads a specific checkpoint file)",
  "inference_backend": "subprocess / torch / onnx / jax (how inference runs)",
  "venv_path": "/data/venv (if using PVC-cached venv)",
  "pip_note": "any special pip install steps done by init container",
  "dependencies": "key Python packages and versions",
  "esm2_cache": "/data/hf_cache (if model uses ESM-2 embeddings)"
}
```

---

## Template C — Embedding-only

Lighter version for pure embedding models (TEI or custom). No chat, no completions.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: CHANGEME-details
  namespace: models
  labels:
    model-details: "true"
data:
  details.json: |
    {
      "id": "CHANGEME",
      "status": "production",
      "type": "embed",
      "description_short": "ONE LINE — embedding model, dimension, domain",
      "description": "2 sentences. What it embeds, dimension, training data.",
      "context_window": 0,
      "max_completion_tokens": 0,
      "endpoints": {
        "primary": "/v1/embeddings",
        "health": "/health"
      },
      "owned_by": "CHANGEME-org",
      "source": "CHANGEME-org/CHANGEME-model",
      "source_url": "https://huggingface.co/CHANGEME-org/CHANGEME-model",
      "license": "CHANGEME",
      "parameters": "CHANGEME",
      "precision": "fp32",
      "architecture": "CHANGEME (BERT, CLIP, etc.)",
      "framework": "custom",
      "deployment": {
        "gpu": CHANGEME,
        "gpu_count": CHANGEME,
        "gpu_type": "CHANGEME",
        "min_replicas": 0,
        "max_replicas": 3,
        "container_image": "CHANGEME",
        "timeout": 300
      },
      "routing": {
        "path_prefix": "/v1/",
        "serialize": false,
        "no_stream": true
      },
      "compatibility": {
        "supports_streaming": false,
        "supports_vision": false,
        "reasoning_model": false,
        "needs_json_fixing": false,
        "strips_thinking": false
      },
      "domain": "CHANGEME",
      "subdomain": "CHANGEME",
      "tags": ["embed", "CHANGEME-domain-tags"],
      "content_types": ["text"],
      "input_map": {
        "input": {
          "type": "CHANGEME (string or array)",
          "required": true,
          "description": "Text or sequence to embed"
        }
      },
      "output_map": {
        "embedding": {
          "type": "array",
          "description": "CHANGEME-dim float vector"
        }
      },
      "server_config": {
        "port": 8080,
        "health_path": "/health",
        "model_path": "/data/model"
      }
    }
```
