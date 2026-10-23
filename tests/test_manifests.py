from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]


def documents(path):
    return [item for item in yaml.safe_load_all(path.read_text()) if item]


def test_lab_contains_each_reproducible_failure():
    pods = [item for item in documents(ROOT / "lab/failures.yaml") if item["kind"] == "Pod"]
    assert {pod["metadata"]["name"] for pod in pods} == {
        "crash-loop", "image-pull", "oom-killed", "pending-capacity"
    }
    assert all(pod["metadata"]["namespace"] == "kubedoctor-lab" for pod in pods)


def test_rbac_is_read_only_and_narrow():
    role = next(item for item in documents(ROOT / "manifests/rbac.yaml") if item["kind"] == "ClusterRole")
    assert role["rules"] == [{
        "apiGroups": [""], "resources": ["pods", "events"], "verbs": ["get", "list"]
    }]
