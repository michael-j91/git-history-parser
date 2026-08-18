from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass(frozen=True)
class FileChange:
    """One file's numstat entry for a single commit.

    added/deleted are None for binary files, where git reports "-" instead
    of a line count. old_path is set only for renames.
    """

    path: str
    added: Optional[int]
    deleted: Optional[int]
    old_path: Optional[str] = None

    @property
    def is_binary(self) -> bool:
        return self.added is None and self.deleted is None

    @property
    def is_rename(self) -> bool:
        return self.old_path is not None


@dataclass(frozen=True)
class Commit:
    sha: str
    parents: Tuple[str, ...]
    author_name: str
    author_email: str
    author_date: str  # ISO 8601 string, as produced by `git log --date=iso-strict`
    subject: str
    files: list = field(default_factory=list)

    @property
    def is_merge(self) -> bool:
        return len(self.parents) > 1

    @property
    def is_root(self) -> bool:
        return len(self.parents) == 0
