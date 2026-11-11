"""The forge (plan, sections 7, 10 and 11): pull requests, CI, labels and the merge, on a fake GitHub (fake_gh.py)."""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from railtest import RailTest, ticket


def bare_log(github, branch="main"):
    bare = github.read()["bare"]
    return subprocess.run(["git", "--git-dir", bare, "log", "-1", "--format=%s%n%b", branch], capture_output=True,
                          text=True).stdout


class Lifecycle(RailTest):
    def test_a_low_ticket_runs_through_its_pull_request_to_a_merge(self):
        a, b, github = self.github_pair()
        a.add(ticket())
        claimed = a.rail("next")
        self.assertEqual(claimed["steps"][-1], {"step": "pr", "status": "ran", "result": "pass", "detail": "opened #1"})
        self.assertEqual(github.pr(1)["title"], "1: Fix add")
        self.assertIn("Not shipped yet", github.pr(1)["body"])

        a.fix_calc("1")
        shipped = a.rail("advance", "1")
        self.assertEqual((shipped["state"], shipped["reason"]["code"]), ("in-ci", "CI_WAIT"))
        self.assertEqual(github.pr(1)["title"], "1: fix add")
        self.assertIn("Ticket: 1\nTier: LOW", github.pr(1)["body"])

        github.ci("1-fix-add", "success")
        ready = a.rail("next")
        self.assertEqual((ready["state"], ready["reason"]["code"]), ("merge-ready", "MERGE"))
        merged = a.rail("advance", "1")
        self.assertEqual(merged["state"], "merged")
        self.assertTrue(github.pr(1)["merged"])
        log = bare_log(github)
        self.assertTrue(log.startswith("1: fix add (#1)\n"), log)
        self.assertIn("Ticket: 1", log)
        self.assertEqual(b.rail("status")["tickets"][0]["state"], "merged")

    def test_a_red_required_check_returns_the_ticket_with_its_output(self):
        a, b, github = self.github_pair()
        a.add(ticket())
        a.rail("next")
        a.fix_calc("1")
        a.rail("advance", "1")
        github.ci("1-fix-add", "failure", summary="tests/test_calc.py::test_negative FAILED")
        red = a.rail("next")
        self.assertEqual((red["state"], red["reason"]["code"]), ("implementing", "RED_CHECK"))
        self.assertIn("test_negative FAILED", red["action"]["brief"])
        a.write("src/calc.py", "def add(a, b):\n    return b + a\n", base=a.worktree("1"))
        self.assertEqual(a.rail("advance", "1")["state"], "in-ci")


class Approvals(RailTest):
    def test_a_backlog_merges_low_and_medium_while_high_waits_on_its_pull_request(self):
        """Phase 5's done-when: one session runs a LOW, a MEDIUM and a HIGH ticket."""
        a, b, github = self.github_pair()
        a.add(ticket(title="Fix add"))
        a.add(ticket(title="Add a status code", tier="MEDIUM", scope=("api/**",), check="grep -q 201 api/handlers.py"))
        a.add(ticket(title="Change the config", tier="HIGH", scope=("src/config/**",), check="test -f src/config/app.toml"))
        contract = github.pr(1)
        self.assertEqual(contract["title"], "3: [contract] Change the config")

        first = a.rail("next")
        self.assertEqual(first["ticket"], "1")
        a.fix_calc("1")
        a.rail("advance", "1")
        github.ci("1-fix-add", "success")
        self.assertEqual(a.rail("advance", "1")["state"], "merged")

        second = a.rail("next")
        self.assertEqual(second["ticket"], "2")
        a.write("api/handlers.py", "def handle():\n    return 201\n", base=a.worktree("2"))
        reviewed = a.rail("advance", "2")
        self.assertEqual(reviewed["state"], "in-ci")
        github.ci("2-add-a-status-code", "success")
        self.assertEqual(a.rail("advance", "2")["state"], "merged")

        waiting = a.rail("next")
        self.assertEqual((waiting["owner"], waiting["reason"]["code"]), ("human", "WAITING_HUMAN"))
        self.assertEqual(waiting["waits"][0]["needs"], "APPROVE_CONTRACT")
        self.assertIn("rail:needs-you", github.pr(1)["labels"])

        github.label(1, "rail:go")
        claimed = a.rail("next")
        self.assertEqual((claimed["ticket"], claimed["state"]), ("3", "implementing"))
        self.assertEqual(github.pr(1)["labels"], [])
        accepted = [json.loads(l) for l in a.git("show", "3-change-the-config:.rail/journal/3-events.jsonl").splitlines()
                    if json.loads(l)["event"] == "accepted"][0]
        self.assertEqual((accepted["by"], accepted["via"]), ("person", "label"))

        a.write("src/config/app.toml", "mode = 'fast'\n", base=a.worktree("3"))
        a.rail("advance", "3")
        github.ci("3-change-the-config", "success")
        ready = a.rail("next")
        self.assertEqual((ready["owner"], ready["waits"][0]["needs"]), ("human", "MERGE_BY_PERSON"))
        self.assertEqual(github.pr(1)["title"], "3: change the config")
        github.person_merges(1)
        self.assertEqual(a.rail("next")["reason"]["code"], "NO_WORK")
        self.assertEqual([t["state"] for t in a.rail("status")["tickets"]], ["merged", "merged", "merged"])
        self.assertIn("Ticket: 3\nTier: HIGH", bare_log(github))

    def test_a_person_holds_a_ticket_with_a_label_and_continues_it_with_rail_go(self):
        a, b, github = self.github_pair()
        a.add(ticket())
        a.rail("next")
        github.label(1, "rail:needs-you")
        held = a.rail("next")
        self.assertEqual((held["owner"], held["waits"][0]["needs"]), ("human", "HOLD"))
        github.update(lambda s: s.setdefault("comments", {}).__setitem__("1", [
            {"body": "Use the shared helper.", "created_at": "2099-01-01T00:00:00Z", "user": {"login": "owner"}}]))
        github.label(1, "rail:go")
        back = a.rail("next")
        self.assertEqual(back["reason"]["code"], "IMPLEMENT")
        self.assertIn('A person said: "Use the shared helper."', back["action"]["brief"])


class Merges(RailTest):
    def test_a_pr_behind_its_base_is_rebased_with_no_agent_work(self):
        a, b, github = self.github_pair()
        github.update(lambda s: s.__setitem__("require_up_to_date", True))
        a.add(ticket())
        a.rail("next")
        a.fix_calc("1")
        a.rail("advance", "1")
        b.write("notes.md", "news\n")
        b.git("add", "notes.md")
        b.git("commit", "--quiet", "-m", "base moves")
        b.git("push", "--quiet", "origin", "main")
        behind = a.rail("next", "--ticket", "1")
        self.assertEqual(behind["state"], "in-ci")
        base = github.head("main")
        self.assertEqual(subprocess.run(["git", "--git-dir", github.read()["bare"], "merge-base", "--is-ancestor", base,
                                         "1-fix-add"]).returncode, 0)

    def test_a_refused_merge_waits_for_a_person(self):
        a, b, github = self.github_pair()
        a.add(ticket())
        a.rail("next")
        a.fix_calc("1")
        a.rail("advance", "1")
        github.ci("1-fix-add", "success")
        github.update(lambda s: s.__setitem__("fail_merge", "Repository rule violations found"))
        refused = a.rail("advance", "1", expect=3)
        self.assertEqual((refused["owner"], refused["reason"]["code"]), ("human", "MERGE_FAILED"))
        self.assertIn("Repository rule violations found", refused["action"]["brief"])

    def test_a_pr_closed_by_hand_drops_the_ticket(self):
        a, b, github = self.github_pair()
        a.add(ticket())
        a.rail("next")
        github.update(lambda s: s["pulls"][0].__setitem__("state", "closed"))
        self.assertEqual(a.rail("status")["tickets"][0]["state"], "dropped")
        a.rail("next")
        self.assertFalse(os.path.exists(a.worktree("1")))


class Resume(RailTest):
    def test_a_later_run_resumes_a_ticket_an_earlier_one_left_half_done(self):
        a, b, github = self.github_pair()
        a.add(ticket())
        a.rail("next", session="run-1")
        a.write("src/calc.py", "def add(a, b):\n    return a * b\n", base=a.worktree("1"))
        a.rail("advance", "1", session="run-1", expect=3)  # the check fails; the work is committed and pushed
        later = b.rail("next", "--ticket", "1", session="run-2")
        self.assertEqual((later["ticket"], later["reason"]["code"]), ("1", "STEP_FAILED"))
        self.assertIn("a * b", open(os.path.join(b.worktree("1"), "src", "calc.py")).read())
        b.fix_calc("1")
        self.assertEqual(b.rail("advance", "1", session="run-2")["state"], "in-ci")
