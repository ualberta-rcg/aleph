# colabfold-msa-search

ColabFold MSA Search NIM — GPU-accelerated multiple sequence alignment and
template search for protein structure prediction workflows.

| Property | Value |
|---|---|
| Image | `nvcr.io/nim/colabfold/msa-search:2.5.0` |
| NGC page | https://build.nvidia.com/colabfold/msa-search |
| Public endpoint | `POST /v1/biology/colabfold/msa-search/predict` |
| Native endpoint | `POST /biology/colabfold/msa-search/predict` |
| Type | predict |
| GPUs | 1 L40S slice (24 GiB vGPU) |
| Scale-to-zero | yes |

## Files

- `pvc.yaml` — 100 Gi ReadWriteMany cache PVC
- `inferenceservice.yaml` — KServe predictor
- `details.yaml` — gateway model card (ConfigMap)
- `test.py` — OpenAPI-driven gateway test battery

## Example request

```bash
curl -k -X POST https://inference.vulcan.alliancecan.ca/v1/biology/colabfold/msa-search/predict \
  -H "Authorization: Bearer $TYK_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "colabfold-msa-search",
    "sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQTLGQHDFSAGEGLYTHMKALRPDEDRLSPLHSVYVDQWDWERVMGDGERQFSTLKSTVEAIWAGIKATEAAVSEEFGLAPFLPDQIHFVHSQELLSRYPDLDAKGRERAIAKDLGAVFLVGIGGKLSDGHRHDVRAPDYDDWSTPSELGHAGLNGDILVWNPVLEDAFELSSMGIRVDADTLKHQLALTGDEDRLELEWHQALLRGEMPTQTDAKTALMAWLDVFAEFGWK",
    "databases": ["pdb70_220313"],
    "output_alignment_formats": ["a3m"],
    "iterations": 1,
    "e_value": 0.0001
  }'
```

## Notes

- The public path is `/v1/biology/colabfold/msa-search/predict`; the NIM native
  path is `/biology/colabfold/msa-search/predict`, so the gateway card sets
  `routing.strip_v1_prefix: true`.
- The request body is passed through unchanged except for the OpenAI-style
  `model` field, which is stripped before reaching the NIM
  (`custom_params.passthrough: true`).
- Cache is stored on `pvc.yaml` to avoid re-downloading search databases on
  every cold start.

## Deploy

```bash
kubectl apply -f models/colabfold-msa-search/pvc.yaml
kubectl apply -f models/colabfold-msa-search/inferenceservice.yaml
kubectl apply -f models/colabfold-msa-search/details.yaml
```

## Test

Run from inside the gateway pod:

```bash
cat models/colabfold-msa-search/test.py | \
  kubectl exec -i -n models deploy/model-gateway -- python3 -
```

Or from the login node:

```bash
sudo ssh root@172.26.92.43 \
  "export PATH=\$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml; \
   cat <<'PY' | kubectl exec -i -n models deploy/model-gateway -- python3 - \
$(cat models/colabfold-msa-search/test.py)
PY"
```
