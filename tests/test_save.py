"""Work in flight is saved as it goes, a ticket that keeps moving is left alone, and a merged contract is an approval."""

import json
import os
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from railtest import CONFIG, Fixture, RailTest, ticket

HALF_DONE = "def add(a, b):\n    return a * b  # not there yet\n"


def events(fx, branch="1-fix-add", ref_prefix=""):
    text = fx.git("show", f"{ref_prefix}{branch}:.rail/journal/1-events.jsonl")
    return [json.loads(line) for line in text.splitlines()]


def home(fx):
    """The home folder the hooks of a test run with: the pulse stamp lives there, and must not be the real one's."""
    path = os.path.join(os.path.dirname(fx.root), "hook-home")
    os.makedirs(path, exist_ok=True)
    return path


def hook(fx, name, session="session-a", command=None, env_extra=None, project_dir=None):
    """Run a hook as Claude Code does: its settings command, with the event's JSON on stdin."""
    where = project_dir or fx.root
    payload = {"hook_event_name": name, "session_id": session, "cwd": where}
    env = dict(os.environ, CLAUDE_PROJECT_DIR=where, CLAUDE_CODE_SESSION_ID=session, RAIL_CLOUD="0", **(env_extra or {}))
    env["HOME"] = home(fx)
    env.setdefault("GIT_CONFIG_GLOBAL", os.path.join(os.path.expanduser("~"), ".gitconfig"))
    env.pop("CLAUDE_CODE_REMOTE_SESSION_ID", None)
    return subprocess.run(["sh", "-c", command or f'"$CLAUDE_PROJECT_DIR"/.rail/bin/rail hook {name}'],
                          input=json.dumps(payload), capture_output=True, text=True, cwd=where, env=env)


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

    def test_a_save_takes_deleted_and_renamed_files(self):
        # A staged deletion is on disk and in the index no more, and git add stops at a path it can't find.
        a, b = self.remote_pair()
        a.add(ticket())
        a.rail("next")
        tree = a.worktree("1")
        a.write("src/old.py", "OLD = 1\n", base=tree)
        a.write("src/keep.py", "KEEP = 1\n", base=tree)
        self.assertEqual(a.rail("save")["steps"][0]["detail"], "ticket 1: 2 files")
        a.git("rm", "--quiet", "src/old.py", cwd=tree)
        a.git("mv", "src/keep.py", "src/kept.py", cwd=tree)
        a.write("src/calc.py", HALF_DONE, base=tree)
        self.assertEqual(a.rail("save")["steps"][0]["result"], "pass")
        self.assertEqual(a.git("status", "--porcelain", cwd=tree), "")  # nothing is left staged
        a.git("fetch", "--quiet")
        files = a.git("ls-tree", "-r", "--name-only", "origin/1-fix-add", "src/").split()
        self.assertEqual(sorted(files), ["src/calc.py", "src/kept.py"])
        a.git("rm", "--quiet", "src/kept.py", cwd=tree)
        done = hook(a, "stop")  # and the hook, with nothing else changed
        self.assertEqual((done.returncode, done.stderr), (0, ""))
        a.git("fetch", "--quiet")
        self.assertEqual(a.git("ls-tree", "-r", "--name-only", "origin/1-fix-add", "src/").split(), ["src/calc.py"])
        self.assertEqual(events(a)[-1]["event"], "saved")

    def test_a_save_leaves_out_files_whose_names_say_they_hold_secrets(self):
        # A save is pushed before verify, where the project's secret scan runs.
        a, b = self.remote_pair()
        a.add(ticket())
        a.rail("next")
        tree = a.worktree("1")
        a.write("src/calc.py", HALF_DONE, base=tree)
        for name in ("src/.env", "src/.env.local", "src/deploy.pem", "src/server.key", "src/id_rsa"):
            a.write(name, "SECRET\n", base=tree)
        a.write("src/.env.example", "KEY=\n", base=tree)
        saved = a.rail("save")
        self.assertEqual(saved["steps"][0]["detail"], "ticket 1: 2 files")
        self.assertIn("their names say they hold secrets: src/.env, src/.env.local, src/deploy.pem, src/id_rsa, src/server.key",
                      saved["action"]["brief"])
        a.git("fetch", "--quiet")
        pushed = a.git("ls-tree", "-r", "--name-only", "origin/1-fix-add", "src/").split()
        self.assertEqual(sorted(pushed), ["src/.env.example", "src/calc.py"])
        self.assertIn("src/deploy.pem", a.git("status", "--porcelain", cwd=tree))  # still there, for the ship to judge
        self.assertEqual(hook(a, "stop").returncode, 0)
        a.git("fetch", "--quiet")
        self.assertEqual(sorted(a.git("ls-tree", "-r", "--name-only", "origin/1-fix-add", "src/").split()),
                         ["src/.env.example", "src/calc.py"])

    def test_a_save_that_fails_in_a_hook_is_told_to_the_agent(self):
        a, b = self.remote_pair()
        a.add(ticket())
        a.rail("next")
        a.write("src/calc.py", HALF_DONE, base=a.worktree("1"))
        refuse = a.path(".git", "hooks", "pre-commit")  # the project's own hook turns the commit down
        a.write(refuse, "#!/bin/sh\necho no commits today >&2\nexit 1\n")
        os.chmod(refuse, 0o755)
        pulse = hook(a, "pulse")
        self.assertEqual(pulse.returncode, 0, pulse.stderr)  # a hook never stops the session
        told = json.loads(pulse.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("could not save the work in flight", told)
        self.assertIn("no commits today", told)
        stop = hook(a, "stop")
        self.assertEqual((stop.returncode, stop.stdout), (0, ""))  # the stop is not held up
        os.remove(refuse)
        self.assertEqual(hook(a, "pulse").stdout, "")
        a.git("fetch", "--quiet")
        self.assertEqual(a.git("show", "origin/1-fix-add:src/calc.py"), HALF_DONE)

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

        stamp = os.path.join(home(a), ".cache", "rail", "pulse", "session-a")
        old = time.time() - 11 * 60
        os.utime(stamp, (old, old))
        hook(a, "PostToolUse", command=command)
        a.git("fetch", "--quiet")
        self.assertEqual(a.git("show", "origin/1-fix-add:src/calc.py"), HALF_DONE + "# more\n")

    def test_the_pulse_hook_waits_as_long_in_a_session_that_stands_in_a_worktree(self):
        # There .git is a file, so a stamp kept under the project's .git folder was never found, and the hook
        # fetched and saved after every tool call.
        a, b = self.remote_pair()
        with open(a.path(".claude", "settings.json")) as f:
            command = json.load(f)["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
        a.add(ticket())
        a.rail("next")
        tree = a.worktree("1")
        a.write("src/calc.py", HALF_DONE, base=tree)
        hook(a, "PostToolUse", command=command, project_dir=tree)
        a.git("fetch", "--quiet")
        self.assertEqual(a.git("show", "origin/1-fix-add:src/calc.py"), HALF_DONE)
        a.write("src/calc.py", HALF_DONE + "# more\n", base=tree)
        hook(a, "PostToolUse", command=command, project_dir=tree)  # the second call is skipped
        a.git("fetch", "--quiet")
        self.assertEqual(a.git("show", "origin/1-fix-add:src/calc.py"), HALF_DONE)
        stamp = os.path.join(home(a), ".cache", "rail", "pulse", "session-a")
        old = time.time() - 11 * 60
        os.utime(stamp, (old, old))
        hook(a, "PostToolUse", command=command, project_dir=tree)
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

    def test_a_sign_of_life_before_a_review_keeps_the_branch_in_step_with_the_remote(self):
        # The event is committed and pushed before the reviewer starts, and the worktree is reset to the head after it.
        a, b = self.remote_pair(config=CONFIG + "\n[claim]\nsave_minutes = 0\n")
        a.add(ticket(tier="MEDIUM"))
        a.rail("next")
        a.fix_calc("1")
        a.rail("advance", "1")
        a.git("fetch", "--quiet")
        self.assertEqual(a.git("rev-parse", "1-fix-add"), a.git("rev-parse", "origin/1-fix-add"))
        self.assertIn('"role": "review"', a.git("show", "origin/1-fix-add:.rail/journal/1-review.json"))
        a.queue_reviews({"summary": "Looked again.", "findings": []})
        a.write("src/calc.py", "def add(a, b):\n    return b + a\n", base=a.worktree("1"))
        a.rail("advance", "1")  # a second ship and review still push
        a.git("fetch", "--quiet")
        self.assertEqual(a.git("rev-parse", "1-fix-add"), a.git("rev-parse", "origin/1-fix-add"))

    def test_a_save_stays_out_while_advance_is_inside_a_review(self):
        # The reviewer writes scratch files into the worktree. A save hook that fired then would push them.
        a, b = self.remote_pair()
        a.add(ticket(tier="MEDIUM"))
        a.rail("next")
        a.fix_calc("1")
        a.queue_reviews({"touch": "src/scratch.py", "sleep": 4, "summary": "Tried an idea.", "findings": []})
        worker = threading.Thread(target=lambda: a.rail("advance", "1"))
        worker.start()
        time.sleep(2.5)  # the review is running, and its scratch file is in the worktree
        self.assertTrue(os.path.exists(os.path.join(a.worktree("1"), "src", "scratch.py")))
        self.assertIn("another rail command is at work", a.rail("save", "1")["action"]["brief"])
        self.assertEqual(hook(a, "stop").returncode, 0)
        worker.join()
        a.git("fetch", "--quiet")
        self.assertEqual(a.git("rev-parse", "1-fix-add"), a.git("rev-parse", "origin/1-fix-add"))
        self.assertNotIn("scratch.py", a.git("ls-tree", "-r", "--name-only", "origin/1-fix-add"))

    def test_next_works_from_a_plain_terminal_after_a_claude_session(self):
        # No session id, and the folder the session-start hook made: next once tried to read that folder as a file.
        p = self.fixture()
        p.add(ticket())
        hook(p, "session-start", command='"$CLAUDE_PROJECT_DIR"/.rail/bin/rail hook session-start')
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CODE_SESSION_ID", "RAIL_TICKET")}
        result = subprocess.run([p.path(".rail", "bin", "rail"), "next", "--json"], capture_output=True, text=True,
                                cwd=p.root, env=dict(env, RAIL_CLOUD="0"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["reason"]["code"], "IMPLEMENT")

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

    def test_a_ticket_file_that_came_in_with_another_merge_is_nobodys_approval(self):
        # Only the ticket's own merged pull request shows a person merged its contract. A HIGH ticket's file that
        # reaches the base branch inside another ticket's merge has no pull request of its own.
        a, b, github = self.github_pair()
        smuggled = ticket(**self.HIGH).replace("+++\n", '+++\nid = "99"\n', 1)
        a.write(".rail/tickets/99.md", smuggled)
        a.git("add", ".rail/tickets/99.md")
        a.git("commit", "--quiet", "-m", "1: Fix add (#7)\n\nTicket: 1\nTier: LOW")
        a.git("push", "--quiet", "origin", "main")
        for fx in (a, b):
            told = fx.rail("next")
            self.assertEqual(told["reason"]["code"], "NO_WORK", told)
            self.assertEqual([t["state"] for t in fx.rail("status")["tickets"] if t["ticket"] == "99"], ["dropped"])
            self.assertEqual(fx.git("branch", "--all", "--list", "*99-*").strip(), "")  # nothing was claimed or accepted

    def test_a_drop_holds_after_the_tickets_branch_is_gone(self):
        # The contract reached the base branch by the merge. Dropped, and its branch deleted, the ticket must not
        # look approved again: the drop is also marked in the counter branch.
        a, b, github = self.github_pair()
        github.update(lambda s: s.__setitem__("delete_branch_on_merge", True))
        a.add(ticket(**self.HIGH))
        github.person_merges(1)
        self.assertEqual(b.rail("status")["tickets"][0]["state"], "new")  # the merge reads as an approval to take up
        self.assertEqual(b.rail("drop", "1", "--reason", "another ticket does this work")["state"], "dropped")
        a.git("fetch", "--quiet", "--prune")
        self.assertIn("rail drop 1", a.git("log", "--format=%s", "origin/rail/ids"))
        fresh = Fixture(os.path.join(self.tmp, "c"), remote=os.path.join(self.tmp, "remote.git"))
        fresh.git("config", "remote.origin.url", a.git("config", "--get", "remote.origin.url").strip())
        fresh.git("config", f"url.{os.path.join(self.tmp, 'remote.git')}.insteadOf",
                  a.git("config", "--get", "remote.origin.url").strip())
        fresh.github = github
        self.assertEqual(fresh.rail("status")["tickets"][0]["state"], "dropped")
        self.assertEqual(fresh.rail("next")["reason"]["code"], "NO_WORK")
        self.assertEqual(fresh.add(ticket(title="Other", scope=("api/**",)))["ticket"], "2")  # and the ID isn't reused

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
