"""The files a repository tracks, and glob matching on their repository paths."""

import re
import subprocess


def tracked_files() -> list[str]:
    """The paths git tracks in the current repository, relative to its root."""
    listing = subprocess.run(["git", "ls-files", "-z"], check=True, capture_output=True, text=True).stdout
    return [path for path in listing.split("\0") if path]


def glob_pattern(glob: str) -> re.Pattern[str]:
    """A glob over repository paths: `**` crosses directories, `*` and `?` do not."""
    expression = ""
    index = 0
    while index < len(glob):
        if glob.startswith("**/", index):
            expression += "(?:.*/)?"
            index += 3
        elif glob.startswith("**", index):
            expression += ".*"
            index += 2
        elif glob[index] == "*":
            expression += "[^/]*"
            index += 1
        elif glob[index] == "?":
            expression += "[^/]"
            index += 1
        else:
            expression += re.escape(glob[index])
            index += 1
    return re.compile(expression + r"\Z")


def matches_any(path: str, globs: list[re.Pattern[str]]) -> bool:
    """Whether `path` matches one of `globs`."""
    return any(glob.match(path) for glob in globs)
