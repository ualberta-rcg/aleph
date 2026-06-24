#!/usr/bin/env bash
# Per-model test helper. Run from the repo root on a Vulcan login node.
#
#   test/test-model.sh <model-dir-name> [action]
#
# actions:
#   apply     - kubectl apply the model's local manifests (reconcile drift)
#   recreate  - delete ISVC, wait until fully cleared from kube, reapply (keeps PVC).
#               Use this whenever you change a model's config (avoids stale revisions).
#   up        - pre-warm: scale LATEST revision to 1 and wait for ISVC Ready + live pod
#   status    - print ISVC readiness + latest revision reason + pod state
#   logs      - tail kserve-container (and init) logs for the live pod
#   curl      - run a raw curl through the gateway:  ... curl <PATH> <JSON>
#   zero      - scale the predictor back to zero
#   cycle     - zero, confirm scaled to zero, then up again (cold-start proof)
#   all       - apply -> up -> status  (mechanical bring-up; payloads are manual)
#
# The gateway ClusterIP (10.43.147.39) is only reachable from inside 230, so all
# kubectl/curl run via SSH to the head node. Request PAYLOADS are intentionally NOT
# baked in here: each model gets a custom test authored into models/<m>/TEST.md.
set -uo pipefail

HEAD="${HEAD:-172.26.92.43}"
GW="${GW:-10.43.147.39}"
NS=models
M="${1:?usage: test-model.sh <model> [action]}"
ACTION="${2:-all}"
DIR="models/${M}"

SSH=(sudo ssh -o StrictHostKeyChecking=no "root@${HEAD}")
KEXPORT='export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml;'

k()  { "${SSH[@]}" "${KEXPORT} kubectl $*"; }
kf() { "${SSH[@]}" "${KEXPORT} kubectl apply -f -"; }   # reads manifest on stdin

apply_one() { [ -f "$1" ] && { echo ">> apply $1"; cat "$1" | kf; }; }

do_apply() {
  [ -d "$DIR" ] || { echo "no dir $DIR"; return 1; }
  apply_one "$DIR/pvc.yaml"
  for c in "$DIR"/*configmap*.yaml; do [ -f "$c" ] && apply_one "$c"; done
  apply_one "$DIR/details.yaml"
  apply_one "$DIR/inferenceservice.yaml"
}

# Deployment backing the LATEST (currently-serving) revision, not just the first match.
latest_dep() {
  local rev
  rev=$(k get isvc -n $NS "$M" -o jsonpath='{.status.components.predictor.latestReadyRevision}' 2>/dev/null)
  [ -z "$rev" ] && rev=$(k get isvc -n $NS "$M" -o jsonpath='{.status.components.predictor.latestCreatedRevision}' 2>/dev/null)
  [ -z "$rev" ] && { k get deploy -n $NS -o name 2>/dev/null | grep "${M}-predictor-[0-9]*-deployment" | sort | tail -1; return; }
  echo "deployment.apps/${rev}-deployment"
}
dep() { latest_dep; }

# Primary endpoint path + catalog id from the LOCAL details.yaml (for activation nudges).
primary_path() {
  grep -o '"primary":[[:space:]]*"[^"]*"' "$DIR/details.yaml" 2>/dev/null | head -1 | sed 's/.*"\(\/[^"]*\)"/\1/'
}
model_id() {
  grep -o '"id":[[:space:]]*"[^"]*"' "$DIR/details.yaml" 2>/dev/null | head -1 | sed 's/.*"id":[[:space:]]*"\([^"]*\)".*/\1/'
}

# Pre-warm a Knative scale-to-zero service the ONLY way that works: send a model-specific
# request so the activator scales it up. (Manually scaling the deployment is reverted by the
# KPA.) Nudge with a throwaway POST to the primary endpoint, then poll for a live pod.
do_up() {
  local path mid; path=$(primary_path); [ -z "$path" ] && path=/health
  mid=$(model_id); [ -z "$mid" ] && mid="$M"
  echo ">> activating $M (id=$mid) via gateway POST ${path} (poll pod, up to ~15m)"
  for i in $(seq 1 90); do
    local out; out=$("${SSH[@]}" "${KEXPORT} kubectl get pods -n $NS --no-headers | grep '^${M}-predictor' | grep -v Terminating | grep Running | grep -E '([2-9]|[0-9][0-9])/[2-9]' | head -1")
    [ -n "$out" ] && { echo "   ready: $out"; return 0; }
    "${SSH[@]}" "curl -s -m 15 -o /dev/null -X POST http://${GW}${path} -H 'Content-Type: application/json' -d '{\"model\":\"${mid}\"}'" >/dev/null 2>&1
    sleep 10
  done
  echo "   (timeout; check logs)"; return 1
}

do_status() {
  echo "--- isvc ---"; k get isvc -n $NS "$M" --no-headers
  echo "--- latest revision ---"; k get revision -n $NS 2>/dev/null \| grep "\"^${M}-\"" \| tail -1
  echo "--- pods ---"; k get pods -n $NS 2>/dev/null \| grep "\"^${M}-\"" \| grep -v Terminating
}

do_logs() {
  local p; p=$("${SSH[@]}" "${KEXPORT} kubectl get pods -n $NS --no-headers | grep '^${M}-' | grep -v Terminating | head -1 | awk '{print \$1}'")
  [ -z "$p" ] && { echo "no live pod"; return; }
  echo "=== $p kserve-container ==="; k logs -n $NS "$p" -c kserve-container --tail=40
  echo "=== $p setup (init) ==="; k logs -n $NS "$p" -c setup --tail=20 2>/dev/null
}

do_curl() {  # $3 = path, $4 = json body (optional). Retries through scale-to-zero cold start.
  local path="${3:?need path}" body="${4:-}" resp
  for i in $(seq 1 20); do
    if [ -n "$body" ]; then
      resp=$("${SSH[@]}" "curl -s -m 180 -X POST http://${GW}${path} -H 'Content-Type: application/json' -d '$body'")
    else
      resp=$("${SSH[@]}" "curl -s -m 60 http://${GW}${path}")
    fi
    if echo "$resp" | grep -q 'model_scaled_to_zero\|is starting up'; then
      echo "   (cold start, retry $i...)" >&2; sleep 15; continue
    fi
    echo "$resp"; return 0
  done
  echo "$resp"
}

# Delete the ISVC and wait until ALL its pods/revisions are gone from kube, then
# reapply from the local repo. Keeps the PVC (weights/venv cache survive).
do_recreate() {
  echo ">> deleting isvc/$M (keeping PVC)"
  k delete isvc -n $NS "$M" --ignore-not-found --wait=true >/dev/null 2>&1
  echo ">> waiting for all ${M}- pods/revisions to clear"
  for i in $(seq 1 60); do
    local pods revs
    pods=$("${SSH[@]}" "${KEXPORT} kubectl get pods -n $NS --no-headers 2>/dev/null | grep -c '^${M}-predictor' || true")
    revs=$("${SSH[@]}" "${KEXPORT} kubectl get revision -n $NS --no-headers 2>/dev/null | grep -c '^${M}-predictor' || true")
    [ "$pods" = "0" ] && [ "$revs" = "0" ] && { echo "   cleared."; break; }
    sleep 5
  done
  do_apply
}

do_zero() {
  local d; d=$(dep)
  [ -n "$d" ] && k scale -n $NS "$d" --replicas=0 >/dev/null 2>&1
  echo ">> scaled $M to zero"
}

do_cycle() { do_zero; sleep 20; do_up; }

case "$ACTION" in
  apply)    do_apply ;;
  recreate) do_recreate ;;
  up)     do_up ;;
  status) do_status ;;
  logs)   do_logs ;;
  curl)   do_curl "$@" ;;
  zero)   do_zero ;;
  cycle)  do_cycle ;;
  all)    do_apply && do_up; do_status ;;
  *) echo "unknown action $ACTION"; exit 2 ;;
esac
