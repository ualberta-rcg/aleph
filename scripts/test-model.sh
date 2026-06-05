#!/usr/bin/env bash
# Per-model test helper for cluster 230. Run from the repo root on a Vulcan login node.
#
#   scripts/test-model.sh <model-dir-name> [action]
#
# actions:
#   apply     - ship + kubectl apply the model's local manifests (reconcile drift)
#   up        - scale predictor to 1 and wait for the ISVC to report Ready
#   status    - print ISVC readiness + latest revision reason + pod state
#   logs      - tail kserve-container (and init) logs for the live pod
#   curl      - run a raw curl through the gateway:  ... curl <PATH> <JSON>
#   zero      - scale the predictor back to zero
#   cycle     - zero, confirm scaled to zero, then up again (cold-start proof)
#   all       - apply -> up -> status  (mechanical bring-up; payloads are manual)
#
# The gateway ClusterIP (10.43.79.101) is only reachable from inside 230, so all
# kubectl/curl run via SSH to the head node. Request PAYLOADS are intentionally NOT
# baked in here: each model gets a custom test authored into models/<m>/TEST.md.
set -uo pipefail

HEAD="${HEAD:-172.26.92.230}"
GW="${GW:-10.43.79.101}"
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

dep() { k get deploy -n $NS -o name 2>/dev/null | grep -m1 "${M}-predictor-[0-9]*-deployment"; }

do_up() {
  local d; d=$(dep)
  [ -n "$d" ] && k scale -n $NS "$d" --replicas=1 >/dev/null 2>&1
  echo ">> waiting for isvc/$M Ready (up to 12m)"
  k wait -n $NS --for=condition=Ready "isvc/$M" --timeout=720s
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

do_curl() {  # $3 = path, $4 = json body (optional)
  local path="${3:?need path}" body="${4:-}"
  if [ -n "$body" ]; then
    "${SSH[@]}" "curl -s -m 120 -X POST http://${GW}${path} -H 'Content-Type: application/json' -d '$body'"
  else
    "${SSH[@]}" "curl -s -m 60 http://${GW}${path}"
  fi
  echo
}

do_zero() {
  local d; d=$(dep)
  [ -n "$d" ] && k scale -n $NS "$d" --replicas=0 >/dev/null 2>&1
  echo ">> scaled $M to zero"
}

do_cycle() { do_zero; sleep 20; do_up; }

case "$ACTION" in
  apply)  do_apply ;;
  up)     do_up ;;
  status) do_status ;;
  logs)   do_logs ;;
  curl)   do_curl "$@" ;;
  zero)   do_zero ;;
  cycle)  do_cycle ;;
  all)    do_apply && do_up; do_status ;;
  *) echo "unknown action $ACTION"; exit 2 ;;
esac
