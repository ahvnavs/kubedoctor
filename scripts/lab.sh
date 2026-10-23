#!/usr/bin/env bash
set -euo pipefail

cluster=kubedoctor
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
doctor=${KUBEDOCTOR_BIN:-kubedoctor}
[[ -x "$root/.venv/bin/kubedoctor" ]] && doctor=${KUBEDOCTOR_BIN:-$root/.venv/bin/kubedoctor}

case "${1:-}" in
  up)
    kind get clusters | grep -qx "$cluster" || kind create cluster --config "$root/lab/kind.yaml"
    kubectl --context "kind-$cluster" create namespace kubedoctor-lab \
      --dry-run=client -o yaml | kubectl --context "kind-$cluster" apply -f -
    kubectl --context "kind-$cluster" wait --for=create serviceaccount/default \
      -n kubedoctor-lab --timeout=60s
    kubectl --context "kind-$cluster" apply -f "$root/lab/failures.yaml"
    ;;
  verify)
    export KUBECONFIG="$(kind get kubeconfig-path --name "$cluster" 2>/dev/null || true)"
    # Newer kind prints kubeconfig directly rather than exposing a path.
    if [[ -z "$KUBECONFIG" ]]; then
      tmp=$(mktemp)
      kind get kubeconfig --name "$cluster" >"$tmp"
      export KUBECONFIG="$tmp"
      trap 'rm -f "$tmp"' EXIT
    fi
    deadline=$((SECONDS + 180))
    while (( SECONDS < deadline )); do
      output=$("$doctor" diagnose -n kubedoctor-lab -o json || true)
      python - "$output" <<'PY' && exit 0 || true
import json, sys
codes = {item["code"] for item in json.loads(sys.argv[1])}
required = {"crash-loop", "oom-killed", "image-pull", "pending-unschedulable"}
missing = required - codes
print("detected:", ", ".join(sorted(codes)), "missing:", ", ".join(sorted(missing)))
raise SystemExit(bool(missing))
PY
      sleep 5
    done
    echo "Timed out waiting for all failure modes" >&2
    exit 1
    ;;
  down)
    kind delete cluster --name "$cluster"
    ;;
  *)
    echo "Usage: $0 {up|verify|down}" >&2
    exit 2
esac

