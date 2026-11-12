"""The forge (plan, sections 7, 10 and 11): pull requests, CI, labels and the merge, on a fake GitHub (fake_gh.py)."""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from railtest import CONFIG, RailTest, ticket


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

    def test_the_brief_counts_only_this_tickets_lines_when_the_projects_own_checkout_is_behind(self):
        # Live on GitHub: after a merge on the remote, the next ticket's brief counted the merged lines as its own.
        a, b, github = self.github_pair()
        a.add(ticket())
        a.rail("next")
        a.fix_calc("1")
        a.rail("advance", "1")
        github.ci("1-fix-add", "success")
        self.assertEqual(a.rail("advance", "1")["state"], "merged")  # GitHub's merge: a's own main stays behind
        a.add(ticket(title="Add a status code", scope=("api/**",), check="grep -q 201 api/handlers.py"))
        self.assertIn("size 0/300", a.rail("next")["action"]["brief"])

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

    def test_a_red_check_from_github_actions_brings_the_failing_steps_log(self):
        # A real check run from Actions has an empty output; what `rail ci` printed is in the job's log.
        a, b, github = self.github_pair()
        a.add(ticket())
        a.rail("next")
        a.fix_calc("1")
        a.rail("advance", "1")
        log = "\n".join([
            "2026-11-12T10:13:42.7741036Z ##[group]Run .rail/bin/rail ci",
            "2026-11-12T10:13:42.7741580Z \x1b[36;1m.rail/bin/rail ci\x1b[0m",
            "2026-11-12T10:13:42.7791915Z ##[endgroup]",
            "2026-11-12T10:13:42.9786130Z owner agent \u00b7 CI_FAILED",
            "2026-11-12T10:13:42.9786790Z   verify: ran, fail (exit 1)",
            "2026-11-12T10:13:42.9797790Z ",
            "2026-11-12T10:13:42.9798224Z FAIL: test_negative (tests.test_calc.CalcTest)",
            "2026-11-12T10:13:43.0000000Z ##[error]Process completed with exit code 1.",
            "2026-11-12T10:13:43.0093031Z Post job cleanup.",
        ])
        github.ci("1-fix-add", "failure", log=log)
        brief = a.rail("next")["action"]["brief"]
        self.assertIn("FAIL: test_negative (tests.test_calc.CalcTest)", brief)
        self.assertIn("verify: ran, fail (exit 1)", brief)
        self.assertIn("Process completed with exit code 1.", brief)
        self.assertNotIn("Post job cleanup", brief)
        self.assertNotIn("2026-11-12T", brief)
        self.assertNotIn("##[group]", brief)


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


    def test_a_shipped_ticket_is_merged_by_whichever_session_looks_next(self):
        # A cloud run ends once its ticket ships. The next run is a new session: it must not wait for the old one.
        a, b, github = self.github_pair()
        a.add(ticket())
        a.rail("next", session="run-1")
        a.fix_calc("1")
        a.rail("advance", "1", session="run-1")
        waiting = b.rail("next", session="run-2")
        self.assertEqual((waiting["ticket"], waiting["reason"]["code"]), ("1", "CI_WAIT"))  # CI isn't done: nothing to do
        github.ci("1-fix-add", "success")
        ready = b.rail("next", session="run-2")
        self.assertEqual((ready["ticket"], ready["reason"]["code"], ready["action"]["command"]),
                         ("1", "MERGE", "rail advance 1"))
        self.assertEqual(b.rail("advance", "1", session="run-2")["state"], "merged")
        claims = [json.loads(l) for l in subprocess.run(
            ["git", "--git-dir", github.read()["bare"], "show", "main:.rail/journal/1-events.jsonl"],
            capture_output=True, text=True).stdout.splitlines() if '"claimed"' in l]
        self.assertEqual([c["session"] for c in claims], ["run-1"])  # merging took no claim

    def test_another_sessions_work_in_flight_is_left_alone_while_it_keeps_moving(self):
        a, b, github = self.github_pair()
        a.add(ticket())
        a.rail("next", session="run-1", env_extra={"CLAUDE_CODE_REMOTE_SESSION_ID": "cse_01abc"})
        other = b.rail("next", session="run-2")
        self.assertEqual(other["reason"]["code"], "NO_WORK")
        self.assertEqual(other["held"], [{"ticket": "1", "quiet_minutes": 0,
                                          "session": "https://claude.ai/code/session_01abc"}])
        self.assertIn("quiet 0 min", other["action"]["brief"])
        row = b.rail("status", session="run-2")["tickets"][0]
        self.assertIn("another session's work", row["note"])
        self.assertFalse(os.path.exists(b.worktree("1")))

    def test_work_an_ended_session_left_is_resumed_once_it_has_gone_quiet(self):
        # claim.stale_minutes = 0 stands in for an hour without a journal event.
        a, b, github = self.github_pair(config=CONFIG + "\n[claim]\nstale_minutes = 0\n")
        a.add(ticket())
        a.rail("next", session="run-1")
        a.write("src/calc.py", "def add(a, b):\n    return a * b\n", base=a.worktree("1"))
        a.rail("advance", "1", session="run-1", expect=3)  # the check fails; the work is committed and pushed
        later = b.rail("next", session="run-2")
        self.assertEqual((later["ticket"], later["reason"]["code"]), ("1", "STEP_FAILED"))
        self.assertIn("a * b", open(os.path.join(b.worktree("1"), "src", "calc.py")).read())
        claims = [json.loads(l) for l in b.git("show", "1-fix-add:.rail/journal/1-events.jsonl").splitlines()
                  if '"claimed"' in l]
        self.assertEqual([(c["session"], c["takeover"]) for c in claims], [("run-1", False), ("run-2", True)])

    def test_the_pull_request_names_the_cloud_session_and_the_reviewers_model(self):
        a, b, github = self.github_pair(config=CONFIG.replace("[review]", '[review]\nmodel = "claude-haiku-5-5"'))
        a.add(ticket(tier="MEDIUM"))
        a.rail("next", env_extra={"CLAUDE_CODE_REMOTE_SESSION_ID": "cse_01abc"})
        a.fix_calc("1")
        a.rail("advance", "1")
        self.assertEqual(a.briefs()[-1]["model"], "claude-haiku-5-5")  # the reviewer command ran on the model named
        body = github.pr(1)["body"]
        self.assertIn("| review | ran, 1 runs by claude-haiku-5-5, no findings |", body)
        self.assertTrue(body.endswith("Tier: MEDIUM\nClaude-Session: https://claude.ai/code/session_01abc"), body)


class Desk(RailTest):
    def test_a_wait_is_labelled_at_once_and_its_brief_says_what_to_do_on_github(self):
        # Live on GitHub: the HIGH ticket's contract got no rail:needs-you while the agent had other work.
        a, b, github = self.github_pair()
        a.add(ticket(title="Change the config", tier="HIGH", scope=("src/config/**",), check="test -f src/config/app.toml"))
        a.add(ticket(title="Fix add"))
        working = a.rail("next")
        self.assertEqual((working["ticket"], working["reason"]["code"]), ("2", "IMPLEMENT"))
        self.assertIn("rail:needs-you", github.pr(1)["labels"])
        a.fix_calc("2")
        a.rail("advance", "2")
        github.ci("2-fix-add", "success")
        a.rail("advance", "2")
        waiting = a.rail("next")
        self.assertEqual(waiting["reason"]["code"], "WAITING_HUMAN")
        self.assertIn("the label rail:go approves it", waiting["waits"][0]["brief"])
        self.assertIn("pull/1", waiting["waits"][0]["brief"])

    def test_a_contract_changed_before_approval_shows_on_its_pull_request(self):
        a, b, github = self.github_pair()
        a.add(ticket(title="Change the config", tier="HIGH", scope=("src/config/**",), check="test -f src/config/app.toml"))
        self.assertIn("test -f src/config/app.toml", github.pr(1)["body"])
        changed = os.path.join(self.tmp, "1.md")
        with open(changed, "w") as f:
            f.write(ticket(title="Change the config and its docs", tier="HIGH", scope=("src/config/**", "docs/**"),
                           check="test -f src/config/app.toml && test -f docs/config.md"))
        a.rail("amend", "1", "--file", changed)
        self.assertEqual(github.pr(1)["title"], "1: [contract] Change the config and its docs")
        self.assertIn("test -f docs/config.md", github.pr(1)["body"])

    def test_a_high_ticket_from_an_issue_gets_its_contract_pull_request_once_the_contract_is_written(self):
        a, b, github = self.github_pair()
        github.update(lambda s: s["issues"].append({"number": 12, "title": "Rework the config", "body": "It is a mess.",
                                                    "labels": ["rail"], "state": "open"}))
        self.assertEqual(a.rail("next")["reason"]["code"], "TICKET_LINT")
        self.assertEqual(github.read()["pulls"], [])  # no contract yet, so nothing to approve
        written = os.path.join(self.tmp, "1.md")
        with open(written, "w") as f:
            f.write(ticket(title="Rework the config", tier="HIGH", scope=("src/config/**",),
                           check="test -f src/config/app.toml", front=('external_id = "github#12"',)))
        waiting = a.rail("amend", "1", "--file", written)
        self.assertEqual((waiting["owner"], waiting["reason"]["code"]), ("human", "APPROVE_CONTRACT"))
        self.assertEqual(github.pr(1)["title"], "1: [contract] Rework the config")
        self.assertIn("pull/1", waiting["action"]["brief"])

    def test_an_issue_labelled_rail_comes_in_with_the_next_rail_next(self):
        a, b, github = self.github_pair()
        github.update(lambda s: s["issues"].append({"number": 12, "title": "Add can't add", "body": "add(2, 3) gives -1.",
                                                    "labels": ["rail"], "state": "open"}))
        stub = a.rail("next")
        self.assertEqual((stub["ticket"], stub["reason"]["code"]), ("1", "TICKET_LINT"))
        self.assertEqual(stub["steps"][0], {"step": "intake", "status": "ran", "result": "pass",
                                            "detail": "ticket 1 from github#12"})
        self.assertEqual(a.rail("next")["steps"], [])  # once: the issue has its ticket now


class Doctor(RailTest):
    def test_doctor_checks_the_one_time_github_settings(self):
        a, b, github = self.github_pair()
        found = {s["step"]: s for s in a.rail("doctor", expect=3)["steps"]}
        self.assertEqual(found["gh"]["result"], "pass")
        self.assertEqual(found["squash merging"]["result"], "fail")
        self.assertEqual(found["required check"]["result"], "pass")
        self.assertEqual(found["labels"]["result"], "fail")
        self.assertEqual(found["merged branches"]["result"], "fail")
        self.assertIn("Automatically delete head branches", found["merged branches"]["detail"])
        github.update(lambda s: s.update(settings={"allow_squash_merge": True, "allow_merge_commit": False,
                                                   "allow_rebase_merge": False, "squash_merge_commit_title": "PR_TITLE",
                                                   "squash_merge_commit_message": "PR_BODY",
                                                   "delete_branch_on_merge": True},
                                         labels=["rail", "rail:go", "rail:needs-you"]))
        found = {s["step"]: s for s in a.rail("doctor", expect=None)["steps"]}
        for name in ("squash merging", "required check", "labels", "merged branches"):
            self.assertEqual(found[name]["result"], "pass", found[name])
        github.update(lambda s: s.__setitem__("required", []))
        missing = {s["step"]: s for s in a.rail("doctor", expect=3)["steps"]}["required check"]
        self.assertIn("import .rail/ruleset.json at https://github.com/acme/app/settings/rules", missing["detail"])
