import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from githist.cochange import cochange_pairs, cochange_partners
from githist.model import Commit, FileChange


def commit(sha, parents, files):
    return Commit(
        sha=sha,
        parents=tuple(parents),
        author_name="Ada",
        author_email="ada@example.com",
        author_date="2024-01-01T00:00:00+00:00",
        subject="subject",
        files=files,
    )


def touching(*paths):
    return [FileChange(path, 1, 0) for path in paths]


class CochangePairsTests(unittest.TestCase):
    def test_counts_pair_across_commits(self):
        commits = [
            commit("c1", [], touching("a.py", "b.py")),
            commit("c2", ["c1"], touching("a.py", "b.py")),
        ]
        result = cochange_pairs(commits, min_commits=1)
        self.assertEqual(len(result), 1)
        pair = result[0]
        self.assertEqual((pair.file_a, pair.file_b), ("a.py", "b.py"))
        self.assertEqual(pair.commits, 2)

    def test_pair_order_is_independent_of_file_order_in_commit(self):
        commits = [commit("c1", [], touching("z.py", "a.py"))]
        result = cochange_pairs(commits, min_commits=1)
        self.assertEqual((result[0].file_a, result[0].file_b), ("a.py", "z.py"))

    def test_three_file_commit_yields_three_pairs(self):
        commits = [commit("c1", [], touching("a.py", "b.py", "c.py"))]
        result = cochange_pairs(commits, min_commits=1)
        pairs = {(p.file_a, p.file_b) for p in result}
        self.assertEqual(pairs, {("a.py", "b.py"), ("a.py", "c.py"), ("b.py", "c.py")})

    def test_single_file_commit_yields_no_pairs(self):
        commits = [commit("c1", [], touching("a.py"))]
        self.assertEqual(cochange_pairs(commits, min_commits=1), [])

    def test_min_commits_filters_rare_pairs(self):
        commits = [commit("c1", [], touching("a.py", "b.py"))]
        self.assertEqual(cochange_pairs(commits), [])
        self.assertEqual(len(cochange_pairs(commits, min_commits=1)), 1)

    def test_max_files_per_commit_skips_huge_commits(self):
        huge = commit("c1", [], touching(*[f"f{i}.py" for i in range(5)]))
        result = cochange_pairs([huge], min_commits=1, max_files_per_commit=4)
        self.assertEqual(result, [])

    def test_merge_commits_excluded_by_default(self):
        commits = [commit("m1", ["p1", "p2"], touching("a.py", "b.py"))]
        self.assertEqual(cochange_pairs(commits, min_commits=1), [])
        result = cochange_pairs(commits, include_merges=True, min_commits=1)
        self.assertEqual(len(result), 1)

    def test_duplicate_path_in_one_commit_counted_once(self):
        commits = [commit("c1", [], touching("a.py", "b.py", "a.py"))]
        result = cochange_pairs(commits, min_commits=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].commits, 1)

    def test_no_commits_yields_empty_result(self):
        self.assertEqual(cochange_pairs([]), [])


class CochangePartnersTests(unittest.TestCase):
    def test_returns_only_pairs_involving_path_sorted_by_commits(self):
        commits = [
            commit("c1", [], touching("a.py", "b.py")),
            commit("c2", ["c1"], touching("a.py", "b.py")),
            commit("c3", ["c2"], touching("a.py", "c.py")),
            commit("c4", ["c3"], touching("b.py", "c.py")),
        ]
        pairs = cochange_pairs(commits, min_commits=1)
        result = cochange_partners(pairs, "a.py")
        self.assertEqual([(p.file_a, p.file_b, p.commits) for p in result], [
            ("a.py", "b.py", 2),
            ("a.py", "c.py", 1),
        ])

    def test_no_matches_yields_empty_list(self):
        commits = [commit("c1", [], touching("a.py", "b.py"))]
        pairs = cochange_pairs(commits, min_commits=1)
        self.assertEqual(cochange_partners(pairs, "z.py"), [])


if __name__ == "__main__":
    unittest.main()
