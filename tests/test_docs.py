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


class Loop(RailTest):
    def test_the_loop_ticket_and_state_pages_cover_what_an_agent_needs(self):
        p = self.fixture()
        loop = p.rail("docs", "loop")["text"]
        for text in ("rail next --json", "rail advance --json", "owner", "human_wait", "Exit codes"):
            self.assertIn(text, loop)
        tickets = p.rail("docs", "tickets")["text"]
        for text in ("rail add", "Check:", "ASSUMED", "rail amend", "rail/ids"):
            self.assertIn(text, tickets)
        states = p.rail("docs", "states")["text"]
        for state in ("new", "accepted", "implementing", "reviewing", "in-ci", "merge-ready", "merged", "dropped"):
            self.assertIn(f"| `{state}` |", states)


class Review(RailTest):
    def test_the_review_contract_and_retry_pages_cover_the_answers_an_agent_gives(self):
        p = self.fixture()
        review = p.rail("docs", "review")["text"]
        for text in ("rail answer NN F1 fixed", "declined", "parked", "refuter", "--owner", "security seat"):
            self.assertIn(text, review)
        self.assertIn("rail amend NN", p.rail("docs", "contract")["text"])
        retries = p.rail("docs", "retries")["text"]
        for text in ("[retry] budget", "rail consult NN", "rail accept NN", "NN-advice.md"):
            self.assertIn(text, retries)


class Operations(RailTest):
    def test_the_operations_pages_are_there(self):
        p = self.fixture()
        self.assertIn("rail doctor", p.rail("docs", "guards")["text"])
        packs = p.rail("docs", "packs")["text"]
        self.assertIn(".rail/packs/NAME/", packs)
        self.assertIn("never changes ticket state", packs)
        self.assertIn("## Decision", p.rail("docs", "adr")["text"])
        self.assertIn("People keep four acts", p.rail("docs", "environments")["text"])
        self.assertIn("/loop", p.rail("docs", "away")["text"])
        self.assertIn("rail intake github", p.rail("docs", "away")["text"])
        self.assertIn("required check", p.rail("docs", "github")["text"])
        self.assertIn("GITHUB_TOKEN", p.rail("docs", "github-runner")["text"])
        self.assertIn("Sweep:", p.rail("docs", "sweep")["text"])
