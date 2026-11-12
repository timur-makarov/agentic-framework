"""End-to-end railroad tests on fixture projects (plan, section 22)."""

import json
import os
import subprocess
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from railtest import ARCHITECTURE, CONFIG, RailTest, ticket


def read(path):
    with open(path) as f:
        return f.read()


def failed_step(answer):
    """(step, detail) of the step that failed. The steps after it are listed as not_run."""
    failed = [s for s in answer["steps"] if s.get("result") == "fail"]
    assert len(failed) == 1, answer["steps"]
    assert all(s["status"] == "not_run" for s in answer["steps"][answer["steps"].index(failed[0]) + 1:])
    return failed[0]["step"], failed[0].get("detail")


class AddToMerge(RailTest):
    """Phase 1's done-when: on the new core, a ticket runs from add to a local merge."""

    def test_low_ticket_runs_from_add_to_local_merge(self):
        p = self.fixture()
        added = p.add(ticket())
        self.assertEqual((added["ticket"], added["state"], added["owner"]), ("1", "accepted", "agent"))
        self.assertEqual(added["reason"]["code"], "CLAIM")
        self.assertEqual(added["branch"], "1-fix-add")

        claimed = p.rail("next")
        self.assertEqual((claimed["ticket"], claimed["state"], claimed["reason"]["code"]), ("1", "implementing", "IMPLEMENT"))
        self.assertEqual(claimed["cwd"], ".claude/worktrees/1")
        self.assertEqual(claimed["action"]["kind"], "agent_task")
        self.assertIn("rail advance 1", claimed["action"]["brief"])
        self.assertTrue(os.path.isdir(p.worktree("1")))

        failed = p.rail("advance", cwd=p.worktree("1"), expect=3)
        self.assertEqual(failed["reason"]["code"], "STEP_FAILED")
        self.assertEqual(failed_step(failed)[0], "checks")
        self.assertIn("AssertionError", failed["action"]["brief"])
        self.assertEqual(p.rail("next")["reason"]["code"], "STEP_FAILED")

        p.fix_calc("1")
        shipped = p.rail("advance", cwd=p.worktree("1"))
        self.assertEqual((shipped["state"], shipped["cwd"]), ("merge-ready", "."))
        self.assertEqual(shipped["action"], {"kind": "script", "brief": "rail advance 1", "command": "rail advance 1"})
        self.assertEqual([s["step"] for s in shipped["steps"]], ["ticket-lint", "assumptions", "scope", "rules", "size", "doc-lint", "verify", "checks"])

        merged = p.rail("advance", "1")
        self.assertEqual((merged["state"], merged["owner"], merged["reason"]["code"]), ("merged", "none", "MERGED"))

        subject, body = p.git("log", "-1", "--format=%s%x00%b", "main").split("\x00")
        self.assertEqual(subject, "1: fix add")
        self.assertIn("Ticket: 1\nTier: LOW", body)
        self.assertIn("| check: python3 -c", body)
        self.assertEqual(p.git("show", "main:src/calc.py"), "def add(a, b):\n    return a + b\n")
        self.assertEqual(read(p.path("src", "calc.py")), "def add(a, b):\n    return a + b\n")
        events = [json.loads(l)["event"] for l in p.git("show", "main:.rail/journal/1-events.jsonl").splitlines()]
        self.assertEqual(events[:2], ["accepted", "claimed"])
        self.assertEqual(events[-1], "shipped")
        self.assertFalse(os.path.exists(p.worktree("1")))
        self.assertNotIn("1-fix-add", p.git("branch"))

        self.assertEqual(p.rail("next")["reason"]["code"], "NO_WORK")
        self.assertEqual(p.rail("status")["tickets"][0]["state"], "merged")

    def test_main_checkout_with_unrelated_changes_still_merges(self):
        p = self.fixture()
        p.add(ticket())
        p.rail("next")
        p.fix_calc("1")
        p.rail("advance", "1")
        p.write("notes.txt", "my own work\n")
        self.assertEqual(p.rail("advance", "1")["state"], "merged")
        self.assertEqual(read(p.path("notes.txt")), "my own work\n")


class Ship(RailTest):
    def test_changes_outside_scope_fail_and_nothing_is_committed(self):
        p = self.fixture()
        p.add(ticket())
        p.rail("next")
        p.fix_calc("1")
        p.write("api/handlers.py", "def handle():\n    return 500\n", base=p.worktree("1"))
        failed = p.rail("advance", "1", expect=3)
        step, detail = failed_step(failed)
        self.assertEqual(step, "scope")
        self.assertIn("api/handlers.py", detail)
        self.assertEqual(p.git("log", "-1", "--format=%s", "1-fix-add").strip(), "1: ship failed")
        self.assertIn("api/handlers.py", p.git("status", "--porcelain", cwd=p.worktree("1")))

    def test_non_ascii_paths_are_in_scope(self):
        p = self.fixture(files={"café/menu.md": "# Menu\n",
                                "ARCHITECTURE.md": ARCHITECTURE + "| menu | café/** | the menu |\n"})
        p.add(ticket(scope=("src/**", "café/**")))
        p.rail("next")
        p.fix_calc("1")
        p.write("café/menu.md", "# Menu\n\nCoffee.\n", base=p.worktree("1"))
        shipped = p.rail("advance", "1")
        self.assertEqual(shipped["state"], "merge-ready")
        self.assertIn("café/**", p.rail("context", "1")["areas"][-1]["paths"])

    def test_open_assumed_row_is_verified_before_ship(self):
        p = self.fixture()
        p.add(ticket(body="\n## Assumptions\n- ASSUMED: nobody calls add with strings.\n"))
        brief = p.rail("next")
        self.assertEqual(brief["reason"]["code"], "VERIFY_ASSUMPTIONS")
        self.assertIn("nobody calls add with strings", brief["action"]["brief"])
        p.fix_calc("1")
        failed = p.rail("advance", "1", expect=3)
        self.assertEqual(failed_step(failed), ("assumptions", "1 open"))
        path = os.path.join(p.worktree("1"), ".rail", "tickets", "1.md")
        text = read(path).replace("ASSUMED: nobody", "VERIFIED: nobody")
        p.write(".rail/tickets/1.md", text, base=p.worktree("1"))
        self.assertEqual(p.rail("next")["reason"]["code"], "IMPLEMENT")
        self.assertEqual(p.rail("advance", "1")["state"], "merge-ready")

    def test_risk_path_change_raises_the_tier_at_ship(self):
        p = self.fixture(config=CONFIG + '\n[risk_paths]\nHIGH = []\nMEDIUM = ["**/*.sql"]\n')
        self.assertEqual(p.add(ticket())["tier"], "LOW")
        p.rail("next")
        p.fix_calc("1")
        p.write("src/report.sql", "select 1;\n", base=p.worktree("1"))
        shipped = p.rail("advance", "1")
        self.assertEqual((shipped["state"], shipped["tier"]), ("merge-ready", "MEDIUM"))
        self.assertEqual([s["step"] for s in shipped["steps"]][-1], "review")
        raised = [json.loads(l) for l in p.git("show", "1-fix-add:.rail/journal/1-events.jsonl").splitlines()
                  if json.loads(l)["event"] == "tier_raised"]
        self.assertEqual((raised[0]["from"], raised[0]["to"], raised[0]["reason"]), ("LOW", "MEDIUM", "risk_paths"))

    def test_migration_needs_reversibility_and_rollback(self):
        p = self.fixture(files={"db/migrations/001.sql": "create table t (id int);\n",
                                "ARCHITECTURE.md": ARCHITECTURE + "| db | db/** | schema and migrations |\n"})
        added = p.add(ticket(title="Add a column", scope=("db/**", "src/**")))
        self.assertEqual((added["tier"], added["state"], added["owner"]), ("HIGH", "new", "human"))
        p.rail("accept", "1")
        p.rail("next")
        p.fix_calc("1")
        p.write("db/migrations/002.sql", "alter table t add column c int;\n", base=p.worktree("1"))
        failed = p.rail("advance", "1", expect=3)
        self.assertEqual(failed_step(failed), ("migration", "missing reversibility, rollback"))
        path = os.path.join(p.worktree("1"), ".rail", "tickets", "1.md")
        text = read(path).replace('tier = "HIGH"', 'tier = "HIGH"\nreversibility = "expand-contract"\nrollback = "drop column c"')
        p.write(".rail/tickets/1.md", text, base=p.worktree("1"))
        ready = p.rail("advance", "1")
        self.assertEqual((ready["state"], ready["owner"], ready["reason"]["code"]), ("merge-ready", "human", "MERGE_BY_PERSON"))
        self.assertEqual([s["step"] for s in ready["steps"]][-2:], ["review", "security"])

    def test_base_moved_rebases_and_ships_again_before_merge(self):
        p = self.fixture()
        p.add(ticket())
        p.add(ticket(title="Add a status code", scope=("api/**",),
                     check="grep -q 201 api/handlers.py"))
        p.rail("next", session="a")
        p.rail("next", session="b")
        p.fix_calc("1")
        p.rail("advance", "1", session="a")
        p.write("api/handlers.py", "def handle():\n    return 201\n", base=p.worktree("2"))
        p.rail("advance", "2", session="b")
        self.assertEqual(p.rail("advance", "1", session="a")["state"], "merged")
        merged = p.rail("advance", "2", session="b")
        self.assertEqual(merged["state"], "merged")
        self.assertEqual(merged["steps"][0], {"step": "rebase", "status": "ran", "result": "pass", "detail": "onto main"})
        self.assertEqual(p.git("log", "--format=%s", "main").splitlines()[:2], ["2: add a status code", "1: fix add"])

    def test_rebase_conflict_returns_the_ticket_to_implementing(self):
        p = self.fixture()
        p.add(ticket())
        p.rail("next", session="a")
        p.fix_calc("1")
        p.rail("advance", "1", session="a")
        p.add(ticket(title="Rewrite add"))
        p.rail("next", "--ticket", "2", session="b")  # a bare next would merge ticket 1 first: it is shipped
        p.write("src/calc.py", "def add(a, b):\n    return sum((a, b))\n", base=p.worktree("2"))
        p.rail("advance", "2", session="b")
        p.rail("advance", "1", session="a")
        failed = p.rail("advance", "2", session="b", expect=3)
        self.assertEqual((failed["steps"][0]["step"], failed["steps"][0]["result"]), ("rebase", "fail"))
        self.assertIn("src/calc.py", failed["steps"][0]["detail"])
        self.assertEqual(failed["state"], "implementing")


class Claim(RailTest):
    def test_setup_runs_in_the_worktree_with_its_include_files_and_reruns_after_a_failure(self):
        setup = 'test -f .env && test "$RAIL_TICKET" = 1'
        p = self.fixture(config=CONFIG.replace("[commands]", f"[commands]\nsetup = '{setup}'"),
                         files={".worktreeinclude": ".env\n", ".gitignore": ".claude/worktrees/\n__pycache__/\n.env\n"})
        p.add(ticket())
        failed = p.rail("next", expect=3)  # setup is a step, so a failed setup exits 3
        self.assertEqual((failed["reason"]["code"], failed["steps"][0]["result"]), ("SETUP_FAILED", "fail"))
        p.write(".env", "TOKEN=local\n")
        p.write(".env", "TOKEN=local\n", base=p.worktree("1"))
        rerun = p.rail("next", "--ticket", "1")
        self.assertEqual((rerun["reason"]["code"], rerun["steps"][0]["result"]), ("IMPLEMENT", "pass"))
        p.rail("drop", "1")
        p.add(ticket(title="Fix add again"))
        self.assertEqual(p.rail("next", expect=3)["reason"]["code"], "SETUP_FAILED")  # ticket 2: RAIL_TICKET is 2
        self.assertEqual(read(os.path.join(p.worktree("2"), ".env")), "TOKEN=local\n")

    def test_a_branch_that_belongs_to_no_ticket_is_left_alone(self):
        p = self.fixture()
        p.git("branch", "7-old-experiment")
        self.assertEqual(p.rail("next")["reason"]["code"], "NO_WORK")
        self.assertIn("7-old-experiment", p.git("branch"))
        self.assertEqual(p.rail("status")["leftovers"],
                         [{"kind": "branch", "ref": "7-old-experiment", "reason": "no ticket; left for you"}])
        self.assertEqual(p.add(ticket())["ticket"], "1")


class TicketLint(RailTest):
    def test_add_rejects_a_malformed_ticket_and_takes_no_id(self):
        p = self.fixture()
        cases = {
            "vacuous Check": ticket(check="true"),
            "did you mean 'scope_paths'": ticket(front=('scope_path = ["x"]',)),
            "put the command in backticks": ticket().replace("`python3", "python3").replace("== 5\"`", "== 5\""),
            "tier must be one of": ticket(tier="URGENT"),
        }
        for needle, text in cases.items():
            with self.subTest(needle):
                failed = p.add(text, expect=3)
                self.assertEqual(failed["reason"]["code"], "TICKET_LINT")
                self.assertIn(needle, failed["action"]["brief"])
        self.assertEqual(p.git("branch", "--list", "[0-9]*"), "")
        self.assertEqual(p.add(ticket())["ticket"], "1")


class Approval(RailTest):
    def test_high_contract_waits_for_a_person_then_runs(self):
        p = self.fixture()
        added = p.add(ticket(tier="HIGH"))
        self.assertEqual((added["state"], added["owner"], added["action"]["kind"]), ("new", "human", "human_wait"))
        self.assertIn("rail accept 1", added["action"]["brief"])
        waiting = p.rail("next")
        self.assertEqual((waiting["owner"], waiting["reason"]["code"]), ("human", "WAITING_HUMAN"))
        self.assertEqual(waiting["waits"][0]["ticket"], "1")
        self.assertEqual(p.rail("advance", "1")["reason"]["code"], "APPROVE_CONTRACT")
        accepted = p.rail("accept", "1", "keep the API stable")
        self.assertEqual(accepted["state"], "accepted")
        event = json.loads(p.git("show", "1-fix-add:.rail/journal/1-events.jsonl").splitlines()[-1])
        self.assertEqual((event["by"], event["via"], event["note"]), ("person", "accept", "keep the API stable"))
        self.assertEqual(p.rail("accept", "1", expect=2)["reason"]["code"], "NOTHING_TO_ACCEPT")
        self.assertEqual(p.rail("next")["state"], "implementing")

    def test_risk_paths_raise_the_tier_at_add(self):
        p = self.fixture()
        added = p.add(ticket(scope=(".github/workflows/**",)))
        self.assertEqual((added["tier"], added["state"]), ("HIGH", "new"))


class Parallel(RailTest):
    def test_after_waits_for_the_earlier_merge(self):
        p = self.fixture()
        p.add(ticket(title="Add a status code", scope=("api/**",), check="grep -q 201 api/handlers.py"))
        p.add(ticket(front=('after = ["1"]',)))
        self.assertEqual(p.rail("next")["ticket"], "1")
        self.assertEqual(p.rail("next", "--ticket", "2", session="b")["reason"]["code"], "WAITING_AFTER")
        self.assertEqual(p.rail("next", session="b")["reason"]["code"], "NO_WORK")
        p.write("api/handlers.py", "def handle():\n    return 201\n", base=p.worktree("1"))
        p.rail("advance", "1")
        p.rail("advance", "1")
        nxt = p.rail("next", session="b")
        self.assertEqual((nxt["ticket"], nxt["state"]), ("2", "implementing"))

    def test_a_claim_starts_from_the_current_base(self):
        p = self.fixture()
        p.add(ticket(title="Add a status code", scope=("api/**",), check="grep -q 201 api/handlers.py"))
        p.add(ticket(front=('after = ["1"]',)))
        p.rail("next")
        p.write("api/handlers.py", "def handle():\n    return 201\n", base=p.worktree("1"))
        p.rail("advance", "1")
        p.rail("advance", "1")
        p.rail("next")
        self.assertIn("201", read(os.path.join(p.worktree("2"), "api", "handlers.py")))
        self.assertEqual(p.git("merge-base", "--is-ancestor", "main", "2-fix-add"), "")

    def test_a_dropped_dependency_waits_for_a_person(self):
        p = self.fixture()
        p.add(ticket(title="Add a status code", scope=("api/**",), check="grep -q 201 api/handlers.py"))
        p.add(ticket(front=('after = ["1"]',)))
        p.rail("drop", "1")
        waiting = p.rail("next")
        self.assertEqual((waiting["owner"], waiting["waits"][0]["needs"]), ("human", "AFTER_DROPPED"))

    def test_overlapping_scope_is_not_claimed_and_claims_belong_to_sessions(self):
        p = self.fixture()
        p.add(ticket())
        p.add(ticket(title="Add subtract"))
        self.assertEqual(p.rail("next", session="a")["ticket"], "1")
        other = p.rail("next", session="b")
        self.assertEqual(other["reason"]["code"], "NO_WORK")
        self.assertEqual(other["resumable"], ["1"])
        self.assertEqual(p.rail("next", "--ticket", "2", session="b")["reason"]["code"], "SCOPE_OVERLAP")
        self.assertEqual(p.rail("next", session="a")["ticket"], "1")

    def test_takeover_records_the_new_session(self):
        p = self.fixture()
        p.add(ticket())
        p.rail("next", session="a")
        taken = p.rail("next", "--ticket", "1", session="b")
        self.assertEqual(taken["reason"]["code"], "IMPLEMENT")
        claims = [json.loads(l) for l in p.git("show", "1-fix-add:.rail/journal/1-events.jsonl").splitlines()
                  if json.loads(l)["event"] == "claimed"]
        self.assertEqual([(c["session"], c["takeover"]) for c in claims], [("a", False), ("b", True)])
        self.assertEqual(p.rail("next", session="a")["resumable"], ["1"])


class Remote(RailTest):
    def test_two_clones_never_take_the_same_id_or_claim(self):
        a, b = self.remote_pair()
        results = []

        def run_both(work):
            threads = [threading.Thread(target=work, args=(fx,)) for fx in (a, b)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        def add_three(fx):
            for i in range(3):
                title = f"T{i}{os.path.basename(fx.root)}"
                results.append(fx.add(ticket(title=title, scope=(f"{title.lower()}/**",))))

        run_both(add_three)
        self.assertEqual(sorted(int(r["ticket"]) for r in results), [1, 2, 3, 4, 5, 6])
        # One counter branch holds all six IDs: a cloud session can't delete branches, so there is none per ID.
        self.assertEqual(a.git("ls-remote", "origin", "refs/heads/rail/*").split()[1::2], ["refs/heads/rail/ids"])
        a.git("fetch", "--quiet")
        self.assertEqual(a.git("log", "--format=%s", "origin/rail/ids").splitlines(),
                         [f"rail id {n}" for n in (6, 5, 4, 3, 2, 1)])  # its own small chain, apart from the project

        claims = {}
        run_both(lambda fx: claims.update({fx.root: fx.rail("next", session=os.path.basename(fx.root))}))
        claimed = [c["ticket"] for c in claims.values() if c["state"] == "implementing"]
        self.assertEqual(len(claimed), 2, claims)
        self.assertNotEqual(claimed[0], claimed[1], claims)

    def test_an_id_taken_after_our_fetch_is_refused_and_the_next_is_taken(self):
        a, b = self.remote_pair()
        b.git("config", "remote.origin.fetch", "+refs/heads/main:refs/remotes/origin/main")
        self.assertEqual(a.add(ticket())["ticket"], "1")
        self.assertEqual(b.add(ticket(title="Other", scope=("api/**",)))["ticket"], "2")
        self.assertEqual(b.git("ls-remote", "origin", "refs/heads/rail/*").count("refs/heads/rail/"), 1)

    def test_a_project_with_the_old_branch_per_id_keeps_counting_from_them(self):
        a, b = self.remote_pair()
        a.git("push", "--quiet", "origin", "main:refs/heads/rail/id/7")  # as an engine before the counter left it
        self.assertEqual(a.add(ticket())["ticket"], "8")
        self.assertEqual(b.add(ticket(title="Other", scope=("api/**",)))["ticket"], "9")

    def test_a_dropped_ticket_whose_branch_was_deleted_keeps_its_id_and_its_text(self):
        a, b = self.remote_pair()
        a.add(ticket())
        a.rail("drop", "1", "--reason", "not needed")  # with a plain git remote the engine deletes the branch too
        self.assertEqual(a.git("ls-remote", "origin", "refs/heads/1-*"), "")
        row = b.rail("status")["tickets"][0]
        self.assertEqual((row["ticket"], row["state"], row["title"]), ("1", "dropped", "Fix add"))
        self.assertEqual(b.add(ticket(title="Other", scope=("api/**",)))["ticket"], "2")  # the ID is never reused

    def test_a_claim_made_offline_after_the_base_moved_still_reaches_the_remote(self):
        a, b = self.remote_pair()
        a.add(ticket())
        b.git("commit", "--quiet", "--allow-empty", "-m", "base moves")
        b.git("push", "--quiet", "origin", "main")
        a.git("fetch", "--quiet")
        remote = os.path.join(self.tmp, "remote.git")
        os.rename(remote, remote + ".away")
        a.rail("next", session="a")  # offline: the claim rebases onto the new base and can't push
        os.rename(remote + ".away", remote)
        a.fix_calc("1")
        a.rail("advance", "1", session="a")
        self.assertEqual(a.git("rev-parse", "1-fix-add"), a.git("ls-remote", "origin", "refs/heads/1-fix-add").split()[0] + "\n")
        self.assertEqual(b.rail("status")["tickets"][0]["state"], "in-ci")

    def test_with_a_remote_ship_pushes_and_waits_for_the_forge(self):
        a, b = self.remote_pair()
        a.add(ticket())
        a.rail("next", session="a")
        a.fix_calc("1")
        shipped = a.rail("advance", "1", session="a")
        self.assertEqual((shipped["state"], shipped["reason"]["code"]), ("in-ci", "FORGE_UNAVAILABLE"))
        self.assertEqual(b.rail("status")["tickets"][0]["state"], "in-ci")
        self.assertIn("shipped", b.git("show", "origin/1-fix-add:.rail/journal/1-events.jsonl"))


class Drop(RailTest):
    def test_drop_ends_a_ticket_and_its_id_is_never_reused(self):
        p = self.fixture()
        p.add(ticket())
        p.rail("next")
        dropped = p.rail("drop", "1", "--reason", "not needed")
        self.assertEqual(dropped["state"], "dropped")
        self.assertFalse(os.path.exists(p.worktree("1")))
        self.assertEqual(p.git("branch", "--list", "1-*"), "")
        self.assertEqual(p.add(ticket(title="Fix add again"))["ticket"], "2")
        self.assertEqual([r["state"] for r in p.rail("status")["tickets"]], ["dropped", "accepted"])
        self.assertEqual(p.rail("drop", "1")["state"], "dropped")


class Reading(RailTest):
    def test_status_lists_leftovers_it_cannot_remove(self):
        p = self.fixture()
        p.add(ticket())
        p.rail("next")
        p.fix_calc("1")
        dropped = p.rail("drop", "1")
        self.assertEqual(dropped["leftovers"][0]["kind"], "worktree")
        self.assertTrue(os.path.exists(p.worktree("1")))
        self.assertEqual(p.rail("next")["leftovers"][0]["ref"], ".claude/worktrees/1")
        status = p.rail("status")
        self.assertEqual(status["leftovers"][0]["ref"], ".claude/worktrees/1")
        text = p.rail("status", raw=True).stdout
        self.assertIn("TICKET", text)
        self.assertIn("leftovers:", text)

    def test_context_returns_matching_areas_and_a_digest(self):
        p = self.fixture()
        p.add(ticket(scope=("api/**",)))
        found = p.rail("context", "1")
        self.assertEqual([a["area"] for a in found["areas"]], ["api"])
        self.assertIn("src/ (1 files)", found["digest"])
        self.assertEqual(len(p.rail("context")["areas"]), 2)


class Usage(RailTest):
    def test_usage_errors_exit_2_with_one_shape(self):
        p = self.fixture()
        self.assertEqual(p.rail("frobnicate", expect=2)["ok"], False)
        self.assertEqual(p.rail("advance", "99", expect=2)["reason"]["code"], "NO_TICKET")

    def test_unknown_config_key_fails_with_a_suggestion(self):
        p = self.fixture(config='base_brnch = "main"\n')
        failed = p.rail("status", expect=2)
        self.assertIn("did you mean 'base_branch'", failed["reason"]["message"])

    def test_outside_a_project(self):
        empty = os.path.join(self.tmp, "empty")
        os.makedirs(empty)
        subprocess.run(["git", "init", "--quiet", empty], check=True)
        p = self.fixture()
        self.assertEqual(p.rail("next", cwd=empty, expect=2)["reason"]["code"], "NOT_A_PROJECT")


if __name__ == "__main__":
    unittest.main()
