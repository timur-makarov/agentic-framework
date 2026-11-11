# NTCoding/autonomous-claude-agent-team

Repo paths are relative to the clone. `fw:` means the framework. License: no LICENSE file and no `license` field in any `package.json` (VERIFIED), so every item below is **idea only, no code**.

## 1. What it really is

- A Claude Code plugin (v4.1.3, 89 commits, 2026-03-01 to 2026-04-12, one author). An event-sourced TypeScript state machine with 11 fixed states drives three LLM agents (lead, developer, reviewer) from a GitHub issue to a draft PR. The README itself says it is "a specific, working example — not a flexible framework".
- Real size, excluding specs (VERIFIED): engine package 2,487 lines, workflow definition 1,966, analysis 2,334, control-center UI 3,631. Specs are 15,211 lines. 100% coverage is enforced (`vitest.config.mts`).
- **It looks broken at HEAD (VERIFIED by reading, not run).** `commands/workflow.md:4`, the only route for `transition` and every operation, calls `src/autonomous-claude-agent-team-workflow.ts`. That file was deleted in d605543 (2026-03-07). `hooks.json` was moved to `src/shell.ts`; the commands never were. INFERRED: the author moved on (`dev-workflow-v2` appears in `opencode-workflow-plugin.ts`), so this repo is an abandoned snapshot of the idea.
- Unsupported README claims: "No cloning or building needed" (`README.md:151`), yet `node_modules` is untracked and hooks need `tsx`, `zod` and a `workspace:*` package (INFERRED: hooks fail on a bare install). A `/tmp` JSON state file (stale; state is SQLite). DB path `~/.claude/workflow-events.db` (code uses `~/.workflow-events.db`, `src/shell.ts:49`). "Lead never writes code" and "the lead can't skip states" are role-blind: no hook input carries the role (`hook-schemas.ts`), and `checkSpawnAllowed` is dead code (`spawn-rules.ts:13`, no non-spec caller).

## 2. Take

All rows: idea only (no license).

| Item | Mechanism and `path:line` | Framework part it changes | Why better | Effort |
|---|---|---|---|---|
| Decision event log with denials | Every gate result, allowed or denied, is an event (`workflow-engine.ts:212-233`, `:254-290`); state is a fold (`fold.ts:102`). Derived metrics: first-pass approval, rework per iteration, denial hotspots by state, state durations, blocked episodes (`src/workflow-analysis/insight-rules.ts`, `packages/workflow-control-center/src/analytics/cross-session-analytics.ts`) | `audit.sh` (raw commands only), scattered `state/*` files; the "Not measured" gap | First step to asking if ceremony pays: a state with clustered denials is flagged as "guardrail/task mismatch". Use JSONL per ticket, not SQLite. It measures process, not outcomes: add cost and post-merge regressions | M |
| Pure decisions over a facts snapshot | Guards are pure functions of `{state, gitInfo, from, to}` (`dsl/domain/types.ts:11-16`, `states/committing.ts:14-32`); I/O sits behind injected deps; tests are `spec.given(...events).withDeps(...).when(...)` (`testing/domain/workflow-spec.ts:12-55`) | `compute_next` (`fw: gate.sh:321`) calls git and files inline | Split into `collect_facts > facts.json > decide`. Gives `next --json` for free and table tests with no git fixture. Keep the end-to-end runs | M |
| Stop refusal tied to state, default on | Idle is denied unless state allows it: lead only in BLOCKED or COMPLETE, developer until `signal-done` (`workflow-predicates.ts:31-50`) | `stop.sh`, `stop_followups: 0` (`fw: config.yml:59`) | Reuse `next`'s verdict and refuse by default. Delete the knob. Needs the BLOCKED exit below or it deadlocks | S |
| Universal BLOCKED with return-only exit | Any state can enter BLOCKED, skipping guards (`workflow-engine.ts:163`); leaving is legal only to the prior state (`states/blocked.ts:12-18`, `fold.ts:39`) | `blocked-on-answers`, which freezes all product writes | Agent gets a legal "I am stuck" move per ticket that also permits stopping. Narrows the block to one ticket | S-M |
| Procedure files keyed to state | `states/*.md` total 162 lines, 9-24 each. Printed on successful transition, and the current one re-printed on a failed transition (`output-guidance.ts:7-25`). Commit 0a60e5e removed per-tool injection because tokens accumulated | Railroad parts of the 18 skills (769 lines) | The script chooses what the agent reads, at the moment it matters. A refused move re-teaches instead of relying on skill routing | M |
| Remote CI as off-box evidence | Terminal state needs live `gh pr checks` (`states/feedback.ts:15`, `workflow-adapter.ts:35`, `infra/github.ts:4-11`) | `pr_checks` and ship are local only (`fw: gate.sh:1042`) | Harder to forge than local stamps. Treat "pending" apart from "failed"; here both are `false` | S |
| Three-way result | `success | blocked | error` mapped to exit 0, 2, 1 (`workflow-engine.ts:18-21`, `cli/domain/exit-codes.ts`) | `next_exit` overloads exit 1 | Separates "agent has work" from "step failed". Needed by any orchestrator | S |
| Legal operations per state | `allowedWorkflowOperations` on each state (`states/*.ts`, `workflow-predicates.ts:52-58`); illegal moves list legal targets (`workflow-engine.ts:155-160`) | `next` prints one move in prose | Expose `legal_ops` in `next --json` as a discoverable API | S |
| Catch-all PreToolUse | No `matcher` in `hooks/hooks.json`, so Grep, Glob and MCP all reach the hook; `pattern` is extracted too (`pre-tool-use-handler.ts:70-74`) | `matcher` (`fw: .claude/settings.json:19`), `*) exit 0` (`fw: adapt.sh:85`) | Closes the verified Grep/Glob gap. Extract `path` and `glob`, not `pattern` alone. Their engine does this at high cost; a bash deny-list would be cheap | S |
| Framework outside the project tree | `.claude-plugin/`, `${CLAUDE_PLUGIN_ROOT}`; lint config lives in the plugin, not the repo (`workflow.ts:219`) | Copy-in, `scripts/` collision, agent-writable policy | Clean split of framework and project files, and an agent cannot weaken policy it cannot reach. Claude-only here, so treat as one install target over a small CLI | L |

## 3. Challenges

- **Bash plus files as runtime.** The repo uses typed TS, Zod and SQLite. Types did give exhaustive registries. But it needs Node 22 and `npx tsx` per tool call with a 30s timeout, and a harder runtime did not stop the worst defects (section 6). Verdict: framework's dependency footprint wins. `gate.sh` at 1,242 lines still needs the facts/decide split. A compiled single binary is a fair later question; this repo offers no evidence on it.
- **Scripts own the loop.** Here an LLM lead follows checklists and calls `transition`. Guards stop illegal moves but nothing makes the next move happen. Framework's `advance` is right. This repo's own stop gate exists because the LLM lead is unreliable.
- **Tickets as unit.** Here a session holds iterations; state is keyed to a host session ID in one per-user DB. Verdict: the framework is right that a durable ticket owns the state. Session keys cannot move across clones or CI. Iteration lists inside one approved plan are worth noting: one human approval covers several fresh-agent runs.
- **Three lanes.** Here one lane of 11 states for everything; a typo gets a team, a planning round and CodeRabbit. Its own insight rule flags RESPAWN overhead (`insight-rules.ts`, `highRespawnOverhead`). Framework right.
- **Review on changed lines.** Reviewer "reviews each line of changed code" and returns a bare APPROVED or REJECTED. There is no findings format, no reasons recorded, and approval binds to no hash. It reviews before commit, so nothing ties approval to what is committed. Framework's report tied to HEAD is stronger, despite its known gaps.
- **Human accepts every ticket.** Here a human approves the plan, then no one until the draft PR. That placement is right and supports a batch-approval unattended mode. The enforcement is wrong: `record-plan-approval` is any agent's claim (`workflow.ts:25`). Move the gate to plan level, and bind it to something an agent cannot write.
- **18 skills, long AGENTS.md.** "Code guides, prompts assist" (`CLAUDE.md`, P6) supports moving step procedure into gate output. Keep skills for judgment only. But agent prompts here are 83-136 lines, so it is no proof that less prose suffices.
- **One hook set for three tools.** Engine plus per-host adapter looks cleaner, but `adapt.sh` with one rule set is simpler and more honest. See OpenCode in section 6. Framework stays; only the event-type split (start, tool, idle) is worth checking.
- **Selftest as main proof.** 100% unit coverage, dependency-cruiser and knip all passed while the sole command path pointed at a deleted file. `/* v8 ignore */` covers the wiring (`src/shell.ts:52`, `docs/testing-strategy.md`, "pure wiring"). Strong evidence that framework end-to-end railroad runs matter more than coverage. Add a check that every path named in commands, hooks and skills exists.
- **Hooks as regex.** Same weakness, narrower list. The better pattern here is checking effects at the transition: HEAD pinned on entry, new commits refused (`states/developing.ts:18`). Hooks warn; gates verify. Framework should say this explicitly.

## 4. Delete or simplify

- `limits.stop_followups`: remove, make refusal the default (depends on the BLOCKED move).
- `audit.sh` and its daily action logs: fold into the event log.
- Railroad procedure in skills: shrink to state files. INFERRED candidates: `agentic-implement`, `agentic-route`, parts of `agentic-pr`, `agentic-critic`. I did not read these skills.
- Config knobs generally: "Strict, not flexible" (`CLAUDE.md`, P1) argues for fewer. Dead `tracker` and `models.*` should go first.
- Do not add a dashboard. JSONL plus one `gate.sh report` command is enough. This repo shows the cost of the other choice: 5,965 lines of analytics and UI against a 1,966-line workflow.

## 5. Orchestration

- **Standalone.** The lead is the orchestrator, using experimental Claude agent teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`). One feature, one machine, no parallelism. Not reusable outside Claude Code in practice.
- **Good plug-in shape.** A closed list of named operations gated by state (`entrypoint.ts:18-37`) maps neatly onto an API. An orchestrator could replace the LLM lead and call `transition` directly. For the framework: `next --json`, `advance --json`, three-way exit, `legal_ops`, plus an event stream to tail.
- **Fresh context as enforced invariant.** `respawn.ts:17` refuses to proceed while agents are registered. For the framework, an orchestrator gets this naturally: a new worker per step, with the state in the ticket.
- **Missing, and needed.** Actor identity: no operation knows who called it, so an orchestrator should issue a per-role token or env value that the gate records and checks. Concurrency: read-fold-guard-append has no expected sequence number; `BEGIN IMMEDIATE` covers only the append (`sqlite-event-store.ts:66`). If the framework adopts events, require expected-seq. Sharing: a per-user DB solves nothing across clones. INFERRED better home: JSONL committed on the ticket branch, so CI can read it.

## 6. Do not copy

- **Self-attested evidence.** `review-approved`, `signal-done`, `record-plan-approval` and `coderabbit-feedback-ignored` are bare state-gated flags (`workflow.ts:117-204`). The lead records the reviewer's verdict, and the ignore path needs no reason. This repo has the same two trust gaps as the framework and no answer to either.
- **Regex command guard.** `(?:^|\s|&&|;)git\s+commit...` (`bash-enforcement.ts:9`). VERIFIED with an equivalent pattern in my own script: it catches `git commit -m x` and misses `(git commit)`, `git -C . commit`, `/usr/bin/git commit`, `a|git commit`, `$(git commit)`, `bash -c`, `python -c`. Only commit, push and checkout are listed (`registry.ts:15-17`), so "the PR stays a draft" is unenforced: `gh pr ready` and `git merge` pass.
- **Procedures that conflict with hooks (VERIFIED by reading).** Only COMMITTING exempts `git commit` and `git push` (`states/committing.ts:10-12`), but `states/pr-creation.md:8` says "fix and push" and `agents/feature-team-developer.md:130-132` commits and pushes in CR_REVIEW. Neither state has `allowForbidden`. No test crosses prose and policy.
- **Emoji identity check.** Tools are denied if the lead's last text lacks the state prefix (`workflow-engine.ts:328-348`, `identity-verification.ts`). Weak signal of drift, tied to transcript format. INFERRED: developer tools are gated on the lead's transcript, since the path comes from session state.
- **Per-tool-call cost.** `pre-tool-use-handler.ts:50-66` makes three engine calls, each rehydrating the full log and reading the transcript tail, writing at least 6 events per tool call, under `npx tsx`.
- **Global activation.** `SessionStart` starts a workflow for every session (`workflow-runner.ts:265-268`). INFERRED: any ordinary session with the plugin enabled sits in SPAWN with git blocked, and is denied all tools after its first unprefixed message.
- **Fail-open.** Unknown session allows (`workflow-runner.ts:271-273`); exceptions exit 1 (`src/shell.ts:167`), which does not block (ASSUMED from Claude Code behavior; `fw: adapt.sh` comment agrees that exit 2 blocks). Framework's fail-closed PreToolUse is better. ASSUMED: a deny JSON on stdout with exit 2 loses the reason.
- **Small bugs that show the risk.** `tickFirstUncheckedIteration` ticks the first `- [ ]` in the whole issue body, and SPAWN copies the user's spec there verbatim (`infra/github.ts:48`). `reviewRejected` is not cleared when DEVELOPING is re-entered, only on a new iteration (`fold.ts:53-57`, `:123`). OpenCode's idle hook re-prompts in any state, including BLOCKED and COMPLETE (`opencode-workflow-plugin.ts:66-76`). Its gates compare against `Bash`, `Write` and `file_path`, passed raw (`:182`). ASSUMED: real OpenCode names differ, so enforcement is inert there; specs use capitalized stubs.
- **Overbuilding and drift.** Two separate insight-rule implementations. 1,337-line `build-workflow` skill for generating plugins. PRDs of about 3,800 lines in the repo, the same history leak the framework has. `agents/feature-team-lead.md:18` still describes the injection removed in 0a60e5e. `docs/architecture.md` describes an `IdentityCheck` union absent from the engine.
- **Hard dependencies.** GitHub, `gh`, CodeRabbit, an experimental Claude feature.
- **Suspicious content.** None found. Note `postinstall` runs `git config core.hooksPath .githooks` (`package.json`), a side effect on the cloner's repo config. Agents are denied reading plugin source (`workflow.ts:230-247`): an interesting but regex-based anti-gaming rule; not worth copying.

## 7. If you rebuilt the framework

Keep bash-level portability, `advance`, tickets, lanes, fail-closed hooks and end-to-end runs. Change the shape in four ways this repo suggests: a small facts collector feeding a pure decision table; an append-only event log per ticket on the branch, from which status and metrics derive; state-keyed procedure files printed by the gate in place of railroad skills; and an installable core outside the project tree, with policy the agent cannot edit. Add what this repo lacks: actor identity and unforgeable reviewer and human evidence.

## 8. Coverage

Read in full: `README.md`, `CLAUDE.md`, all `states/*.md`, `commands/*`, `agents/*`, `hooks/*`, CI, `.githooks`, `workflow-engine.ts`, `workflow-runner.ts`, `pre-tool-use-handler.ts`, `bash-enforcement.ts`, identity, output, transcript readers, event store, `workflow-spec.ts`, `workflow.ts`, `fold.ts`, `spawn-rules.ts`, predicates, registry, all state `.ts`, infra git and github, `src/shell.ts`, entrypoint, `insight-rules.ts`, most of the OpenCode plugin. git log, plus selected commits.

Partly read: `docs/architecture.md`, `docs/testing-strategy.md`, `docs/research/SUMMARY.md`, cross-session analytics, `build-workflow.md` (first 50 lines), specs (samples).

Not read: control-center UI and server, most of `src/workflow-analysis`, PRDs, other research docs, framework skills. Framework compared via `gate.sh` excerpts, `adapt.sh`, `stop.sh`, `audit.sh`, settings and config.

Nothing from the repo was run; the only execution was my own regex check. Confidence: high on engine, guards and defects; medium on Claude Code and OpenCode runtime behavior, labeled ASSUMED. `MANIFEST.tsv:22` lists the license as NONE, matching the repo's own files.
