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


def paths_renamed_since(git_ref: str) -> dict[str, str]:
    """Each tracked file git sees as renamed since `git_ref`, old path to new."""
    shown = subprocess.run(
        ["git", "diff", "--name-status", "-M", "-z", git_ref], capture_output=True, text=True
    )
    if shown.returncode != 0:
        return {}
    fields = shown.stdout.split("\0")
    renamed = {}
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index]
        if status.startswith(("R", "C")):
            if status.startswith("R"):
                renamed[fields[index + 1]] = fields[index + 2]
            index += 3
        else:
            index += 2
    return renamed


def key_after_renames(key: str, renamed: dict[str, str]) -> str:
    """`key` with its path, its last word, moved to where the file went."""
    *rule, file_path = key.split(" ")
    return " ".join([*rule, renamed.get(file_path, file_path)])


def growth_failures(allowed: dict[str, int], git_ref: str, path: str) -> list[str]:
    """Each entry that is new since `git_ref`, or whose count rose. An entry of a file renamed since
    `git_ref` is the same entry under the file's new path."""
    renamed = paths_renamed_since(git_ref)
    before = {}
    for key, count in exception_list_at(git_ref, path).items():
        moved = key_after_renames(key, renamed)
        before[moved] = max(count, before.get(moved, 0))
    failures = []
    for key, count in sorted(allowed.items()):
        if key not in before:
            failures.append(f"{path}: {key} is a new exception; the list only shrinks.")
        elif count > before[key]:
            failures.append(f"{path}: {key} rose from {before[key]} to {count}; the list only shrinks.")
    return failures
