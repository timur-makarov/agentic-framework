#!/usr/bin/env python3
"""A stand-in for `gh api` in tests: a tiny GitHub over a JSON state file and the bare test remote.

It answers the REST calls the forge makes: pulls, labels, comments, issues, check runs, rulesets and the async
merge, which squash-merges in the bare repository. State: $RAIL_FAKE_GITHUB.
"""

import fcntl
import json
import os
import subprocess
import sys
from urllib.parse import parse_qs, urlparse


def git(bare, *args, input=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="GitHub", GIT_AUTHOR_EMAIL="noreply@github.com",
               GIT_COMMITTER_NAME="GitHub", GIT_COMMITTER_EMAIL="noreply@github.com")
    return subprocess.run(["git", "--git-dir", bare, *args], capture_output=True, text=True, input=input, env=env)


def head_sha(state, ref):
    return git(state["bare"], "rev-parse", "--verify", "--quiet", f"refs/heads/{ref}").stdout.strip() or None


def pr_view(state, pr):
    view = dict(pr)
    view["labels"] = [{"name": n} for n in pr["labels"]]
    sha = pr.get("frozen_sha") or head_sha(state, pr["head"])
    view["head"] = {"ref": pr["head"], "sha": sha}
    view["base"] = {"ref": pr["base"]}
    view["html_url"] = f"https://github.com/{state['repo']}/pull/{pr['number']}"
    if pr["state"] == "open" and sha:
        base = head_sha(state, pr["base"])
        if pr.get("mergeable_state"):
            view["mergeable_state"] = pr["mergeable_state"]
        elif git(state["bare"], "merge-base", "--is-ancestor", base, sha).returncode == 0:
            view["mergeable_state"] = "clean"
        elif git(state["bare"], "merge-tree", "--write-tree", base, sha).returncode != 0:
            view["mergeable_state"] = "dirty"
        else:
            view["mergeable_state"] = "behind" if state.get("require_up_to_date") else "clean"
    return view


def list_view(state, pr):
    """A pull request as GitHub's list endpoint gives it: merged_at, and no merged flag or mergeable_state."""
    view = pr_view(state, pr)
    view.pop("merged", None)
    view.pop("mergeable_state", None)
    view["merged_at"] = "2026-11-12T12:00:00Z" if pr.get("merged") else None
    return view


def respond(status, body=None):
    reason = {200: "OK", 201: "Created", 202: "Accepted", 204: "No Content", 404: "Not Found",
              405: "Method Not Allowed", 409: "Conflict", 422: "Unprocessable Entity"}.get(status, "")
    print(f"HTTP/2.0 {status} {reason}\r\nContent-Type: application/json\r\n\r\n" +
          (json.dumps(body) if body is not None else ""))
    return 0 if status < 400 else 1


def handle(state, method, path, body):
    url = urlparse(path)
    query = {k: v[0] for k, v in parse_qs(url.query).items()}
    parts = url.path.strip("/").split("/")
    if parts[:1] != ["repos"] or "/".join(parts[1:3]) != state["repo"]:
        return respond(404, {"message": "Not Found"})
    rest = parts[3:]
    state.setdefault("calls", []).append(f"{method} {'/'.join(rest)}")
    pulls, issues = state.setdefault("pulls", []), state.setdefault("issues", [])

    def find_pr(n):
        return next((p for p in pulls if p["number"] == int(n)), None)

    if not rest and method == "GET":
        return respond(200, state.get("settings", {}))
    if rest == ["labels"] and method == "GET":
        return respond(200, [{"name": n} for n in state.setdefault("labels", [])])
    if rest == ["labels"] and method == "POST":
        state["labels"].append(body["name"])
        return respond(201, {"name": body["name"]})
    if rest == ["pulls"] and method == "POST":
        if any(p["head"] == body["head"] and p["state"] == "open" for p in pulls):
            return respond(422, {"message": "A pull request already exists"})
        number = state.get("next_number", 1)
        state["next_number"] = number + 1
        pr = {"number": number, "title": body["title"], "body": body.get("body", ""), "head": body["head"],
              "base": body["base"], "state": "open", "merged": False, "labels": []}
        pulls.append(pr)
        return respond(201, pr_view(state, pr))
    if rest == ["pulls"] and method == "GET":
        found = [p for p in pulls if query.get("state", "open") in ("all", p["state"])]
        if "head" in query:
            found = [p for p in found if p["head"] == query["head"].split(":", 1)[1]]
        return respond(200, [list_view(state, p) for p in sorted(found, key=lambda p: -p["number"])])
    if len(rest) == 2 and rest[0] == "pulls":
        pr = find_pr(rest[1])
        if not pr:
            return respond(404, {"message": "Not Found"})
        if method == "PATCH":
            for key in ("title", "body", "state"):
                if key in body:
                    pr[key] = body[key]
            if pr["state"] == "closed":
                pr["frozen_sha"] = head_sha(state, pr["head"])
        return respond(200, pr_view(state, pr))
    if len(rest) == 3 and rest[0] == "pulls" and rest[2] == "merge-async" and method == "PUT":
        pr = find_pr(rest[1])
        view = pr_view(state, pr)
        if body.get("sha") and body["sha"] != view["head"]["sha"]:
            return respond(409, {"message": "Head branch was modified. Review and try the merge again."})
        if view.get("mergeable_state") == "dirty":
            return respond(405, {"message": "Pull Request is not mergeable"})
        if state.get("fail_merge"):
            return respond(405, {"message": state["fail_merge"]})
        base = head_sha(state, pr["base"])
        tree = git(state["bare"], "merge-tree", "--write-tree", base, view["head"]["sha"]).stdout.split()[0]
        commit = git(state["bare"], "commit-tree", tree, "-p", base, "-m", body.get("commit_title", pr["title"]),
                     "-m", body.get("commit_message", "")).stdout.strip()
        git(state["bare"], "update-ref", f"refs/heads/{pr['base']}", commit, base)
        if state.get("delete_branch_on_merge"):
            git(state["bare"], "update-ref", "-d", f"refs/heads/{pr['head']}")
        pr.update(state="closed", merged=True, merge_commit_sha=commit, frozen_sha=view["head"]["sha"])
        return respond(202, {"status": "pending", "details": {"message": "Merge request enqueued."}})
    if len(rest) == 3 and rest[0] == "issues" and rest[2] == "labels" and method == "POST":
        target = find_pr(rest[1]) or next(i for i in issues if i["number"] == int(rest[1]))
        target["labels"] += [n for n in body["labels"] if n not in target["labels"]]
        return respond(200, [{"name": n} for n in target["labels"]])
    if len(rest) == 4 and rest[0] == "issues" and rest[2] == "labels" and method == "DELETE":
        target = find_pr(rest[1]) or next(i for i in issues if i["number"] == int(rest[1]))
        if rest[3] not in target["labels"]:
            return respond(404, {"message": "Label does not exist"})
        target["labels"].remove(rest[3])
        return respond(200, [{"name": n} for n in target["labels"]])
    if len(rest) == 3 and rest[0] == "issues" and rest[2] == "comments":
        comments = state.setdefault("comments", {}).setdefault(rest[1], [])
        if method == "POST":
            comments.append({"body": body["body"], "user": {"login": "rail"}, "created_at": "2026-11-11T12:00:00Z"})
            return respond(201, comments[-1])
        return respond(200, comments)
    if len(rest) == 2 and rest[0] == "issues" and method == "GET":
        issue = next((i for i in issues if i["number"] == int(rest[1])), None)
        if not issue:
            return respond(404, {"message": "Not Found"})
        return respond(200, dict(issue, labels=[{"name": n} for n in issue["labels"]]))
    if rest == ["issues"] and method == "GET":
        found = [i for i in issues if i["state"] == query.get("state", "open")
                 and (not query.get("labels") or query["labels"] in i["labels"])]
        return respond(200, [dict(i, labels=[{"name": n} for n in i["labels"]]) for i in found])
    if len(rest) == 3 and rest[0] == "commits" and rest[2] == "check-runs":
        runs = state.setdefault("checks", {}).get(rest[1], [])
        return respond(200, {"total_count": len(runs), "check_runs": runs})
    if len(rest) == 4 and rest[:2] == ["actions", "jobs"] and rest[3] == "logs":
        log = state.get("logs", {}).get(rest[2])  # plain text, as GitHub sends a job's log
        print(log if log is not None else json.dumps({"message": "Not Found"}))
        return 0 if log is not None else 1
    if len(rest) == 3 and rest[0] == "rules" and rest[1] == "branches":
        required = [{"context": c} for c in state.get("required", [])]
        return respond(200, [{"type": "required_status_checks",
                              "parameters": {"required_status_checks": required}}] if required else [])
    if len(rest) == 4 and rest[0] == "branches" and rest[2:] == ["protection", "required_status_checks"]:
        return respond(404, {"message": "Branch not protected"})
    return respond(404, {"message": f"fake gh: no route for {method} {url.path}"})


def main(argv):
    if argv[:1] != ["api"]:
        print("fake gh: only `gh api` is supported", file=sys.stderr)
        return 1
    method, path, body = "GET", None, None
    i = 1
    while i < len(argv):
        a = argv[i]
        if a in ("--method", "-X"):
            method, i = argv[i + 1], i + 2
        elif a in ("-H", "--header"):
            i += 2
        elif a == "--input":
            body, i = json.loads(sys.stdin.read() or "null"), i + 2
        elif a.startswith("-"):
            i += 1
        else:
            path, i = a, i + 1
    with open(os.environ["RAIL_FAKE_GITHUB"], "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        state = json.load(f)
        code = handle(state, method, path, body or {})
        f.seek(0)
        f.truncate()
        json.dump(state, f, indent=1)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
