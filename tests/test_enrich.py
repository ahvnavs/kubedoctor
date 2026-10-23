import json

import pytest

from kubedoctor.enrich import EnrichmentError, add_llm_explanations, add_prometheus_context
from kubedoctor.models import Diagnosis, Severity


def diagnosis():
    return Diagnosis("oom-killed", "Out of memory", "limit exceeded", Severity.CRITICAL,
                     "pod/api", "kubectl edit pod/api")


class Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *_): return None
    def read(self): return json.dumps(self.payload).encode()


def test_prometheus_adds_memory_evidence(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: Response({
        "data": {"result": [{"value": [1, "104857600"]}]}
    }))
    item = add_prometheus_context([diagnosis()], "http://prometheus:9090")[0]
    assert item.evidence[-1].detail == "recent memory usage=100.0 MiB"


def test_llm_is_explicitly_configured(monkeypatch):
    for key in ("KUBEDOCTOR_LLM_URL", "KUBEDOCTOR_LLM_API_KEY", "KUBEDOCTOR_LLM_MODEL"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(EnrichmentError, match="KUBEDOCTOR_LLM_URL"):
        add_llm_explanations([diagnosis()])


def test_llm_explanation_is_added_without_changing_fix(monkeypatch):
    monkeypatch.setenv("KUBEDOCTOR_LLM_URL", "https://llm.example/v1/chat/completions")
    monkeypatch.setenv("KUBEDOCTOR_LLM_API_KEY", "test-token")
    monkeypatch.setenv("KUBEDOCTOR_LLM_MODEL", "small-model")
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: Response({
        "choices": [{"message": {"content": "The container used more memory than allowed."}}]
    }))
    item = add_llm_explanations([diagnosis()])[0]
    assert item.explanation.startswith("The container")
    assert item.fix_command == diagnosis().fix_command
