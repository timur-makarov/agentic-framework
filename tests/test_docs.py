"""rail docs (plan, section 13): the framework's docs, read from the engine."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from railtest import RailTest


class Reference(RailTest):
    def test_the_config_reference_names_every_field_and_its_reader(self):
        p = self.fixture()
        sys.path.insert(0, p.path(".rail", "engine"))
        from rail import config, docs
        names = [name for name, _ in docs._fields(config.DEFAULTS)]
        self.assertEqual(sorted(set(names) - set(docs.READERS)), [])
        page = p.rail("docs", "config")["text"]
        for name in names:
            self.assertIn(f"`{name}`", page)
        self.assertIn("| `retry.budget` | `2` | next and advance", page)
        self.assertIn("## Default `review.command`\n\n```text\nclaude -p --safe-mode", page)
        self.assertNotIn("seed/", page)

    def test_the_cli_reference_lists_every_verb(self):
        p = self.fixture()
        page = p.rail("docs", "cli")["text"]
        for verb in ("init", "add", "accept", "amend", "answer", "next", "advance", "status", "context", "drop",
                     "doctor", "ci", "consult", "docs"):
            self.assertIn(f"## rail {verb}", page)
        self.assertNotIn("## rail hook", page)

    def test_the_index_lists_topics_and_an_unknown_topic_is_a_usage_error(self):
        p = self.fixture()
        index = p.rail("docs")["text"]
        self.assertIn("- rules: Structure rules", index)
        self.assertIn("- config: Config reference", index)
        self.assertIn("Structure rules", p.rail("docs", "rules", raw=True).stdout)
        failed = p.rail("docs", "nothing", expect=2)
        self.assertIn("topics: ", failed["reason"]["message"])
