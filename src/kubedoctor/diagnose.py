"""Deterministic rules for the failure modes KubeDoctor supports."""

from typing import Any

from .models import Diagnosis, Evidence, Severity

IMAGE_REASONS = {"ImagePullBackOff", "ErrImagePull", "InvalidImageName"}


def _identity(pod: dict[str, Any]) -> tuple[str, str, str]:
    metadata = pod.get("metadata", {})
    return metadata.get("namespace", "default"), metadata.get("name", "unknown"), f"pod/{metadata.get('name', 'unknown')}"


def _statuses(pod: dict[str, Any]) -> list[dict[str, Any]]:
    status = pod.get("status", {})
    return [*(status.get("initContainerStatuses") or []), *(status.get("containerStatuses") or [])]


def diagnose_snapshot(snapshot: dict[str, Any]) -> list[Diagnosis]:
    pod = snapshot["pod"]
    events = snapshot.get("events", [])
    namespace, name, resource = _identity(pod)
    found: list[Diagnosis] = []

    for container in _statuses(pod):
        cname = container.get("name", "container")
        state = container.get("state") or {}
        waiting = state.get("waiting") or {}
        terminated = state.get("terminated") or {}
        previous = (container.get("lastState") or {}).get("terminated") or {}
        reason = waiting.get("reason")

        oom_killed = terminated.get("reason") == "OOMKilled" or previous.get("reason") == "OOMKilled"
        if reason == "CrashLoopBackOff" and not oom_killed:
            found.append(Diagnosis(
                "crash-loop", "Container repeatedly crashes",
                "Inspect the previous container attempt; its logs usually contain the application error.",
                Severity.CRITICAL, resource,
                f"kubectl -n {namespace} logs {name} -c {cname} --previous",
                (Evidence(f"container/{cname}", f"waiting={reason}, restarts={container.get('restartCount', 0)}"),),
            ))
        if reason in IMAGE_REASONS:
            message = waiting.get("message") or "image pull failed"
            found.append(Diagnosis(
                "image-pull", "Container image cannot be pulled",
                "Correct the image reference or registry credentials, then let the workload retry.",
                Severity.CRITICAL, resource,
                f"kubectl -n {namespace} set image pod/{name} {cname}=<working-image>",
                (Evidence(f"container/{cname}", f"{reason}: {message}"),),
            ))
        ended = terminated if terminated.get("reason") == "OOMKilled" else previous
        if oom_killed:
            found.append(Diagnosis(
                "oom-killed", "Container exceeded its memory limit",
                "Raise the workload memory limit after checking actual usage and application behavior.",
                Severity.CRITICAL, resource,
                f"kubectl -n {namespace} describe pod {name}",
                (Evidence(f"container/{cname}", f"OOMKilled with exit code {ended.get('exitCode', 137)}"),),
            ))

    # Waiting state is transient between restarts. The kubelet's BackOff event is
    # durable and keeps crash-loop diagnosis reliable across slower API polls.
    backoff = next((
        event for event in reversed(events)
        if event.get("reason") == "BackOff"
        and "restarting failed container" in event.get("message", "").lower()
    ), None)
    existing_codes = {item.code for item in found}
    if backoff and not {"crash-loop", "oom-killed"} & existing_codes:
        statuses = _statuses(pod)
        cname = statuses[0].get("name", "container") if statuses else "container"
        message = backoff.get("message", "kubelet is backing off container restarts")
        found.append(Diagnosis(
            "crash-loop", "Container repeatedly crashes",
            "Inspect the previous container attempt; its logs usually contain the application error.",
            Severity.CRITICAL, resource,
            f"kubectl -n {namespace} logs {name} -c {cname} --previous",
            (Evidence("event/BackOff", message),),
        ))

    if pod.get("status", {}).get("phase") == "Pending" and not found:
        failed = [e for e in events if e.get("reason") == "FailedScheduling"]
        if failed:
            message = failed[-1].get("message", "scheduler could not place the pod")
            if "Insufficient" in message:
                title = "Pod requests unavailable node capacity"
                command = f"kubectl -n {namespace} describe pod {name}"
            elif "unbound immediate PersistentVolumeClaims" in message:
                title = "Pod is waiting for a persistent volume claim"
                command = f"kubectl -n {namespace} get pvc"
            elif "taint" in message:
                title = "Node taints prevent scheduling"
                command = f"kubectl -n {namespace} describe pod {name}"
            else:
                title = "Scheduler cannot place the pod"
                command = f"kubectl -n {namespace} describe pod {name}"
            found.append(Diagnosis(
                "pending-unschedulable", title, message, Severity.WARNING, resource, command,
                (Evidence("event/FailedScheduling", message),),
            ))
    return found


def diagnose_all(snapshots: list[dict[str, Any]]) -> list[Diagnosis]:
    return [item for snapshot in snapshots for item in diagnose_snapshot(snapshot)]
