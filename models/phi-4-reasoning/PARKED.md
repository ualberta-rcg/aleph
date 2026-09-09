Phi-4-reasoning is parked as of 2026-09-09.

`model-details=false` excludes the card from gateway discovery. `serving.kserve.io/stop=true` instructs KServe v0.15.2 to stop the serverless runtime; merely setting minReplicas to zero would still permit wake-ups. The original min/max values are retained for restoration, not active scaling. Weights and the Bound `phi-4-reasoning` PVC remain in place.

Applied through the live Warewulf client first: hide the card, verify its absence on all three gateway replicas, observe zero vLLM running/waiting requests and zero Knative average concurrent/proxied requests and request counts, then apply the stop annotation. Verified Stopped=True and zero predictor pods. No PVC deletion or other-model change.

To restore during an approved capacity window: remove the stop annotation, wait for the runtime to become Ready and pass synthetic checks, then restore the card's model-details label to true. Copy the tested state back into these files. Do not expose the card before the runtime is ready. These model files belong in this repo; they are not node boot overlays.

Implementation reference: https://github.com/kserve/kserve/blob/v0.15.2/pkg/controller/v1beta1/inferenceservice/components/predictor.go
