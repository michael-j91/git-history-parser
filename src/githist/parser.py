from typing import List, Optional, Tuple

from .model import Commit, FileChange

# ASCII record/unit separators. Neither shows up in commit metadata in
# practice, so splitting on them is far more reliable than guessing at
# delimiters git might also use inside a subject line (":", "|", "-").
RECORD_SEP = "\x1e"
UNIT_SEP = "\x1f"

PRETTY_FORMAT = (
    f"{RECORD_SEP}%H{UNIT_SEP}%P{UNIT_SEP}%an{UNIT_SEP}%ae{UNIT_SEP}%aI{UNIT_SEP}%s"
)

_HEADER_FIELD_COUNT = 6

# git quotes a path in C style (wrapping it in double quotes and escaping
# special bytes) whenever it contains a tab, newline, backslash, double
# quote, or -- with the default core.quotepath -- any non-ASCII byte. The
# named escapes below cover the control characters git ever emits this way;
# everything else that needs escaping comes out as a \NNN octal byte.
_C_STYLE_ESCAPES = {
    "\\": b"\\",
    '"': b'"',
    "a": b"\a",
    "b": b"\b",
    "f": b"\f",
    "n": b"\n",
    "r": b"\r",
    "t": b"\t",
    "v": b"\v",
}


def parse_log(text: str) -> List[Commit]:
    """Parse output produced by `git log` run with PRETTY_FORMAT and --numstat.

    Merge commits are parsed the same way as regular commits: a header
    followed by zero or more numstat lines. Whether a merge actually has
    file lines depends on how the log text was produced -- run_git_log()
    passes --diff-merges=first-parent so merges carry a normal diff, but
    text from a plain `git log --numstat` will still parse fine with
    Commit.files simply empty for merges.
    """
    commits = []
    for block in text.split(RECORD_SEP):
        if not block.strip():
            continue
        header, _, rest = block.partition("\n")
        commits.append(_parse_commit(header, rest))
    return commits


def _parse_commit(header: str, numstat_block: str) -> Commit:
    fields = header.split(UNIT_SEP)
    if len(fields) != _HEADER_FIELD_COUNT:
        raise ValueError(f"malformed commit header (expected {_HEADER_FIELD_COUNT} fields): {header!r}")

    sha, parents_raw, author_name, author_email, author_date, subject = fields
    parents = tuple(parents_raw.split())

    files = []
    for line in numstat_block.splitlines():
        line = line.strip("\r")
        if not line.strip():
            continue
        files.append(_parse_numstat_line(line))

    return Commit(
        sha=sha,
        parents=parents,
        author_name=author_name,
        author_email=author_email,
        author_date=author_date,
        subject=subject,
        files=files,
    )


def _parse_numstat_line(line: str) -> FileChange:
    added_str, deleted_str, path_field = line.split("\t", 2)
    added = None if added_str == "-" else int(added_str)
    deleted = None if deleted_str == "-" else int(deleted_str)
    old_path, path = _split_rename(_unquote_c_style(path_field))
    return FileChange(path=path, added=added, deleted=deleted, old_path=old_path)


def _unquote_c_style(field: str) -> str:
    """Undo git's C-style quoting of a numstat path field.

    git wraps the whole field in double quotes (and only then) when some
    part of it needs escaping, so an unquoted field is passed through
    untouched. Non-ASCII bytes come out as \\NNN octal escapes one byte at
    a time, so escapes are collected into a byte buffer alongside the
    literal bytes around them and decoded as UTF-8 only at the end.
    """
    if len(field) < 2 or field[0] != '"' or field[-1] != '"':
        return field

    inner = field[1:-1]
    raw = bytearray()
    i = 0
    length = len(inner)
    while i < length:
        char = inner[i]
        if char == "\\" and i + 1 < length:
            escape = inner[i + 1]
            if escape in _C_STYLE_ESCAPES:
                raw.extend(_C_STYLE_ESCAPES[escape])
                i += 2
                continue
            if escape.isdigit():
                octal_digits = inner[i + 1 : i + 4]
                raw.append(int(octal_digits, 8))
                i += 4
                continue
        raw.extend(char.encode("utf-8"))
        i += 1
    return raw.decode("utf-8")


def _split_rename(field: str) -> Tuple[Optional[str], str]:
    """Split a numstat path field into (old_path, new_path).

    Plain path: ("path", ...) -> (None, path)
    Whole-path rename: "old.py => new.py" -> ("old.py", "new.py")
    Partial rename with shared prefix/suffix: "dir/{old => new}.py"
      -> ("dir/old.py", "dir/new.py")
    """
    if "=>" not in field:
        return None, field

    if "{" in field and "}" in field:
        prefix, _, tail = field.partition("{")
        middle, _, suffix = tail.partition("}")
        old_middle, _, new_middle = middle.partition(" => ")
        return f"{prefix}{old_middle}{suffix}", f"{prefix}{new_middle}{suffix}"

    old_path, _, new_path = field.partition(" => ")
    return old_path.strip(), new_path.strip()
