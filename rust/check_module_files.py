#!/usr/bin/env python3
"""Fails when a Rust module is both `foo.rs` and a `foo/` directory: a module with children is `foo/mod.rs`."""

import argparse
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from tracked_files import glob_pattern, matches_any, tracked_files  # noqa: E402

CRATE_ROOTS = {"mod.rs", "lib.rs", "main.rs", "build.rs"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exclude", action="append", default=[], help="a glob of files never checked, added to vendor/")
    arguments = parser.parse_args()
    exclude = [glob_pattern(glob) for glob in ["**/vendor/**", *arguments.exclude]]

    rust_files = [path for path in tracked_files() if path.endswith(".rs") and not matches_any(path, exclude)]
    directories_with_rust = {str(PurePosixPath(path).parent) for path in rust_files}
    failures = [
        f"{path}: a module with children is `{path[:-3]}/mod.rs`, not `{path}` beside `{path[:-3]}/`."
        for path in sorted(rust_files)
        if PurePosixPath(path).name not in CRATE_ROOTS and path[:-3] in directories_with_rust
    ]
    for failure in failures:
        print(failure, file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
