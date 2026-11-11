# Agentic framework: findings and rebuild recommendation

Date: 2026-11-06. Based on 9 discovery files, 37 study reports in `reports/`, and my own tests in throwaway copies. The framework itself was not changed. Section 10 covers how features plug in. A skeptical review of this document is in [REVIEW-completeness.md](REVIEW-completeness.md); its must-fix items are applied here. Explanations of the design are in [ANSWERS.md](ANSWERS.md).

**Scope rules from the owner, which override anything else here:** keep it simple. Fix what needs fixing, and handle later problems later. Include only what about 80% of workflows use. Tests stay general; edge-case tests belong to the framework's users. Measurement waits, apart from cheap data that is easy to collect. Everything must work for any language and in monorepos. A feature is either a pack or standard behaviour. No orchestrator plug-ins are built: the framework offers a clean surface, and future hosts integrate through it. Diagrams stay an open question until their shape and use are settled.

**Added 2026-11-09:** assume no attacks; everything is done by a person or checked elsewhere, so guards are mistake prevention only and no attack suites are built. The standard setup is: clone the framework and use Claude Code. Compatibility with common orchestrators is welcome but never at the cost of simplicity, and no decision is based on a host. Drop anything a person or agent can set up once in a few minutes. Recommended verdicts on every completeness item, including what "no attacks" removes from this document, are in [VERDICTS-completeness.md](VERDICTS-completeness.md) and await approval; this document is not yet changed for them.

**The lens for every change:** the framework is the layer between craft content and orchestration. Craft (how to code, design, debug) belongs in skill libraries or packs. Orchestration (starting agents, queues, dashboards, fan-out) belongs to hosts. The rail (what is legal next, what counts as done, when a person must act) is core. Every change names its layer first. This is not a product: it is built for the owner and anyone interested, on the premise that a machine should program the machine, so people stop fighting it.

Labels: **VERIFIED** means I ran it or read the code. **Reported** means a study agent read it in the repo's code and I did not recheck it. **Judgment** is my recommendation.

## 1. Verdict

Keep the idea and rebuild the machine around it.

The core held up in all 33 comparisons: one first-match table names the next legal move, scripts own state, and tickets carry a frozen contract with runnable checks. Many rival projects are larger and still lack this. Several reports use their repo as a negative control (ccpm, spec-driven-development, ship, CADRE).

Three things did not hold up:

1. **The trust model.** The framework treats local files as proof. Anything the agent's OS user can write is a claim, not evidence.
2. **The packaging.** Copy-in mixes framework, framework history and project in one tree. This is why your ADRs are hard to delete.
3. **The interface.** Text output and an overloaded exit 1 cannot be driven by an orchestrator.

Outcomes are unmeasured, here and in every studied project. That waits: the focus now is the framework itself.

The rebuild is a rewrite of the runtime, not a redesign of the workflow.

## 2. Keep, change, delete

### Keep

| Item | Why |
|---|---|
| `compute_next` as a first-match table; `next` and `advance` | Nearly every report says keep it |
| Scripts own state; state derived from files and git | ccpm, ship and CADRE history show the cost of stored or prose-owned state |
| Tickets as the unit of work, on their own branch | Fits Symphony and Archon per-issue models |
| Done Contract with runnable `Check:` commands | Rare in the field and valuable |
| Three lanes, with risk floors from paths | Keep the lanes. The tier is the highest of the author's choice and the path floors, frozen at claim |
| floor-guard, as a concept | Rewrite it (it has real bypasses, section 3). gstack's gate-diff is the model: listed, read, finding, and an honest partial result past its read cap |
| Fail-closed guards for irreversible acts | Reframed as mistake prevention, not as a boundary |
| End-to-end railroad tests | Keep them, with fixtures instead of the template's own files |

### Change

| Today | Target | Main sources |
|---|---|---|
| Bash, awk, jq, regex | Stdlib Python 3 core; no third-party dependencies. Measured with 120 synthetic tickets: `gate.sh next` 308 ms, `ticket-lint` 4.7 s; Python parses the same files in 32 ms including startup. A second run with a heavier ticket mix got 1.7 s and 27 s, so treat these as direction only. Python floor 3.11 for `tomllib` (owner decision 2026-11-09; macOS ships 3.9, so `install` stops with one line and `brew install python` fixes it). Config is `.agentic/config.toml` and ticket front matter is TOML between `+++` lines, so no custom parser is needed. Unknown keys are rejected | spec-kit, lanegate, statem, maestro |
| Copy-in tree | Engine under `.agentic/engine/`, plus `install` and `doctor`. No `upgrade` or `uninstall` (owner decision 2026-11-09): after install every file is the project's, and `.agentic/SOURCE` records the framework commit for a later manual integration | spec-kit, ownmem, ADOS |
| Dev repo equals the template | Dev repo builds `engine/` and `seed/`; a test proves a fresh project has no template history | hhamja, spec-kit |
| Text output, overloaded exit 1 | Versioned JSON on every verb, closed exit table | maestro, beads, Symphony, Archon |
| Reviewer writes a report file | Gate launches the reviewer and captures schema-valid JSON | Ruihang, disler, CADRE, lanegate |
| Contract fields mutable | Contract read from the claim commit; changes only through `amend` | repo-harness, proctor, statem, saptarshibasu |
| CI runs the PR's own scripts | CI judges with engine and policy from the base ref, in two jobs (see Trust levels) | repo-harness, proctor, Archon |
| Human sets `status: open` per ticket | `acceptance` policy, per tier | ralph, ccpm, hhamja |
| One waiting ticket freezes the checkout | Waits are per ticket | issue-orchestrator, beads |
| Findings on changed lines; free decline; reviewer barred from unchanged files | The reviewer reads anywhere and reports only what the change touches, required decline reasons, every finding id accounted for | maestro, Archon, superpowers |
| Ratchet needing a local stamp | `Check:` commands run at ship and in CI and must pass; the vacuous-check lint stays. No red-first rule: test order is craft, and a new test file fails on base for a trivial reason, so the rule proves little | owner decision 2026-11-09 |
| Regex over shell text | A short rule table; integrity checks on the diff, not the command | sondera, karanb192, rmax-ai |
| Lessons linted but barely read | No lesson files. A mistake that could recur becomes a check: a review finding with a `check` field opens a LOW "make it a check" ticket, and an escaped defect's `caused_by` fix ticket includes the check that would have caught it (owner decision 2026-11-09, ANSWERS H2) | owner |
| Local claims | Optional compare-and-swap claims in origin refs | SwarmOS, issue-orchestrator, beads |

### Delete

| Item | Reason |
|---|---|
| The two ADRs, framework `CONTEXT.md`, self-referencing `verify:` from the seed | Template history. Keep them in the dev repo |
| `tracker`, `limits.exception_max_days` | VERIFIED dead config |
| `models.*` and `model-check.sh`, unless something applies them | VERIFIED validated but never applied. "No reader, no field" |
| Local stamp ratchet | Mostly skipped, so it gives false comfort |
| Modes A and B | One review contract; the assurance value says who ran it (see Review) |
| About half the skills (Judgment) | Three tiers: railroad procedures are files printed by `next` at no always-on cost; a few model-invoked references; user-invoked skills in packs. Merge grill, interview and idea into one `grilling` primitive. Rebuild debug on mattpocock's `diagnosing-bugs`. Turn archive and postmortem into a retro sorter (a mechanical mistake becomes a check, a judgment mistake becomes a reviewer standard). Replace route and status with CLI verbs, and handoff with a derived snapshot |

Deletion test for every guard, field and step: it must name the real run it would have saved, or stand in front of an irreversible action.

## 3. What is broken today

### VERIFIED by running it in a throwaway copy

| Bug | Result |
|---|---|
| Author hand-writes the critic report | MEDIUM ticket ships |
| Commit after the critic report | Ships unreviewed |
| Lower `risk_tier` from MEDIUM to LOW after claim | Reviewer skipped |
| Weaken `Check:` after claim | Passes lint and checks |
| `color.ui=always` with a removed assertion | floor-guard reports clean |
| `gh pr merge 1 --squash` on main | Hooks allow it |
| Unclaimed write to `scripts/hooks/guard.sh`, `.claude/settings.json` | Hooks allow it |
| `python3 -c` write to `.agentic/state/` | Hooks allow it |
| `curl -d @.env` | Hooks allow it |

Also VERIFIED by reading: `agentic-gates.yml:17` checks out the PR head and runs that branch's own scripts, so a PR can edit the gate that judges it.

### Reported, not rechecked

- floor-guard reports clean on failing python3, `diff.external`, assume-unchanged, `.bak` renames, xfail.
- Unattended `blocked_by` chains cannot flow (ralph).
- Cursor rejects `ask` on `beforeReadFile` and may lack a pre-exec write event (allowlister).
- `.codex` hooks may not load in fresh workspace paths; hook firing under bypassPermissions is unconfirmed.
- `@file` mentions may skip the secret guard.
- A lost workspace can create a duplicate ticket (Symphony).
- Printed remedies can carry injected text (`gate.sh:416`, maestro comparison).

## 4. Target shape

### Layout

```text
dev repo                         installed project
  engine/   copied at install      .agentic/
  seed/     copied once              engine/     framework, the project's after install
  clients/  claude, codex, cursor    config.yml  project policy (schema-versioned)
            wiring and hooks         tickets/    project (schema-versioned)
  packs/    optional features        journal/    project
  docs/     ADRs and user docs       SOURCE      framework repo and commit installed from
                                   AGENTS.md     a section added at install
                                   .github/, .claude/, .codex/, .cursor/  from clients
                                   (state lives in the git common dir)
```

Clients are a separate kind, not packs: their whole job is harness hooks and sandbox settings, which packs may not touch. There is no `upgrade` and no override layer (owner decision 2026-11-09): after `install` every file is the project's, and a project bends the engine through HIGH tickets or forks the framework. To take changes from a newer framework, the agent clones it and diffs from the commit in `.agentic/SOURCE`, guided by the framework's `CHANGELOG.md`; that is an ordinary HIGH ticket.

Vendor the engine rather than requiring pip (Judgment). It pins the version per commit, works in every clone a host creates, and CI can read it from the base ref. A host may keep its own read-only copy outside the repo and point hooks at it with `AGENTIC_ENGINE`. Use that where the host allows it, because it stops an agent editing its own guards. Cloud agents usually cannot, so their runs stay `local` until CI. Editing the engine or hook config in a commit is already a `risk_paths` change, so it goes to HIGH and a human at merge. Pinning covers the other case: edit a guard, act, revert, all before any commit, so nothing reaches the diff. That is unlikely from an agent that is not adversarial, and the sandbox is the real control, so this is low priority.

Local state is a cache, keyed by ticket and versioned. Anything a budget or resume needs is in the ticket's journal, so state rebuilds from the pushed branch. A cloud VM is thrown away and depends on this.

### Trust levels

Every receipt states its level. Steps report `ran`, `not_run` or `unavailable`, so a skipped step can never look like a pass. The docs stop claiming more than this.

| Level | Who runs it | What it proves |
|---|---|---|
| `local` | Agent's OS user, hooks | Catches mistakes. Proves nothing against an agent that misbehaves |
| `gate` | Gate launches reviewer, captures output | The step ran, unless the agent tampered with the local process |
| `host` | An orchestrator ran the step and captured output outside the agent's reach | Same, with the agent out of the path. Claimed only when the host made the call |
| `ci` | CI runs engine and policy from base; forge branch protection | Authority. The agent has no write access |

Sandbox and CI are the boundary; hooks are fast feedback. This wording appears in at least seven reports. Hash receipts alone are not proof, and neither is any field an agent can write. The claim commit is on the agent's branch, so the contract check is `local` unless compared with a copy on base or in the tracker. `amend` needs the tier's acceptance.

**CI from base needs two jobs on GitHub** (Reported by the review, matches my understanding, not run). `pull_request` takes the workflow from the PR itself, so a PR could edit its judge. `pull_request_target` runs the base workflow but must never run PR code. So a `pull_request_target` job runs only the base engine over the PR diff as data, with a read-only token and no secrets. A plain `pull_request` job runs the project's tests with no secrets. `doctor` confirms the first is a required check, or reports `unavailable`; without branch protection, `ci` is not claimed.

**Two cases have no base to read from:** the PR that installs the framework, and any PR that changes policy or the engine. These run head policy and the receipt says `policy: head (unreviewed)`, as in gstack. HIGH acceptance applies.

### Machine contract

Every verb accepts `--json` and returns:

```json
{"schema_version": 1, "ok": true, "ticket": "12", "state": "needs_review",
 "owner": "agent", "action": {"kind": "agent_task", "profile": "reviewer",
 "brief": "...", "result_schema": "review/v1"},
 "reason": {"code": "REVIEW_MISSING", "detail": "..."}, "assurance": "gate"}
```

`owner` is one of `agent`, `human`, `tracker`, `none`. `action.kind` is one of `script`, `agent_task`, `human_wait`, `tracker_move`, `rest`. `human_wait` carries responder, question, options and `if_unanswered`. No ticket is not an error: `next` returns `rest`.

**Exit codes.** Symphony's analysis wants one exit code per outcome. Archon's wants 0 whenever work is owed, because it treats non-zero as a failed step. Both can be met the way `git diff` does it:

| Mode | Behavior |
|---|---|
| Default, and `--json` | 0 = the command worked (read `owner`), 2 = usage, 3 = step failed |
| `--exit-code` | 0 rest, 10 agent owes work, 11 human owes, 12 failed, 2 usage |

Values printed in remedies are sanitised, because `next` output is a prompt.

### Review

There is one review contract. Only the runner differs, and `assurance` records which.

1. The gate spawns `reviewer.command` in a detached worktree, using base-branch config, a reduced environment and `AGENTIC_ROLE=reviewer` so project hooks skip railroad prompts. Each client ships a default command. If no command can run, or a host runs review itself, `next` returns an `agent_task` and the result arrives through `submit-review`. That records `local` or `host`. A `local` review may reach `pr-open` but cannot satisfy `plan` acceptance.
2. It captures JSON against `review/v1`, bound to the ticket's patch (`git patch-id`) and contract hash, so a clean rebase re-runs checks instead of the review. Invalid or missing output fails closed.
3. The reviewer may read anywhere. Findings carry a severity and cover what the change touches. Existing bugs noticed on the way become `parked`.
4. Every finding ends as `fixed`, `declined` with a reason, or `parked`. A script checks that none went missing. The author cannot decline a blocking finding. A fresh refuter checks a blocking finding: it sees the location and claim, not the author's argument.
5. A retry cap stops the loop, and reaching it gives `owner: human`. Re-review covers only what changed since the last pass.

HIGH adds the security reviewer.

**Where review runs: `review.runs_in: gate | ci`.** CI cannot tell a captured review from one an agent committed, so a gate review is `gate` level at best.

- `gate` (default): the gate runs the reviewer before ship. Fast loop, works offline and with no remote. A forged MEDIUM review is caught only by a person reading the PR, and the docs say so.
- `ci`: the gate skips local review. After the PR opens, the base-engine CI job runs the same reviewer over the diff as data, with its own key and read-only tools. It publishes `review.json` (bound by `git patch-id`) as the check's output and a one-comment summary. The ticket sits in `awaiting-ci`; `next` returns a `script` action, `forge wait NN`, which blocks with a timeout (a host may instead re-invoke the agent when CI finishes). Once CI is done, `forge review NN` fetches the JSON and `next` returns an `agent_task` listing the findings. The agent fixes, or answers each id in `journal/NN-review-response.md`, commits and pushes. CI re-reviews only what changed and checks every id is accounted for; a declined blocking finding goes to a refuter in CI. One review, not two, at `ci` level. It costs a secret and a CI round trip per fix. `ci` proves the review ran on this patch. It does not prove the reviewer could not be swayed by text planted in the diff, so the reviewer gets read-only tools and the do-not-trust-the-diff line in its brief.

Recommend `ci` for unattended batches, where nobody reads MEDIUM PRs closely. Whether it is the default for HIGH is decision 4 in section 12.

### CI

What the installed workflow does, by job. Neither job merges, runs the agent or writes tickets.

| Job | Trigger, checkout | Runs | Why there |
|---|---|---|---|
| `agentic-policy` | `pull_request_target`, base engine and policy, PR diff read as data, read-only token | Ticket lint; contract vs claim commit and base or tracker; diff inside `scope_paths`; tier vs `risk_paths`; protected diff (engine, policy, hooks give HIGH or `policy: head (unreviewed)`); structure rules on added lines; migrations, new deps, diff size; secret scan; review receipt bound to the patch; with `runs_in: ci`, the reviewer | The PR cannot change its own judge. Nothing here executes PR code |
| `agentic-checks` | `pull_request`, PR head, no secrets | The project's `verify` command; each `Check:` cell | It must run PR code, so it gets nothing worth stealing |
| `agentic-sweep` | Schedule on main, weekly by default | Dependency scan, `doc-lint`, and the sweep (section 10) when it is due. Results become tickets or one tracking issue | Drift and advisories appear without any PR |

Both PR jobs post one receipt table: step, `ran`/`not_run`/`unavailable`, level. `doctor` checks both are required checks; otherwise `ci` is not claimed. The engine reads CI through `forge` to move a ticket from `awaiting-ci` to `merge-ready`.

**Other CI systems.** The engine side is CI-neutral: `agentic ci policy --base <ref>`, `agentic ci checks` and `agentic ci sweep` read policy from base with plain git and print the receipt. Only two pieces are per forge: a job template, shipped like a client (`ci/github`, later `ci/gitlab`), and the `forge` adapter (`gh` first, `glab` next). Each forge protects the judge differently:

| Forge | Judge the PR cannot edit | Secrets kept from PR code |
|---|---|---|
| GitHub | `pull_request_target` job | `pull_request` jobs get no secrets |
| GitLab | CI config file kept in another project (custom CI config path, all tiers), or a pipeline execution policy (Ultimate) | Protected variables reach protected branches only |
| Jenkins, Buildkite, others | Pipeline defined outside the repo, or trusted from the target branch | Per system; `doctor` reports `unavailable` when it cannot tell |

A forge without a protected judge still runs the jobs, but receipts say `local`, not `ci`. GitHub ships first. GitLab is a job template of about 50 lines plus a `glab` adapter of about 100, added when a project needs it. The GitLab rows come from docs and issues, not a test.

### Confidence without reading every line

The aim is that a person trusts a green result from the evidence, not from reading the code. In order of strength:

1. **A person accepts the contract, not the code.** At `plan` acceptance they approve what will change, the scope and the `Check:` cells. Minutes per batch, and it is where judgment pays most.
2. **The contract's checks pass in CI,** and the vacuous-check lint rejects checks such as `true`. Whether a check really tests the change is the reviewer's question on MEDIUM and the sweep's on LOW. A red-first rule was considered and dropped (section 2).
3. **Deterministic gates** in CI: tests, types, lint, structure rules, scans, scope.
4. **The reviewer covers what checks cannot:** whether the checks test the contract, what the diff does outside it, security, and shape. It is a check on the evidence, not a second author.
5. **A person at irreversible effects and HIGH.**

Every finding the reviewer repeats should become a rule or a check (the correction ladder in section 10). Review then shrinks to new problems, and its cost falls as the project ages. That is the practical meaning of a machine programming the machine: people write contracts and rules, machines do the rest.

### Acceptance

```yaml
acceptance:
  LOW: human       # install default; set auto once risk_paths are real. Others: plan, tracker
  MEDIUM: plan     # human accepts a batch once
  HIGH: human      # always individual, merged through forge protection
```

Tiers freeze at acceptance. Humans stay on four effects: merge, deletion, credentials, release. Where a person approves and how waits work: Approvals and waiting, below (proposed 2026-11-09, awaiting approval; it replaces `plan` and `acceptance: tracker`).

### Lifecycle and verbs

`shipped` is split into `pr-open`, `awaiting-ci`, `merge-ready`, then `merged`, and `deployed` when the optional `[deploy]` is set (Environments below), because no script reads CI today and a closed ticket says nothing about mergeability (ship, Ruihang). Failure signatures and a bounded attempt budget stop loops (ship, statem).

New verbs: `install`, `doctor`, `accept`, `amend`, `submit-review`, `intake`, `frontier`, `context`, and optional `run`.

Forge reads go through one `forge` command returning JSON, with `gh` as the default. With no remote, tickets stop at `shipped` and local merge stays available. A claim shows its age in `next`, attempts separate an outage from a code failure, and `doctor` lists stale worktrees and branches. A `setup:` command runs after any worktree is created.

`run` is a small driver that starts one fresh process per step (ralph, agent-loops). It gives solo users the unattended mode, and an orchestrator simply does not use it. Do not build a daemon, a queue, dashboards or fan-out: those belong to the host. Archon, issue-orchestrator and beads show how much code that path costs (280k, 342k and 475k lines).

### PR shape

One ticket, one branch, one PR, one squash commit on main. Research: ANSWERS.md G2.

- **Size caps per tier** (owner decision): LOW 300 changed lines, MEDIUM 600, HIGH none. Counted with `git diff --numstat -M` from the merge base, excluding files marked `linguist-generated` or `-diff` in `.gitattributes`, lockfiles and `[size] exclude` globs. `next` shows the count and suggests a split at 80%. At ship, over the cap raises the tier one step (LOW to MEDIUM, MEDIUM to HIGH); tiers only go up. The CI job repeats the count and fails a PR labelled below its size tier. A refactor mixed with a feature is split.
- **Dependent tickets wait for the earlier merge.** Native stacks are open decision 7.
- **The engine writes the description from the ticket:** Why, Look at, Evidence (the receipt table), Risk, then trailers `Ticket:`, `Tier:`, `Review:`, `Assisted-by:`.
- **Squash with the description as the body;** subject `NN: title (#PR)`. Ticket and journal files merge with the code.
- **Other reviewers' comments are findings.** `forge review` collects bot and human review comments; each must end `fixed`, `declined` or `parked`. Bots stay advisory unless a project requires them.
- **Learning hooks, in core:** the `Ticket:` trailer, a `caused_by:` ticket field, and revert detection give a future learning pack its unit, join key and outcome labels from git alone.

### Approvals and waiting (proposed, ANSWERS H4)

- **A wait is a ticket state, never a blocking call.** `next` returns `owner: human` with what is needed and a link; the agent takes the next ticket it can act on (skipping waits, unmerged `after:` and overlapping scopes). Nothing polls.
- **The ticket's PR is where a person acts.** A HIGH ticket opens a draft contract PR at claim; the label `agentic:go` (or `agentic accept NN`, which sets it) approves the contract; the agent implements on the same branch; the person merges. The engine sets `agentic:needs-you` on every PR waiting for a person, so one label filter is the inbox on any device or host. A host with its own approval step runs `accept` instead. No remote: `accept` writes to the journal.
- **Trackers need no code.** GitHub issues: `intake --source github`, `Closes #N`. Linear and Jira: the key in the branch name and PR title (`Fixes KEY` for Linear); their own integrations move the status.
- **Event-driven runs** (label an issue, get a PR, with no machine on) are the optional `github-runner` pack: one workflow running Claude Code on issue labels, `agentic:go` and PR comments.

### Environments (proposed, ANSWERS H1)

Environments belong to the project. Local: `[commands] setup` per worktree (with `AGENTIC_TICKET` set) and `verify`. Dev: optional `[deploy] wait` and `check` add a `deployed` state after merge; a failed dev check opens a `caused_by` fix ticket. Prod: people only; the framework never deploys and holds no prod credentials, and risky paths are HIGH before they reach dev.

### Host surface

No plug-ins are built. Future hosts (Paperclip, OpenRig, Orca, cloud agents, Symphony, Archon) integrate through the CLI, with a skill and a short host config. Research: [discovery-H-orchestrators.md](../discovery/discovery-H-orchestrators.md). It was read from docs; nothing was tested on a host.

The rule for every overlap: the host decides whether and where work runs; the framework decides what is legal next and what counts as done; forge and CI decide what merges.

The whole integration is one loop, which ships as a seed prompt under 20 lines. Only the last step varies per host:

```text
intake (if the host gave a task) -> next --json -> do action.brief -> advance --json -> repeat
stop on owner != agent, tell the host, end the turn
```

The surface must therefore offer, in core:

1. `--ticket <id or external id>`, then `AGENTIC_TICKET`, then a marker file. A ticket branch is a default, never a requirement. IDs are strings.
2. Idempotent `intake --source <host> --external-id <id>`, with a mirror mode that refuses local `new`.
3. State that rebuilds from the pushed branch.
4. Offline-safe `next`, `advance` and `context`; network steps report `unavailable`.
5. The `host` assurance level and structured `human_wait`.
6. `AGENTIC_UNATTENDED=1` turning `ask` into `deny`.
7. A managed block in `AGENTS.md` that coexists with another tool's block.

The framework does not schedule, poll, keep a daemon, spawn agents when a host is present, call a host's API, merge, sync issues both ways, or ship an MCP server.

The Symphony and Archon findings stay in their reports as host notes.

## 5. Tests and measurement

**Tests.** Keep general end-to-end railroad tests and fix the bugs in section 3 as ordinary work, each with an ordinary regression test where that is cheap. There is no attack suite, cheat set or edge-case programme. A project adds its own edge cases if it wants them. During the port, the same railroad scenarios run through old and new, comparing final ticket state; that comparison is retired after Phase 1.

**Measurement waits.** The event log (section 10) is the only groundwork, because the engine needs it anyway. It gives cost, step and outcome data for free later. Everything else from the research is deferred: planted-defect benches, three-arm runs, held-out splits, ablation, parts ledgers.

## 6. Roadmap

| Phase | Work | Done when | Effort |
|---|---|---|---|
| 1. Core | Python port of the table, verbs, linters and surviving gates (section 11). JSON and exit contract; event log, `context`, pack manifest; host surface items 1-4 | Current workflow runs on the new core; comparison with the old one matches | L, about 4,100 lines of bash to replace |
| 2. Clean install | `engine/`, `seed/`, `clients/` split; install for fresh and existing repos (hook-preserving merge, dry run, non-interactive, stack detection as a proposal), writing `.agentic/SOURCE`; a `CHANGELOG.md` in the framework repo; doctor; straight port of hooks and the three client wirings; ADRs moved | Both a fresh and an existing repo install with guards working and no template history | L |
| 3. Trust | Claim-commit contract and `amend`; gate-launched reviewer and `review.runs_in`; failure signatures and the `consult` pack; two-job CI with checks on base, and bootstrap; floor-guard rewrite; secret and dependency scans | Section 3 bugs 1-5 no longer ship at `gate` level. Bug 1 is closed against CI only with `runs_in: ci`. `consult` fires on a repeated failure | L |
| 4. Hooks | Short rule table, git hooks as a tool-neutral layer, one neutral model, a coverage table per tool, unattended semantics | Section 3 bugs 6-9 are fixed; each tool's gaps are documented | M |
| 5. Autonomy | Acceptance policy; per-ticket waits; lifecycle past the PR; `forge` command; retry budgets; `run` | An unattended run takes a batch to `merge-ready` | L |
| 6. Standard features and docs | Section 10 standard rows (sweep, size caps, repo docs), the skill cut, `## Split`, framework docs via `agentic docs`, license | **Ready to use:** a fresh and an existing repo each reach a merged MEDIUM ticket by following the docs alone | M |
| 7. Host proof | A stub host in the test suite drives the loop through JSON only | The surface works with no plug-in | S |
| 8. Capabilities | Packs from section 10, as needed | Each pack has a named reader | M each |

Phases 1 and 2 can overlap. Hooks must keep working through both, because their paths and state move.

If you want value sooner, two fixes work on the current code before any rewrite: read policy and engine from base, using the two jobs above, and compare the contract to the claim commit. Requiring `report_sha_ok` to fail when no record exists does not work today: tested in a copy, it stops every Mode A ticket, and in CI the record can never exist.

## 7. Do not copy

- Scale. Each of the big repos spends most of its code on what a host already does.
- Hash receipts presented as proof, and any agent-written approval.
- Regex or AST allowlisting presented as a security boundary.
- Full-permission defaults, unbounded retries, fail-open review, telemetry on by default.
- Doctrine libraries, plugin catalogs, presets, workflow DSLs, MCP layers, until a user needs one.
- A database or graph tool for tickets. Markdown plus git refs is enough.

## 8. Removing the ADRs

They record decisions made while building the template. Nothing reads them at runtime. The mechanism stays: the `adr/` directory, `.agentic/templates/adr.md`, the grill and archive skills, and debt-lint's `PONYTAIL(adr-NNNN)`.

| Step | Result (VERIFIED) |
|---|---|
| Baseline | selftest 210 passed; memory-lint and env-lint OK |
| Delete only the 2 files | 188 passed, 22 failed; memory-lint fails on `CONTEXT.md:37-38`; env-lint then blocks ship on every ticket |
| Also remove `CONTEXT.md:37-38`, `.agentic/map.md:14`, `README.md:135` | memory-lint OK; 209 passed, 1 failed |
| Remaining failure | `selftest.sh:304-305` uses the real ADR. Give it a fixture ADR in its temp directory |

That is three reference edits and one test fix. It only solves part of the leak, because `CONTEXT.md` and `verify:` also describe the framework itself. Phase 2 solves it properly. Keep ADR 0001's reasoning in the dev repo's `docs/`.

## 9. Limits of this research

- Study agents read code and ran only harmless checks. No third-party repo was executed.
- Discovery B and C mostly read Exa excerpts. C skipped some known names: OpenHands, claude-flow, Container Use.
- Many studied repos are young and low-star, so their claims are unproven.
- `lee259/lessons` could not be cloned (git says not found) and is unverified. No substitute was searched for.
- Numbers quoted from other repos are their own and were not reproduced.
- Size figures for big repos come from the reports.
- Second round: nothing from the four new repos or the surveyed tools was run. "Works" means the code and docs read that way, and their numbers are their own. I rechecked the gstack ledger entries for /investigate and /review in `docs/inventory/evidence.json`. `gstack-evals` is not in the clone, so those results could not be reproduced.
- `cursor/plugins` has no root license, but 17 of its plugin directories carry their own. Treat it as ideas only unless you pick a specific plugin and check it.
- The survey did not read licenses for several tools (marked unknown there) and did not cover Mem0, Letta or Zep.

## 10. Capabilities

The features named so far are examples, not limits. The goal is a structure where any good feature drops in, for any language and in monorepos. A feature is either standard behaviour or a pack; there are no language-specific fallbacks.

### What shaped this

**Prose steps do not run on their own.** gstack's ledger records that its `/investigate` skill loaded every time, yet 0 of 46 sessions ran any step. In the same ledger, 42 of 66 `/review` sessions ran the review readers only after a Stop hook blocked them. So a feature is delivered by an engine step, not left to a skill's instructions.

**More context is not automatically better.** The AGENTS.md paper (arXiv 2602.11988) found context files raised cost about 20% with no significant gain in task success, and repo overviews did not help agents find files. So nothing generated goes into always-loaded files. It is served on demand and scoped to the ticket.

### The three pieces that let features drop in

| Piece | What it is | Why the core needs it |
|---|---|---|
| Event log | Script-written, append-only, per ticket: step, outcome, tokens if known | Retry budgets, recovery, and later metrics |
| `context` verb | The one read path. `context NN --json` returns a short, fenced brief for the ticket. Packs add to it and return nothing when absent | Memory, maps, docs and the reviewer brief all arrive the same way |
| Pack manifest | Small closed schema | Every optional feature |

Finding a ticket's code needs no store: it is a query over `NN:` commits and `scope_paths`.

```json
{"name": "example", "version": "1.0.0", "engine": ">=2.0",
 "clients": {"claude": "*", "codex": "*", "cursor": "*"},
 "verbs": {"example": "bin/example"},
 "on": {"ticket.claimed": "bin/refresh"},
 "provides": {"context": "bin/context"},
 "reader": "who uses this output",
 "writes": [".agentic/packs/example/"]}
```

A pack can be written in any language: it talks to the engine through JSON and events.

### Pack rules

1. **A pack names its reader.** gstack shipped a 563-line context loader that the study found no caller for.
2. **Packs subscribe to engine events, not harness hooks.** Only 3 of Cursor's 130 plugins use hooks. Removing a pack leaves no settings behind.
3. **Packs can only add hints.** They cannot change ticket state or sit ahead of a core row, so the table stays readable.
4. **The seed holds no pack data.** Files appear on first write.
5. **Stored text is untrusted on read.** It is fenced and escaped like `next` output, because it becomes a prompt.

A tracker pack only supplies the tracker call; `intake` and `acceptance: tracker` are core.

### Features

| Feature | Design | Where |
|---|---|---|
| Memory | Git journals stay the truth. No lesson files: what the machine must not repeat becomes a check (Change table), and knowledge that cannot be a check goes into `ARCHITECTURE.md` or an ADR | Standard |
| Mistakes become fixes | Any correction goes to the strongest layer that fits: the code or architecture, then a check, then a skill or rule, then a doc (Lauren Tan's ladder) | Standard procedure |
| Session recovery | A snapshot derived from git, ticket and events at `next`, so a crash needs no agent-written handoff. After compaction, reinject the Done Contract and scope | Standard |
| Doc references | `doc-lint`: paths, commands and headings in docs resolve. Language-neutral | Standard |
| Repo docs out of the box | `ARCHITECTURE.md` drafted by `install` (rows from top-level directories, the agent fills `Holds`), kept current by `doc-lint` at ship, by the reviewer's "stale doc" finding, and by the weekly sweep. Nothing is generated into always-loaded files | Standard |
| Framework docs | Ship inside the engine and are read with `agentic docs [topic]`; the project tree gets only the `AGENTS.md` pointer. Config and CLI reference pages are generated from the engine's own schema and checked in the dev repo's CI | Standard |
| Sweep | Periodic review of what shipped without review (below) | Standard |
| Size caps | LOW 300, MEDIUM 600 changed lines; over the cap raises the tier one step (see PR shape) | Standard |
| Repo map | Root `ARCHITECTURE.md` with a parsed `## Areas` table (below) | Standard |
| Security | One review brief with a security section, baseline scans, optional threat model (below) | Standard |
| Glossary and ADRs | Lazy glossary; an ADR only if hard to reverse, surprising, and a real trade-off | Standard format, empty seed |
| Diagrams | **Open question.** Nothing is standard until shape and use are settled (below) | Undecided |
| Structure rules | A short rule table checked on added lines, plus any real checker in a `Check` cell (below) | Standard |
| Feature map and drive harness | See `verify` below | Pack |
| Code graph | See `graph` below | Pack |
| Whole-repo security audit | `security-audit` wraps a pinned `cloudflare/security-audit-skill`, on demand. Replaces today's hunt mode in `agentic-audit`. Output becomes tickets | Pack |
| Extra scanners | `security-scanners`: Semgrep or Opengrep, Trivy, zizmor, ZAP, advisory until a project chooses to block | Pack |
| Doc repair job | Folded into the sweep; no separate `gardener` | Standard |
| Human review brief | At HIGH merge: core, wiring and boilerplate grouped, and merge danger as a one-way or two-way door | Pack |
| Second opinion | `consult` from a different model on a repeated failure, before a HIGH claim, or at a retry cap (below). Advisory, never counted as review | Pack, built in Phase 3 |
| Browser QA | Wrap an external browser tool; do not vendor one | Pack |
| History search | Disposable SQLite full-text index over tickets and journals. No vectors, no daemon | Pack |

### Security

Research: [discovery-G-security.md](../discovery/discovery-G-security.md). Keep the skills small and fix three gaps: reviewers cannot read unchanged code, there is no threat model, and nothing deterministic scans secrets or dependencies. The best independent data (SecPRBench: real commits in C, C++ and Rust, recall only) puts a direct focused review near specialist products at about a tenth of the cost.

| Trigger | Runs | Cost |
|---|---|---|
| PR, all tiers | Secret scan on the range; dependency scan if a lockfile changed | Free |
| Gate, MEDIUM and HIGH | Reviewer with a security section | About $1 a pass |
| Gate, HIGH | Separate security seat, one refuter per blocking finding | About $1-4 |
| Before release | History secret scan; optional one-seat review of the cumulative diff (no evidence for this yet) | About $1-5 |
| Daily or weekly | Dependency scan on main; failure opens one tracking issue | Free |
| On demand | Audit pack: first release, new auth or tenancy, then monthly at most | $30 or more |

- Costs are estimates from benchmark and small-sample runs. A daily LLM audit would be about $900 a month and mostly re-read unchanged code.
- `agentic-security` is about 60 lines, with a 25-line brief section: ten one-line scope prompts ("a checklist, not a ceiling"), the do-not-report list, and fixed finding fields. Long checklists are not used.
- Scan commands are plain config, run by exit code. A missing scanner prints `not_run`. Suggested tools are named, not vendored.
- Optional `THREAT_MODEL.md`, about 30 lines, read by reviewers and listed in `risk_paths`, because editing it can silence findings.
- Installed workflows pin actions by SHA, set minimal permissions and give a CI reviewer only its own key. Dependency updates wait 3-7 days, apart from security fixes.

### Structure rules

A rule stops a bad shape from entering the code. This is the second rung of the correction ladder. Tan, OpenAI and Spotify all rely on this, with project-specific tools.

```yaml
rules:
  - id: web-no-db
    paths: "apps/web/**"
    forbid: "@acme/db"
    fix: "Call the API client in apps/web/lib/api."
    why: "ticket 41"
  - id: migrations-home
    files: "**/*.sql"
    only_in: "db/migrations/**"
    fix: "Create migrations with make migration."
```

- `forbid` checks added lines. `only_in` checks added files. So old code never fails and adopting a rule needs no cleanup first.
- The check runs at ship and in CI from base. `fix` is printed to the agent. The rules file is a `risk_paths` entry, so loosening a rule takes a HIGH review.
- This is a text match, so it is mistake prevention, not proof. Real dependency analysis goes in a `Check` cell using any checker the project likes. The framework ships no tool list.
- A finding a rule already covers is not a review finding.

The rule table is my design, about 60 lines, and untested.

### Second opinion

`consult` asks a different model for advice when the working agent is in trouble. It is a pack with one verb, reusing the reviewer launch path. **It is built now, in Phase 3, with the reviewer launch path,** not after stuck loops show up. Failure signatures move to Phase 3 with it; the retry-cap trigger arrives with retry budgets in Phase 5.

- **When:** the engine sees the same failure signature twice, before a HIGH claim, or at a retry cap. `next` shows it as a hint. A person can also ask.
- **What it reads:** the engine builds the brief from the ticket, diff and raw check output, plus one question from the agent. The agent's own story is left out, because it may carry the mistake.
- **What it returns:** `proceed`, `change` or `stop`, with reasons, written to `journal/NN-advice.md`. About three consults per ticket.
- **Limits:** read-only, never a gate, never counted as review. A same-model consult is labelled, because maestro retired a same-model seat that added only a hop. If two consults fail to unstick a ticket, the owner becomes `human`.

No studied repo has outcome data for this. SecPRBench shows different models catch different bugs in review, which is the only related support.

### Diagrams: open question

Nothing about diagrams is standard for now. Research ([discovery-I-navigation.md](../discovery/discovery-I-navigation.md), section 9) found no study showing Mermaid helps agents navigate; strong models do about equally well with text. For humans, results are mixed: a diagram helps when drawn for one question and not as standing orientation. Two shapes are still candidates: one on-demand diagram in the human review brief, and nothing at all. Rules stay in checks either way.

### Maps: what real setups do

Full research: [discovery-F-maps.md](../discovery/discovery-F-maps.md). It is grep-level across the 37 repos plus web sources, and much of the web evidence is vendors reporting on themselves.

Most working setups have no code graph. By grep, 4 of 37 repos have a real one and 1 requires it. What OpenAI, Anthropic, Stripe, Meta and Spotify describe is plainer: a short entry file that points elsewhere, live search owned by the tool, conventions per directory, rules that fail in CI, and a scheduled job that repairs drift.

A map stays true if it is derived from code or git, runs a command in CI, is coarse enough to change rarely, or a scheduled job proves it. Files get read only when the engine delivers them: `llms.txt` was fetched in 0 of 5 runs unless the agent was told to (small sample).

"Feature map" also means something unexpected. In Lauren Tan's talk and in pstack it is not a feature-to-code map. It lists user-facing features, how to reach each, how to drive it and what proves it works, and it leaves code paths out on purpose. Its reader is verification and bug triage.

### Repo map: `ARCHITECTURE.md`

This is the standard map, for any language and any monorepo. It is hand-curated, updated by the agent on the ticket, and capped at about 150 lines. It is absent from the seed and created on first need. An existing file just gains the section.

```markdown
## Areas
| Area | Paths | Holds | Check |
|---|---|---|---|
| api | services/api/** | public HTTP handlers | make -C services/api test |
| web | apps/web/** | browser client | pnpm --filter web test |
```

- **`Paths` are globs,** so nothing depends on a language.
- **`Check` is any shell command.** It gives a monorepo a verify command per area, and `verify` runs the `Check` of each touched area. A command that runs at ship cannot rot silently. `config.yml` `verify:` stays as the fallback when no area matches.
- **`AGENTS.md` carries one pointer line.** `context NN` returns only the rows matching `scope_paths`, at claim and in the reviewer brief. The whole file is never pushed into context.
- **`doc-lint` has four script rules:** every glob matches a tracked file; every directory at `map.depth` is in an area or `map.ignore`; the file is under the cap and its cites resolve; and a diff that adds, removes or renames a directory at `map.depth` must also change this file.

- **`Holds` uses the words a bug reporter would use,** not the words already in the path, such as `checkout, payment failure, refunds`. That meaning is what the filesystem and grep cannot supply.
- **`context NN` adds a derived directory digest:** for each matched area, a directory list with file counts, capped at about 40 lines. It is rebuilt per call from `git ls-files` and never stored.
- **`Check` cells are read from base in CI,** and the vacuous-check lint applies, because an agent could otherwise set one to `true`.

Live search stays the default way to find code, and the framework owns no index or tree. Research: [discovery-I-navigation.md](../discovery/discovery-I-navigation.md). A walk costs a model turn per level, while search jumps when the agent knows a word. Structure helps where search has no handle: unfamiliar wording, look-alike packages and hidden dependencies. That is what `Holds`, the digest and the `graph` pack cover. Agents often skip optional tools, so all of this arrives through `context`.

No source uses this exact form, so this design is untested. It is about 100-150 lines of script.

### Map packs

| Pack | What it adds | Why a pack |
|---|---|---|
| `verify` (build first) | A project-local way to drive the software, plus `docs/features/` with one file per feature: how to reach it, how to drive it, gotchas. Works for UI, CLI, API or library. Optional coarse `paths:` show which features need re-proving after a change | Needs a way to run the software |
| `graph` | The provider contract: `refresh`, `search`, `status`. The default provider is git change coupling, which needs no language tooling. Tree-sitter, SCIP, LSP or Graphify are optional providers. It gives one hop only, delivered by `context` and the reviewer brief, not offered as a tool. With thin history or no provider it returns nothing | Few workflows need it, and real symbol data is per-language |

Skipped: generated summaries in always-loaded files, a framework-owned symbol index or embeddings, a repo `llms.txt`, a pass/fail feature ledger (tickets do this), hand-kept feature-to-code tables, generated wikis, committed generated diagrams, a separate diagrams pack, and a CODEOWNERS reader (the forge already does this).

Small rename: the ticket section `## Capability Map` is a work breakdown, not a repo map, so call it `## Split` to avoid confusion.

### Learning: held for the owner's own pack

These lessons are for the person: what to understand about the project, its changes, docs and code to prompt the agent well tomorrow. The framework's own lessons are checks (Change table). The core only keeps the raw material in git, joined by ticket id: tickets, PR descriptions, findings and how each ended, `caused_by` links, reverts and sweep summaries. The owner has their own system (desktop app, CLI, generated lessons, sparring, and a PR to the repo after learning) and will add it as a pack. The current idea is lessons stored in the repo with an index recording whether each was learnt. Nothing is built now. The pack contract above already covers this: a verb, files in the repo, and a read through `context`. One thing to check when it arrives: repo-stored lessons belong in project paths, which the pack `writes` field can declare.

### Sweep

Per-ticket review cannot see drift: three LOW tickets each add a small helper, and together they are a second copy of an existing module. The sweep reviews what shipped without review, all at once.

- **When:** after `sweep.after` unreviewed tickets (default 20), or weekly, whichever comes first. `next` returns it as an `agent_task` when no ticket work is waiting, and the `agentic-sweep` CI job runs it on schedule. A person can run it any time.
- **Scope:** the cumulative diff since the last sweep marker (`refs/agentic/sweep` on the base branch), limited to LOW tickets and commits with no ticket. Already-reviewed work is left out.
- **Deterministic part, free:** `doc-lint`, structure rules over the whole tree reported as a count (not a failure), dependency scan, and git-only signals: files past a size threshold, most-changed files, new top-level directories not in `## Areas`.
- **Review part, one pass, about $1-5:** the same reviewer and `review/v1` schema, with a sweep brief: duplication across tickets, logic in the wrong area, missing or vacuous checks, security, stale docs. Same do-not-report list.
- **Output:** findings become tickets (`sweep-NN`) or `parked`, never edits. A one-page summary goes to the journal and, from CI, to one tracking issue. A finding the sweep repeats is a candidate for a structure rule.
- **Standing:** advisory; it never blocks a merge. It takes over the periodic role of today's `agentic-audit`. The whole-repo security hunt goes to the on-demand `security-audit` pack.

### Keeping the code in shape

No single step does this. The layers, in the order a change meets them:

| When | What holds the shape |
|---|---|
| Before code | A person accepts the contract; `risk_paths` set the tier; `## Areas` says where things go |
| While coding | Scope paths, structure rules on added lines, new-dependency check, tier size caps |
| At ship | Verify and checks, doc-lint, review on MEDIUM and HIGH, security seat on HIGH |
| After merge | Weekly sweep, dependency scans, security audit on its triggers |
| Over time | Repeated findings become rules or checks; the retro sorter turns mistakes into fixes |

### Not taken

Automatic writes to always-loaded memory, GitNexus (noncommercial license), repowise code (AGPL), a vendored browser stack, role-play prose, LLM judges as gates, ai-memory or gbrain as a dependency.

## 11. What survives the rewrite

Judgment. Each item must still pass the deletion test in section 2.

| Today | Verdict |
|---|---|
| Migration gate, `reversibility`, `rollback` | Port. It stands before an irreversible act |
| `new_deps` lockfile check, diff size limits | Port |
| Session traps (production URLs at claim) | Port |
| Scope overlap and `blocked_by` refusal | Port; `plan` acceptance depends on it |
| `--widen`, `reopen`, `pr --require-shipped`, `check`, `next --all` | Port |
| ASSUMED rows blocking claim and ship | Port |
| `env-lint --protected-diff` on non-ticket PRs | Port, in the base-engine CI job |
| `floor_ignore`, `floor_exceptions` | Port; a project's only way out of a false floor finding |
| Worktree flow, `require_worktree` | Port, with `setup:` |
| Memory-lint needles, lesson TTL, `CONTEXT.md` cap | Drop needles, TTL and lesson files; the `CONTEXT.md` cap moves into `doc-lint` |
| `ticket-lint`, `debt-lint`, `floor-guard`, `env-lint` | Port. Language pattern lists (`ts-ignore`, lockfiles, SQL) become data a project or pack can extend |
| Hook command log, `metrics.jsonl` | Move to the event log |
| `audit:` config, `agentic-audit` | Split: the periodic check becomes the sweep (standard), the hunt becomes the `security-audit` pack |
| Sandbox lines in `.claude/settings.json`, `.codex/config.toml` | Port into clients. These are the boundary section 4 relies on |
| Evaluator agents, security persona, `references/judgment.md`, `dod.md`, templates | Port; the review brief uses them |

## 12. Open decisions for the owner

1. **License.** Decided: no license.
2. **CLI name.** Nothing says what a user types once `scripts/gate.sh` is gone.
3. **Diagrams.** See section 10.
4. **Review in CI.** Whether `review.runs_in` defaults to `ci` for HIGH. I suggest `gate` by default and `ci` for unattended batches.
5. **Platform.** Decided: macOS and Linux, Claude Code as the standard client, no Windows.
6. **Moving copy-in projects.** Decided: not needed; old versions are not supported.
7. **Stacked PRs.** GitHub's native stacks (generally available 2026-10-06 per GitHub's changelog, found by a subagent and not rechecked by me) could carry `blocked_by` chains as a `forge` option. I suggest waiting for merges until a project needs stacks.
