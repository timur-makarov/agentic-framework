"""Rail in a Claude Code cloud session: provisioning, and what differs from a person's machine."""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from railtest import CONFIG, Fixture, RailTest, ticket


def read(path):
    with open(path) as f:
        return f.read()


class Provision(RailTest):
    def project(self, command=None):
        self.log = os.path.join(self.tmp, "provisioned.log")
        command = command or f"echo ran >> {self.log}"
        p = self.fixture(config=CONFIG.replace("[commands]", f'[commands]\nprovision = "{command}"'))
        self.vm = {"HOME": os.path.join(self.tmp, "vm-home")}  # the machine's own home: where the marker lives
        os.makedirs(self.vm["HOME"], exist_ok=True)
        return p

    def test_on_a_persons_own_machine_rail_installs_nothing(self):
        p = self.project()
        told = p.rail("provision", env_extra=self.vm)
        self.assertEqual((told["owner"], told["reason"]["code"]), ("human", "PROVISION_LOCAL"))
        self.assertIn(f"echo ran >> {self.log}", told["action"]["brief"])
        self.assertFalse(os.path.exists(self.log))
        self.assertEqual(p.rail("next", env_extra=self.vm)["reason"]["code"], "NO_WORK")  # and next doesn't ask for it

    def test_a_cloud_session_provisions_its_machine_once(self):
        p = self.project()
        first = p.rail("next", cloud=True, env_extra=self.vm)
        self.assertEqual((first["reason"]["code"], first["action"]["command"]), ("PROVISION", "rail provision"))
        done = p.rail("provision", cloud=True, env_extra=self.vm)
        self.assertEqual((done["reason"]["code"], done["steps"][0]["result"]), ("PROVISIONED", "pass"))
        self.assertEqual(read(self.log), "ran\n")
        self.assertEqual(p.rail("next", cloud=True, env_extra=self.vm)["reason"]["code"], "NO_WORK")
        self.assertEqual(p.rail("provision", cloud=True, env_extra=self.vm)["steps"], [])  # already done here
        self.assertEqual(read(self.log), "ran\n")

        # A new machine (an environment whose snapshot predates the project) starts without the marker.
        fresh = {"HOME": os.path.join(self.tmp, "another-vm")}
        os.makedirs(fresh["HOME"])
        self.assertEqual(p.rail("next", cloud=True, env_extra=fresh)["reason"]["code"], "PROVISION")

    def test_a_changed_provision_command_runs_again(self):
        p = self.project()
        p.rail("provision", cloud=True, env_extra=self.vm)
        text = read(p.path(".rail/config.toml")).replace("echo ran", "echo again")
        p.write(".rail/config.toml", text)
        self.assertEqual(p.rail("next", cloud=True, env_extra=self.vm)["reason"]["code"], "PROVISION")
        p.rail("provision", cloud=True, env_extra=self.vm)
        self.assertEqual(read(self.log), "ran\nagain\n")

    def test_a_failed_provision_says_what_failed(self):
        p = self.project(command="echo no such tool; exit 7")
        failed = p.rail("provision", cloud=True, env_extra=self.vm, expect=3)
        self.assertEqual(failed["reason"]["code"], "PROVISION_FAILED")
        self.assertIn("no such tool", failed["action"]["brief"])
        self.assertEqual(p.rail("next", cloud=True, env_extra=self.vm)["reason"]["code"], "PROVISION")

    def test_ci_provisions_its_runner_before_the_checks(self):
        p = self.project()
        ci = p.rail("ci", env_extra={**self.vm, "GITHUB_ACTIONS": "true", "RAIL_BRANCH": "a-persons-branch"})
        self.assertEqual([s["step"] for s in ci["steps"]][:2], ["provision", "verify"])
        self.assertEqual(read(self.log), "ran\n")
        failing = self.fixture("failing", config=CONFIG.replace("[commands]", '[commands]\nprovision = "exit 3"'))
        ci = failing.rail("ci", env_extra={"HOME": os.path.join(self.tmp, "runner-home"), "GITHUB_ACTIONS": "true",
                                           "RAIL_BRANCH": "a-persons-branch"}, expect=3)
        self.assertEqual((ci["reason"]["code"], ci["steps"][0]["step"]), ("CI_FAIL", "provision"))


class Doctor(RailTest):
    def test_in_a_cloud_session_doctor_says_what_the_environment_still_needs(self):
        p = self.fixture(config=CONFIG.replace("[commands]", '[commands]\nprovision = "true"'))
        local = {s["step"] for s in p.rail("doctor", expect=None)["steps"]}
        self.assertFalse({"cloud", "provision", "environment"} & local)  # a person's machine: none of it applies

        found = {s["step"]: s for s in p.rail("doctor", expect=None, cloud=True)["steps"]}
        self.assertEqual(found["cloud"]["result"], "pass")
        self.assertEqual(found["provision"]["result"], "fail")
        self.assertIn("rail provision", found["provision"]["detail"])
        self.assertEqual(found["environment"]["result"], "fail")
        self.assertIn("RAIL_CLOUD=1 .rail/bin/rail provision", found["environment"]["detail"])
        # No hook ran for this session id: a session with several repositories, or a project thread.
        self.assertEqual(found["session hooks"]["status"], "unavailable")

        p.rail("provision", cloud=True)
        hook = {"hook_event_name": "SessionStart", "session_id": "session-a", "cwd": p.root}
        subprocess.run([p.path(".rail", "bin", "rail"), "hook", "session-start"], input=json.dumps(hook), text=True,
                       capture_output=True, cwd=p.root, check=True)
        found = {s["step"]: s for s in p.rail("doctor", expect=None, cloud=True)["steps"]}
        self.assertEqual([found[name]["result"] for name in ("provision", "environment", "session hooks")], ["pass"] * 3)


class Machine(RailTest):
    """A cloud machine's own settings carry Rail's hooks, for the sessions that load no repository's hooks."""

    def machine(self, p):
        base = os.path.join(os.path.dirname(p.root), "machine")
        return os.path.join(base, "home"), os.path.join(base, "bin")

    def hook(self, p, name, cwd, payload=None, session="cloud-1"):
        """A machine hook as Claude Code runs it: the linked rail, from the directory the session stands in."""
        home, bin_dir = self.machine(p)
        env = dict(os.environ, HOME=home, RAIL_CLOUD="1", CLAUDE_CODE_SESSION_ID=session)
        data = {"hook_event_name": name, "session_id": session, "cwd": cwd, **(payload or {})}
        result = subprocess.run([os.path.join(bin_dir, "rail"), "hook", name, "--machine"], input=json.dumps(data),
                                capture_output=True, text=True, cwd=cwd, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def decide(self, p, command, cwd, **kw):
        out = self.hook(p, "guard", cwd, {"tool_name": "Bash", "tool_input": {"command": command}}, **kw)
        return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out.strip() else None

    def test_provision_links_rail_and_writes_the_hooks_into_the_machines_settings(self):
        p = self.fixture()
        home, bin_dir = self.machine(p)
        os.makedirs(os.path.join(home, ".claude"))
        with open(os.path.join(home, ".claude", "settings.json"), "w") as f:
            json.dump({"modelSettings": {"x": 1}, "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo theirs"}]}]}}, f)
        self.assertEqual(p.rail("next", cloud=True)["reason"]["code"], "PROVISION")  # even with no provision command
        done = p.rail("provision", cloud=True)
        self.assertEqual([(s["step"], s["result"]) for s in done["steps"]], [("machine", "pass")])
        self.assertEqual(os.path.realpath(os.path.join(bin_dir, "rail")), os.path.realpath(p.path(".rail", "bin", "rail")))
        with open(os.path.join(home, ".claude", "settings.json")) as f:
            settings = json.load(f)
        self.assertEqual(settings["modelSettings"], {"x": 1})  # what was there stays
        self.assertEqual(settings["hooks"]["Stop"][0]["hooks"][0]["command"], "echo theirs")
        commands = json.dumps(settings["hooks"])
        for name in ("session-start", "guard", "pulse", "stop"):
            self.assertIn(f"hook {name} --machine", commands)
        self.assertEqual(settings["hooks"]["PreToolUse"][0]["matcher"], "Bash")
        p.rail("provision", "--force", cloud=True)
        with open(os.path.join(home, ".claude", "settings.json")) as f:
            self.assertEqual(json.load(f), settings)  # written once
        self.assertEqual(p.rail("next", cloud=True)["reason"]["code"], "NO_WORK")

    def test_a_tickets_newer_engine_leaves_the_machine_to_the_projects_own(self):
        """The link and the hooks call the engine in the project's checkout. An older one there doesn't know them,
        and a hook that fails on every tool call would stop the session."""
        log = os.path.join(self.tmp, "provisioned.log")
        p = self.fixture(config=CONFIG.replace("[commands]", f'[commands]\nprovision = "echo ran >> {log}"'))
        home, bin_dir = self.machine(p)
        theirs = p.path(".rail", "engine", "rail", "cli.py")
        p.write(theirs, read(theirs).replace('MACHINE_SETUP = "', 'MACHINE_SETUP = "older-'))
        self.assertEqual(p.rail("next", cloud=True)["reason"]["code"], "PROVISION")  # the project's command still runs
        done = p.rail("provision", cloud=True)
        self.assertEqual([(s["step"], s["result"]) for s in done["steps"]], [("provision", "pass")])
        self.assertEqual(read(log), "ran\n")
        self.assertFalse(os.path.lexists(os.path.join(bin_dir, "rail")))
        self.assertFalse(os.path.exists(os.path.join(home, ".claude", "settings.json")))
        self.assertEqual(p.rail("next", cloud=True)["reason"]["code"], "NO_WORK")

        # Once the project's own engine is this one, provision is asked for again and sets the machine up.
        p.write(theirs, read(theirs).replace('MACHINE_SETUP = "older-', 'MACHINE_SETUP = "'))
        self.assertEqual(p.rail("next", cloud=True)["reason"]["code"], "PROVISION")
        p.rail("provision", cloud=True)
        self.assertTrue(os.path.exists(os.path.join(home, ".claude", "settings.json")))
        self.assertEqual(read(log), "ran\nran\n")

        # With no command of the project's, a different engine there leaves nothing for provision to do.
        q = self.fixture(name="other")
        theirs = q.path(".rail", "engine", "rail", "cli.py")
        q.write(theirs, read(theirs).replace('MACHINE_SETUP = "', 'MACHINE_SETUP = "older-'))
        self.assertEqual(q.rail("next", cloud=True)["reason"]["code"], "NO_WORK")
        told = q.rail("provision", cloud=True)
        self.assertEqual(told["reason"]["code"], "NO_WORK")
        self.assertIn("isn't this one", told["action"]["brief"])

    def test_above_several_repositories_the_guard_finds_the_project_a_command_runs_in(self):
        work = os.path.join(self.tmp, "work")
        os.makedirs(work)
        p = Fixture(os.path.join(work, "proj"))
        other = os.path.join(work, "other")
        subprocess.run(["git", "init", "--quiet", "-b", "main", other], check=True)
        p.rail("provision", cloud=True)
        for command in ("cd proj && git push origin main", "git -C proj push origin main", "cd proj && gh pr merge 3",
                        "cd proj && git commit --no-verify -m x", "cd $SOMEWHERE && git push origin main"):
            self.assertEqual(self.decide(p, command, work), "deny", command)
        for command in ("cd other && git push origin main", "git push origin main", "cd proj && git push origin 7-work",
                        "sudo apt-get install -y ripgrep"):
            self.assertIsNone(self.decide(p, command, work), command)
        # Where the guard loses track of the folder, the command is judged on the branch the project's own checkout
        # is on: here the base branch, where a bare push and a merge are denied.
        for command in ("cd proj; git push", "cd proj\ngit push origin", "pushd proj; git push -u origin",
                        "cd proj; git merge 9-x", "cd proj && git push", "cd proj && git merge 9-x"):
            self.assertEqual(self.decide(p, command, work), "deny", command)

    def test_the_guard_covers_a_repository_the_command_names_from_further_above(self):
        top = os.path.join(self.tmp, "m")
        os.makedirs(os.path.join(top, "work"))
        p = Fixture(os.path.join(top, "work", "repo"))
        p.rail("provision", cloud=True)
        for command in ("cd work/repo && git push origin main", f"cd {p.root} && git push -f origin 7-work",
                        "git -C work/repo push origin main", "cd work/repo && gh pr merge 3"):
            self.assertEqual(self.decide(p, command, top), "deny", command)
        for command in ("cd work && ls", "cd work/repo && git push origin 7-work", "git push origin main"):
            self.assertIsNone(self.decide(p, command, top), command)

    def test_where_the_repositorys_own_hooks_ran_the_machines_step_aside(self):
        p = self.fixture()
        p.rail("provision", cloud=True)
        self.assertEqual(self.decide(p, "git push origin main", p.root), "deny")  # a project thread: no repository hook
        start = {"hook_event_name": "SessionStart", "session_id": "cloud-1", "cwd": p.root}
        subprocess.run([p.path(".rail", "bin", "rail"), "hook", "session-start"], input=json.dumps(start), text=True,
                       capture_output=True, cwd=p.root, check=True)
        self.assertIsNone(self.decide(p, "git push origin main", p.root))  # the repository's own guard denies it
        self.assertEqual(self.hook(p, "session-start", p.root), "")

    def test_above_several_repositories_the_session_gets_its_snapshot_and_its_saves(self):
        work = os.path.join(self.tmp, "work")
        os.makedirs(work)
        p = Fixture(os.path.join(work, "proj"))
        p.rail("provision", cloud=True)
        p.add(ticket())
        p.rail("next", session="cloud-1")
        shown = self.hook(p, "session-start", work)
        self.assertIn("The repository proj/ runs on Rail. Run rail from inside it.", shown)
        self.assertIn("Your ticket 1: Fix add", shown)
        p.write("src/calc.py", "def add(a, b):\n    return a * b\n", base=p.worktree("1"))
        self.hook(p, "stop", work)
        self.assertIn("1: save work in progress [skip ci]", p.git("log", "--format=%s", "1-fix-add"))
        home, _ = self.machine(p)
        p.write("src/calc.py", "def add(a, b):\n    return a + b\n", base=p.worktree("1"))
        self.hook(p, "pulse", work)
        self.assertTrue(os.path.exists(os.path.join(home, ".cache", "rail", "pulse", "cloud-1")))
        self.assertEqual(p.git("show", "1-fix-add:src/calc.py"), "def add(a, b):\n    return a + b\n")


if __name__ == "__main__":
    import unittest
    unittest.main()
