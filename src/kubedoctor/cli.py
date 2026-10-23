"""Command-line entry point."""

import argparse

from . import __version__


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
    diagnose.add_argument("--output", "-o", choices=("text", "json"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    parser.error("Live cluster diagnosis is added in phase 2.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

