"""doc-lint (plan, section 13): ARCHITECTURE.md's ## Areas keeps matching the tree."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from railtest import RailTest, ticket


def failed_lint(answer):
    step = [s for s in answer["steps"] if s.get("result") == "fail"][0]
    return step["step"], answer["action"]["brief"]


class Areas(RailTest):
    def test_rows_must_match_files_and_cover_every_directory(self):
        p = self.fixture(files={"docs/guide.md": "# Guide\n"})
        p.add(ticket(scope=("src/**", "ARCHITECTURE.md")))
        p.rail("next")
        p.fix_calc("1")
        p.write("ARCHITECTURE.md", "# Architecture\n\n## Areas\n| Area | Paths | Holds |\n|---|---|---|\n"
                "| calc | src/** | the calculator |\n| web | web/** | pages |\n", base=p.worktree("1"))
        step, brief = failed_lint(p.rail("advance", "1", expect=3))
        self.assertEqual(step, "doc-lint")
        self.assertIn("'web': web/** matches no tracked file", brief)
        self.assertIn("api/ is in no ## Areas row", brief)
        self.assertIn("docs/ is in no ## Areas row", brief)
        self.assertNotIn(".rail/", brief)

    def test_a_long_file_fails_and_a_project_without_one_skips(self):
        p = self.fixture()
        p.add(ticket(scope=("src/**", "ARCHITECTURE.md")))
        p.rail("next")
        p.fix_calc("1")
        rows = "".join(f"| a{i} | src/** | x |\n" for i in range(160))
        p.write("ARCHITECTURE.md", "## Areas\n| Area | Paths | Holds |\n|---|---|---|\n" + rows +
                "| api | api/** | handlers |\n", base=p.worktree("1"))
        step, brief = failed_lint(p.rail("advance", "1", expect=3))
        self.assertIn("lines; keep it to 150 or fewer", brief)
        os.remove(os.path.join(p.worktree("1"), "ARCHITECTURE.md"))
        shipped = p.rail("advance", "1")
        self.assertEqual([s["status"] for s in shipped["steps"] if s["step"] == "doc-lint"], ["not_run"])

    def test_an_ignored_directory_may_end_in_a_slash(self):
        from railtest import CONFIG
        p = self.fixture(config=CONFIG + '\n[map]\nignore = ["docs/"]\n', files={"docs/guide.md": "# Guide\n"})
        p.add(ticket())
        p.rail("next")
        p.fix_calc("1")
        shipped = p.rail("advance", "1")
        self.assertEqual([s.get("result") for s in shipped["steps"] if s["step"] == "doc-lint"], ["pass"])

    def test_non_ascii_paths_are_read_as_they_are(self):
        from railtest import ARCHITECTURE
        p = self.fixture(files={"café/menu.md": "# Menu\n", "ARCHITECTURE.md": ARCHITECTURE + "| menu | café/** | the menu |\n"})
        p.add(ticket())
        p.rail("next")
        p.fix_calc("1")
        shipped = p.rail("advance", "1")
        self.assertEqual([s.get("result") for s in shipped["steps"] if s["step"] == "doc-lint"], ["pass"])
