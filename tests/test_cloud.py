"""Rail in a Claude Code cloud session (plan, section 26): provisioning, and what differs from a person's machine."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from railtest import CONFIG, RailTest, ticket


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


if __name__ == "__main__":
    import unittest
    unittest.main()
