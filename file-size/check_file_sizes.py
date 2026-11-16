#!/usr/bin/env python3
"""Fails when a hand-written file is over the line limit and is not a listed exception.

The exception list holds one `<lines> <path>` entry per file not split yet; `#` starts a comment.
A listed file may not grow past its count, an entry whose file is back under the limit must go,
and with `--compare-to <git-ref>` the list may only shrink: no new entry, no raised count.
`--tighten` rewrites each count down to the file's length now.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from exception_list import growth_failures, read_exception_list, write_exception_list  # noqa: E402
from tracked_files import glob_pattern, matches_any, tracked_files  # noqa: E402

DEFAULT_INCLUDE = ["**/*.rs", "**/*.py", "**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx", "**/*.mjs", "**/*.cjs", "**/*.astro", "**/*.swift", "**/*.m", "**/*.mm", "**/*.c", "**/*.h", "**/*.cpp", "**/*.sh"]
DEFAULT_EXCLUDE = ["**/vendor/**", "**/node_modules/**"]
GENERATED_MARKERS = ("@generated", "do not edit")


def line_count(path: str) -> int:
    """The lines in `path`, blank lines and comments counted."""
    text = Path(path).read_bytes()
    return text.count(b"\n") + (0 if text.endswith(b"\n") or not text else 1)


def is_generated(path: str) -> bool:
    """Whether the file says in its first lines, in any case, that a tool wrote it."""
    with open(path, encoding="utf-8", errors="replace") as file:
        head = "".join(file.readline() for _ in range(5))
    return any(marker in head.lower() for marker in GENERATED_MARKERS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--exceptions", required=True, help="the exception list, relative to the repository root")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--include", action="append", help="a glob of files checked (default: common source extensions)")
    parser.add_argument("--exclude", action="append", default=[], help="a glob of files never checked, added to vendor/ and node_modules/")
    parser.add_argument("--compare-to", help="a git ref whose exception list this one may only shrink from")
    parser.add_argument("--tighten", action="store_true", help="rewrite each count down to the file's length now")
    arguments = parser.parse_args()

    include = [glob_pattern(glob) for glob in arguments.include or DEFAULT_INCLUDE]
    exclude = [glob_pattern(glob) for glob in DEFAULT_EXCLUDE + arguments.exclude]
    allowed = read_exception_list(arguments.exceptions)

    lengths = {
        path: line_count(path)
        for path in tracked_files()
        if matches_any(path, include) and not matches_any(path, exclude) and Path(path).is_file() and not is_generated(path)
    }

    if arguments.tighten:
        tightened = {path: min(count, lengths[path]) for path, count in allowed.items() if lengths.get(path, 0) > arguments.limit}
        write_exception_list(arguments.exceptions, tightened)
        allowed = tightened

    failures: list[str] = []
    for path, length in sorted(lengths.items()):
        if length > arguments.limit and path not in allowed:
            failures.append(f"{path}: {length} lines, over {arguments.limit}. Split it; a new exception is not an option.")
        elif path in allowed and length > allowed[path]:
            failures.append(f"{path}: {length} lines, grown past its exception of {allowed[path]}.")
    for path, count in sorted(allowed.items()):
        if path not in lengths:
            failures.append(f"{arguments.exceptions}: {path} is listed but is not a checked file; remove the entry.")
        elif lengths[path] <= arguments.limit:
            failures.append(f"{arguments.exceptions}: {path} is {lengths[path]} lines now, within the limit; remove the entry.")
    if arguments.compare_to:
        failures += growth_failures(allowed, arguments.compare_to, arguments.exceptions)

    for failure in failures:
        print(failure, file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
