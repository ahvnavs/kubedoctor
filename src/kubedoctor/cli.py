"""Command-line entry point."""

import argparse
import sys

from . import __version__
from .cluster import ClusterError, collect, load_client
from .engine import DiagnosisEngine
from .render import render_json, render_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kubedoctor",
        description="Explain common Kubernetes pod failures and suggest exact fixes.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subcommands = parser.add_subparsers(dest="command")
    diagnose = subcommands.add_parser("diagnose", help="Inspect unhealthy pods")
    diagnose.add_argument("--namespace", "-n", default="default")
    diagnose.add_argument("--all-namespaces", "-A", action="store_true")
    diagnose.add_argument("--pod", help="Inspect one pod by name")
    diagnose.add_argument("--context", help="Kubeconfig context to use")
    diagnose.add_argument("--output", "-o", choices=("text", "json"), default="text")
    diagnose.add_argument("--prometheus-url", help="Add recent resource evidence from Prometheus")
    diagnose.add_argument("--explain", action="store_true", help="Add optional LLM explanations")
    diagnose.add_argument("--show-stages", action="store_true", help="Report each engine stage")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        api = load_client(args.context)
        snapshots = collect(api, args.namespace, args.all_namespaces, args.pod)
    except ClusterError as exc:
        print(f"kubedoctor: {exc}", file=sys.stderr)
        return 2
    report = DiagnosisEngine(args.prometheus_url, args.explain).run(snapshots)
    results = report.diagnoses
    if args.show_stages:
        for stage in report.stages:
            print(f"stage/{stage.name}: {stage.state} ({stage.detail})", file=sys.stderr)
    for warning in report.warnings:
        print(f"kubedoctor: optional enrichment skipped: {warning}", file=sys.stderr)
    print(render_json(results) if args.output == "json" else render_text(results))
    return 1 if results else 0


if __name__ == "__main__":
    raise SystemExit(main())

