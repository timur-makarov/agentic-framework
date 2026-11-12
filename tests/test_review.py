"""Review, contract and retries (plan, sections 5, 7, 8, 9 and 12; SPEC). The reviewer is a stand-in (fake_reviewer.py)."""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from railtest import CONFIG, RailTest, ticket

BLOCKING = {"severity": "blocking", "file": "src/calc.py", "line": 2, "claim": "add(-1, 1) returns the wrong sign.",
            "check": "a test of add with negative numbers"}
ADVISORY = {"severity": "advisory", "file": "src/calc.py", "claim": "add has no docstring."}


def clean(summary="Read the diff, ran the check."):
    return {"summary": summary, "findings": []}


def found(*findings, summary="Read the diff, ran the check."):
    return {"summary": summary, "findings": list(findings)}


def events(p, branch, kind=None):
    rows = [json.loads(l) for l in p.git("show", f"{branch}:.rail/journal/1-events.jsonl").splitlines()]
    return [e for e in rows if kind is None or e["event"] == kind]


def review_steps(answer):
    return [s for s in answer["steps"] if s["step"] == "review"]


def read(path):
    with open(path) as f:
        return f.read()


class Review(RailTest):
    def medium(self, p, **kw):
        p.add(ticket(tier="MEDIUM", **kw))
        p.rail("next")
        p.fix_calc("1")

    def test_a_blocking_finding_is_fixed_and_the_fix_reviewed_again(self):
        p = self.fixture(files={"AGENTS.md": "# Conventions\n\nPrefer small functions.\n"})
        self.medium(p)
        p.queue_reviews(found(BLOCKING, ADVISORY), found(ADVISORY | {"repeats": "F2"}))
        failed = p.rail("advance", "1", expect=3)
        self.assertEqual((failed["state"], failed["reason"]["code"]), ("reviewing", "ANSWER_FINDINGS"))
        self.assertEqual(failed["steps"][-1]["detail"], "run 1: 1 blocking, 2 findings")
        self.assertIn("F1 (blocking, review) src/calc.py:2: add(-1, 1) returns the wrong sign.", failed["action"]["brief"])
        brief = p.briefs()[0]["brief"]
        self.assertIn("Prefer small functions.", brief)
        self.assertNotIn("rail next --json", brief)  # the ## Rail section stays out of the brief
        self.assertIn("This run's job: Review this change.", brief)
        self.assertIn("Security. This list is a checklist", brief)  # MEDIUM: the security section is in the review

        p.write("src/calc.py", "def add(a, b):\n    return b + a\n", base=p.worktree("1"))
        p.rail("answer", "1", "F1", "fixed", "Order no longer matters.")
        p.rail("answer", "1", "F2", "declined", "The project has no docstrings.")
        ready = p.rail("advance", "1")  # the re-review repeats F2: open again, and advisory, so the step passes
        self.assertEqual(ready["reason"]["code"], "ANSWER_FINDINGS")
        rereview = p.briefs()[1]["brief"]
        self.assertIn("now fixed (by author): Order no longer matters.", rereview)
        done = p.rail("answer", "1", "F2", "declined", "Still: the project has no docstrings.")
        self.assertEqual(done["state"], "merge-ready")
        doc = json.loads(p.git("show", "1-fix-add:.rail/journal/1-review.json"))
        self.assertEqual([r["role"] for r in doc["runs"]], ["review", "review"])
        self.assertNotEqual(doc["runs"][0]["patch_id"], doc["runs"][1]["patch_id"])
        self.assertEqual(doc["runs"][0]["model"], "fake-model")
        self.assertEqual(p.rail("advance", "1")["state"], "merged")
        self.assertIn("| review | ran, 2 runs by fake-model, 2 findings, all answered |", p.git("log", "-1", "--format=%b", "main"))

    def test_marking_a_blocking_finding_fixed_without_a_change_needs_a_clean_rereview(self):
        p = self.fixture()
        self.medium(p)
        p.queue_reviews(found(BLOCKING), found(BLOCKING | {"repeats": "F1"}))
        p.rail("advance", "1", expect=3)
        p.rail("answer", "1", "F1", "fixed", "Done.")
        again = p.rail("advance", "1", expect=3)
        self.assertEqual(review_steps(again)[-1]["detail"], "run 2: 1 blocking, 1 findings")
        self.assertEqual(again["reason"]["code"], "ANSWER_FINDINGS")

    def test_a_disputed_blocking_finding_goes_to_a_refuter(self):
        p = self.fixture()
        self.medium(p)
        p.queue_reviews(found(BLOCKING), clean("The sign is right: -1 + 1 is 0."))
        p.rail("advance", "1", expect=3)
        disputed = p.rail("answer", "1", "F1", "declined", "add(-1, 1) is 0, which is right.")
        self.assertEqual(disputed["reason"]["code"], "REVIEW")
        done = p.rail("advance", "1")
        self.assertEqual(done["state"], "merge-ready")
        last = events(p, "1-fix-add", "finding")[-1]
        self.assertEqual((last["outcome"], last["by"], last["reason"]), ("declined", "refuter", "The sign is right: -1 + 1 is 0."))
        refuter = p.briefs()[1]["brief"]
        self.assertIn("You are the refuter.", refuter)
        self.assertNotIn("which is right", refuter)  # it never sees the author's argument

    def test_an_upheld_finding_the_agent_still_disputes_waits_for_a_person(self):
        p = self.fixture()
        self.medium(p)
        p.queue_reviews(found(BLOCKING), found(BLOCKING | {"repeats": "F1"}, summary="It holds."))
        p.rail("advance", "1", expect=3)
        p.rail("answer", "1", "F1", "declined", "It is fine.")
        upheld = p.rail("advance", "1", expect=3)
        self.assertEqual((upheld["steps"][-1]["step"], upheld["steps"][-1]["detail"]), ("refuter", "run 2: upheld F1"))
        waiting = p.rail("answer", "1", "F1", "declined", "Still fine.")
        self.assertEqual((waiting["owner"], waiting["reason"]["code"]), ("human", "FINDING_UPHELD"))
        owner = p.rail("answer", "1", "F1", "declined", "Negative inputs never happen here.", "--owner")
        self.assertEqual(owner["state"], "merge-ready")

    def test_high_runs_the_security_seat_with_a_refuter_and_a_person_approves_the_merge(self):
        p = self.fixture()
        p.add(ticket(tier="HIGH"))
        p.rail("accept", "1")
        p.rail("next")
        p.fix_calc("1")
        leak = {"severity": "blocking", "file": "src/calc.py", "claim": "The result is logged with the user's token."}
        p.queue_reviews(clean(), found(leak), clean("Nothing is logged at all."))
        ready = p.rail("advance", "1")
        self.assertEqual([s["step"] for s in ready["steps"]][-3:], ["review", "security", "refuter"])
        self.assertEqual((ready["state"], ready["owner"], ready["reason"]["code"]), ("merge-ready", "human", "MERGE_BY_PERSON"))
        briefs = [b["brief"] for b in p.briefs()]
        self.assertIn("Security is the security seat's job", briefs[0])
        self.assertIn("You are the security seat.", briefs[1])
        approved = p.rail("accept", "1")
        self.assertEqual(approved["reason"]["code"], "MERGE")
        self.assertEqual(p.rail("advance", "1")["state"], "merged")

    def test_invalid_output_fails_the_step(self):
        p = self.fixture()
        self.medium(p)
        ghost = {"severity": "blocking", "file": "src/missing.py", "claim": "x"}
        p.queue_reviews(found(ghost), {"raw": "not json at all"})
        failed = p.rail("advance", "1", expect=3)
        self.assertIn("src/missing.py isn't a tracked file", review_steps(failed)[-1]["detail"])
        failed = p.rail("advance", "1", expect=3)
        self.assertEqual(review_steps(failed)[-1]["detail"], "invalid output: the output is not JSON")

    def test_the_worktree_is_reset_after_each_run(self):
        p = self.fixture()
        self.medium(p)
        p.queue_reviews({"touch": "scratch_test.py", **clean()})
        p.rail("advance", "1")
        self.assertEqual(p.git("status", "--porcelain", cwd=p.worktree("1")), "")

    def test_two_timeouts_wait_for_a_person(self):
        p = self.fixture(config=CONFIG.replace("timeout_secs = 60", "timeout_secs = 2"))
        self.medium(p)
        p.queue_reviews("timeout", "timeout")
        stuck = p.rail("advance", "1", expect=3)
        self.assertEqual([s.get("detail") for s in stuck["steps"] if s["step"] == "review"], ["timeout", "timeout"])
        self.assertEqual((stuck["owner"], stuck["reason"]["code"]), ("human", "STUCK_REVIEW"))
        timeouts = [e for e in events(p, "1-fix-add", "step") if e["step"] == "review"]
        self.assertEqual([e.get("counted") for e in timeouts], [False, False])
        self.assertEqual(p.rail("accept", "1", "the test server waited on stdin")["reason"]["code"], "REVIEW")


class Retry(RailTest):
    def test_at_the_budget_consult_advises_then_a_person_continues(self):
        p = self.fixture()
        p.add(ticket())
        p.rail("next")
        p.rail("advance", "1", expect=3)
        p.write("src/calc.py", "def add(a, b):\n    return a * b\n", base=p.worktree("1"))
        second = p.rail("advance", "1", expect=3)
        self.assertIn("consult says change: The check expects a + b.", second["action"]["brief"])
        consulted = events(p, "1-fix-add", "consulted")[0]
        self.assertEqual((consulted["trigger"], consulted["step"], consulted["verdict"], consulted["same_model"]),
                         ("retry_cap", "checks", "change", False))
        advice = p.git("show", "1-fix-add:.rail/journal/1-advice.md")
        self.assertIn("retry_cap at 'checks', change", advice)
        p.write("src/calc.py", "def add(a, b):\n    return a ** b\n", base=p.worktree("1"))
        capped = p.rail("advance", "1", expect=3)
        self.assertEqual((capped["owner"], capped["reason"]["code"]), ("human", "RETRY_CAP"))
        self.assertEqual(p.rail("next")["reason"]["code"], "WAITING_HUMAN")
        p.rail("accept", "1", "the check wants plain addition")
        continued = p.rail("next")
        self.assertEqual(continued["reason"]["code"], "STEP_FAILED")
        self.assertIn('A person said: "the check wants plain addition".', continued["action"]["brief"])
        p.fix_calc("1")
        self.assertEqual(p.rail("advance", "1")["state"], "merge-ready")

    def test_approving_an_amend_gives_a_fresh_budget(self):
        p = self.fixture(config=CONFIG.replace("[commands]", "[commands]").replace("timeout_secs = 60", "timeout_secs = 60")
                         .replace("[consult]", "[retry]\nbudget = 1\n\n[consult]"))
        p.add(ticket(tier="HIGH"))
        p.rail("accept", "1")
        p.rail("next")
        p.rail("advance", "1", expect=3)  # the check fails: the budget of 1 is used, consult advises
        p.rail("advance", "1", expect=3)  # the attempt after consult fails too
        self.assertEqual(p.rail("next")["reason"]["code"], "WAITING_HUMAN")
        path = os.path.join(p.worktree("1"), ".rail", "tickets", "1.md")
        p.write(".rail/tickets/1.md", read(path).replace("== 5", "== 5 and calc.add(1, 1) == 2"), base=p.worktree("1"))
        self.assertEqual(p.rail("amend", "1")["reason"]["code"], "APPROVE_AMEND")
        approved = p.rail("accept", "1")
        self.assertNotEqual(approved["owner"], "human", approved["reason"]["code"] + " " + approved["action"]["brief"][:300])

    def test_consult_on_request(self):
        p = self.fixture()
        p.add(ticket())
        p.rail("next")
        asked = p.rail("consult", "1", "Is a + b the right fix?")
        self.assertIn("consult says change", asked["advice"])
        self.assertEqual(events(p, "1-fix-add", "consulted")[0]["trigger"], "request")


class Contract(RailTest):
    def test_weakening_a_check_after_claim_fails_until_amended(self):
        """Section 20, bug 4."""
        p = self.fixture()
        p.add(ticket())
        p.rail("next")
        path = os.path.join(p.worktree("1"), ".rail", "tickets", "1.md")
        weaker = read(path).replace("assert calc.add(2, 3) == 5", "assert calc.add(0, 0) == 0")
        p.write(".rail/tickets/1.md", weaker, base=p.worktree("1"))
        failed = p.rail("advance", "1", expect=3)
        self.assertIn("differs from the accepted one; change it with rail amend 1", failed["steps"][0]["detail"])
        amended = p.rail("amend", "1")
        self.assertEqual(amended["state"], "implementing")
        record = events(p, "1-fix-add", "amended")[0]
        self.assertEqual((record["changed"], record["needs_approval"]), (["done_contract"], False))
        self.assertEqual(p.rail("advance", "1")["state"], "merge-ready")

    def test_lowering_the_tier_after_claim_fails(self):
        """Section 20, bug 3."""
        p = self.fixture()
        p.add(ticket(tier="MEDIUM"))
        p.rail("next")
        p.fix_calc("1")
        path = os.path.join(p.worktree("1"), ".rail", "tickets", "1.md")
        p.write(".rail/tickets/1.md", read(path).replace('tier = "MEDIUM"', 'tier = "LOW"'), base=p.worktree("1"))
        failed = p.rail("advance", "1", expect=3)
        self.assertIn("below the accepted MEDIUM", failed["steps"][0]["detail"])
        self.assertEqual(p.rail("amend", "1", expect=2)["reason"]["message"], "the tier can't go below the accepted MEDIUM")

    def test_a_high_done_contract_change_needs_approval_and_a_wider_scope_does_not(self):
        p = self.fixture()
        p.add(ticket(tier="HIGH"))
        p.rail("accept", "1")
        p.rail("next")
        path = os.path.join(p.worktree("1"), ".rail", "tickets", "1.md")
        p.write(".rail/tickets/1.md", read(path).replace('["src/**"]', '["src/**", "api/**"]'), base=p.worktree("1"))
        widened = p.rail("amend", "1")
        self.assertEqual(widened["reason"]["code"], "IMPLEMENT")
        self.assertEqual(events(p, "1-fix-add", "amended")[0]["added_paths"], ["api/**"])
        text = read(path).replace("== 5", "== 5 and calc.add(0, 0) == 0")
        p.write(".rail/tickets/1.md", text, base=p.worktree("1"))
        waiting = p.rail("amend", "1")
        self.assertEqual((waiting["owner"], waiting["reason"]["code"]), ("human", "APPROVE_AMEND"))
        self.assertEqual(p.rail("accept", "1")["reason"]["code"], "IMPLEMENT")


class Bugs(RailTest):
    def test_a_hand_written_review_file_is_ignored_and_the_reviewer_runs(self):
        """Section 20, bug 1."""
        p = self.fixture()
        p.add(ticket(tier="MEDIUM"))
        p.rail("next")
        p.fix_calc("1")
        fake = {"schema": "review/v1", "ticket": "1", "runs": [{"run": 1, "role": "review", "patch_id": "x", "findings": []}]}
        p.write(".rail/journal/1-review.json", json.dumps(fake), base=p.worktree("1"))
        p.rail("advance", "1")
        self.assertEqual(len(p.briefs()), 1)
        doc = json.loads(p.git("show", "1-fix-add:.rail/journal/1-review.json"))
        self.assertEqual(doc["runs"][0]["patch_id"] != "x", True)

    def test_a_commit_after_the_review_is_reviewed_again(self):
        """Section 20, bug 2."""
        p = self.fixture()
        p.add(ticket(tier="MEDIUM"))
        p.rail("next")
        p.fix_calc("1")
        self.assertEqual(p.rail("advance", "1")["state"], "merge-ready")
        p.write("src/calc.py", "def add(a, b):\n    return a + b  # changed after review\n", base=p.worktree("1"))
        p.git("commit", "--quiet", "-am", "1: sneak", cwd=p.worktree("1"))
        self.assertEqual(p.rail("next")["state"], "implementing")
        self.assertEqual(p.rail("advance", "1")["state"], "merge-ready")
        self.assertEqual(len(p.briefs()), 2)

    def test_rules_check_added_lines_even_with_color_ui_always(self):
        """Section 20, bug 5, and the default rule."""
        rules = '\n[[rules]]\nid = "no-new-suppressions"\nforbid = ["eslint-disable", "@ts-ignore", "# noqa", ".skip("]\n' \
                'fix = "Fix the cause instead of silencing the check."\n'
        p = self.fixture(config=CONFIG + rules)
        p.git("config", "color.ui", "always")
        p.add(ticket())
        p.rail("next")
        p.write("src/calc.py", "def add(a, b):\n    return a + b  # noqa\n", base=p.worktree("1"))
        failed = p.rail("advance", "1", expect=3)
        step = [s for s in failed["steps"] if s.get("result") == "fail"][0]
        self.assertEqual((step["step"], step["detail"]), ("rules", "1 broken: no-new-suppressions"))
        self.assertIn("Fix the cause instead of silencing the check.", failed["action"]["brief"])
        p.fix_calc("1")
        self.assertEqual(p.rail("advance", "1")["state"], "merge-ready")


class Shape(RailTest):
    def test_only_in_keeps_new_files_in_their_home(self):
        rule = '\n[[rules]]\nid = "migrations-home"\nfiles = "**/*.sql"\nonly_in = "db/migrations/**"\nfix = "Use make migration."\n'
        p = self.fixture(config=CONFIG + rule + '\n[risk_paths]\nHIGH = []\nMEDIUM = []\n')
        p.add(ticket(scope=("src/**",)))
        p.rail("next")
        p.fix_calc("1")
        p.write("src/schema.sql", "create table t (id int);\n", base=p.worktree("1"))
        failed = p.rail("advance", "1", expect=3)
        self.assertIn("is a new file outside db/migrations/**", failed["action"]["brief"])

    def test_over_the_size_cap_the_tier_rises_and_lockfiles_do_not_count(self):
        p = self.fixture(config=CONFIG + "\n[size]\nLOW = 10\nMEDIUM = 600\n")
        p.add(ticket())
        p.rail("next")
        p.fix_calc("1")
        p.write("src/package-lock.json", "{}\n" * 50, base=p.worktree("1"))
        p.write("src/gen.py", "x = 1\n" * 40, base=p.worktree("1"))
        p.write(".gitattributes", "src/gen.py linguist-generated\n")
        p.git("add", ".gitattributes")
        p.git("commit", "--quiet", "-m", "generated files")
        brief = p.rail("next")["action"]["brief"]
        self.assertIn("size", brief)
        p.write("src/more.py", "".join(f"x{i} = {i}\n" for i in range(12)), base=p.worktree("1"))
        shipped = p.rail("advance", "1")
        self.assertEqual(shipped["tier"], "MEDIUM")
        raised = events(p, "1-fix-add", "tier_raised")[0]
        self.assertEqual((raised["reason"], raised["to"]), ("size", "MEDIUM"))
        size = [s for s in shipped["steps"] if s["step"] == "size"][0]
        self.assertEqual(size["detail"], "size 14/10")

    def test_the_migration_brief_comes_with_a_migration_ticket(self):
        p = self.fixture(files={"db/migrations/001.sql": "create table t (id int);\n"})
        p.add(ticket(scope=("db/**", "src/**")))
        p.rail("accept", "1")
        self.assertIn("Migrations: expand, then contract.", p.rail("next")["action"]["brief"])


class CIReview(RailTest):
    def test_ci_needs_a_complete_review_for_the_patch(self):
        p = self.fixture()
        p.add(ticket(tier="MEDIUM"))
        p.rail("next")
        p.fix_calc("1")
        p.queue_reviews(found(BLOCKING))
        p.rail("advance", "1", expect=3)
        ci = os.path.join(self.tmp, "ci")
        subprocess.run(["git", "clone", "--quiet", p.root, ci], check=True)
        subprocess.run(["git", "checkout", "--quiet", "--detach", p.git("rev-parse", "1-fix-add").strip()], cwd=ci, check=True)
        result = subprocess.run([os.path.join(ci, ".rail", "bin", "rail"), "ci", "--json"], cwd=ci, capture_output=True,
                                text=True, env=dict(os.environ, RAIL_BRANCH="1-fix-add"))
        self.assertEqual(result.returncode, 3, result.stdout)
        self.assertEqual(json.loads(result.stdout)["steps"][-1]["detail"], "no complete review for this patch")


class Answer(RailTest):
    def test_a_decline_needs_a_reason_and_a_finding_must_exist(self):
        p = self.fixture()
        p.add(ticket(tier="MEDIUM"))
        p.rail("next")
        p.fix_calc("1")
        p.queue_reviews(found(ADVISORY))
        self.assertEqual(p.rail("advance", "1")["reason"]["code"], "ANSWER_FINDINGS")
        self.assertEqual(p.rail("answer", "1", "F1", "declined", expect=2)["reason"]["message"], "a decline needs a reason")
        self.assertEqual(p.rail("answer", "1", "F9", "fixed", expect=2)["reason"]["code"], "NO_FINDING")
        self.assertEqual(p.rail("answer", "1", "f1", "parked", "Old code.")["state"], "merge-ready")
