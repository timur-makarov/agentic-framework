"""The first-match table: for one ticket's facts, the first matching row names the next legal move.

Rows whose code is in TRANSITIONS are moves `next` makes itself (accepting an auto tier, claiming,
resuming); `next` makes the move, derives the facts again, and reads the table once more.
"""

from .project import ticket_path

TRANSITIONS = {"ACCEPT_AUTO", "CLAIM", "RESUME"}


def _join(items):
    return ", ".join(items)


def _done_contract(f):
    return f.ticket.sections.get("Done Contract", "") if f.ticket else ""


def _implement(f):
    out_of_scope = f.ticket.sections.get("Out of scope", "")
    lines = [
        f"Implement ticket {f.id}: {f.ticket.title}",
        f"Work in {f.cwd}, on branch {f.t.branch}. The ticket is {ticket_path(f.id)}.",
        "", "Done Contract:", _done_contract(f), "",
        f"Change only paths inside scope_paths: {_join(f.ticket.scope)}.",
    ]
    if out_of_scope:
        lines += ["Out of scope:", out_of_scope]
    lines += [
        "Before you ship, write \"## Look at\" in the ticket: what a reader of this change should check.",
        f"When the Done Contract holds, run: rail advance {f.id}",
    ]
    return "\n".join(lines)


def _assumptions(f):
    rows = "\n".join(f"- {r}" for r in f.open_assumptions)
    return (f"Ticket {f.id} has open ASSUMED rows. Verify each one in the code or the docs before you implement,"
            f" then change \"ASSUMED:\" to \"VERIFIED:\" in {ticket_path(f.id)} and say how you checked."
            f" If you can't verify one, ask the person and stop.\n{rows}\nWork in {f.cwd}.")


def _step_failed(f):
    e = f.last_fail
    return (f"The last ship of ticket {f.id} failed at '{e.get('step')}': {e.get('detail', '')}. Nothing has changed"
            f" since. Fix the cause in {f.cwd}, then run: rail advance {f.id}")


def _setup_failed(f):
    return (f"setup failed in {f.cwd}: {f.setup_failed.get('detail', '')}. Fix the cause, then run"
            f" rail next --ticket {f.id} to run setup again.")


ROWS = [
    # (code,               owner,   kind,          when,                                         brief)
    ("MERGED",             "none",  "rest",        lambda f: f.state == "merged",
     lambda f: f"Ticket {f.id} is merged."),
    ("DROPPED",            "none",  "rest",        lambda f: f.state == "dropped",
     lambda f: f"Ticket {f.id} was dropped."),
    ("TICKET_LINT",        "agent", "agent_task",  lambda f: f.state == "new" and f.lint_errors,
     lambda f: f"Ticket {f.id} fails ticket lint: {'; '.join(f.lint_errors)}. Fix {ticket_path(f.id)} on branch"
               f" {f.t.name} and commit it there."),
    ("ACCEPT_AUTO",        "agent", "script",      lambda f: f.state == "new" and f.auto,
     lambda f: f"rail next --ticket {f.id}"),
    ("APPROVE_CONTRACT",   "human", "human_wait",  lambda f: f.state == "new",
     lambda f: f"Approve the contract of ticket {f.id} ({f.tier}): read {ticket_path(f.id)} on branch {f.t.name},"
               f" then run: rail accept {f.id}. To change it, say what to change. To reject it, run: rail drop {f.id}"),
    ("WAITING_AFTER",      "none",  "rest",        lambda f: f.state == "accepted" and f.after_open,
     lambda f: f"Ticket {f.id} waits for ticket {_join(f.after_open)} to merge."),
    ("SCOPE_OVERLAP",      "none",  "rest",        lambda f: f.state == "accepted" and f.overlaps,
     lambda f: f"Ticket {f.id} can't be claimed while ticket {_join(f.overlaps)} changes the same paths."),
    ("CLAIM",              "agent", "script",      lambda f: f.state == "accepted",
     lambda f: f"rail next --ticket {f.id}"),
    ("CLAIMED_ELSEWHERE",  "none",  "rest",        lambda f: f.claimed_elsewhere and not f.explicit,
     lambda f: f"Ticket {f.id} is claimed by another session. To take it over: rail next --ticket {f.id}"),
    ("RESUME",             "agent", "script",      lambda f: f.claimed_elsewhere or not f.worktree,
     lambda f: f"rail next --ticket {f.id}"),
    ("SETUP_FAILED",       "agent", "agent_task",  lambda f: f.state == "implementing" and f.setup_failed,
     _setup_failed),
    ("VERIFY_ASSUMPTIONS", "agent", "agent_task",  lambda f: f.state == "implementing" and f.open_assumptions,
     _assumptions),
    ("STEP_FAILED",        "agent", "agent_task",  lambda f: f.state == "implementing" and f.last_fail and not f.dirty,
     _step_failed),
    ("IMPLEMENT",          "agent", "agent_task",  lambda f: f.state == "implementing",
     _implement),
    ("REVIEW_UNAVAILABLE", "none",  "rest",        lambda f: f.state == "reviewing",
     lambda f: f"Ticket {f.id} ({f.tier}) needs a review, and the reviewer isn't built yet (Phase 3)."),
    ("CI_UNAVAILABLE",     "none",  "rest",        lambda f: f.state == "in-ci",
     lambda f: f"Ticket {f.id} shipped. CI and the merge go through the forge, which isn't built yet (Phase 5)."),
    ("MERGE",              "agent", "script",      lambda f: f.state == "merge-ready" and f.auto,
     lambda f: f"rail advance {f.id}"),
    ("MERGE_BY_PERSON",    "human", "human_wait",  lambda f: f.state == "merge-ready",
     lambda f: f"Ticket {f.id} ({f.tier}) is ready to merge, and a person merges it."),
]


def first_match(f):
    """(code, owner, action) for the first row that matches."""
    for code, owner, kind, when, brief in ROWS:
        if when(f):
            action = {"kind": kind, "brief": brief(f)}
            if kind == "script":
                action["command"] = action["brief"]
            return code, owner, action
    raise AssertionError(f"no row matches ticket {f.id} in state {f.state}")
