# githist

`git log` is the only reliable source for a repository's history, but its
text output is awkward to parse correctly. Commit subjects can contain
almost anything, renamed files show up as `old => new` or the more
confusing `dir/{old => new}/file.py`, binary files report `-` instead of
line counts, and merge commits silently drop their file list unless you
ask for it a different way. Every script I've written that scraped `git
log` by splitting on spaces or guessing at column widths has broken on one
of these eventually.

This library parses `git log` output into plain dataclasses (`Commit`,
`FileChange`) using a format string built around ASCII record/unit
separator characters, so commit metadata can't collide with the
delimiters used to split it apart.

## Usage

```python
from githist import run_git_log, parse_log

raw = run_git_log("/path/to/repo", since="6 months ago")
commits = parse_log(raw)

for commit in commits:
    if commit.is_merge:
        continue
    for change in commit.files:
        if change.is_binary:
            continue
        print(commit.sha[:8], change.path, f"+{change.added} -{change.deleted}")
```

If you already have `git log` output from somewhere else (a saved log, a
CI artifact), run `git log` yourself with the same format `run_git_log`
uses and feed the text straight to `parse_log`:

```python
from githist import parse_log
from githist.collect import LOG_ARGS

# LOG_ARGS is the exact argument list run_git_log() uses, in case you want
# to build the git invocation yourself (different cwd, extra flags, etc).
commits = parse_log(saved_log_text)
```

## What `Commit` and `FileChange` look like

```python
Commit(
    sha="a1b2c3d",
    parents=("f0e0d0c",),
    author_name="Ada Lovelace",
    author_email="ada@example.com",
    author_date="2024-01-05T09:12:00+00:00",
    subject="rename module",
    files=[
        FileChange(path="new_name.py", added=0, deleted=0, old_path="old_name.py"),
    ],
)
```

`FileChange.is_binary` is true when git reported `-`/`-` instead of line
counts. `FileChange.is_rename` is true when `old_path` is set.

## Known limitations

- Merge commits carry no file list from a plain `git log --numstat` run;
  `commit.files` will be empty for them. Diffing merge commits properly
  needs `-m` or `--first-parent`, which isn't wired up yet.
- Paths containing a literal tab character aren't unescaped from git's
  C-style quoting. Rare in practice, but not handled.

## Running the tests

The test suite uses only `unittest` from the standard library:

```
python -m unittest discover -s tests
```
