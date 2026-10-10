#!/usr/bin/env python3
"""The two steps of the canfail action that read JSON.

filter DECLARATION OUT [--skip FIELD]
    Write DECLARATION to OUT without the checks whose FIELD is true. With no
    FIELD, OUT is DECLARATION unchanged. Exits 2 when the declaration cannot be
    read or nothing is left to run.

compare DECLARATION REPORT
    Hold a canfail --json report to the verdicts the declaration expects, and
    print a Markdown table of them. canfail's exit code cannot say what it
    found (blind and wrong-failure both exit 1, catches and look both exit 0),
    so this reads the per-break verdicts instead, and expects `catches` of
    every declared break unless the break carries an `expectedVerdict`.

    Exits 0 when every declared break was scored exactly once with the verdict
    it expects; 1 when any break was scored differently, not scored at all, or
    scored without being declared; 2 when an input cannot be read.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VERDICTS = ("catches", "blind", "wrong-failure", "look")

Key = tuple[str, str]


class InputError(Exception):
    """An input that cannot be read as a declaration or a report."""


def label(key: Key) -> str:
    return f"{key[0]} / {str(key[1]).rstrip('.')}"


def cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _load(path: Path, what: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"{path} cannot be read as {what}: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError(f"{path} is not {what}")
    return data


def filtered(declaration: dict, skip: str) -> dict:
    checks = declaration.get("checks")
    if not isinstance(checks, list):
        raise InputError("the declaration has no checks list")
    if skip:
        declaration = {**declaration, "checks": [c for c in checks if c.get(skip) is not True]}
    if not declaration["checks"]:
        raise InputError(f"no check is left to run after skipping those with {skip} set")
    return declaration


def declared(declaration: dict) -> dict[Key, str]:
    """Each break's expected verdict."""
    expected: dict[Key, str] = {}
    for check in declaration.get("checks") or []:
        for brk in check.get("breaks") or []:
            if not check.get("name") or not brk.get("name"):
                raise InputError("every check and break needs a name to be matched to its verdict")
            key = (check["name"], brk["name"])
            if key in expected:
                raise InputError(f"{label(key)}: declared twice")
            verdict = brk.get("expectedVerdict", "catches")
            if verdict not in VERDICTS:
                raise InputError(f"{label(key)}: expects {verdict!r}, which canfail never reports")
            expected[key] = verdict
    if not expected:
        raise InputError("the declaration declares no breaks")
    return expected


def scored(report: dict) -> tuple[dict[Key, tuple[str, str]], list[str]]:
    """Each scored break's verdict and detail, plus any break scored twice."""
    outcomes = report.get("outcomes")
    if not isinstance(outcomes, list):
        raise InputError("the report has no outcomes list")
    verdicts: dict[Key, tuple[str, str]] = {}
    twice: list[str] = []
    for outcome in outcomes:
        key = (outcome.get("check"), outcome.get("break_name"))
        if key in verdicts:
            twice.append(f"{label(key)}: scored twice")
        verdicts[key] = (outcome.get("verdict"), outcome.get("detail") or "")
    return verdicts, twice


def compare(expected: dict[Key, str], verdicts: dict[Key, tuple[str, str]]) -> list[str]:
    problems = []
    for key, want in expected.items():
        if key not in verdicts:
            problems.append(f"{label(key)}: declared but never scored")
        elif verdicts[key][0] != want:
            got, detail = verdicts[key]
            problems.append(f"{label(key)}: expected {want}, got {got} ({detail})")
    for key in verdicts.keys() - expected.keys():
        problems.append(f"{label(key)}: scored but not declared")
    return problems


def run_filter(args: argparse.Namespace) -> int:
    try:
        declaration = filtered(_load(args.declaration, "a canfail declaration"), args.skip)
    except InputError as exc:
        print(f"canfail-action: {exc}", file=sys.stderr)
        return 2
    args.out.write_text(json.dumps(declaration, indent=2) + "\n", encoding="utf-8")
    return 0


def run_compare(args: argparse.Namespace) -> int:
    try:
        expected = declared(_load(args.declaration, "a canfail declaration"))
        verdicts, problems = scored(_load(args.report, "a canfail --json report"))
    except InputError as exc:
        print(f"canfail-action: {exc}")
        return 2

    problems += compare(expected, verdicts)

    print("## canfail")
    print()
    print("| Check | Planted defect | Expected | Verdict |")
    print("|---|---|---|---|")
    for key, want in expected.items():
        got = verdicts.get(key, ("not scored", ""))[0]
        print(f"| {cell(key[0])} | {cell(key[1])} | {want} | {got} |")
    print()
    if problems:
        print(f"**{len(problems)} verdict(s) differ from the declaration:**")
        print()
        for problem in problems:
            print(f"- {cell(problem)}")
        return 1
    print(f"All {len(expected)} verdicts as declared.")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    f = sub.add_parser("filter")
    f.add_argument("declaration", type=Path)
    f.add_argument("out", type=Path)
    f.add_argument("--skip", default="")
    f.set_defaults(func=run_filter)

    c = sub.add_parser("compare")
    c.add_argument("declaration", type=Path)
    c.add_argument("report", type=Path)
    c.set_defaults(func=run_compare)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
