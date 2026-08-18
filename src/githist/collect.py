import subprocess
from pathlib import Path
from typing import Iterable, Optional, Union

from .parser import PRETTY_FORMAT

# --numstat is what makes per-file add/delete counts show up in the output;
# without -m, merge commits carry no numstat lines at all (see parser.py).
LOG_ARGS = ["log", "--numstat", "--no-color", f"--pretty=format:{PRETTY_FORMAT}"]


def run_git_log(
    repo_path: Union[str, Path],
    *,
    since: Optional[str] = None,
    until: Optional[str] = None,
    paths: Optional[Iterable[str]] = None,
) -> str:
    """Run `git log` in repo_path with the format parse_log() expects.

    Returns raw stdout as text. Raises subprocess.CalledProcessError if git
    exits non-zero (e.g. repo_path isn't a git repository).
    """
    args = ["git", "-C", str(repo_path), *LOG_ARGS]
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")
    if paths:
        args.append("--")
        args.extend(paths)

    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout
