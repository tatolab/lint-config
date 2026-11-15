#!/usr/bin/env python3
"""Fails when a workspace's `[workspace.lints]` or `clippy.toml` is looser than lint-config's reference.

Every lint the reference sets must be set in the workspace at the same level or stricter
(allow < warn < deny < forbid). Every entry of a reference list in `clippy.toml` (a disallowed
macro, method or type, matched by its `path`) must be in the workspace's list. Anything else
the reference sets must be equal. The workspace may add lints and entries of its own.
"""

import argparse
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    raise SystemExit("check_lint_table.py needs Python 3.11 or newer for tomllib")

REFERENCE = Path(__file__).resolve().parent
LEVELS = ["allow", "warn", "deny", "forbid"]


def level_of(setting: object) -> str | None:
    """A lint's level, written as `"deny"` or as `{ level = "deny", … }`."""
    if isinstance(setting, str):
        return setting
    if isinstance(setting, dict) and isinstance(setting.get("level"), str):
        return setting["level"]
    return None


def lint_table_failures(reference: dict, workspace: dict) -> list[str]:
    """Each reference lint the workspace drops or sets looser."""
    failures = []
    for tool, lints in reference.get("workspace", {}).get("lints", {}).items():
        workspace_lints = workspace.get("workspace", {}).get("lints", {}).get(tool, {})
        for lint, setting in lints.items():
            wanted = level_of(setting)
            found = level_of(workspace_lints.get(lint.replace("-", "_"), workspace_lints.get(lint.replace("_", "-"))))
            if found is None:
                failures.append(f"[workspace.lints.{tool}] {lint} is missing; lint-config sets it to {wanted!r}.")
            elif found not in LEVELS or LEVELS.index(found) < LEVELS.index(wanted):
                failures.append(f"[workspace.lints.{tool}] {lint} is {found!r}, looser than lint-config's {wanted!r}.")
    return failures


def clippy_failures(reference: dict, workspace: dict) -> list[str]:
    """Each reference `clippy.toml` entry the workspace drops or changes."""
    failures = []
    for key, wanted in reference.items():
        found = workspace.get(key)
        if isinstance(wanted, list) and all(isinstance(entry, dict) and "path" in entry for entry in wanted):
            found_paths = {entry.get("path") if isinstance(entry, dict) else entry for entry in found or []}
            failures += [f"clippy.toml {key} lacks {entry['path']}." for entry in wanted if entry["path"] not in found_paths]
        elif found != wanted:
            failures.append(f"clippy.toml {key} is {found!r}; lint-config sets {wanted!r}.")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cargo-toml", default="Cargo.toml", help="the workspace's root Cargo.toml")
    parser.add_argument("--clippy-toml", default="clippy.toml", help="the workspace's clippy.toml")
    arguments = parser.parse_args()

    workspace_lints = tomllib.loads(Path(arguments.cargo_toml).read_text())
    clippy_path = Path(arguments.clippy_toml)
    workspace_clippy = tomllib.loads(clippy_path.read_text()) if clippy_path.exists() else {}
    failures = lint_table_failures(tomllib.loads((REFERENCE / "workspace-lints.toml").read_text()), workspace_lints)
    failures += clippy_failures(tomllib.loads((REFERENCE / "clippy.toml").read_text()), workspace_clippy)
    for failure in failures:
        print(failure, file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
