import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from githist.parser import RECORD_SEP, UNIT_SEP, parse_log


def record(sha, parents, name, email, date, subject, numstat_lines=""):
    header = UNIT_SEP.join([sha, parents, name, email, date, subject])
    body = f"{header}\n{numstat_lines}" if numstat_lines else header
    return f"{RECORD_SEP}{body}"


# Each case is (name, raw log text, expected list of tuples describing the
# parsed commits). Expected tuples are kept shallow (sha, parent count,
# file summaries) so a failure points straight at what went wrong.
CASES = [
    (
        "single file, normal edit",
        record(
            "abc123", "", "Ada Lovelace", "ada@example.com",
            "2024-01-01T00:00:00+00:00", "initial commit",
            "10\t0\tREADME.md\n",
        ),
        [("abc123", 0, [("README.md", 10, 0, None)])],
    ),
    (
        "root commit has no parents",
        record(
            "root1", "", "Grace Hopper", "grace@example.com",
            "2024-01-01T00:00:00+00:00", "root",
            "3\t0\tmain.py\n",
        ),
        [("root1", 0, [("main.py", 3, 0, None)])],
    ),
    (
        "merge commit carries no numstat lines when log ran without a diff-merges flag",
        record(
            "merge1", "parentA parentB", "Grace Hopper", "grace@example.com",
            "2024-01-02T00:00:00+00:00", "Merge branch 'feature'",
        ),
        [("merge1", 2, [])],
    ),
    (
        "merge commit with --diff-merges=first-parent carries a normal file list",
        record(
            "merge2", "parentA parentB", "Grace Hopper", "grace@example.com",
            "2024-01-02T00:00:00+00:00", "Merge branch 'feature'",
            "4\t1\tsrc/app.py\n",
        ),
        [("merge2", 2, [("src/app.py", 4, 1, None)])],
    ),
    (
        "binary file shows dashes instead of counts",
        record(
            "bin1", "abc123", "Ada Lovelace", "ada@example.com",
            "2024-01-03T00:00:00+00:00", "add logo",
            "-\t-\tassets/logo.png\n",
        ),
        [("bin1", 1, [("assets/logo.png", None, None, None)])],
    ),
    (
        "whole-path rename",
        record(
            "ren1", "bin1", "Ada Lovelace", "ada@example.com",
            "2024-01-04T00:00:00+00:00", "rename module",
            "0\t0\told_name.py => new_name.py\n",
        ),
        [("ren1", 1, [("new_name.py", 0, 0, "old_name.py")])],
    ),
    (
        "partial rename with shared prefix and suffix",
        record(
            "ren2", "ren1", "Ada Lovelace", "ada@example.com",
            "2024-01-05T00:00:00+00:00", "reorganize package",
            "2\t1\tsrc/{old => new}/mod.py\n",
        ),
        [("ren2", 1, [("src/new/mod.py", 2, 1, "src/old/mod.py")])],
    ),
    (
        "multiple files in one commit, mixed types",
        record(
            "multi1", "ren2", "Grace Hopper", "grace@example.com",
            "2024-01-06T00:00:00+00:00", "big change",
            "5\t2\ta.py\n-\t-\tb.png\n1\t1\tc.py => d.py\n",
        ),
        [
            (
                "multi1",
                1,
                [
                    ("a.py", 5, 2, None),
                    ("b.png", None, None, None),
                    ("d.py", 1, 1, "c.py"),
                ],
            )
        ],
    ),
    (
        "subject containing arrow-like text is not mistaken for a rename",
        record(
            "sub1", "multi1", "Ada Lovelace", "ada@example.com",
            "2024-01-07T00:00:00+00:00", "docs: old => new naming convention",
            "1\t0\tdocs/naming.md\n",
        ),
        [("sub1", 1, [("docs/naming.md", 1, 0, None)])],
    ),
    (
        "empty log text yields no commits",
        "",
        [],
    ),
    (
        "two commits back to back",
        record("c1", "", "A", "a@example.com", "2024-01-01T00:00:00+00:00", "first", "1\t0\tx.py\n")
        + record("c2", "c1", "A", "a@example.com", "2024-01-02T00:00:00+00:00", "second", "2\t0\ty.py\n"),
        [
            ("c1", 0, [("x.py", 1, 0, None)]),
            ("c2", 1, [("y.py", 2, 0, None)]),
        ],
    ),
]


class ParseLogTests(unittest.TestCase):
    def test_cases(self):
        for name, raw_text, expected in CASES:
            with self.subTest(name=name):
                commits = parse_log(raw_text)
                actual = [
                    (
                        c.sha,
                        len(c.parents),
                        [(f.path, f.added, f.deleted, f.old_path) for f in c.files],
                    )
                    for c in commits
                ]
                self.assertEqual(actual, expected)

    def test_malformed_header_raises(self):
        broken = f"{RECORD_SEP}only{UNIT_SEP}three{UNIT_SEP}fields"
        with self.assertRaises(ValueError):
            parse_log(broken)

    def test_commit_is_merge_and_is_root_properties(self):
        text = record("m1", "p1 p2", "A", "a@example.com", "2024-01-01T00:00:00+00:00", "merge")
        commit = parse_log(text)[0]
        self.assertTrue(commit.is_merge)
        self.assertFalse(commit.is_root)

        text = record("r1", "", "A", "a@example.com", "2024-01-01T00:00:00+00:00", "root")
        commit = parse_log(text)[0]
        self.assertTrue(commit.is_root)
        self.assertFalse(commit.is_merge)

    def test_file_change_is_binary_and_is_rename(self):
        text = record(
            "f1", "", "A", "a@example.com", "2024-01-01T00:00:00+00:00", "subj",
            "-\t-\timg.png\n1\t1\told.py => new.py\n2\t0\tplain.py\n",
        )
        img, renamed, plain = parse_log(text)[0].files
        self.assertTrue(img.is_binary)
        self.assertFalse(img.is_rename)
        self.assertTrue(renamed.is_rename)
        self.assertFalse(renamed.is_binary)
        self.assertFalse(plain.is_binary)
        self.assertFalse(plain.is_rename)


if __name__ == "__main__":
    unittest.main()
