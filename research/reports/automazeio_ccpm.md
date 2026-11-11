# automazeio/ccpm

Paths are relative to the clone unless they start with `fw:` (`agentic-framework/`). `R/` means `skill/ccpm/references/`. License: MIT (`LICENSE`, Ran Aroussi 2025), so code may be copied with the notice kept. Claims are VERIFIED (read in code) unless marked otherwise. Nothing from the repo was executed.

## 1. What it really is

A planning-and-delegation skill, not a harness. One `SKILL.md` (84 lines) routes to 6 prose references (1,188 lines with SKILL.md) and 16 bash files (1,819 lines). `neon-branch.sh` alone is 529 of those, 29%, for the sponsor named at `README.md:15`. Flow: PRD, epic, task files in `.claude/`, GitHub issues, parallel subagents. 92 commits, 8,400 stars claimed, almost dormant from March to November 2026 (`funding.json:19`). v2 (`af74666`) cut 8,726 lines from a slash-command system down to 1,156.

Every state change is prose the LLM retypes. Reporting scripts only read (no `sed -i` or file writes in status, standup, next, blocked, validate, epic-*, prd-*, search, in-progress). There are no hooks, no tests, no CI, no review step and no gate. "Enforces" (`README.md:131`) means asks nicely.

README claims the code does not support:
- **"Eval score 100%", 4/4 vs 2/4** (`README.md:3,383-392`). The evals are not in the repo: `skill/ccpm/evals/` is gitignored (`.gitignore:2`), and no branch I listed has eval files. `funding.json:19` lists CI that runs them as future work. The rows measure skill compliance ("correct paths", "runs script"), not delivery outcome. An agent that reads a skill beating one that lacks it says little.
- **That 100% coexisted with a broken core flow.** From v2 until `0bcfabb` (2026-11-04, 7.5 months) `sync.md` used `gh issue create --json`, a flag the fix commit says does not exist, plus a `sed` that per the same commit empties the body on GNU sed. It is still documented at `R/conventions.md:102`, while `R/sync.md:33` forbids it.
- **"89% less time", "75% reduction in bug rates", "3x"** (`README.md:377-381`): no source, method or data anywhere.
- **"Falls back to task lists"** (`README.md:411`): no fallback. `R/sync.md:85` just skips linking. So `R/sync.md:204` (`s/- \[ \] #<N>/`) has nothing to match; `R/structure.md:89` writes `- [ ] 001.md`, and sync never writes `#N` lines (INFERRED no-op).
- **Source of truth is claimed both ways**: GitHub Issues (`README.md:115,121`) and files (`README.md:325`). In v2 it is files. Scripts never call `gh`; v1's bidirectional `sync.md` was dropped, yet `help.sh:53` still advertises it. A human closing an issue on GitHub does not reach local state.
- **"Without conflicts"** (`README.md:176`) vs agents sharing one worktree (`README.md:157`). `funding.json:19` even says "separate git worktrees".
- **"Harness-agnostic"** (`README.md:184`): `Task:`/`subagent_type` blocks (`R/execute.md:131`, `R/structure.md:35`) and `.claude/` paths are Claude Code shapes. No harness-specific test exists.
- **"Every line of code must trace back"** (`README.md:129`): nothing checks the `Issue #N:` commit format.

## 2. Take

| Item | Mechanism and `path:line` | Framework part it changes or replaces | Why better | Effort | Copy or idea |
|---|---|---|---|---|---|
| Batch acceptance at a publish point | The human says "sync" once, after reviewing PRD, epic and task list; then N tasks may start (`R/structure.md:98`, `R/sync.md:23`). Prose only in CCPM. | "Every ticket needs a human", "no unattended mode", one waiting ticket freezing writes (`fw:scripts/gate.sh:compute_next`) | Human effort moves to one reviewable plan. Accepting a parent can open its children. To be safe it must be gated: a parent hash, tiers capped at accept time, HIGH still per ticket. | M | Idea (MIT) |
| A plan layer above the ticket | `structure.md` turns one epic into tasks with `depends_on`/`conflicts_with`; `plan.md:96` caps at about 10 tasks and says "prefer simplicity over completeness". | Framework has `blocked_by` and frontier logic but no decomposition skill (grep found none; `agentic-grill` only mentions "splits" of interpretations). | Adds the missing step. Output must be plain tickets with disjoint `scope_paths` and `blocked_by`, plus a `parent:` field. Not a new artifact type. | M | Idea |
| Tracker as ID and shared-state source | Files renamed to the issue number after sync (`R/sync.md:92-100`). Issue numbers are globally unique across clones. | `refs/agentic/nn` local-only numbering; dead `tracker: github-issues` (`fw:.agentic/config.yml:6`) | Solves the "local state is not shared" gap for numbering. Better than CCPM's version: create the issue at `gate.sh new` so the ID never changes, skipping the fragile rename (`R/sync.md:98`, `\b` in sed is not portable to BSD, INFERRED). | M | Idea |
| Idempotent tracker write-back | Write `github: <url>` immediately after each create; skip files that have one, so a re-run cannot duplicate (`R/sync.md:55,59,90`). Number parsed from the returned URL (`:39`). `--repo` always explicit (`:47`, learned in `23616e7`). | Any tracker adapter | The three real failure modes, found the hard way. Put it in a script, not prose. | S | Copy the pattern |
| Per-worktree resource provisioning, opt-in | `neon-branch.sh`: no-op exit 0 when not configured (`:105-122`). Epic and per-writer child branches; state file holds names only (`:185`). Env file is `chmod 600` (`:347`), refused if tracked by git (`:314`), and tool output is withheld because it contains secrets (`:396`). | `make_worktree` (`fw:scripts/gate.sh:792`) isolates files only | Parallel tickets share a DB, port or cache today. Generalize: `worktree.setup` and `worktree.teardown` commands in config, run at claim and ship, with `NN` in env. Do not ship a vendor script. | S-M | Idea; the secret-handling checks are copyable |
| Schema change as a serialization point | Migration task is `parallel: false`; users of it go in `depends_on`; child DBs are cut after it lands (`docs/guides/using-ccpm-with-a-database.md:154,176`). | `claims_rule` (`fw:scripts/gate.sh:572`) checks only scope overlap | Cheap rule: a claim touching `migrations_dir` refuses to run beside any other in-progress ticket. Two migrations with disjoint paths still collide on order. | S | Idea |
| Defect link back to origin | `bug_for: <N>` on a follow-up ticket (`R/sync.md:284`). | `agentic-postmortem`, reopen; "not measured" gap | CCPM never counts it, but the field gives the framework a real outcome signal: escaped defects per ticket, per lane, per reviewer mode. Cheap start on measuring whether ceremony pays. | S | Idea |
| Template-remote guard | Refuse tracker writes when `origin` is the template (`R/sync.md:12-17`; `702d9a9`, after users filed issues upstream). | `gate.sh new`, and any tracker write | Fits the "template stays clean" goal. Match the exact remote, not a substring. | S | Idea |
| Sanitize what leaves the machine | `d6453fa` fixed absolute local paths leaking in issue comments. v2 dropped the check. | Future tracker or PR text | Any public output needs a path and secret scrub, by script. | S | Idea |
| Negative triggers in skill descriptions | "Do NOT use for: debugging code, writing tests, reviewing PRs..." (`SKILL.md:3`). | 18 descriptions in `fw:.agents/skills/` | Cheap disambiguation. The rest of that description is too greedy, so copy only the negative clause. | S | Idea |

## 3. Challenges

- **Bash plus files as runtime.** Not contradicted; CCPM uses the same substrate. Scripts have no JSON, and report scripts exit 0 even when nothing is ready; only `validate.sh` exits on health.
- **Scripts own state.** CCPM runs the opposite experiment: scripts read, the LLM mutates by retyping bash from prose. Its bug history is what you would predict: empty bodies, a fictional flag, temp-file races, duplicate issues, all fixed together in `0bcfabb` (`Fixes #1022, #1024, #1027`). Framework is right, and this is the strongest evidence here. Any new framework flow must be a script.
- **Ticket as unit of work.** CCPM says "Issues Aren't Atomic" (`README.md:145`) and adds streams inside an issue, all in one worktree. CCPM is wrong. Concurrent agents share an index and a working tree. `git pull --rebase origin epic/<name>` (`R/execute.md:224`) is meaningless between them and fails on another agent's dirty files (INFERRED). The stream prompt says "if you need to touch files outside your scope, note it... and wait" (`:147`), with nothing to wait on. Keep the ticket atomic; make small tickets in separate worktrees. But CCPM is right that something above the ticket is needed.
- **Human accepting every ticket.** CCPM has no gate, but its implicit batch approval is better shaped. Verdict: replace per-ticket accept with per-plan accept, keep an escape for HIGH. Note the framework's gap (agent can self-accept) stays until acceptance is recorded where the agent cannot forge it, such as a label whose actor CI checks (ASSUMED feasible; CCPM does none of this).
- **Three risk lanes.** CCPM has none. Its only signal is effort size. No evidence against lanes.
- **Review limited to changed lines.** No review exists; "Code reviewed" is an unchecked box (`R/structure.md:78`). One useful contrast: merging an epic is a natural point for a whole-feature review against the plan's success criteria, which line-bound review cannot do. Add as a parent-level check, not per ticket.
- **Copy-in distribution.** CCPM: symlink the skill dir; project data is created in the host. By construction no template history reaches a project, and there is no `scripts/` collision. Right on the split, wrong on the method: no version pin, no upgrade story, and hook registration cannot work by symlink alone. Take the split (tool in one prefix, data in another), not the symlink.
- **18 skills.** v2 collapsed 46 command files, 4 agents and 11 rule files into 1 router and 6 references. Evidence that consolidation is survivable, and 1 trigger is enough where the router works. But CCPM reaches references only through a greedy description. The framework has `gate.sh next`, which already names the step, so most skills need not be auto-triggered at all. Reduce to a few entry skills plus references. CCPM's own total prose (1,188 lines) exceeds the framework's skills (769), so count is not the same as weight.
- **A selftest as main proof.** CCPM has none and shipped a broken core flow for months. Selftest stands. But it should test real external contracts, so a mock `gh` would not have caught the `--json` bug. Needs a real-CLI smoke check.
- **`max_active_tickets: 1` default** (`fw:.agentic/config.yml:58`). CCPM defaults to parallel. Parallelism is its headline, yet the claimed "1x vs 5x" table (`README.md:163`) is arithmetic, not a measurement. Keep default 1 for standalone; an orchestrator sets it by config.

## 4. Delete or simplify

- **Delete `tracker` until a script implements it.** Dead config now. Scope it one-way: create and link at `new`, comment at ship, read state at `next`. No bidirectional sync: CCPM wrote it in v1 and dropped it in v2 (`git show origin/v1:ccpm/commands/pm/sync.md`).
- **Don't add a standup, PRD or stream layer.** `gate.sh next --all` (`fw:scripts/gate.sh:1166`) already gives what `next.sh` and `blocked.sh` give, with real claim data. CCPM's report scripts add no capability.
- **Skip stored progress files.** `completion:` is self-reported, and `standup.sh:40-48` lists every `updates/*/progress.md` as "In Progress" with no status check, so closed issues appear (`in-progress.sh:14` likewise). Derive status from git, never from agent-written percentages.
- **Skills:** see Challenges. v2's cut is the precedent, but it also cut the only hook, so copy the merge, not the removal of enforcement.

## 5. Orchestration

Standalone it is usable only as a planning aid; the conductor is the main chat, an LLM polling `next.sh` (`R/execute.md:213`). As a plug-in it offers little: text output with emoji, exit 0 even when empty, no claim step. Two agents reading `next.sh` take the same task, since `status: in-progress` is an LLM edit (`R/execute.md:113`) and `--add-assignee @me` is not a lock.

Lessons that do transfer:
- A remote tracker is an orchestrator-visible queue that works across clones. It costs a network dependency, so it must be optional; the framework's plain-file mode should remain the default.
- Dependency data must be symmetric and derived. `active_conflicts` reads only the candidate's own list (`lib.sh:73-85`), and `next.sh` ignores `parallel: false` although `R/execute.md:209` relies on it. The framework's derivation from `scope_paths` and both-direction `blocked_by` check (`fw:scripts/gate.sh:582-586`) is better.
- Per-worktree env and resources belong to the claim, not to the agent's memory. CCPM relies on the LLM loading `.env.issue-<N>` for one agent (`R/execute.md:88`).
- An epic branch is a useful integration unit for orchestrators that batch merges, but only with a gate on it. Here it pushes straight to main (`R/sync.md:233-234`).

## 6. Do not copy

- **A hard-coded success claim.** `echo "✅ Task completed — all acceptance criteria met." | gh issue comment` (`R/sync.md:198`) posts this with no check. It forges evidence into the audit trail, which is the exact failure the framework exists to stop.
- **Merge without gates.** Tests are "if detectable", failure handling unspecified (`R/sync.md:227-229`). Then `git push origin main`.
- **Prose-embedded bash as the implementation.** It is untested and retyped per run. `sync.md` is 335 lines of it.
- **Stale surface after a rewrite.** `/pm:*` commands that no longer exist are printed by 10 scripts, and `help.sh` advertises `/pm:sync`, `/pm:import` and others. `init.sh:71-81` creates or copies dirs nothing uses. `validate.sh:25` checks `.claude/rules`. `track.md:19` cites `ccpm/scripts/pm/`. `conventions.md:27` mentions a `context/` system v2 deleted. Shows why the framework's own dead config matters.
- **Unclear commit story.** No step commits `.claude/` (grep: no `git add`, no ignore rule). But the worktree is cut after sync and agents read `.claude/epics/...`, and `R/execute.md:194` blocks on a dirty tree. Either the files are uncommitted and absent from the worktree, or the user commits by hand (INFERRED). Neither is stated. Stream progress written in a worktree is also invisible to scripts run from main.
- **Fail-open parsing.** Empty `status` counts as open (`next.sh:20`). `frontmatter_field` greps the whole file (`lib.sh:38`). The framework's scoped awk is better.
- **Side effects in init.** `init.sh` runs `brew install`, `sudo apt-get install`, an unpinned third-party `gh extension install`, `gh auth login`, creates `CLAUDE.md` in the host (`:35-38,53,63,151`), and `gh label create --force` resets existing labels (`:117`). The framework should ask or print, not do.
- **Greedy triggers.** "Use ccpm any time the user is talking about shipping a feature... even if they don't say 'ccpm'" (`SKILL.md:3`). Not malicious, but it grabs routing. No prompt-injection or malicious content found. Promotional text exists in the README only (Automaze booking link, Neon sponsor).
- **Vendor script in core.** Largest file in the repo is a sponsor's integration. Keep integrations out of the core.
- **Marketing evals.** Compliance scoring with hidden fixtures, shown as a badge.

## 7. If you rebuilt the framework

Keep the core: scripts own state, a decision table, gates, tickets as the atomic unit in their own worktree. CCPM is a useful negative control, showing what happens with the same ideas when prose owns state. It would change the shape in one place: add a thin plan layer above tickets. An `agentic-plan` step produces a capped set of ordinary tickets with disjoint scopes under one `parent`. The human accepts the plan once; children open by script, tiers frozen; HIGH stays individual. Optional tracker adapter as a script, with issue number as ID, one-way and idempotent. Claim-time setup and teardown hooks for per-worktree resources, `bug_for` to feed outcome metrics, and framework code in one prefix with project data in another.

## 8. Coverage

Read in full: `README.md`, `CHANGELOG.md`, `.gitignore`, `SKILL.md`, all 6 references, and `lib, next, blocked, validate, status, standup, in-progress, epic-status, init`. Read part: `neon-branch.sh` (lines 1-140 plus grep), `help.sh`, `epic-show`, `epic-list`, `search`, `prd-*` (grep only), the database guide (lines 1-60 plus headings), `funding.json` (top). History: log, stats for `af74666`, `0bcfabb`, `31f6721`, `7d7e462`, `23616e7`, `d6453fa`, `702d9a9`; the v1 `sync.md` and worktree hook (openings only). `git log -S` failed because the clone is partial, so "no evals in history" rests on `.gitignore` and tree listings of all 7 remote branches, not on a full history search.

Framework read for comparison: `gate.sh` (claim, scope, ship, worktree, `next_all`), `config.yml`, ticket template, `agentic-task`, skill line counts. Nothing was run, so the failure behaviours above are from reading; the GNU sed and `gh --json` facts come from the fix commit's message and I did not test them. Confidence: high on what the code does, medium on INFERRED runtime effects, and none on real-world outcomes, since no data exists.
