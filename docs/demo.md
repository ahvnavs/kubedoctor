# Six-minute demo

## 1. Create the lab

Run `make install`, then `make lab-up`. The script creates a local `kind-kubedoctor` cluster and applies four purpose-built failures in `kubedoctor-lab`.

Show the raw state first:

```sh
kubectl --context kind-kubedoctor get pods -n kubedoctor-lab
```

## 2. Diagnose it

```sh
kubedoctor diagnose --context kind-kubedoctor -n kubedoctor-lab
```

Connect each result to its evidence: restart count for the crash, the prior `OOMKilled` termination, the image pull runtime message, and the scheduler's insufficient-capacity event.

Then demonstrate automation-friendly output:

```sh
kubedoctor diagnose --context kind-kubedoctor -n kubedoctor-lab -o json
```

KubeDoctor exits with `1` when it finds failures. This distinguishes a finding from a tool error (`2`) and a clean result (`0`). Shell automation should handle the finding code deliberately.

## 3. Explain the design

The Kubernetes API is the source of truth. Prometheus can add recent resource evidence. The optional LLM sees only an already-formed diagnosis and explains it; it cannot replace the rule result or command. RBAC is read-only, the container is non-root, and CI proves the rules against a real cluster.

Finish with `make lab-down` to release the local cluster resources.
