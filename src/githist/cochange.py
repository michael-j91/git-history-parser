from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, List

from .model import Commit

# A commit that touches more files than this is almost always a vendoring
# drop, a mass reformat, or a merge that slipped past the include_merges
# filter -- not a set of files anyone actually edited together. Counting
# every pair from such a commit is also O(n^2) in its file count, so one
# large enough commit could dwarf every real signal in the result.
DEFAULT_MAX_FILES_PER_COMMIT = 100


@dataclass
class CochangePair:
    """How often two files were touched by the same commit.

    file_a and file_b are ordered by sorted path, not by which one changed
    first, so the same pair never appears twice under swapped names.
    """

    file_a: str
    file_b: str
    commits: int


def cochange_pairs(
    commits: Iterable[Commit],
    *,
    include_merges: bool = False,
    min_commits: int = 2,
    max_files_per_commit: int = DEFAULT_MAX_FILES_PER_COMMIT,
) -> List[CochangePair]:
    """Count how often pairs of files were changed in the same commit.

    Renamed files are counted under whatever path they had in that commit
    (their new path), the same choice churn_by_file makes, so a rename
    doesn't by itself register as a co-change with its own old identity.
    Results with fewer than min_commits shared commits are dropped, since
    two files sharing a single commit is usually coincidence rather than a
    real coupling worth surfacing.
    """
    counts: "Counter[tuple]" = Counter()
    for commit in commits:
        if commit.is_merge and not include_merges:
            continue
        paths = sorted({change.path for change in commit.files})
        if len(paths) < 2 or len(paths) > max_files_per_commit:
            continue
        for file_a, file_b in combinations(paths, 2):
            counts[(file_a, file_b)] += 1

    return [
        CochangePair(file_a=file_a, file_b=file_b, commits=count)
        for (file_a, file_b), count in counts.items()
        if count >= min_commits
    ]


def cochange_partners(pairs: Iterable[CochangePair], path: str) -> List[CochangePair]:
    """Return the pairs involving path, most-frequent first.

    Meant for looking up "what tends to change alongside this file" once
    you already have the full result of cochange_pairs -- computing pairs
    is the expensive part, so this just filters and sorts what's there.
    """
    matches = [pair for pair in pairs if path in (pair.file_a, pair.file_b)]
    matches.sort(key=lambda pair: pair.commits, reverse=True)
    return matches
