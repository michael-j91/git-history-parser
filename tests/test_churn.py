import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from githist.churn import churn_by_author, churn_by_file
from githist.model import Commit, FileChange


def commit(sha, parents, author_name, author_email, files):
    return Commit(
        sha=sha,
        parents=tuple(parents),
        author_name=author_name,
        author_email=author_email,
        author_date="2024-01-01T00:00:00+00:00",
        subject="subject",
        files=files,
    )


class ChurnByFileTests(unittest.TestCase):
    def test_accumulates_across_commits(self):
        commits = [
            commit("c1", [], "Ada", "ada@example.com", [FileChange("a.py", 10, 2)]),
            commit("c2", ["c1"], "Grace", "grace@example.com", [FileChange("a.py", 3, 1)]),
        ]
        result = churn_by_file(commits)
        self.assertEqual(result["a.py"].commits, 2)
        self.assertEqual(result["a.py"].added, 13)
        self.assertEqual(result["a.py"].deleted, 3)
        self.assertEqual(result["a.py"].authors, {"ada@example.com", "grace@example.com"})

    def test_binary_files_count_touch_but_not_lines(self):
        commits = [commit("c1", [], "Ada", "ada@example.com", [FileChange("logo.png", None, None)])]
        result = churn_by_file(commits)
        self.assertEqual(result["logo.png"].commits, 1)
        self.assertEqual(result["logo.png"].added, 0)
        self.assertEqual(result["logo.png"].deleted, 0)

    def test_rename_splits_churn_across_old_and_new_path(self):
        commits = [
            commit("c1", [], "Ada", "ada@example.com", [FileChange("old.py", 5, 0)]),
            commit("c2", ["c1"], "Ada", "ada@example.com", [FileChange("new.py", 1, 1, old_path="old.py")]),
        ]
        result = churn_by_file(commits)
        self.assertEqual(set(result), {"old.py", "new.py"})
        self.assertEqual(result["old.py"].added, 5)
        self.assertEqual(result["new.py"].added, 1)

    def test_merge_commits_excluded_by_default(self):
        commits = [
            commit("m1", ["p1", "p2"], "Ada", "ada@example.com", [FileChange("a.py", 4, 1)]),
        ]
        self.assertEqual(churn_by_file(commits), {})
        result = churn_by_file(commits, include_merges=True)
        self.assertEqual(result["a.py"].commits, 1)

    def test_no_commits_yields_empty_result(self):
        self.assertEqual(churn_by_file([]), {})


class ChurnByAuthorTests(unittest.TestCase):
    def test_accumulates_across_commits_and_files(self):
        commits = [
            commit("c1", [], "Ada Lovelace", "ada@example.com", [FileChange("a.py", 10, 2)]),
            commit(
                "c2",
                ["c1"],
                "Ada Lovelace",
                "ada@example.com",
                [FileChange("a.py", 1, 0), FileChange("b.py", 2, 0)],
            ),
        ]
        result = churn_by_author(commits)
        entry = result["ada@example.com"]
        self.assertEqual(entry.author_name, "Ada Lovelace")
        self.assertEqual(entry.commits, 2)
        self.assertEqual(entry.added, 13)
        self.assertEqual(entry.deleted, 2)
        self.assertEqual(entry.files, {"a.py", "b.py"})

    def test_same_email_keeps_first_seen_name(self):
        commits = [
            commit("c1", [], "ada", "ada@example.com", [FileChange("a.py", 1, 0)]),
            commit("c2", ["c1"], "Ada Lovelace", "ada@example.com", [FileChange("a.py", 1, 0)]),
        ]
        result = churn_by_author(commits)
        self.assertEqual(result["ada@example.com"].author_name, "ada")

    def test_merge_commits_excluded_by_default(self):
        commits = [
            commit("m1", ["p1", "p2"], "Ada", "ada@example.com", [FileChange("a.py", 4, 1)]),
        ]
        self.assertEqual(churn_by_author(commits), {})
        result = churn_by_author(commits, include_merges=True)
        self.assertEqual(result["ada@example.com"].commits, 1)

    def test_commit_with_no_files_still_counted(self):
        commits = [commit("c1", [], "Ada", "ada@example.com", [])]
        result = churn_by_author(commits)
        self.assertEqual(result["ada@example.com"].commits, 1)
        self.assertEqual(result["ada@example.com"].files, set())


if __name__ == "__main__":
    unittest.main()
