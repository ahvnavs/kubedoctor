import pytest

from kubedoctor.diagnose import diagnose_snapshot


def snap(state, *, phase="Running", events=None):
    return {"pod": {"metadata": {"name": "api-1", "namespace": "demo"}, "status": {
        "phase": phase, "containerStatuses": [{"name": "api", "restartCount": 4, **state}]
    }}, "events": events or []}


@pytest.mark.parametrize(("state", "code"), [
    ({"state": {"waiting": {"reason": "CrashLoopBackOff"}}}, "crash-loop"),
    ({"state": {"waiting": {"reason": "ImagePullBackOff", "message": "not found"}}}, "image-pull"),
    ({"state": {"waiting": {"reason": "CrashLoopBackOff"}}, "lastState": {"terminated": {"reason": "OOMKilled", "exitCode": 137}}}, "oom-killed"),
])
def test_container_failures(state, code):
    diagnoses = diagnose_snapshot(snap(state))
    assert code in {item.code for item in diagnoses}
    assert all(item.fix_command.startswith("kubectl -n demo") for item in diagnoses)


@pytest.mark.parametrize(("message", "title"), [
    ("0/1 nodes are available: 1 Insufficient cpu.", "capacity"),
    ("pod has unbound immediate PersistentVolumeClaims", "persistent volume"),
    ("node(s) had untolerated taint", "taints"),
])
def test_pending_causes(message, title):
    diagnoses = diagnose_snapshot(snap({}, phase="Pending", events=[{"reason": "FailedScheduling", "message": message}]))
    assert title in diagnoses[0].title.lower()
    assert message in diagnoses[0].summary


def test_healthy_pod_has_no_diagnosis():
    assert diagnose_snapshot(snap({"state": {"running": {}}})) == []
