"""Install, rail init, the init task, doctor, the SessionStart hook and rail ci (plan, sections 11, 14 and 15)."""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from railtest import CONFIG, RAIL, Fixture, RailTest, ticket  # noqa: E402

FRAMEWORK = os.path.dirname(os.path.dirname(RAIL))


def read(path):
    with open(path) as f:
        return f.read()


class Init(RailTest):
    def test_a_fresh_repo_gets_a_working_rail_next(self):
        root = os.path.join(self.tmp, "fresh")
        p = Fixture(root, files={}, init=False)
        for path in ("ARCHITECTURE.md", "src/calc.py", "api/handlers.py", ".gitignore"):
            os.remove(p.path(path))
        done = p.rail("init")
        self.assertEqual(done["reason"]["code"], "INITIALISED")
        for path in (".rail/engine/rail/cli.py", ".rail/bin/rail", ".rail/config.toml", ".rail/SOURCE",
                     ".rail/tickets/TEMPLATE.md", ".github/workflows/rail.yml", "AGENTS.md", ".claude/settings.json"):
            self.assertTrue(os.path.exists(p.path(path)), path)
        self.assertFalse(os.path.exists(p.path("CLAUDE.md")))
        self.assertIn(".claude/worktrees/", read(p.path(".gitignore")))
        self.assertIn(f'commit = "', read(p.path(".rail/SOURCE")))

        task = p.rail("next")
        self.assertEqual((task["reason"]["code"], task["owner"], task["action"]["kind"]), ("INIT_TASK", "agent", "agent_task"))
        self.assertIn("## Areas", task["action"]["brief"])
        p.git("add", "-A")
        p.git("commit", "--quiet", "-m", "Set up Rail")
        self.assertEqual(p.rail("next")["reason"]["code"], "NO_WORK")
        self.assertEqual(p.rail("add", p.path(".rail/tickets/TEMPLATE.md"))["ticket"], "1")

    def test_an_existing_repo_keeps_its_files_and_init_runs_again_safely(self):
        settings = {"permissions": {"allow": ["Bash(make test)"]},
                    "hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}}
        p = Fixture(os.path.join(self.tmp, "existing"), init=False, files={
            "AGENTS.md": "# Project rules\n\nUse tabs.\n",
            "CLAUDE.md": "# Claude\n\nBe brief.\n",
            ".claude/settings.json": json.dumps(settings),
            ".rail/config.toml": CONFIG,
        })
        p.git("add", "-A")
        p.git("commit", "--quiet", "-m", "existing project")
        p.git("branch", "-m", "trunk")
        done = p.rail("init")
        ran = {s["step"]: s["status"] for s in done["steps"]}
        self.assertEqual(ran[".rail/config.toml"], "not_run")
        self.assertEqual(read(p.path(".rail/config.toml")), CONFIG)
        agents = read(p.path("AGENTS.md"))
        self.assertTrue(agents.startswith("# Project rules\n\nUse tabs.\n\n## Rail\n"), agents)
        self.assertEqual(read(p.path("CLAUDE.md")), "# Claude\n\nBe brief.\n\n@AGENTS.md\n")
        merged = json.loads(read(p.path(".claude/settings.json")))
        self.assertEqual(merged["permissions"]["allow"], ["Bash(make test)"])
        commands = [h["command"] for group in merged["hooks"]["SessionStart"] for h in group["hooks"]]
        self.assertEqual(commands[0], "echo mine")
        self.assertIn('"$CLAUDE_PROJECT_DIR"/.rail/bin/rail hook session-start', commands)
        self.assertTrue(merged["sandbox"]["enabled"])

        again = p.rail("init")
        self.assertEqual({s["status"] for s in again["steps"]}, {"not_run"})
        self.assertEqual(read(p.path("AGENTS.md")), agents)

    def test_the_base_branch_comes_from_the_repo(self):
        p = Fixture(os.path.join(self.tmp, "master"), init=False)
        p.git("add", "-A")
        p.git("commit", "--quiet", "-m", "start")
        p.git("branch", "-m", "master")
        p.rail("init")
        self.assertIn('base_branch = "master"', read(p.path(".rail/config.toml")))


class Launcher(RailTest):
    def test_inside_a_project_rail_runs_the_projects_own_engine(self):
        p = self.fixture()
        p.write(".rail/bin/rail", "#!/usr/bin/env python3\nprint('{\"schema_version\": 1, \"ok\": true, \"marker\": \"project\"}')\n")
        self.assertEqual(json.loads(p.rail("next", raw=True).stdout)["marker"], "project")

    def test_outside_a_project_only_init_is_offered(self):
        empty = os.path.join(self.tmp, "empty")
        subprocess.run(["git", "init", "--quiet", empty], check=True)
        result = subprocess.run([sys.executable, RAIL, "status"], cwd=empty, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("rail init", result.stdout)

    def test_docs_can_be_read_before_init_and_no_bytecode_is_left_in_a_project(self):
        empty = os.path.join(self.tmp, "nowhere")
        os.makedirs(empty)
        result = subprocess.run([sys.executable, RAIL, "docs", "loop"], cwd=empty, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("# The loop", result.stdout)
        p = self.fixture()
        p.add(ticket())
        p.rail("next")
        self.assertEqual(p.git("status", "--porcelain", "--ignored", "--", ".rail"), "")

    def test_install_links_rail_into_local_bin(self):
        home = os.path.join(self.tmp, "home2")
        os.makedirs(home)
        result = subprocess.run([os.path.join(FRAMEWORK, "install")], capture_output=True, text=True,
                                env={**os.environ, "HOME": home, "PATH": "/usr/bin:/bin"})
        self.assertEqual(result.returncode, 0, result.stderr)
        link = os.path.join(home, ".local", "bin", "rail")
        self.assertEqual(os.path.realpath(link), os.path.realpath(RAIL))
        self.assertIn('export PATH="$HOME/.local/bin:$PATH"', result.stdout)


class Hooks(RailTest):
    def hook(self, p, session, env_file):
        env = dict(os.environ, CLAUDE_ENV_FILE=env_file)
        env.pop("CLAUDE_CODE_SESSION_ID", None)
        payload = json.dumps({"session_id": session, "cwd": p.root, "hook_event_name": "SessionStart", "source": "compact"})
        return subprocess.run([p.path(".rail", "bin", "rail"), "hook", "session-start"], input=payload,
                              capture_output=True, text=True, env=env, cwd=p.root)

    def test_session_start_puts_rail_on_path_and_shows_this_sessions_ticket(self):
        p = self.fixture()
        p.add(ticket())
        p.rail("next", session="a")
        env_file = os.path.join(self.tmp, "env")
        mine = self.hook(p, "a", env_file)
        self.assertEqual(mine.returncode, 0, mine.stderr)
        self.assertIn("Your ticket 1: Fix add (LOW, implementing), in .claude/worktrees/1.", mine.stdout)
        self.assertIn("- Check: `python3 -c", mine.stdout)
        self.assertIn("scope_paths: src/**", mine.stdout)
        self.assertEqual(read(env_file), f'export PATH="{p.path(".rail", "bin")}:$PATH"\n')
        other = self.hook(p, "b", env_file)
        self.assertIn("No ticket is claimed by this session", other.stdout)
        self.assertIn("Claimed by other sessions: 1.", other.stdout)

    def test_a_hook_never_fails_the_session(self):
        empty = os.path.join(self.tmp, "plain")
        subprocess.run(["git", "init", "--quiet", empty], check=True)
        p = self.fixture()
        result = subprocess.run([p.path(".rail", "bin", "rail"), "hook", "session-start"], input="not json",
                                capture_output=True, text=True, cwd=empty)
        self.assertEqual(result.returncode, 0)


class Doctor(RailTest):
    def test_doctor_reports_what_is_missing(self):
        p = self.fixture()
        found = {s["step"]: s for s in p.rail("doctor", expect=None)["steps"]}
        for name in ("python", "git", "hooks", "AGENTS.md", "config"):
            self.assertEqual(found[name]["result"], "pass", found[name])
        p.write("CLAUDE.local.md", "local notes\n")
        failed = p.rail("doctor", expect=3)
        self.assertEqual({s["step"]: s.get("result") for s in failed["steps"]}["CLAUDE.local.md"], "fail")
        self.assertEqual(failed["owner"], "human")


class CI(RailTest):
    def checkout(self, p, ref):
        """What the workflow does: a full clone, the PR head checked out by its SHA."""
        ci = os.path.join(self.tmp, "ci")
        subprocess.run(["git", "clone", "--quiet", p.root, ci], check=True)
        sha = p.git("rev-parse", ref).strip()
        subprocess.run(["git", "checkout", "--quiet", "--detach", sha], cwd=ci, check=True)
        return ci

    def ci(self, cwd, branch, expect):
        env = dict(os.environ, RAIL_BRANCH=branch)
        result = subprocess.run([os.path.join(cwd, ".rail", "bin", "rail"), "ci", "--json"], cwd=cwd,
                                capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, expect, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_ci_repeats_the_ship_checks_and_fails_before_ship(self):
        p = self.fixture()
        p.add(ticket())
        p.rail("next")
        p.fix_calc("1")
        p.git("add", "-A", cwd=p.worktree("1"))
        p.git("commit", "--quiet", "-m", "1: fix", cwd=p.worktree("1"))
        early = self.ci(self.checkout(p, "1-fix-add"), "1-fix-add", expect=3)
        self.assertEqual(early["steps"][0]["detail"], "not shipped yet")
        subprocess.run(["rm", "-rf", os.path.join(self.tmp, "ci")], check=True)

        p.rail("advance", "1")
        passed = self.ci(self.checkout(p, "1-fix-add"), "1-fix-add", expect=0)
        self.assertEqual(passed["reason"]["code"], "CI_PASS")
        self.assertEqual([s["step"] for s in passed["steps"]],
                         ["shipped", "ticket-lint", "assumptions", "scope", "rules", "size", "doc-lint", "verify", "checks"])

    def test_a_pr_with_no_ticket_gets_verify_and_its_tier(self):
        p = self.fixture()
        p.git("checkout", "--quiet", "-b", "dependabot/bump")
        p.write(".claude/settings.json", "{}\n")
        p.git("commit", "--quiet", "-am", "bump")
        result = self.ci(self.checkout(p, "dependabot/bump"), "dependabot/bump", expect=0)
        self.assertEqual((result["reason"]["code"], result["tier"]), ("CI_NO_TICKET", "HIGH"))
        self.assertEqual(result["steps"][0]["step"], "verify")
