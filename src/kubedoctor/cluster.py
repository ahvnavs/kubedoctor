"""Read-only Kubernetes API collection."""

from typing import Any

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException


class ClusterError(RuntimeError):
    pass


def load_client(context: str | None = None) -> client.CoreV1Api:
    try:
        config.load_kube_config(context=context)
    except ConfigException:
        try:
            config.load_incluster_config()
        except ConfigException as exc:
            raise ClusterError("No Kubernetes configuration found") from exc
    return client.CoreV1Api()


def collect(api: client.CoreV1Api, namespace: str, all_namespaces: bool, pod: str | None) -> list[dict[str, Any]]:
    try:
        if pod:
            pods = [api.read_namespaced_pod(pod, namespace)]
        elif all_namespaces:
            pods = api.list_pod_for_all_namespaces().items
        else:
            pods = api.list_namespaced_pod(namespace).items
        serializer = client.ApiClient()
        results = []
        for item in pods:
            ns = item.metadata.namespace
            events = api.list_namespaced_event(
                ns, field_selector=f"involvedObject.uid={item.metadata.uid}"
            ).items
            results.append({
                "pod": serializer.sanitize_for_serialization(item),
                "events": [serializer.sanitize_for_serialization(event) for event in events],
            })
        return results
    except client.ApiException as exc:
        detail = getattr(exc, "reason", None) or str(exc)
        raise ClusterError(f"Kubernetes API request failed: {detail}") from exc
