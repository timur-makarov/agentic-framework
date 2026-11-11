"""Test harness: throwaway fixture projects driven through the real `rail` launcher."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin", "rail")

FAKE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_reviewer.py")

CONFIG = f"""\
[commands]
verify = "python3 -m py_compile src/calc.py"
timeout_secs = 60

[review]
command = "python3 {FAKE}"

[consult]
command = "python3 {FAKE} --consult"
"""

ARCHITECTURE = """\
# Architecture

## Areas
| Area | Paths | Holds |
|---|---|---|
| calc | src/** | the calculator |
| api | api/** | public HTTP handlers |
"""


CHECK_ADD = "python3 -c \"import sys; sys.path.insert(0, 'src'); import calc; assert calc.add(2, 3) == 5\""


def ticket(title="Fix add", tier="LOW", scope=("src/**",), check=CHECK_ADD, front=(), body=""):
    """A ticket file in the plan's format (section 5)."""
    scope_list = ", ".join(f'"{s}"' for s in scope)
    lines = ["+++", f'title = "{title}"', f'tier = "{tier}"', f"scope_paths = [{scope_list}]", *front, "+++", "",
             "## Why", "add subtracts instead of adding.", "",
             "## Done Contract", f"- Check: `{check}`", ""]
    return "\n".join(lines) + body


class Fixture:
    """A git project set up with `rail init`, with a test config and a tiny calculator.

    With `remote`, it is a clone of that bare repository instead.
    """

    def __init__(self, root, config=CONFIG, files=None, remote=None, init=True):
        self.root = root
        if remote:
            self.git("clone", "--quiet", remote, root, cwd=os.path.dirname(root))
            return
        os.makedirs(root)
        self.git("init", "--quiet", "-b", "main")
        defaults = {
            ".gitignore": ".claude/worktrees/\n__pycache__/\n",
            "ARCHITECTURE.md": ARCHITECTURE,
            "src/calc.py": "def add(a, b):\n    return a - b\n",
            "api/handlers.py": "def handle():\n    return 200\n",
        }
        defaults.update(files or {})
        for path, text in defaults.items():
            self.write(path, text)
        if not init:
            return
        self.rail("init")
        self.write(".rail/config.toml", config)
        self.git("add", "-A")
        self.git("commit", "--quiet", "-m", "init")

    def path(self, *parts):
        return os.path.join(self.root, *parts)

    def write(self, rel, text, base=None):
        full = os.path.join(base or self.root, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(text)

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.root, capture_output=True, text=True, check=True).stdout

    @property
    def reviews(self):
        return self.root + ".reviews.json"

    @property
    def review_log(self):
        return self.root + ".reviews.log"

    def queue_reviews(self, *responses):
        """What the stand-in reviewer answers to the next review runs, in order."""
        with open(self.reviews, "w") as f:
            json.dump(list(responses), f)

    def briefs(self):
        if not os.path.exists(self.review_log):
            return []
        with open(self.review_log) as f:
            return [json.loads(line) for line in f]

    def rail(self, *args, cwd=None, session="session-a", expect=0, raw=False):
        env = dict(os.environ)
        env.pop("RAIL_TICKET", None)
        env["CLAUDE_CODE_SESSION_ID"] = session
        env["RAIL_FAKE_REVIEWS"] = self.reviews
        env["RAIL_FAKE_LOG"] = self.review_log
        cmd = [sys.executable, RAIL, *args] + ([] if raw else ["--json"])
        result = subprocess.run(cmd, cwd=cwd or self.root, capture_output=True, text=True, env=env)
        if expect is not None and result.returncode != expect:
            raise AssertionError(f"rail {' '.join(args)} exited {result.returncode}, expected {expect}\n"
                                 f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        if raw:
            return result
        answer = json.loads(result.stdout)
        check_shape(answer)
        return answer

    def add(self, text, **kw):
        fd, path = tempfile.mkstemp(suffix=".md")
        with os.fdopen(fd, "w") as f:
            f.write(text)
        try:
            return self.rail("add", path, **kw)
        finally:
            os.unlink(path)

    def worktree(self, nn):
        return self.path(".claude", "worktrees", nn)

    def fix_calc(self, nn):
        self.write("src/calc.py", "def add(a, b):\n    return a + b\n", base=self.worktree(nn))


def check_shape(answer):
    """Every verb answers in the same shape (plan, section 6)."""
    assert answer["schema_version"] == 1, answer
    if not answer["ok"]:
        assert answer["reason"]["code"] and answer["reason"]["message"], answer
        return
    for key in ("ticket", "state", "owner", "cwd", "action", "reason", "steps"):
        assert key in answer, (key, answer)
    assert answer["owner"] in ("agent", "human", "none"), answer
    assert answer["action"]["kind"] in ("script", "agent_task", "human_wait", "rest"), answer
    for step in answer["steps"]:
        assert step["status"] in ("ran", "not_run", "unavailable"), step
        assert ("result" in step) == (step["status"] == "ran"), step


class RailTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rail-test-")
        home = os.path.join(self.tmp, "home")
        os.makedirs(home)
        gitconfig = os.path.join(home, ".gitconfig")
        with open(gitconfig, "w") as f:
            f.write("[user]\n\tname = Rail Test\n\temail = rail@example.com\n[commit]\n\tgpgsign = false\n"
                    "[init]\n\tdefaultBranch = main\n")
        self._env = {k: os.environ.get(k) for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM")}
        os.environ["GIT_CONFIG_GLOBAL"] = gitconfig
        os.environ["GIT_CONFIG_NOSYSTEM"] = "1"

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fixture(self, name="proj", **kw):
        return Fixture(os.path.join(self.tmp, name), **kw)

    def remote_pair(self):
        """A bare remote and two clones of it: a laptop and a cloud run."""
        seed = self.fixture("seed")
        bare = os.path.join(self.tmp, "remote.git")
        seed.git("clone", "--quiet", "--bare", seed.root, bare, cwd=self.tmp)
        return Fixture(os.path.join(self.tmp, "a"), remote=bare), Fixture(os.path.join(self.tmp, "b"), remote=bare)
