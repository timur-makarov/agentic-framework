# Rail: brief for the learning pack

Date: 2026-11-11. This is what the person who builds the learning pack needs to know about the framework. It does not design the pack: that is the owner's own system. Section numbers refer to [PLAN.md](PLAN.md), and field names come from [SPEC.md](SPEC.md). Where they differ from this file, they win.

## 1. What the pack is for

- **The framework's lessons are checks.** A mistake that could happen again ends as a test, a rule, a gate or a lint (section 13). The core handles this, and the pack doesn't.
- **The person's lessons are the pack.** They are what someone needs to understand about the project, its changes, docs and code to prompt the agent well tomorrow.
- **The owner's current idea,** as of 2026-11-06:
  - the owner already has a learning system: a desktop app, a CLI, lesson generation, sparring, and a PR to the repo after learning;
  - lessons are stored in the repo;
  - an index records whether each lesson was learnt.
- **The core builds nothing for it.** It only keeps the raw material in git, joined by ticket id.

## 2. What it must not do

- **No lesson files for the agent.** The plan removed them (section 13). A lesson the agent should follow becomes a check, a rule, or a line in the project's part of `AGENTS.md`.
- **No writes to always-loaded files.** Section 24 rules out automatic writes to `AGENTS.md`, `CLAUDE.md` or any memory the agent loads every session.
- **No change to ticket state.** A pack only adds hints (section 18). It never accepts, claims, ships or merges.
- **No writes to the journal.** Only the engine writes `.rail/journal/**`, and the guard denies edits there (section 15).
- **Nothing that blocks a merge.** The pack is not a gate.

## 3. How a pack fits in

| Part | Rule (section 18) |
|---|---|
| Folder | `.rail/packs/learning/`, with a `README.md` that names its reader and a `bin/` of commands |
| Verb | `rail learning ...` runs `.rail/packs/learning/bin/learning` |
| Settings | A `[learning]` section in `.rail/config.toml`. Unknown keys fail, so the pack declares its own |
| Language | Any |
| Events | None yet. A manifest with event subscriptions waits until a second pack needs them. Until then the pack is run on demand, or reads git when it starts |
| Reader | The person. The pack must name it, as every pack does |

- **The pack's own files** can live anywhere in the repo that isn't `.rail/tickets/**` or `.rail/journal/**`. Those two are the only non-product paths.
- **A PR from the pack is a PR with no ticket,** unless the pack makes a ticket with `rail add`. CI runs `verify` and the rules on it, and its commits count towards the sweep (section 11).
- **Lesson files count as product paths.** If a ticket's branch touches them, they count for scope, size and tier. To keep lessons out of ticket work, write them on their own branch.
- **Cloud sessions start from a fresh clone.** Anything the pack keeps outside the repo, such as a desktop app's database, isn't there. The repo copy has to be enough.

## 4. The raw material

Everything below is on the base branch after a merge.

| Material | Where | What it tells the person |
|---|---|---|
| The ticket | `.rail/tickets/NN.md` | Why the work was done, the Done Contract, scope, assumptions, and what the agent wanted looked at |
| The squash commit | One per ticket on base, subject `NN: title (#PR)` | What changed. The body is the PR description: Why, Look at, Evidence, Risk |
| Trailers | `Ticket: NN`, `Tier: ...`, `Assisted-by: ...` in that commit | The join key, the risk tier, the model |
| Events | `.rail/journal/NN-events.jsonl` | What happened in order: steps that failed and passed, retries, tier raises, waits a person continued |
| Review runs | `.rail/journal/NN-review.json` | Each finding: severity, file, claim, the check that would catch it, the evidence |
| Finding outcomes | `finding` events in the events file | How each finding ended: `fixed`, `declined` or `parked`, with who decided and why |
| Advice | `.rail/journal/NN-advice.md` | Where the agent got stuck, and what a second model said |
| Sweep summary | `.rail/journal/NN-summary.md` on a sweep ticket | What the periodic review of unreviewed work found |
| Repo map | `ARCHITECTURE.md`, `## Areas` | Which area a path belongs to |

**The three learning hooks (section 9):**

- **The join key** is the `Ticket:` trailer. `git blame` on any line reaches a commit, and that commit names its ticket.
- **The outcome labels** are `caused_by` and reverts. A fix ticket sets `caused_by` to the ticket that introduced the defect. A revert of a ticket's squash commit says the same thing more bluntly.
- **The record of belief** is the journal. It holds what the agent and the reviewer thought at the time, before the outcome was known.

## 5. How to read it

**Every merged ticket, oldest first:**

```bash
git log --reverse --format='%H %(trailers:key=Ticket,valueonly,separator=%x2C)' origin/main
```

**One ticket's commit and its diff:**

```bash
git log --grep='^Ticket: 14$' --format=%H origin/main | xargs git show
```

**The ticket behind a line of code:**

```bash
git blame -L 40,40 --porcelain auth/refresh.py | head -1
```

**Tickets that caused a later fix:**

```bash
grep -l '^caused_by = "[^"]' .rail/tickets/*.md
```

**Reverts:**

```bash
git log --grep='^Revert "' --format='%H %s' origin/main
```

**Events** are one JSON object per line. Every line has `v`, `at`, `ticket` and `event`. A reader ignores fields and events it doesn't know. The events worth a learner's attention:

| Event | Why it matters for learning |
|---|---|
| `step` with `result: "fail"` | Where the agent struggled; `detail` names the check |
| `finding` | What the reviewer caught, and whether it was fixed, declined or parked |
| `tier_raised` | The work turned out bigger or riskier than the ticket said |
| `consulted` | The agent hit the retry cap or asked for help |
| `continued` | A person stepped in; `note` holds what they said |
| `amended` | The contract changed after work began |

## 6. What isn't there

- **A dropped ticket's journal.** It goes with the branch. Only the ticket file stays reachable, through the `rail/NN` tag.
- **The author's token use.** The engine knows the cost of review and consult runs, not of the session that wrote the code.
- **The conversation.** No transcript is stored. The person's words survive only in the ticket's `## Request`, in `accept` notes and in PR comments.
- **PR comments.** They stay on GitHub. The journal keeps only the note given with `rail:go` or `accept`.
- **Waits.** No event marks the start of a wait. Its end is a `continued` or `accepted` event.
- **A list of lessons, or whether one was learnt.** That index is the pack's to define.
- **Open tickets on base.** A ticket exists only on its branch until it merges, so base shows finished work only.

## 7. Decisions left to the owner

1. **Where lessons live** in the repo, and their format.
2. **The index:** one file or one entry per lesson, and how "learnt" is recorded for more than one person.
3. **What triggers a lesson:** every merged ticket, only tickets with a `caused_by` fix or a revert, a sweep, or on demand.
4. **How the pack's PR is made:** with no ticket, or as a LOW ticket through `rail add`.
5. **What the desktop app holds** that the repo doesn't, given that cloud sessions see only the repo.
6. **Whether a lesson may propose a rule or a check.** If so, it does that by opening a ticket, never by editing `config.toml` itself.
