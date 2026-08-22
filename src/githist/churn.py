from dataclasses import dataclass, field
from typing import Dict, Iterable, Set

from .model import Commit


@dataclass
class FileChurn:
    """Accumulated churn for one path across a set of commits.

    added/deleted only count text-file changes; binary touches still bump
    commits so a file that's mostly image replacements isn't invisible.
    """

    path: str
    commits: int = 0
    added: int = 0
    deleted: int = 0
    authors: Set[str] = field(default_factory=set)

    @property
    def total_lines(self) -> int:
        return self.added + self.deleted


@dataclass
class AuthorChurn:
    """Accumulated churn for one author, keyed by email.

    author_name is whatever name was attached to the first commit seen for
    this email -- real normalization across name spellings is a job for
    mailmap handling, not this aggregation.
    """

    author_email: str
    author_name: str
    commits: int = 0
    added: int = 0
    deleted: int = 0
    files: Set[str] = field(default_factory=set)

    @property
    def total_lines(self) -> int:
        return self.added + self.deleted


def churn_by_file(commits: Iterable[Commit], *, include_merges: bool = False) -> Dict[str, FileChurn]:
    """Aggregate added/deleted lines and touch counts per file path.

    Renamed files are tracked under their path at the time of each commit,
    not a single canonical identity, so a file's total churn is split
    across old_path and path if it was ever renamed. Merge commits are
    skipped by default since the lines they touch were usually already
    counted in the commits merged in.
    """
    files: Dict[str, FileChurn] = {}
    for commit in commits:
        if commit.is_merge and not include_merges:
            continue
        for change in commit.files:
            entry = files.get(change.path)
            if entry is None:
                entry = FileChurn(path=change.path)
                files[change.path] = entry
            entry.commits += 1
            entry.authors.add(commit.author_email)
            if not change.is_binary:
                entry.added += change.added
                entry.deleted += change.deleted
    return files


def churn_by_author(commits: Iterable[Commit], *, include_merges: bool = False) -> Dict[str, AuthorChurn]:
    """Aggregate added/deleted lines, commit counts, and touched files per author.

    Keyed by author_email since two commits with the same display name but
    different emails aren't reliably the same person, while the reverse
    (same email, differing name capitalization/spelling) is common enough
    that mailmap-based normalization is left for later.
    """
    authors: Dict[str, AuthorChurn] = {}
    for commit in commits:
        if commit.is_merge and not include_merges:
            continue
        entry = authors.get(commit.author_email)
        if entry is None:
            entry = AuthorChurn(author_email=commit.author_email, author_name=commit.author_name)
            authors[commit.author_email] = entry
        entry.commits += 1
        for change in commit.files:
            entry.files.add(change.path)
            if not change.is_binary:
                entry.added += change.added
                entry.deleted += change.deleted
    return authors
