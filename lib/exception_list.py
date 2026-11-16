"""A repository's list of findings not fixed yet, one `<count> <key>` entry per line, that may only shrink.

`#` starts a comment. The key is the rest of the line: a path for the file-size check, or a rule id
and a path for the ast-grep check.
"""

import subprocess
from pathlib import Path


def parse_exception_list(text: str, source: str) -> dict[str, int]:
    """The `<count> <key>` entries of an exception list."""
    allowed: dict[str, int] = {}
    for number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        count, _, key = line.partition(" ")
        if not count.isdigit() or not key.strip():
            raise SystemExit(f"{source}:{number}: an entry is `<count> <key>`, not {raw_line!r}")
        allowed[" ".join(key.split())] = int(count)
    return allowed


def read_exception_list(path: str) -> dict[str, int]:
    """The exception list at `path`; empty when there is none."""
    file = Path(path)
    return parse_exception_list(file.read_text(), path) if file.exists() else {}


def write_exception_list(path: str, allowed: dict[str, int]) -> None:
    """Writes `allowed` to `path` sorted by key, or removes the file when nothing is left."""
    file = Path(path)
    if allowed:
        file.write_text("".join(f"{count} {key}\n" for key, count in sorted(allowed.items())))
    elif file.exists():
        file.unlink()


def exception_list_at(git_ref: str, path: str) -> dict[str, int]:
    """The exception list as `git_ref` has it; empty when it has none."""
    shown = subprocess.run(["git", "show", f"{git_ref}:{path}"], capture_output=True, text=True)
    return parse_exception_list(shown.stdout, f"{git_ref}:{path}") if shown.returncode == 0 else {}


def growth_failures(allowed: dict[str, int], git_ref: str, path: str) -> list[str]:
    """Each entry that is new since `git_ref`, or whose count rose."""
    before = exception_list_at(git_ref, path)
    failures = []
    for key, count in sorted(allowed.items()):
        if key not in before:
            failures.append(f"{path}: {key} is a new exception; the list only shrinks.")
        elif count > before[key]:
            failures.append(f"{path}: {key} rose from {before[key]} to {count}; the list only shrinks.")
    return failures
