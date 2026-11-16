#!/usr/bin/env python3
"""Runs `ast-grep scan` and fails on each finding that is not a listed exception.

The exception list holds one `<count> <rule-id> <path>` entry per rule and file not fixed yet;
`#` starts a comment. A listed file may not gain findings of that rule, an entry whose file has
none left must go, and with `--compare-to <git-ref>` the list may only shrink: no new entry, no
raised count. `--tighten` rewrites each count down to the findings now. `--path` names what to
scan (the repository by default); ast-grep skips hidden directories it walks into, so a rule for
`.github/` needs `--path . --path .github`.
"""

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from exception_list import growth_failures, read_exception_list, write_exception_list  # noqa: E402


def findings_by_rule_and_path(config: str, paths: list[str]) -> tuple[Counter[str], dict[str, list[str]]]:
    """The error findings of `ast-grep scan`, counted by `<rule-id> <path>`, and each one's location."""
    scan = subprocess.run(["ast-grep", "scan", "--config", config, "--json=compact", *paths], capture_output=True, text=True)
    if scan.returncode not in (0, 1) or not scan.stdout.strip().startswith("["):
        raise SystemExit(f"ast-grep scan failed ({scan.returncode}):\n{scan.stderr}")
    counts: Counter[str] = Counter()
    locations: dict[str, list[str]] = {}
    for finding in json.loads(scan.stdout):
        if finding.get("severity", "error") != "error":
            continue
        key = f"{finding['ruleId']} {finding['file']}"
        counts[key] += 1
        locations.setdefault(key, []).append(f"{finding['file']}:{finding['range']['start']['line'] + 1}: {finding['message']}")
    return counts, locations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--exceptions", required=True, help="the exception list, relative to the repository root")
    parser.add_argument("--config", default="sgconfig.yml", help="the ast-grep project configuration")
    parser.add_argument("--compare-to", help="a git ref whose exception list this one may only shrink from")
    parser.add_argument("--path", action="append", help="a path to scan, repeatable; the repository by default")
    parser.add_argument("--tighten", action="store_true", help="rewrite each count down to the findings now")
    arguments = parser.parse_args()

    allowed = read_exception_list(arguments.exceptions)
    counts, locations = findings_by_rule_and_path(arguments.config, arguments.path or ["."])

    if arguments.tighten:
        allowed = {key: min(count, counts[key]) for key, count in allowed.items() if counts[key] > 0}
        write_exception_list(arguments.exceptions, allowed)

    failures: list[str] = []
    for key, count in sorted(counts.items()):
        if key not in allowed:
            failures += locations[key]
        elif count > allowed[key]:
            failures.append(f"{key}: {count} findings, more than its exception of {allowed[key]}.")
            failures += locations[key]
    for key in sorted(allowed):
        if counts[key] == 0:
            failures.append(f"{arguments.exceptions}: {key} has no findings left; remove the entry.")
    if arguments.compare_to:
        failures += growth_failures(allowed, arguments.compare_to, arguments.exceptions)

    for failure in failures:
        print(failure, file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
