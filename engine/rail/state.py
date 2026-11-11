"""State derivation (plan, section 7; SPEC, section 4). State is derived from git and the journal, never stored."""

import os

from . import gitx
from .project import NON_PRODUCT, ticket_path
from .ticket import TIERS, Ticket, highest, lint, rank
from .util import globs_overlap, match_any

OPEN = ("implementing", "reviewing", "in-ci", "merge-ready")  # claimed and not finished


def floor(project, scope):
    """The tier the risk and migration paths set for a scope, and why. Matched at add (plan, section 5)."""
    cfg = project.config
    if not hasattr(project, "_tracked"):
        listing = gitx.git(["ls-tree", "-r", "--name-only", project.base_ref], project.root, check=False)
        project._tracked = listing.stdout.splitlines()

    def hits(globs):
        if any(globs_overlap(s, g) for s in scope for g in globs):
            return True
        return any(match_any(scope, f) and match_any(globs, f) for f in project._tracked)

    if hits(cfg["migration_paths"]):
        return "HIGH", "migration_paths"
    if hits(cfg["risk_paths"]["HIGH"]):
        return "HIGH", "risk_paths"
    if hits(cfg["risk_paths"]["MEDIUM"]):
        return "MEDIUM", "risk_paths"
    return "LOW", None


def raised_tier(project, files):
    """The tier the changed files need, and why. Used at ship (SPEC: tier_raised)."""
    cfg = project.config
    if any(match_any(cfg["migration_paths"], f) for f in files):
        return "HIGH", "migration_paths"
    if any(match_any(cfg["risk_paths"]["HIGH"], f) for f in files):
        return "HIGH", "risk_paths"
    if any(match_any(cfg["risk_paths"]["MEDIUM"], f) for f in files):
        return "MEDIUM", "risk_paths"
    return "LOW", None


class Facts:
    """Everything the first-match table reads about one ticket."""

    def __init__(self, project, t):
        self.project, self.t, self.id = project, t, t.id
        self.ticket = t.ticket
        self.explicit = False
        self.lint_errors = lint(t.ticket, expect_id=t.id) if t.ticket else ["the ticket file is missing"]
        self.accepted = t.last("accepted")
        self.claimed = t.last("claimed")
        self.dropped_event = t.last("dropped")
        self.patch_id = None
        self.dirty = []
        self.shipped = None
        self.last_fail = None
        self.setup_failed = None
        self.after_open = []
        self.overlaps = []
        self.open_assumptions = []

        author = self.ticket.tier if self.ticket and self.ticket.tier in TIERS else "LOW"
        if self.accepted:
            raises = [e.get("to") for e in t.events if e.get("event") == "tier_raised"]
            self.tier = highest(self.accepted.get("tier"), author, *raises)
        elif self.ticket and not self.lint_errors:
            self.tier = highest(author, floor(project, self.ticket.scope)[0])
        else:
            self.tier = author
        self.auto = self.tier in project.config["auto_tiers"]
        self.state = self._state()

    @property
    def worktree(self):
        return self.t.worktree

    @property
    def cwd(self):
        return self.project.rel(self.t.worktree) if self.t.worktree else None

    @property
    def claimed_elsewhere(self):
        return bool(self.claimed) and self.claimed.get("session") != self.project.session

    @property
    def needs_review(self):
        return rank(self.tier) >= rank("MEDIUM")

    def _state(self):
        t, project = self.t, self.project
        if t.merged:
            return "merged"
        if self.dropped_event or not t.name:
            return "dropped"  # a dropped event, or the ID ref is all that is left (SPEC, section 4)
        if not self.accepted:
            return "new"
        if not self.claimed:
            return "accepted"

        self.patch_id = project.patch_id(t.ref)
        self.open_assumptions = self.ticket.open_assumptions()
        if self.worktree:
            self.dirty = gitx.dirty(self.worktree, exclude=[NON_PRODUCT[1]])
            copy = os.path.join(self.worktree, ticket_path(t.id))
            if os.path.exists(copy):  # the agent marks rows VERIFIED here before advance commits them
                with open(copy) as f:
                    self.open_assumptions = Ticket(f.read()).open_assumptions()
        steps = [e for e in t.events if e.get("event") == "step"]
        setups = [e for e in steps if e.get("step") == "setup"]
        if setups and setups[-1].get("result") == "fail":
            self.setup_failed = setups[-1]
        # The last word on the current patch: a shipped event, or a ship step that failed.
        verdicts = [e for e in t.events if e.get("patch_id") == self.patch_id and (
            e.get("event") == "shipped" or (e.get("event") == "step" and e.get("result") == "fail"
                                            and e.get("step") != "setup"))]
        if verdicts and verdicts[-1].get("event") == "shipped":
            self.shipped = verdicts[-1]
        elif verdicts:
            self.last_fail = verdicts[-1]
        if self.dirty or not self.shipped:
            return "implementing"
        if self.needs_review:
            return "reviewing"  # Phase 1: no review is ever complete; the reviewer comes in Phase 3
        if project.remote:
            return "in-ci"      # Phase 1: CI and the merge go through the forge, built in Phase 5
        return "merge-ready"


def derive(project, tickets):
    """Facts for every ticket, with the cross-ticket facts: `after` and scope overlap."""
    facts = {nn: Facts(project, t) for nn, t in tickets.items()}
    implementing = [f for f in facts.values() if f.state == "implementing"]
    for f in facts.values():
        if f.state != "accepted" or not f.ticket:
            continue
        f.after_open = [a for a in f.ticket.after if a not in facts or facts[a].state != "merged"]
        f.overlaps = [o.id for o in implementing if o.ticket and any(
            globs_overlap(a, b) for a in f.ticket.scope for b in o.ticket.scope)]
    return facts
