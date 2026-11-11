"""The `rail` verbs. Every verb answers in one JSON shape (plan, section 6) with --json, or as text without it.

Exit codes: 0 when the command worked (read `owner`), 2 for a usage error, 3 when a step failed.
"""

import argparse
import json
import os
import re
import sys

from . import areas, gitx, steps
from .project import Project, event, events_path, ticket_path
from .state import OPEN, derive, floor
from .table import TRANSITIONS, first_match
from .ticket import Ticket, branch_name, highest, lint, with_id
from .util import RailError, age, match_any

VERBS = ("add", "accept", "next", "advance", "status", "context", "drop")
STALE_DAYS = 3


def answer(ticket=None, state=None, owner="none", action=None, code="NO_WORK", steps_=None, cwd=None, **extra):
    result = {
        "schema_version": 1, "ok": True, "ticket": ticket, "state": state, "owner": owner, "cwd": cwd,
        "action": action or {"kind": "rest", "brief": ""}, "reason": {"code": code}, "steps": steps_ or [],
    }
    result.update(extra)
    return result


def from_facts(f, steps_=None, code=None, **extra):
    row_code, owner, action = first_match(f)
    return answer(f.id, f.state, owner, action, code or row_code, steps_, f.cwd, tier=f.tier, **extra)


# --- finding the ticket ----------------------------------------------------------


def ticket_from_cwd(project):
    cwd = os.path.realpath(os.getcwd())
    base = os.path.realpath(os.path.join(project.root, ".claude", "worktrees"))
    if cwd.startswith(base + os.sep):
        return os.path.relpath(cwd, base).split(os.sep)[0]
    head = gitx.git(["rev-parse", "--abbrev-ref", "HEAD"], cwd, check=False).stdout.strip()
    m = re.match(r"^(\d+)-", head)
    return m.group(1) if m else None


def requested(project, args):
    """--ticket, then RAIL_TICKET, then the worktree the command runs in (plan, section 6)."""
    return getattr(args, "ticket", None) or os.environ.get("RAIL_TICKET") or ticket_from_cwd(project)


def load(project):
    tickets = project.tickets()
    return tickets, derive(project, tickets)


# --- moves `next` makes itself -------------------------------------------------------


def ensure_local(project, t):
    """Make the local ticket branch, and fast-forward it to the remote one when that is ahead."""
    if t.remote_branch and project.remote:
        remote_tip = gitx.rev(f"refs/remotes/{project.remote}/{t.remote_branch}", project.root)
        if not t.branch:
            t.branch = t.remote_branch
            gitx.update_ref(project.root, f"refs/heads/{t.branch}", remote_tip, None)
        else:
            local_tip = gitx.rev(f"refs/heads/{t.branch}", project.root)
            if local_tip != remote_tip and gitx.ok(["merge-base", "--is-ancestor", local_tip, remote_tip], project.root):
                if t.worktree:
                    gitx.git(["merge", "--quiet", "--ff-only", remote_tip], t.worktree)
                else:
                    gitx.update_ref(project.root, f"refs/heads/{t.branch}", remote_tip, local_tip)
    t.ref = f"refs/heads/{t.branch}"


def claim(project, t, takeover=False):
    """A claim is a commit with the `claimed` event on the ticket branch, pushed (plan, section 5)."""
    for _ in range(3):
        ensure_local(project, t)
        before = gitx.rev(t.ref, project.root)
        claimed = event(t.id, "claimed", session=project.session, takeover=takeover)
        result = project.append_events(t, [claimed], "claim" if not takeover else "take over")
        if result != "rejected":
            return True
        # The branch moved on the remote: drop the local claim and look again.
        project.sync()
        remote_tip = gitx.rev(f"refs/remotes/{project.remote}/{t.remote_branch or t.branch}", project.root)
        gitx.update_ref(project.root, t.ref, remote_tip, gitx.rev(t.ref, project.root))
        fresh = project.tickets().get(t.id)
        if not fresh or fresh.last("claimed") or remote_tip == before:
            return False
        t.__dict__.update(fresh.__dict__)
    return False


def make_ready(project, t, run):
    """A worktree for the ticket, with setup run in it."""
    if not t.worktree:
        steps.make_worktree(project, t)
        steps.setup(project, t, run)
        if run.events:
            project.append_events(t, run.events, "setup")


def transition(project, f, code):
    """Make one of the moves the table leaves to `next`. False when another clone got there first."""
    t = f.t
    run = steps.Run(project, t)
    if code == "ACCEPT_AUTO":
        ensure_local(project, t)
        project.append_events(t, [event(t.id, "accepted", by="engine", via="lint", tier=f.tier,
                                        contract=f.ticket.contract_hash())], "accept")
    elif code == "CLAIM":
        if not claim(project, t):
            return False, run
        make_ready(project, t, run)
    elif code == "RESUME":
        ensure_local(project, t)
        if f.claimed_elsewhere and not claim(project, t, takeover=True):
            return False, run
        make_ready(project, t, run)
    return True, run


def settle(project, nn, explicit):
    """Read the table for one ticket, making the moves `next` makes itself, until a row names a move to report."""
    receipts = []
    for _ in range(6):
        tickets, facts = load(project)
        f = facts[nn]
        f.explicit = explicit
        code, owner, action = first_match(f)
        if code not in TRANSITIONS:
            return f, receipts
        done, run = transition(project, f, code)
        receipts += run.steps
        if not done:
            return None, receipts
    raise AssertionError(f"ticket {nn} did not settle")


def cleanup(project, tickets, facts):
    leftovers = []
    for nn, f in facts.items():
        if f.state in ("merged", "dropped"):
            leftovers += steps.remove_ticket(project, f.t)
    return leftovers


# --- verbs ---------------------------------------------------------------------------


def cmd_add(project, args):
    text = sys.stdin.read() if args.file == "-" else open(args.file).read()
    draft = Ticket(text)
    errors = lint(draft)
    if errors:
        return answer(owner="agent", code="TICKET_LINT",
                      action={"kind": "agent_task", "brief": "Fix the ticket, then run rail add again:\n- " + "\n- ".join(errors)},
                      steps_=[{"step": "ticket-lint", "status": "ran", "result": "fail", "detail": "; ".join(errors)}])
    project.sync()
    base_tip = gitx.rev(project.base_ref, project.root)
    if not base_tip:
        raise RailError(f"the base branch '{project.base}' has no commits yet")
    tickets = project.tickets()

    def build(nn):
        body = with_id(text, nn)
        ticket = Ticket(body)
        files = {ticket_path(nn): body}
        tier = highest(ticket.tier, floor(project, ticket.scope)[0])
        if tier in project.config["auto_tiers"]:
            accepted = event(nn, "accepted", by="engine", via="lint", tier=tier, contract=ticket.contract_hash())
            files[events_path(nn)] = json.dumps(accepted, separators=(",", ":")) + "\n"
        return gitx.commit_files(project.root, base_tip, files, f"{nn}: add ticket: {ticket.title}")

    nn, commit = project.take_id(project.max_id(tickets) + 1, build)
    branch = branch_name(Ticket(with_id(text, nn)))
    if not gitx.update_ref(project.root, f"refs/heads/{branch}", commit, None):
        raise RailError(f"branch {branch} already exists")
    pushed = project.push_branch(branch) if project.remote else None
    tickets, facts = load(project)
    f = facts[nn]
    receipts = [{"step": "ticket-lint", "status": "ran", "result": "pass"}]
    if pushed:
        receipts.append({"step": "push", "status": "ran" if pushed == "ok" else "unavailable",
                         **({"result": "pass"} if pushed == "ok" else {})})
    return from_facts(f, receipts, branch=branch)


def cmd_accept(project, args):
    project.sync()
    tickets, facts = load(project)
    nn = project.find(args.ticket or requested(project, args), tickets).id
    f = facts[nn]
    if f.state != "new":
        raise RailError(f"ticket {nn} is {f.state}; nothing waits for a person's approval", code="NOTHING_TO_ACCEPT")
    if f.lint_errors:
        raise RailError(f"ticket {nn} fails ticket lint: {'; '.join(f.lint_errors)}", code="TICKET_LINT")
    ensure_local(project, f.t)
    note = {"note": args.note} if args.note else {}
    project.append_events(f.t, [event(nn, "accepted", by="person", via="accept", tier=f.tier,
                                      contract=f.ticket.contract_hash(), **note)], "accept")
    tickets, facts = load(project)
    return from_facts(facts[nn])


def cmd_next(project, args):
    project.sync()
    tickets, facts = load(project)
    leftovers = cleanup(project, tickets, facts)
    explicit = requested(project, args)
    if explicit:
        nn = project.find(explicit, tickets).id
        f, receipts = settle(project, nn, explicit=True)
        if f is None:
            return answer(nn, None, "none", None, "CLAIMED_ELSEWHERE", receipts,
                          action={"kind": "rest", "brief": f"Another session claimed ticket {nn} first."})
        return from_facts(f, receipts, leftovers=leftovers)

    tickets, facts = load(project)
    mine = [f for f in facts.values() if f.state in OPEN and not f.claimed_elsewhere]
    fresh = [f for f in facts.values() if f.state in ("new", "accepted")]
    for candidate in mine + fresh:
        f, receipts = settle(project, candidate.id, explicit=False)
        if f is not None and first_match(f)[1] == "agent":
            return from_facts(f, receipts, leftovers=leftovers)

    tickets, facts = load(project)
    waits, resumable = [], []
    for f in facts.values():
        code, owner, action = first_match(f)
        if owner == "human":
            waits.append({"ticket": f.id, "needs": code, "brief": action["brief"]})
        elif code == "CLAIMED_ELSEWHERE":
            resumable.append(f.id)
    extra = {"waits": waits, "resumable": resumable, "leftovers": leftovers}
    if waits:
        brief = "Tickets wait for a person:\n" + "\n".join(f"- {w['ticket']}: {w['brief']}" for w in waits)
        return answer(owner="human", code="WAITING_HUMAN", action={"kind": "human_wait", "brief": brief}, **extra)
    brief = "No ticket to work on. New work starts with: rail add <ticket file>"
    if resumable:
        brief += f"\nClaimed by other sessions, resumable with rail next --ticket NN: {', '.join(resumable)}"
    return answer(code="NO_WORK", action={"kind": "rest", "brief": brief}, **extra)


def commit_work(project, f, run):
    """`advance` commits the agent's in-scope changes with the NN: prefix. Changes outside scope fail."""
    t = f.t
    changes = gitx.dirty(t.worktree, exclude=[".rail/journal"])
    if not changes:
        return True
    product = [c for c in changes if not c.startswith(".rail/tickets/")]
    outside = [c for c in product if not match_any(f.ticket.scope, c)]
    if outside:
        run.record("scope", False, f.patch_id, f"outside scope: {', '.join(outside)}",
                   output=f"These changes are outside scope_paths ({', '.join(f.ticket.scope)}):\n" + "\n".join(outside)
                          + "\nUndo them, or move them to another ticket. Nothing was committed.")
        return False
    gitx.git(["add", "-A", "--", ".", ":(exclude).rail/journal"], t.worktree)
    gitx.git(["commit", "--quiet", "-m", f"{t.id}: {f.ticket.title}"], t.worktree)
    return True


def finish(project, f, run, message):
    """Commit the run's events, push, and answer from the facts that follow."""
    t = f.t
    if run.events:
        lease = None
        if run.rebased and t.remote_branch:
            # A rebased branch replaces the pushed one; the lease makes sure nobody else pushed meanwhile.
            lease = f"{t.branch}:{gitx.rev(f'refs/remotes/{project.remote}/{t.remote_branch}', project.root)}"
        project.append_events(t, run.events, message, lease=lease)
    elif project.remote:
        project.push_branch(t.branch)
    tickets, facts = load(project)
    nf = facts[f.id]
    if run.failure:
        brief = steps.ship_failed_brief(t, run)
        return answer(f.id, nf.state, "agent", {"kind": "agent_task", "brief": brief}, "STEP_FAILED",
                      run.steps, nf.cwd, tier=nf.tier)
    return from_facts(nf, run.steps)


def cmd_advance(project, args):
    project.sync()
    tickets, facts = load(project)
    key = requested(project, args)
    if not key:
        mine = [f for f in facts.values() if f.state in OPEN and f.claimed and not f.claimed_elsewhere]
        if len(mine) != 1:
            raise RailError("which ticket? Run it in the ticket's worktree, or pass --ticket NN")
        key = mine[0].id
    f = facts[project.find(key, tickets).id]
    f.explicit = True
    run = steps.Run(project, f.t)

    if f.state == "implementing" and f.worktree and not f.claimed_elsewhere:
        if not commit_work(project, f, run):
            return finish(project, f, run, "ship failed")
        tickets, facts = load(project)
        f = facts[f.id]
        steps.ship(project, f, run)
        return finish(project, f, run, "ship" if run.ok else "ship failed")

    if f.state == "merge-ready" and f.auto and not project.remote:
        base_tip = gitx.rev(project.base_ref, project.root)
        if not gitx.ok(["merge-base", "--is-ancestor", base_tip, f.t.ref], project.root):
            # The base moved since ship: rebase and ship again before merging (plan, section 10).
            steps.ship(project, f, run)
            if not run.ok:
                return finish(project, f, run, "ship failed")
            project.append_events(f.t, run.events, "ship")
            run.events = []
            tickets, facts = load(project)
            f = facts[f.id]
            if f.state != "merge-ready":
                return from_facts(f, run.steps)
        merged = steps.merge_local(project, f, run)
        if not merged:
            return answer(f.id, f.state, "human", {"kind": "human_wait", "brief": run.failure[1]}, "MERGE_FAILED",
                          run.steps, f.cwd, tier=f.tier)
        tickets, facts = load(project)
        leftovers = steps.remove_ticket(project, facts[f.id].t)
        tickets, facts = load(project)
        return from_facts(facts[f.id], run.steps, leftovers=leftovers, merge_commit=merged)

    receipts = []
    if f.state == "reviewing":
        receipts = [{"step": "review", "status": "unavailable", "detail": "built in Phase 3"}]
    elif f.state == "in-ci":
        receipts = [{"step": "ci", "status": "unavailable", "detail": "built in Phase 5"}]
    return from_facts(f, receipts)


def cmd_status(project, args):
    project.sync()
    tickets, facts = load(project)
    rows, leftovers = [], []
    for nn, f in facts.items():
        t = f.t
        code, owner, action = first_match(f)
        last = t.events[-1]["at"] if t.events else ""
        note = ""
        if owner == "human":
            note = f"waiting: {code.lower().replace('_', ' ')}"
        elif f.state == "implementing" and not t.worktree:
            note = "STALE: no worktree found"
        elif f.state in OPEN and last and age(last).endswith("d") and int(age(last)[:-1]) >= STALE_DAYS:
            note = f"STALE: no event for {age(last)[:-1]} days"
        elif f.state in ("new", "accepted") and code in ("WAITING_AFTER", "SCOPE_OVERLAP"):
            note = action["brief"]
        if t.ticket is None and not t.merged and f.state != "dropped":
            leftovers.append({"kind": "branch", "ref": t.name, "reason": "no ticket; left for you"})
            continue
        rows.append({"ticket": nn, "title": t.ticket.title if t.ticket else "", "state": f.state, "owner": owner,
                     "tier": f.tier, "last_event": age(last), "branch": t.name, "note": note})
        if f.state in ("merged", "dropped"):
            if t.worktree:
                leftovers.append({"kind": "worktree", "ref": project.rel(t.worktree), "reason": f"ticket {nn} {f.state}"})
            if t.branch:
                leftovers.append({"kind": "branch", "ref": t.branch, "reason": f"ticket {nn} {f.state}"})
            if t.remote_branch:
                leftovers.append({"kind": "remote branch", "ref": t.remote_branch, "reason": f"ticket {nn} {f.state}"})
    return answer(code="STATUS", tickets=rows, leftovers=leftovers)


def cmd_context(project, args):
    key = args.ticket or requested(project, args)
    if key:
        tickets = project.tickets()
        t = project.find(key, tickets)
        found = areas.context(project, t.ref or project.base_ref, t.ticket.scope if t.ticket else [])
        return answer(t.id, code="CONTEXT", **found)
    return answer(code="CONTEXT", **areas.context(project, project.base_ref))


def cmd_drop(project, args):
    project.sync()
    tickets, facts = load(project)
    f = facts[project.find(args.ticket or requested(project, args), tickets).id]
    if f.state == "merged":
        raise RailError(f"ticket {f.id} is merged; follow-up work is a new ticket with caused_by", code="MERGED")
    receipts = []
    if f.state != "dropped":
        ensure_local(project, f.t)
        project.append_events(f.t, [event(f.id, "dropped", by=args.by, reason=args.reason or "")], "drop")
    if project.remote:
        receipts.append({"step": "close-pr", "status": "unavailable", "detail": "built in Phase 5"})
    tickets, facts = load(project)
    leftovers = steps.remove_ticket(project, facts[f.id].t)
    tickets, facts = load(project)
    return from_facts(facts[f.id], receipts, leftovers=leftovers)


# --- output ----------------------------------------------------------------------------


def render(result):
    if not result.get("ok"):
        return f"rail: {result['reason'].get('message')}"
    if "tickets" in result:
        lines = [f"{'TICKET':<7} {'STATE':<13} {'OWNER':<6} {'TIER':<7} {'LAST':<5} NOTE"]
        for r in result["tickets"]:
            lines.append(f"{r['ticket']:<7} {r['state']:<13} {r['owner']:<6} {r['tier']:<7} {r['last_event']:<5} {r['note']}")
        for i, l in enumerate(result.get("leftovers", [])):
            lines.append(f"{'leftovers:' if i == 0 else '':<11}{l['kind']} {l['ref']} ({l['reason']})")
        return "\n".join(lines)
    if "digest" in result:
        lines = ["## Areas"] + [f"- {a['area']} ({', '.join(a['paths'])}): {a['holds']}" for a in result["areas"]]
        if not result["architecture"]:
            lines.append("(no ARCHITECTURE.md yet)")
        return "\n".join(lines + ["", "## Directories", result["digest"]])
    head = " · ".join(str(x) for x in (
        f"ticket {result['ticket']}" if result.get("ticket") else None, result.get("state"),
        f"owner {result['owner']}", result["reason"]["code"]) if x)
    lines = [head]
    if result.get("cwd"):
        lines.append(f"cwd: {result['cwd']}")
    for s in result.get("steps", []):
        lines.append(f"  {s['step']}: {s['status']}" + (f", {s['result']}" if s.get("result") else "")
                     + (f" ({s['detail']})" if s.get("detail") else ""))
    if result["action"].get("brief"):
        lines += ["", result["action"]["brief"]]
    return "\n".join(lines)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise RailError(message)


def parser():
    p = _Parser(prog="rail", description="Keeps coding agents on the rail: what is legal next, and what counts as done.")
    sub = p.add_subparsers(dest="verb", required=True, parser_class=_Parser)

    def verb(name, help_, ticket=True):
        v = sub.add_parser(name, help=help_)
        v.add_argument("--json", action="store_true", help="answer in JSON")
        if ticket:
            v.add_argument("ticket", nargs="?", help="ticket ID or external id")
            v.add_argument("--ticket", dest="ticket_opt", help="ticket ID or external id")
        return v

    add = verb("add", "create a ticket from a ticket file", ticket=False)
    add.add_argument("file", help="the ticket file, or - for stdin")
    accept = verb("accept", "approve a ticket's contract")
    accept.add_argument("note", nargs="?", help="a note for the agent's next brief")
    verb("next", "the next legal move")
    verb("advance", "run the step the ticket's state calls for: ship, or merge")
    verb("status", "every ticket and its state", ticket=False)
    verb("context", "the ## Areas rows that match a ticket, and a directory digest")
    drop = verb("drop", "end a ticket without merging it")
    drop.add_argument("--reason", default="")
    drop.add_argument("--by", choices=("agent", "person"), default="agent")
    return p


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    as_json = "--json" in argv
    try:
        args = parser().parse_args(argv)
        if getattr(args, "ticket_opt", None):
            args.ticket = args.ticket_opt
        project = Project(os.getcwd())
        result = globals()[f"cmd_{args.verb}"](project, args)
        code = 3 if any(s.get("result") == "fail" for s in result.get("steps", [])) else 0
    except RailError as e:
        result = {"schema_version": 1, "ok": False, "reason": {"code": e.code, "message": str(e)}}
        code = 2
    print(json.dumps(result, indent=2) if as_json else render(result))
    return code
