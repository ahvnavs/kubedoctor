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


def test_specific_container_failure_suppresses_stale_scheduler_event():
    snapshot = snap(
        {"state": {"waiting": {"reason": "ImagePullBackOff"}}},
        phase="Pending",
        events=[{"reason": "FailedScheduling", "message": "node had untolerated taint"}],
    )
    assert [item.code for item in diagnose_snapshot(snapshot)] == ["image-pull"]


def test_oom_root_cause_suppresses_generic_crash_loop():
    snapshot = snap({
        "state": {"waiting": {"reason": "CrashLoopBackOff"}},
        "lastState": {"terminated": {"reason": "OOMKilled", "exitCode": 137}},
    })
    assert [item.code for item in diagnose_snapshot(snapshot)] == ["oom-killed"]


def test_restart_backoff_event_covers_transient_container_state():
    snapshot = snap(
        {"state": {"terminated": {"reason": "Error", "exitCode": 1}}},
        events=[{"reason": "BackOff", "message": "Back-off restarting failed container app"}],
    )
    diagnoses = diagnose_snapshot(snapshot)
    assert [item.code for item in diagnoses] == ["crash-loop"]
    assert diagnoses[0].evidence[0].source == "event/BackOff"


def test_image_pull_backoff_event_is_not_misclassified_as_crash():
    snapshot = snap(
        {"state": {"waiting": {"reason": "ImagePullBackOff"}}},
        events=[{"reason": "BackOff", "message": "Back-off pulling image missing"}],
    )
    assert [item.code for item in diagnose_snapshot(snapshot)] == ["image-pull"]
