#!/usr/bin/env python3
"""Run the end-to-end tests on several workers: python3 tests/run.py [-j N] [-k TEXT].

Every test builds its own project in a temporary folder, so tests don't touch each other. unittest has no
parallel mode, so this splits the tests across worker processes and prints the output of any worker that
fails. `python3 -m unittest discover -s tests` still runs them one after another.
"""

import argparse
import os
import subprocess
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def ids(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from ids(item)
        else:
            yield item.id()


def main():
    parser = argparse.ArgumentParser(description="Run Rail's tests on several workers.")
    parser.add_argument("-j", "--jobs", type=int, default=2 * (os.cpu_count() or 2),
                        help="worker processes (default: twice the CPUs; the tests mostly wait on git)")
    parser.add_argument("-k", dest="text", help="run only the tests whose id contains this text")
    args = parser.parse_args()

    sys.path.insert(0, HERE)
    names = sorted(ids(unittest.defaultTestLoader.discover(HERE)))
    broken = [n for n in names if n.startswith("unittest.loader._FailedTest")]
    if broken:
        print("These test files don't import: " + ", ".join(n.rsplit(".", 1)[-1] for n in broken))
        return 1
    if args.text:
        names = [n for n in names if args.text in n]
    if not names:
        print("No tests match.")
        return 1
    jobs = max(1, min(args.jobs, len(names)))
    start = time.time()
    workers = [subprocess.Popen([sys.executable, "-m", "unittest", *names[i::jobs]], cwd=HERE, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT) for i in range(jobs)]
    failed = 0
    for worker in workers:
        output, _ = worker.communicate()
        if worker.returncode != 0:
            failed += 1
            print(output)
    took = time.time() - start
    print(f"{len(names)} tests on {jobs} workers in {took:.0f}s: " + ("OK" if not failed else f"FAILED in {failed} workers"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
