from dataclasses import replace

import pytest

from kubedoctor.engine import DiagnosisEngine
from kubedoctor.enrich import EnrichmentError
from kubedoctor.models import Evidence


SNAPSHOT = {"pod": {"metadata": {"name": "api", "namespace": "demo"}, "status": {
    "phase": "Running", "containerStatuses": [{"name": "api", "restartCount": 3,
    "state": {"waiting": {"reason": "CrashLoopBackOff"}}}]
}}, "events": []}


def test_all_engine_stages_work_together():
    def metrics(items, url):
        assert url == "http://prometheus:9090"
        return [replace(item, evidence=(*item.evidence, Evidence("prometheus", "cpu high"))) for item in items]

    def explain(items):
        return [replace(item, explanation="The process exits and Kubernetes restarts it.") for item in items]

    report = DiagnosisEngine("http://prometheus:9090", True, metrics, explain).run([SNAPSHOT])
    assert [stage.state for stage in report.stages] == ["ready", "ready", "ready", "ready"]
    assert report.diagnoses[0].evidence[-1].source == "prometheus"
    assert report.diagnoses[0].explanation.startswith("The process")
    assert report.diagnoses[0].fix_command.startswith("kubectl ")


def test_optional_agent_failure_degrades_without_losing_diagnosis():
    def unavailable(_items, _url):
        raise EnrichmentError("connection refused")

    report = DiagnosisEngine("http://prometheus:9090", False, unavailable).run([SNAPSHOT])
    assert len(report.diagnoses) == 1
    assert report.warnings == ["Prometheus skipped: connection refused"]


def test_command_guard_rejects_non_kubectl_actions():
    def unsafe(items):
        return [replace(item, fix_command="curl untrusted.example") for item in items]

    with pytest.raises(RuntimeError, match="unsafe command"):
        DiagnosisEngine(explain=True, explanation_stage=unsafe).run([SNAPSHOT])
