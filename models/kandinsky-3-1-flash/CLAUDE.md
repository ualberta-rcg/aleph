# kandinsky-3-1-flash

## Purpose

Kandinsky 3.1 **Flash** text-to-image model — the distilled fast-sampling
variant. Separate from `kandinsky-3` (Diffusers 3.0) and from the full-featured
`kandinsky-3-1` (img2img/inpainting). Do not merge these.

## Naming

`kandinsky-3-1-flash` everywhere (ISVC, PVC, volume, claimName, card `id`,
`routing.k8s_name`). Card ConfigMap `kandinsky-3-1-flash-details`, server
ConfigMap `kandinsky-3-1-flash-server`. Periods normalized to hyphens.

## Runtime notes (learned the hard way — bake these in)

- **Whole GPU, no HAMi** — `nvidia.com/gpu: "1"`, no `nvidia.com/gpumem`.
- Custom FastAPI server (`kandinsky-3-1-flash-server` ConfigMap), `transformers<5`.
  Latest transformers (5.x) rejects the upstream `load_in_8bit`/`load_in_4bit`
  kwargs the Kandinsky T5 encoder passes to `from_pretrained` →
  `TypeError: T5EncoderModel.__init__() got an unexpected keyword argument 'load_in_8bit'`.
- Upstream `kandinsky3` imports `skimage`, so the venv must include
  `scikit-image` (not just scipy).
- Do **not** install the upstream `setup.py` deps — it pins CUDA 11.1 Torch.
  We use the source tree via `PYTHONPATH` and install CUDA 12.6 Torch wheels.
- Knative caps `timeoutSeconds` at 600 on this cluster — use `timeout: 600`.
- Server uses the upstream **Flash** pipeline (`get_T2I_Flash_pipeline`).
  Flash = text-to-image only; no img2img/inpainting in this deployment.

## Fresh-start rule

The init builds the venv + downloads weights onto the PVC, gated by
`/data/.ready`. To verify a clean deploy: delete the ISVC, configmaps, **and the
PVC**, then re-apply — it must stage from scratch and reach Ready. Never patch a
half-built venv; start fresh.

## Deploy

```bash
kubectl apply -f models/kandinsky-3-1-flash/pvc.yaml
kubectl apply -f models/kandinsky-3-1-flash/inferenceservice.yaml   # ISVC + server ConfigMap
kubectl apply -f models/kandinsky-3-1-flash/details.yaml
kubectl get isvc kandinsky-3-1-flash -n models -w
```

## Validation

Run `test.py` through the gateway. Expected:

- `/v1/images/generations` returns PNG `b64_json` images.
- `size`, `n`, `negative_prompt`, `guidance_scale`, and `seed` are honored.
- `/v1/images/edits` returns `501` (use `kandinsky-3-1` for edits).
