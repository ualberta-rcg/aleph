# Aleph post-deploy steps

These are the few steps that can't be auto-deployed by RKE2 — either because they are
site-specific fill-ins that need external prereqs (DNS, port 80) or because they are
one-time verifications.

**Everything else is fully automated.** Once the Warewulf image is baked with the tokens
filled in `ww-overlays/overlays/` and nodes are provisioned, the entire platform comes up:
MetalLB, Tyk, NFS, cert-manager, Istio, Knative, KServe, and the model-gateway.

## 1. Issue a Tyk API key (required to use the gateway)

```bash
# Discover the VIP MetalLB assigned to Tyk (or use your __VIP__ directly):
VIP=$(kubectl get svc tyk-gateway-nodeport -n tyk \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
SECRET=$(kubectl get secret secrets-tyk-oss-tyk-gateway -n tyk \
  -o jsonpath='{.data.APISecret}' | base64 -d)

KEY=$(curl -s -X POST http://$VIP/tyk/keys/create \
  -H "x-tyk-authorization: $SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "alias": "myuser",
    "meta_data": {"username": "myuser"},
    "access_rights": {
      "model-gateway": {
        "api_id": "model-gateway",
        "api_name": "model-gateway",
        "versions": ["Default"]
      }
    }
  }' | grep -o '"key":"[^"]*"' | cut -d'"' -f4)

echo "TYK_KEY=$KEY"
```

Save the key — Tyk does not return raw tokens after creation (only hashes).
For day-2 key management: `gateway/tyk/tyk-keys.sh`.

## 2. Smoke-test the stack

```bash
export TYK_KEY=<from above>
bash ww-overlays/post-deploy/verify-test-model.sh cpu    # CPU path (~2 min)
bash ww-overlays/post-deploy/verify-test-model.sh gpu    # GPU + HAMi path (~5 min)
bash ww-overlays/post-deploy/verify-test-model.sh cleanup
```

## 3. Add models

For each model, apply its card and InferenceService. The gateway picks them up via K8s Watch
within seconds — no gateway restart needed.

```bash
kubectl apply -f models/<model>/details.yaml
kubectl apply -f models/<model>/inferenceservice.yaml
kubectl get isvc <model> -n models -w    # wait for Ready
```

## 4. TLS certificate (optional, requires public DNS + port 80)

Once DNS points `__PUBLIC_HOSTNAME__` at the VIP and Traefik exposes port 80:

```bash
# Fill in __PUBLIC_HOSTNAME__ then:
kubectl apply -f ww-overlays/post-deploy/certificate.example.yaml
kubectl get certificate -n tyk    # Ready=True once ACME challenge passes
```

## Nothing else needed

The following are fully managed by the WW-overlay manifests — no manual kubectl required:
- MetalLB install + VIP pool + L2 advertisement
- Tyk OSS + Redis install, env config, API-def ConfigMap mount
- model-gateway Deployment + RBAC + Service
- cert-manager + ClusterIssuer
- NFS StorageClass
- HAMi vGPU scheduler + device plugin
- Istio + Knative + KServe bootstrap
