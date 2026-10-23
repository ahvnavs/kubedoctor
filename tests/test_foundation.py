from kubedoctor import __version__
from kubedoctor.cli import build_parser, main
from kubedoctor.models import Diagnosis, Evidence, Severity
from kubedoctor.render import render_text


def test_version_is_exposed(capsys):
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    assert capsys.readouterr().out.strip() == f"kubedoctor {__version__}"


def test_diagnose_defaults_are_predictable():
    args = build_parser().parse_args(["diagnose"])
    assert args.namespace == "default"
    assert args.all_namespaces is False
    assert args.output == "text"


def test_text_renderer_keeps_evidence_and_exact_command():
    result = Diagnosis(
        code="image-pull",
        title="Image cannot be pulled",
        summary="The registry rejected the image reference.",
        severity=Severity.CRITICAL,
        resource="pod/api",
        fix_command="kubectl -n demo set image deployment/api api=repo/api:1.2.3",
        evidence=(Evidence("container/api", "ImagePullBackOff"),),
    )
    output = render_text([result])
    assert "ImagePullBackOff" in output
    assert result.fix_command in output


def test_empty_renderer_is_clear():
    assert render_text([]) == "No supported pod failures found."

