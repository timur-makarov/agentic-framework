# openai_symphony

Head `be10a1b`, 47 commits, 2026-03 to 2026-09, v0.0.3. Apache-2.0 (`LICENSE`, `NOTICE`, © OpenAI). The repo is missing from `other-solutions/MANIFEST.tsv`, so the license comes from the file. Paths are relative to the repo. `fw:` means the framework. Nothing was run; everything below is from reading code and `git log`.

## 1. What it really is

A scheduler, not a coding framework. A daemon polls a tracker, keeps one in-memory claim map, gives each issue a directory, starts `codex app-server` there, sends a rendered prompt, and re-reads the tracker after each turn. The product is `SPEC.md` (2,312 lines, RFC-2119, conformance profiles). The Elixir code (about 13,000 lines, 1,990 orchestrator, 1,071 app-server client, 1,941 terminal dashboard) is labelled "prototype software intended for evaluation only" (`elixir/README.md:7`).
The code does what the spec's core says. `git log` shows careful failure-driven hardening in July 2026: stale retries, claim leaks, cleanup races, invalid reloads.
It has no quality gate at all. "Completion bar before Human Review" is prose (`elixir/WORKFLOW.md:265-273`), and a run ends when the agent moves the tracker state.
It is Codex-only: `codex.command` must speak the app-server protocol and the client sets `experimentalApi` (`app_server.ex:281`).
Claims the code does not support: "proof of work: ... complexity analysis, and walkthrough videos" (`README.md:8`) has no implementation here; `launch-app`, `github-pr-media`, the "update script" and an `App runtime validation` section are referenced (`WORKFLOW.md:218,273,282`) and do not exist (VERIFIED). The 100% coverage threshold excludes Orchestrator, AgentRunner, AppServer, Workspace, Config and every client (`elixir/mix.exs:11-45`, VERIFIED).

## 2. Take

All items are Apache-2.0, so code may be copied with attribution, but Elixir does not port into bash. Treat all as ideas unless noted.

| Item | Mechanism and `path:line` | Framework part it changes | Why better | Effort | Copy or idea |
|---|---|---|---|---|---|
| Three-class tracker states | Active = run, terminal = stop and clean, anything else = stop and keep the workspace (`orchestrator.ex:421-441`, `SPEC.md:819`). A human wait costs nothing and blocks nobody | `blocked-on-answers`, the global write freeze, `status: open` | Waiting is per issue and outside the agent's repo. Gives unattended mode with humans at chosen stops | M | Idea |
| Two-call read kernel | `fetch_issues_by_states`, `fetch_issues_by_ids`, plus adapter-derived `dispatchable` (`tracker.ex:22-27`, `SPEC.md:1186`). "Do not add generic ... CRUD" (`SPEC.md:1182`) | Dead `tracker:` config, `compute_next` scan | A tracker integration is two reads. Provider logic stays in the adapter | M | Idea |
| Fresh worker as reviewer | Every worker does `thread/start` (`app_server.ex:321`); nothing resumes. The prompt can branch on `issue.state` (`prompt_builder.ex`, strict Liquid) | Reviewer Mode A; Codex has no subagent (`fw:README.md:20`) | An `Agent Review` active state gives a reviewer with no author context, same workspace, per-state concurrency. Not a forgery fix alone; see next row | M | Idea (mine, built on their mechanism) |
| Host-side evidence | Local hooks run outside the Codex sandbox (`workspace.ex:404`); the default sandbox writes only the workspace (`schema.ex:570`) | "A self-written critic report ships" (`fw:gate.sh:235`) | `after_run` can record report hashes where the agent cannot write. First real trust root outside the author's reach. INFERRED: needs a test, and SSH workers differ | M | Idea |
| Blocked is not retry | `3365695`: "human-input blockers are not transient failures". Separate `blocked` map, kept claimed until the tracker moves (`orchestrator.ex:757-779`) | `fw:gate.sh:532`, exit 1 means work or failure | Directly names the exit-code split the framework needs | S | Idea |
| Continuation prompt | Same thread gets short guidance, not the task again (`agent_runner.ex:144-154`); `attempt` goes to the template | `stop.sh`, parts of `agentic-handoff` | With `gate.sh next` printing the resume point, stop hook and handoff shrink | S | Copy the text |
| Comment sweep | Every actionable comment, human or bot, blocks until fixed or answered with "explicit, justified pushback" (`WORKFLOW.md:171-186`) | `bound_findings`, decline with no reason | No changed-line limit, and a decline needs a reason where others can read it | S | Copy the text |
| Token accounting | Use absolute totals, track deltas, ignore `last_token_usage` (`elixir/docs/token_accounting.md`, `SPEC.md` 13.5); per-issue totals in `/api/v1/<id>` | "Not measured" gap, `fw:lib.sh:395` | Join tokens and wall time with `metrics.jsonl`. Then run the same issues with and without the railroad. This is the first cheap outcome eval | S-M | Idea |
| Spec with conformance profiles | Core, Extension and Real Integration profiles; a skipped live test "reported as skipped" (`SPEC.md:2049,2191`); `implementation-defined` must be documented | `selftest.sh` as sole proof | Publishing the gate contract as a versioned spec gives orchestrators a stable target. Add one live profile: a real agent on a scratch repo | M | Idea |
| Last known good and strict rendering | Bad reload keeps old config; unknown template variables fail (`cdb466a`, `d476215`, `prompt_builder.ex:8`) | awk config, dead keys | Unknown or dead config keys should fail `env-lint` | S | Idea |
| Workpad stamp | One tracker comment holds plan and state, with `host:path@sha` (`WORKFLOW.md:142-157,295-329`) | Local `.agentic/state`, handoff | Readable from any clone. Useful only with a tracker | S | Copy the template |

## 3. Challenges

- **Scripts own state.** Half right on each side. Symphony lets the model move the tracker (`SPEC.md:39,1310`), so nothing checks that "Human Review" was earned. That is its biggest hole and exactly what `compute_next` fills. But scheduling state does not belong in a repo. Verdict: gate owns the legality of the next step inside one issue; the orchestrator owns which issue runs.
- **Tickets as the unit, front matter as the state.** Partly wrong. Verdict: split them. The tracker owns routing (should an agent run, who is waiting). The ticket file owns the contract and evidence (tier, scope, checks, reports).
- **A human accepts every ticket.** Replace, do not drop. Human acceptance becomes moving an issue to an active state, optionally with `tracker.required_labels` (`54b456b`). This is better than a file the agent can edit (`protect.sh`), but not airtight: `linear_graphql` can do anything the token can (`elixir/README.md:232-233`), and "wait for human to move it to Todo" is prose (`WORKFLOW.md:279`).
- **Hooks as the guard.** Symphony uses zero agent hooks: OS sandbox, approval policy, host-held credentials. For unattended runs that is the real boundary, and regex over shell text is advisory. Verdict: the framework's own `.codex/config.toml` sandbox matters more than `guard.sh`. Keep hooks as fast feedback, stop calling them enforcement. Symphony's sample config undercuts its own point (`approval_policy: never`, `networkAccess: true`, `inherit=all`, `WORKFLOW.md:34-39`).
- **Three lanes.** Symphony has one lane, and it is heavy: every issue gets a PR, sweep and human review. Framework is right; keep the lanes.
- **Changed-line review.** Symphony has no line limit on feedback. It supports the known gap: findings on deleted lines or callers should not vanish.
- **Bash plus files.** Right for the per-issue inner loop. Wrong for a daemon: `476b2b0` shows supervising workers and scheduler as one restart unit took real runtime support. Verdict: do not write a daemon in bash.
- **Copy-in distribution.** Symphony's repo contract is one `WORKFLOW.md` plus optional skills, and the runtime lives outside the repo (binary or "make your own"). Verdict: right direction; framework runtime should not sit in the host's `scripts/`.
- **18 skills, long AGENTS.md.** Weak evidence. Symphony ships 7 skills and a 76-line `AGENTS.md`, but its prompt is 329 lines. The useful finding: `/agentic-interview`, `/agentic-grill` and the PR menu assume a person in the session; unattended they trigger a block, so they need unattended forms.
- **Selftest as main proof.** About 300 tests plus live E2Es against real trackers and Codex beat a mechanics-only selftest. But it has no outcome evals either.

## 4. Delete or simplify

- `limits.max_active_tickets`, `other_claims`, local scope overlap: in per-clone runs each clone sees only itself (`fw:gate.sh:165,572`). Replace with a shared lease or remove in orchestrated mode.
- `refs/agentic/nn` reservation in tracker mode: the tracker already allocates identity.
- `stop.sh`, `stop_followups`: continuation turns replace them under an orchestrator, and the default is already off.
- `.worktrees`, `gate.sh implement --worktree` under an orchestrator: the workspace is the isolation.
- `tracker:` must become real or go. `limits.exception_max_days` and `models.*` should go regardless.
- `ask` as a guard outcome in unattended mode: nothing can answer it (see E9).

## 5. Orchestration

**Division of labour.** `README.md:17` requires a "harness engineering" repo; `SPEC.md` non-goals exclude ticket and PR logic. So the framework is the missing Policy Layer, with no need to build a scheduler. Symphony: which issue, when, where, retry, stop. Framework: what is legal next, what counts as done, what evidence proves it.

**What Symphony actually gives a repo (all VERIFIED).** A cwd named after the sanitized identifier (`workspace.ex:268-276`). Four shell hooks with **no issue data and no env added** (`workspace.ex:404`), so `basename "$PWD"` is the only ID; default timeout 60 s, one value for all hooks (`schema.ex:241`). One rendered prompt with `issue` and `attempt`. Tracker tools callable **only by the model**, tokens scrubbed from the child (`app_server.ex:207,246`, `github/client.ex:25-26`). Up to 20 turns on a thread, then a new worker with a **new thread**. Kill at any tick. The only completion signal is tracker state, and **no retry or budget limit exists**: a normal exit always reschedules (`orchestrator.ex:216`), failures back off to 5 minutes forever (`:1240-1243`). `grep` finds no attempt or token cap. An agent that stops without moving the tracker loops and spends until someone notices.

**State map to ship.**

| Tracker state | Class | Framework meaning |
|---|---|---|
| `Backlog` | ignored | Not accepted |
| `Todo` + label `agentic` | active | Accepted to work on: intake runs |
| `Contract Review` | neutral | MEDIUM/HIGH: human approves tier, scope, checks |
| `Needs Input` | neutral | `WHO=human`, a blocker or question is on the issue |
| `In Progress`, `Rework` | active | `advance` loop |
| `Agent Review` | active, optional | Fresh-thread critic |
| `Human Review` | neutral | Shipped, PR open |
| `Merging` | active | Non-HIGH land only |
| `Done`, `Canceled` | terminal | Workspace removed |

**What the framework must expose.** Required for a working integration:

| # | Contract | Today | Gap to close |
|---|---|---|---|
| E1 | A shipped pack: `integrations/symphony/WORKFLOW.md`, front matter plus prompt, with the loop "run `advance`, do NEXT, on TRACKER line move the issue, end turn" | Nothing | Prompt must be strict-Liquid safe. S |
| E2 | `bootstrap`: idempotent, runs in `after_create` after a full clone, under 60 s or with `hooks.timeout_ms` raised | `/agentic-init` is an interactive skill | Non-interactive; no `--depth 1`, which breaks merge-base and hides `origin/ticket/*` (INFERRED). S |
| E3 | String or external identity. Accept `MT-649`, keep `NN`-style commits | `NN` must be digits (`fw:gate.sh:69`, `lib.sh` `branch_nn`) | In tracker mode derive NN from the numeric suffix and store `external_id:`. Multi-prefix trackers collide, so `ticket_id` strings are the durable fix. M |
| E4 | `gate.sh intake --id --title --body-file`: idempotent create-or-find | `new` needs a slug, allocates locally (`:757-775`), leaves `blocked-on-answers` | Two clones get the same number today. Tracker becomes allocator. M |
| E5 | `acceptance: tracker` config, so `status: open` is set by intake because the tracker said so | Only a human file edit (`:825`, `blocked-on-answers` refuses claim) | LOW: go straight to claim. MEDIUM/HIGH: stop at `Contract Review`. Contract Check commands stay agent-authored until a human approves, which also closes the mutable-contract gap if the approved contract is hashed. M |
| E6 | Resume from any clone | `claimed_here` needs gitignored `scope-NN.txt` (`:141`); `ticket_branch_for` sees only `refs/heads` (`:146`); missing ticket prints "create it" (`:358`) | Lost workspace or new SSH host creates a **duplicate ticket**. Look at `origin/ticket/*`, restore the frozen scope, tier and check hash from the claim commit, not from local state. M |
| E7 | Tracker directive in `next`/`advance`: `TRACKER: move to "Human Review"`, from a `tracker_states:` map keyed on rows | `WHO` exists (`:319`) but is only printed as text | Must cover every human and rest exit. Without it the agent ends the turn on a still-active issue and Symphony loops. S |
| E8 | Distinct exit codes: 0 rest, 10 agent work, 11 waiting on human, 12 step failed, 2 usage | Exit 0 or 1 (`:532`) | Hooks need them; the model does not. `--json` with `who`, `next`, `why`, `tracker_state`, `failed_step`, `schema` is for hooks and other orchestrators. Symphony itself never parses gate output. S |
| E9 | `AGENTIC_UNATTENDED=1`: `ask` becomes deny, interactive skills write to the issue instead | `ask` depends on the tool. Under `approval_policy: never` everything is auto-approved (`app_server.ex:761-781`). Otherwise a request ends in `blocked` with no way to answer (`:528-536`) | Set it with `env VAR=1 codex ...` in `codex.command`; the launcher prefixes `exec` (`app_server.ex:224`), so a bare `VAR=1` fails. An `.agentic/config` flag is agent-writable; pair it with the sandbox. S |
| E10 | Guard wiring that survives a new path | `.codex/` loads only if the project is trusted (`fw:README.md:14`, `.codex/config.toml:1`). Every workspace is a new path; Symphony also passes its own sandbox and approval at `thread/start` | **Hooks and rules may silently not run at all** (ASSUMED: Codex app-server trust and hook behaviour is not in this repo). `bootstrap` must prove it: a canary denied write, failing `before_run` if absent. `env-lint` should treat this as fatal. M |
| E11 | Unattended reviewer | Mode A needs a subagent. Mode B runs `critic.command` in a nested worktree (`:972`) | Pick: Mode B calling a nested non-interactive Codex (auth, sandbox, network all untested), or the `Agent Review` state. Either way CI must reject reports with no attestation. M |
| E12 | Crash safety: any `gate` step survives a kill | `move_ticket` is commit-based with rollback only on failure (`:1085`) | Terminate is abrupt. `advance` must clear a stale `.git/index.lock` and detect half moves. S |
| E13 | Base handling for merged-in upstream | `base_ref` prefers local `main` (`lib.sh:89`); `diff_files` uses that merge-base (`:103`) | The clone's local `main` goes stale after `git fetch`, so a branch that merged `origin/main` shows upstream files as its diff: false scope breaches (INFERRED). Prefer `origin/<base>` in orchestrated mode. Also, syncing after ship reopens the ticket (`:308`), so each base merge reruns review. Exempt merges whose product diff against base is unchanged. M |
| E14 | A budget fuse | Nothing on either side | Pinned host script in `before_run`: count runs per issue under a host directory, move to `Needs Input` over the limit. Must be host-installed, see below. S |

Optional: pushed lease `refs/agentic/claims/<id>` (atomic `git push`) to restore cross-clone scope overlap checks; publishing `.agentic/journal` summaries to the workpad; a thin app-server shim so Claude Code or Cursor could run under `codex.command` (L: needs `initialize`, `thread/start`, `turn/start`, turn events, `item/tool/call`, and only then would non-Codex tools work).

The framework does **not** need to expose a daemon, HTTP API, tracker client or Elixir adapter. A `local-markdown` adapter would need a Symphony patch (`@adapters` is compile-time, `tracker.ex:13`); use a real tracker instead.

**Sketch.**
```yaml
tracker: { kind: github, provider: { repo: org/app }, required_labels: [agentic],
  active_states: [...], terminal_states: [...] }   # GitHub only has open/closed, so Linear or Jira fits the state map
hooks:
  after_create: |
    git clone "$REPO_URL" . && scripts/agentic bootstrap --external-id "$(basename "$PWD")"
  before_run: /opt/agentic/fuse "$(basename "$PWD")"     # host copy, never the workspace copy
  after_run:  /opt/agentic/attest "$(basename "$PWD")"   # host copy
codex: { command: "env AGENTIC_UNATTENDED=1 codex app-server", approval_policy: {...}, thread_sandbox: workspace-write }
```

**Three traps.** (1) A local hook inherits the host env with tracker tokens, but only the Codex child is scrubbed. A hook that calls a script in the workspace runs agent-edited code with those secrets; Symphony's own sample does so (`WORKFLOW.md:29`). Framework hooks must be host-pinned. (2) `after_run` is not a reliable place for anything: failures are ignored, it is per worker not per turn, and it probably does not run on cancellation (see section 6). (3) `github_api` allows `PUT` and `DELETE` with the tracker token (`github/agent_tool.ex:9`), so the agent can merge through a dynamic tool the framework's shell guard never sees (INFERRED). "HIGH needs a human merge" must be forge branch protection, not `guard.sh`.

**Standalone.** Symphony's lesson is not to grow a scheduler. Standalone stays a person running `advance`. A small loop can cover overnight runs, but anyone wanting concurrency should use an orchestrator. Keep one rule set for both modes and have only intake, acceptance and the waiting mechanism differ.

## 6. Do not copy

- **Unbounded retries and no spend cap** (section 5). `SPEC.md` has no attempt limit either.
- **Prose as the only quality gate**, and the model as sole author of state transitions.
- **Sample trust posture**: no approvals, network on, full env inherited. The README limits it to trusted environments, but it is what people copy.
- **Raw tracker tools at full token scope**, with idempotency left to "workflows" (`elixir/README.md:234`).
- **In-memory-only state**: `blocked` is lost on restart (documented), and a second instance would double-dispatch; there is no lease (`SPEC.md:2239` lists persistence as TODO).
- **Spec and code disagree.** `SPEC.md:432` says `after_run` runs on cancellation. `AgentRunner` runs it in `try/after` (`agent_runner.ex:45-51`), termination goes through `Task.Supervisor.terminate_child` and no module traps exits (`grep`), so it likely does not run for reconciled or stalled workers (INFERRED from OTP semantics; no test covers it). `SPEC.md:1036` says keep stderr separate; the client merges it (`app_server.ex:204`). `Port.close` sends no kill, so child processes may outlive a stop (ASSUMED).
- **Dead workflow text.** `Human Review` is not in `active_states` (`WORKFLOW.md:7-11`), so "poll for updates" (`:247`) can never run.
- **Input detection by guessing field names** (`app_server.ex:1061-1068`). Tied to an experimental protocol.
- **Stall retries drop host and workspace metadata** (`orchestrator.ex:628-634`), unlike other retry paths, despite the spec preferring host stickiness.
- **Template leakage**: `docs/symphony-smoke-*.md` are agent smoke artifacts in the main tree. Same failure as the framework's.
- Suspicious content: none found. `WORKFLOW.md` and skills are ordinary instructions for its own agents; I treated them as data.

## 7. If you rebuilt the framework

Keep the first-match decision table, the Done Contract, the lanes, floor-guard and CI re-derivation: Symphony has none of these and needs them. Change the shape around them. Treat the framework as a per-issue state machine with a versioned contract (spec, exit codes, JSON), not a tree that owns the project lifecycle. Ticket file for contract and evidence, tracker when present for routing and human waits. Every piece of state either committed to the branch or re-derivable, so any clone can resume. Host-installed runtime and a host-side evidence directory, sandbox as boundary, hooks as feedback. A ready Symphony pack as first integration, and a with/without run over real issues using Symphony's token data as the first evidence that the ceremony pays.

## 8. Coverage

Read in full: `README.md`, `SPEC.md`, `elixir/README.md`, `elixir/WORKFLOW.md`, `elixir/AGENTS.md`, `orchestrator.ex` (to line 1677; the rest is token extraction, skimmed by spec), `codex/app_server.ex`, `agent_runner.ex`, `workspace.ex`, `tracker.ex`, `tracker/issue.ex`, `tracker/memory.ex`, `prompt_builder.ex`, `workflow.ex`, `mix/tasks/workspace.before_remove.ex`. Partly: `config/schema.ex`, `github/*`, `linear/client.ex` (dispatch rules), `token_accounting.md` (first 50 lines), `land/SKILL.md` (first 80 lines), 12 commit messages, test counts. Framework: `gate.sh` (`compute_next`, claim, new, ship, advance, reviewer), parts of `lib.sh`, `.codex/*`, `stop.sh`, config, README, CI start.
Not read: `status_dashboard.ex`, web layer, Jira/Asana/GitLab clients, test bodies, `land_watch.py`, `linear`/`release` skills, `workflow_store.ex` body (behaviour taken from commits), Burrito workflows, the demo video.
Confidence: high on Symphony's mechanics and on E3-E8, E13. Medium on anything crossing into Codex behaviour, which this repo does not define: E10 and E11 and the sandbox-based trust root need a live test before design commits to them. Nothing here is measured.
