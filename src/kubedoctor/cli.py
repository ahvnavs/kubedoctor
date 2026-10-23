"""Command-line entry point."""

import argparse
import sys

from . import __version__
from .cluster import ClusterError, collect, load_client
from .diagnose import diagnose_all
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        api = load_client(args.context)
        results = diagnose_all(collect(api, args.namespace, args.all_namespaces, args.pod))
    except ClusterError as exc:
        print(f"kubedoctor: {exc}", file=sys.stderr)
        return 2
    print(render_json(results) if args.output == "json" else render_text(results))
    return 1 if results else 0


if __name__ == "__main__":
    raise SystemExit(main())

