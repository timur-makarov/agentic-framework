"""Intake, the red base, the notify hook and the sweep (plan, sections 6, 7, 12 and 15)."""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from railtest import CONFIG, RailTest, ticket


def read(path):
    with open(path) as f:
        return f.read()


class Intake(RailTest):
    def test_issues_labelled_rail_become_tickets_once_and_a_drop_releases_the_issue(self):
        a, b, github = self.github_pair()
        github.update(lambda s: s["issues"].append({"number": 12, "title": "Add can't add", "body": "add(2, 3) gives -1.",
                                                    "labels": ["rail"], "state": "open"}))
        taken = a.rail("intake", "github")
        self.assertEqual(taken["created"], ["1"])
        self.assertEqual(a.rail("intake", "github")["skipped"], ["github#12"])
        stub = a.rail("next")
        self.assertEqual(stub["reason"]["code"], "TICKET_LINT")
        self.assertIn("rail amend 1 --file", stub["action"]["brief"])
        self.assertIn("1-github-12-add-can-t-add", a.git("branch", "--list", "1-*"))

        written = os.path.join(self.tmp, "1.md")
        with open(written, "w") as f:
            f.write(ticket(title="Add can't add", front=('external_id = "github#12"',),
                           body="\n## Request\nadd(2, 3) gives -1.\n"))
        a.rail("amend", "1", "--file", written)
        claimed = a.rail("next")
        self.assertEqual((claimed["ticket"], claimed["state"]), ("1", "implementing"))
        a.fix_calc("1")
        a.rail("advance", "1")
        self.assertIn("Closes #12", github.pr(1)["body"])

        a.rail("drop", "1", "--reason", "a duplicate")
        issue = github.read()["issues"][0]
        self.assertNotIn("rail", issue["labels"])
        self.assertIn("Label this issue `rail` again to retry", github.read()["comments"]["12"][0]["body"])

    def test_a_failed_deploy_names_the_ticket_that_caused_it(self):
        a, b, github = self.github_pair()
        a.add(ticket())
        a.rail("next")
        a.fix_calc("1")
        a.rail("advance", "1")
        github.ci("1-fix-add", "success")
        a.rail("advance", "1")
        a.git("fetch", "--quiet")
        sha = a.git("rev-parse", "origin/main").strip()
        github.update(lambda s: s["issues"].append({"number": 30, "title": "Smoke check failed on dev",
                                                    "body": f"Commit: {sha}\n\nGET /health returned 500.",
                                                    "labels": ["rail"], "state": "open"}))
        nn = a.rail("intake", "github")["created"][0]
        text = a.git("show", f"{nn}-github-30-smoke-check-failed-on-dev:.rail/tickets/{nn}.md")
        self.assertIn('caused_by = "1"', text)

    def test_any_tracker_comes_in_with_an_external_id(self):
        p = self.fixture()
        brief = os.path.join(self.tmp, "brief.txt")
        with open(brief, "w") as f:
            f.write("Customers see negative totals.\n")
        taken = p.rail("intake", "--external-id", "PROJ-7", "--title", "Fix totals", "--brief", brief)
        self.assertEqual(taken["created"], ["1"])
        self.assertEqual(p.rail("intake", "--external-id", "PROJ-7", "--title", "Fix totals", "--brief", brief)["created"], [])
        self.assertIn("Customers see negative totals.", p.git("show", "1-proj-7-fix-totals:.rail/tickets/1.md"))


class RedBase(RailTest):
    def test_a_red_base_spends_no_budget_and_gets_one_fix_ticket(self):
        p = self.fixture(config=CONFIG.replace("python3 -m py_compile src/calc.py", "python3 -m compileall -q src"))
        p.add(ticket())
        p.rail("next")
        p.fix_calc("1")
        p.write("src/broken.py", "def broken(:\n")
        p.git("add", "src/broken.py")
        p.git("commit", "--quiet", "-m", "someone breaks main")
        failed = p.rail("advance", "1", expect=3)
        verify = [s for s in failed["steps"] if s["step"] == "verify"][0]
        self.assertEqual(verify["detail"], "red base")
        self.assertIn("verify fails on the base branch too", failed["action"]["brief"])
        event = [json.loads(l) for l in p.git("show", "1-fix-add:.rail/journal/1-events.jsonl").splitlines()][-1]
        self.assertEqual((event["step"], event["counted"]), ("verify", False))
        fix = p.rail("next")
        self.assertEqual((fix["ticket"], fix["reason"]["code"]), ("2", "TICKET_LINT"))
        self.assertIn("broken.py", p.git("show", "2-red-base-" + p.git("rev-parse", "main").strip()[:12]
                                         + "-make-verify-pass-on-main-again:.rail/tickets/2.md"))
        self.assertEqual(p.rail("next", "--ticket", "1")["reason"]["code"], "RED_BASE")


class Notify(RailTest):
    def test_each_new_wait_is_announced_once(self):
        p = self.fixture()
        p.add(ticket(tier="HIGH"))

        def hook(term_program):
            env = dict(os.environ, TERM_PROGRAM=term_program)
            payload = json.dumps({"hook_event_name": "Notification", "cwd": p.root})
            return subprocess.run([p.path(".rail", "bin", "rail"), "hook", "notify"], input=payload,
                                  capture_output=True, text=True, env=env, cwd=p.root).stdout

        first = json.loads(hook("iTerm.app"))
        self.assertEqual(first["terminalSequence"], "\x1b]9;Rail: 1: approve the contract\x07")
        self.assertEqual(hook("iTerm.app"), "")
        p.rail("accept", "1")
        self.assertEqual(hook("iTerm.app"), "")
        p.add(ticket(title="Another", tier="HIGH", scope=("api/**",)))
        self.assertEqual(json.loads(hook("ghostty"))["terminalSequence"],
                         "\x1b]777;notify;Rail;Rail: 2: approve the contract\x07")


class Sweep(RailTest):
    def test_after_enough_unreviewed_work_a_sweep_turns_findings_into_tickets(self):
        p = self.fixture(config=CONFIG + "\n[sweep]\nafter = 2\n")
        for title, scope, check, path, text in (
                ("Fix add", ("src/**",), None, None, None),
                ("Add a status code", ("api/**",), "grep -q 201 api/handlers.py", "api/handlers.py",
                 "def handle():\n    return 201\n")):
            nn = p.add(ticket(title=title, scope=scope, **({"check": check} if check else {})))["ticket"]
            p.rail("next")
            if path:
                p.write(path, text, base=p.worktree(nn))
            else:
                p.fix_calc(nn)
            p.rail("advance", nn)
            p.rail("advance", nn)
        offer = p.rail("next")
        self.assertEqual((offer["reason"]["code"], offer["action"]["command"], offer["unreviewed"]), ("SWEEP", "rail sweep", 2))

        dup = {"severity": "advisory", "file": "src/calc.py", "claim": "add and handle both lack tests.",
               "check": "a test per public function"}
        p.queue_reviews({"summary": "Swept two LOW tickets.", "findings": [dup]})
        swept = p.rail("sweep")
        self.assertEqual((swept["ticket"], swept["reason"]["code"]), ("3", "SWEEP_TICKETS"))
        summary = read(os.path.join(p.worktree("3"), ".rail", "journal", "3-summary.md"))
        self.assertIn("2 commits merged without a review", summary)
        self.assertIn("F1 (advisory) src/calc.py: add and handle both lack tests.", summary)
        self.assertIn("Sweep brief", p.briefs()[-1]["brief"])
        self.assertIn("return 201", p.briefs()[-1]["brief"])

        self.assertEqual(p.rail("advance", "3")["state"], "merge-ready")
        self.assertEqual(p.rail("advance", "3")["state"], "merged")
        self.assertIn("Sweep: since", p.git("log", "-1", "--format=%b", "main"))
        self.assertEqual(p.rail("next")["reason"]["code"], "NO_WORK")
