"""`forge`: the engine's only way to talk to GitHub, through `gh api` REST calls (plan, section 11).

`gh pr` and `gh issue` use GraphQL, which Claude Code cloud sessions block, so they are never used.
"""

import json
import re
import subprocess

from . import gitx

LABELS = {
    "rail": ("0e8a16", "Rail: an issue for rail intake to turn into a ticket"),
    "rail:go": ("1d76db", "Rail: a person approves or continues this ticket"),
    "rail:needs-you": ("d93f0b", "Rail: this ticket waits for a person"),
}


class ForgeError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def github_repo(project):
    """'owner/name' from the origin remote's URL, or None when it isn't on GitHub."""
    url = gitx.git(["config", "--get", f"remote.{project.remote}.url"], project.root, check=False).stdout.strip()
    m = re.match(r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def api(method, path, body=None):
    """One REST call. Returns the decoded JSON, or None for an empty body. Raises ForgeError.

    Lists are read one page of 100, which is enough for labels, check runs and a ticket's comments.
    """
    args = ["gh", "api", "--method", method, path, "-H", "Accept: application/vnd.github+json", "--include"]
    if body is not None:
        args += ["--input", "-"]
    try:
        result = subprocess.run(args, input=json.dumps(body) if body is not None else None,
                                capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise ForgeError(None, f"gh api {path}: {e}")
    head, _, payload = result.stdout.partition("\r\n\r\n") if "\r\n\r\n" in result.stdout else result.stdout.partition("\n\n")
    m = re.match(r"HTTP/[\d.]+ (\d+)", head)
    status = int(m.group(1)) if m else None
    if result.returncode != 0 or (status and status >= 400):
        message = payload.strip() or result.stderr.strip()
        try:
            message = json.loads(payload).get("message", message)
        except ValueError:
            pass
        raise ForgeError(status, f"gh api {method} {path}: {status or ''} {message}".strip())
    payload = payload.strip()
    return json.loads(payload) if payload else None


def doctor_checks(project, repo):
    """[(name, passed or None, detail)] for the GitHub side of the setup (plan, sections 11 and 14)."""
    found = []
    try:
        info = api("GET", f"repos/{repo}")
    except ForgeError as e:
        return [("gh", False, f"gh can't read {repo}: {e}. Log in with gh auth login")]
    found.append(("gh", True, f"gh reads {repo}"))
    squash_only = (info.get("allow_squash_merge") and not info.get("allow_merge_commit")
                   and not info.get("allow_rebase_merge"))
    message = info.get("squash_merge_commit_title") == "PR_TITLE" and info.get("squash_merge_commit_message") == "PR_BODY"
    found.append(("squash merging", bool(squash_only and message),
                  "squash only, with the PR title and description" if squash_only and message else
                  "in Settings > General > Pull Requests allow squash merging only, with 'Pull request title and "
                  "description' as the default message"))
    base = project.base
    contexts = set()
    try:
        for rule in api("GET", f"repos/{repo}/rules/branches/{base}") or []:
            if rule.get("type") == "required_status_checks":
                contexts |= {c.get("context") for c in rule.get("parameters", {}).get("required_status_checks", [])}
    except ForgeError:
        pass
    try:
        protection = api("GET", f"repos/{repo}/branches/{base}/protection/required_status_checks") or {}
        contexts |= set(protection.get("contexts", []))
        contexts |= {c.get("context") for c in protection.get("checks", [])}
    except ForgeError:
        pass
    found.append(("required check", "rail" in contexts,
                  f"rail is required on {base}" if "rail" in contexts else
                  f"make the rail check required on {base} (a ruleset or branch protection)"))
    try:
        names = {label["name"] for label in api("GET", f"repos/{repo}/labels?per_page=100") or []}
    except ForgeError as e:
        names = set()
        found.append(("labels", False, str(e)))
        return found
    missing = [name for name in LABELS if name not in names]
    found.append(("labels", not missing, "rail, rail:go and rail:needs-you exist" if not missing
                  else f"missing labels: {', '.join(missing)}; rail init creates them"))
    return found


def create_labels(repo):
    """Create the three labels that are missing. Returns the names created."""
    names = {label["name"] for label in api("GET", f"repos/{repo}/labels?per_page=100") or []}
    created = []
    for name, (color, description) in LABELS.items():
        if name not in names:
            api("POST", f"repos/{repo}/labels", {"name": name, "color": color, "description": description})
            created.append(name)
    return created
