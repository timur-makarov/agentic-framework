"""Work in flight is saved as it goes, a ticket that keeps moving is left alone, and a merged contract is an approval."""

import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from railtest import CONFIG, RailTest, ticket

HALF_DONE = "def add(a, b):\n    return a * b  # not there yet\n"


def events(fx, branch="1-fix-add", ref_prefix=""):
    text = fx.git("show", f"{ref_prefix}{branch}:.rail/journal/1-events.jsonl")
    return [json.loads(line) for line in text.splitlines()]


def hook(fx, name, session="session-a", command=None, env_extra=None):
    """Run a hook as Claude Code does: its settings command, with the event's JSON on stdin."""
    payload = {"hook_event_name": name, "session_id": session, "cwd": fx.root}
    env = dict(os.environ, CLAUDE_PROJECT_DIR=fx.root, CLAUDE_CODE_SESSION_ID=session, RAIL_CLOUD="0", **(env_extra or {}))
    env.pop("CLAUDE_CODE_REMOTE_SESSION_ID", None)
    return subprocess.run(["sh", "-c", command or f'"$CLAUDE_PROJECT_DIR"/.rail/bin/rail hook {name}'],
                          input=json.dumps(payload), capture_output=True, text=True, cwd=fx.root, env=env)


class Save(RailTest):
    def test_rail_save_pushes_the_work_as_it_is_and_checks_nothing(self):
        a, b = self.remote_pair()
        a.add(ticket())
        a.rail("next")
        a.write("src/calc.py", HALF_DONE, base=a.worktree("1"))
        a.write("api/handlers.py", "def handle():\n    return 500\n", base=a.worktree("1"))  # outside scope_paths
        saved = a.rail("save")
        self.assertEqual(saved["steps"], [{"step": "save", "status": "ran", "result": "pass", "detail": "ticket 1: 1 files"}])
        self.assertIn("outside scope_paths: api/handlers.py", saved["action"]["brief"])
        a.git("fetch", "--quiet")
        self.assertEqual(a.git("show", "origin/1-fix-add:src/calc.py"), HALF_DONE)
        self.assertIn("1: save work in progress [skip ci]", a.git("log", "--format=%s", "origin/1-fix-add"))
        self.assertEqual(events(a)[-1]["event"], "saved")
        self.assertEqual((events(a)[-1]["via"], events(a)[-1]["files"]), ("save", 1))
        self.assertEqual(a.rail("status")["tickets"][0]["state"], "implementing")  # saving ships nothing
        self.assertIn("api/handlers.py", a.git("status", "--porcelain", cwd=a.worktree("1")))
        self.assertEqual(a.rail("save")["action"]["brief"], "Nothing to save.")  # and a moment later there is nothing new

    def test_a_fresh_clone_resumes_from_the_last_save(self):
        a, b = self.remote_pair(config=CONFIG + "\n[claim]\nstale_minutes = 0\n")
        a.add(ticket())
        a.rail("next", session="run-1")
        a.write("src/calc.py", HALF_DONE, base=a.worktree("1"))
        a.rail("save", session="run-1")
        later = b.rail("next", session="run-2")  # run-1's machine is gone
        self.assertEqual((later["ticket"], later["reason"]["code"]), ("1", "IMPLEMENT"))
        with open(os.path.join(b.worktree("1"), "src", "calc.py")) as f:
            self.assertEqual(f.read(), HALF_DONE)

    def test_the_stop_hook_saves_at_the_end_of_a_turn(self):
        a, b = self.remote_pair()
        a.add(ticket())
        a.rail("next")
        a.write("src/calc.py", HALF_DONE, base=a.worktree("1"))
        done = hook(a, "stop")
        self.assertEqual((done.returncode, done.stdout), (0, ""), done.stderr)  # it never blocks the stop, and says nothing
        a.git("fetch", "--quiet")
        self.assertEqual(a.git("show", "origin/1-fix-add:src/calc.py"), HALF_DONE)
        tip = a.git("rev-parse", "origin/1-fix-add")
        hook(a, "stop")  # a turn that changed nothing, a moment later: no commit
        a.git("fetch", "--quiet")
        self.assertEqual(a.git("rev-parse", "origin/1-fix-add"), tip)

    def test_the_pulse_hook_saves_while_the_agent_works_at_most_every_few_minutes(self):
        a, b = self.remote_pair()
        with open(a.path(".claude", "settings.json")) as f:
            command = json.load(f)["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
        a.add(ticket())
        a.rail("next")
        a.write("src/calc.py", HALF_DONE, base=a.worktree("1"))
        hook(a, "PostToolUse", command=command)
        a.git("fetch", "--quiet")
        self.assertEqual(a.git("show", "origin/1-fix-add:src/calc.py"), HALF_DONE)

        a.write("src/calc.py", HALF_DONE + "# more\n", base=a.worktree("1"))
        hook(a, "PostToolUse", command=command)  # a moment later: the stamp is fresh, so the engine isn't even started
        a.git("fetch", "--quiet")
        self.assertEqual(a.git("show", "origin/1-fix-add:src/calc.py"), HALF_DONE)

        stamp = a.path(".git", "rail", "cache", "pulse", "session-a")
        old = time.time() - 11 * 60
        os.utime(stamp, (old, old))
        hook(a, "PostToolUse", command=command)
        a.git("fetch", "--quiet")
        self.assertEqual(a.git("show", "origin/1-fix-add:src/calc.py"), HALF_DONE + "# more\n")

    def test_a_session_whose_ticket_was_taken_over_is_told_to_stand_down(self):
        a, b = self.remote_pair()
        a.add(ticket())
        a.rail("next", session="run-1")
        a.write("src/calc.py", HALF_DONE, base=a.worktree("1"))
        b.rail("next", "--ticket", "1", session="run-2")  # run-2 takes it over while run-1 is still alive
        told = a.rail("save", session="run-1")
        self.assertEqual(told["steps"], [])
        self.assertIn("was taken over by another session", told["action"]["brief"])
        self.assertIn("Stop work on it here", told["action"]["brief"])
        pulse = hook(a, "pulse", session="run-1")
        self.assertIn("was taken over by another session", json.loads(pulse.stdout)["hookSpecificOutput"]["additionalContext"])
        back = a.rail("advance", "1", session="run-1")
        self.assertEqual(back["reason"]["code"], "CLAIMED_ELSEWHERE")
        self.assertIn("Stop work on it here", back["action"]["brief"])
        with open(os.path.join(a.worktree("1"), "src", "calc.py")) as f:
            self.assertEqual(f.read(), HALF_DONE)  # its unsaved work is still there to look at

    def test_advance_shows_life_before_each_long_command(self):
        p = self.fixture(config=CONFIG + "\n[claim]\nsave_minutes = 0\n")  # 0: every command counts as long
        p.add(ticket())
        p.rail("next")
        p.fix_calc("1")
        p.rail("advance", "1")
        alive = [e for e in events(p) if e["event"] == "saved"]
        self.assertTrue(alive and all(e["via"] == "advance" for e in alive), alive)

    def test_the_brief_asks_for_saves_only_where_no_hook_makes_them(self):
        p = self.fixture()
        p.add(ticket())
        self.assertIn("rail save 1 every ten minutes", p.rail("next")["action"]["brief"])
        hook(p, "session-start", command='"$CLAUDE_PROJECT_DIR"/.rail/bin/rail hook session-start')
        self.assertNotIn("rail save", p.rail("next")["action"]["brief"])


class MergedContract(RailTest):
    HIGH = dict(title="Change the config", tier="HIGH", scope=("src/config/**",), check="test -f src/config/app.toml")

    def test_a_merged_contract_counts_as_its_approval_and_the_ticket_goes_on(self):
        a, b, github = self.github_pair()
        a.add(ticket(**self.HIGH))
        github.person_merges(1)  # the contract's pull request has a merge button, and a person pressed it
        on = a.rail("next")
        self.assertEqual((on["ticket"], on["reason"]["code"]), ("1", "IMPLEMENT"))
        self.assertIn({"step": "contract", "status": "ran", "result": "pass",
                       "detail": "its pull request was merged before the work: taken as the approval"}, on["steps"])
        accepted = [e for e in events(a, "1-change-the-config") if e["event"] == "accepted"]
        self.assertEqual([(e["by"], e["via"]) for e in accepted], [("person", "merge")])
        self.assertEqual((github.pr(2)["state"], github.pr(2)["title"]), ("open", "1: Change the config"))

        a.write("src/config/app.toml", "debug = false\n", base=a.worktree("1"))
        self.assertEqual(a.rail("advance", "1")["state"], "in-ci")
        github.ci("1-change-the-config", "success")
        self.assertEqual(a.rail("next")["waits"][0]["needs"], "MERGE_BY_PERSON")
        github.person_merges(2)
        self.assertEqual(a.rail("status")["tickets"][0]["state"], "merged")

    def test_it_goes_on_in_a_fresh_clone_after_github_deleted_the_merged_branch(self):
        a, b, github = self.github_pair()
        github.update(lambda s: s.__setitem__("delete_branch_on_merge", True))
        a.add(ticket(**self.HIGH))
        github.person_merges(1)
        on = b.rail("next")
        self.assertEqual((on["ticket"], on["reason"]["code"]), ("1", "IMPLEMENT"))
        self.assertEqual(github.pr(2)["state"], "open")
        self.assertTrue(os.path.exists(os.path.join(b.worktree("1"), ".rail", "tickets", "1.md")))

    def test_a_work_pull_request_merged_before_its_ship_is_not_a_finished_ticket(self):
        a, b, github = self.github_pair()
        a.add(ticket())
        a.rail("next")
        github.person_merges(1)  # "Not shipped yet" was merged by hand
        self.assertEqual(a.rail("status")["tickets"][0]["state"], "implementing")
        on = a.rail("next")
        self.assertEqual((on["ticket"], on["reason"]["code"]), ("1", "IMPLEMENT"))
        self.assertEqual(github.pr(2)["state"], "open")
        a.fix_calc("1")
        a.rail("advance", "1")
        github.ci("1-fix-add", "success")
        self.assertEqual(a.rail("advance", "1")["state"], "merged")


if __name__ == "__main__":
    import unittest
    unittest.main()
