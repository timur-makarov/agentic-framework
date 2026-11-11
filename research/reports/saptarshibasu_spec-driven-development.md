# saptarshibasu/spec-driven-development

Licence: Apache-2.0 (`LICENSE`, `.agents/LICENSE`). Code may be copied with notice. One author, 93 commits, 2026-06-24 to 2026-07-13.

## 1. What it really is

- A prompt kit, not a runtime. Nearly all "logic" is markdown: 9 agents (1,275 lines) and 7 skills plus phase references (1,544 lines). About 848 lines of bash do scaffolding, mirroring, log condensing and file copying. No script knows workflow state. VERIFIED. 9,459 of 17,873 lines (53%) are generated mirrors. VERIFIED.
- The gated pipeline (Route, Specify, Plan, Tasks, Analyze, Tests red, Implement, Review) lives only in `.agents/skills/develop-feature/SKILL.md` and its `references/`. "Deterministic guardrails" (`README.md:8`) means an optional pre-commit hook and CI, neither distributed by the updater (`kit-manifest.conf:45-54`). There are no agent runtime hooks at all. VERIFIED.
- No tests. No sample `specs/` run: `specs/` holds only `contracts/.gitkeep`. `AGENTS.md:98` says "no test suite". Git history suggests real use (the Copilot "always Sonnet in JetBrains" bug, `model-map.conf:20`). INFERRED.
- README claims the code does not support:
  - "Your `src/`, `tests/`, CI, and existing docs are untouched" (`README.md:311-312`). False: `file=docs/README.md` overwrites a host's file, and `dir=templates` merges into a host's `templates/` (`kit-manifest.conf:94,100`). `mirror-agents.sh:119-121` deletes every `*.md`/`*.toml` in `.claude/agents`, `.github/agents`, `.codex/agents`, including a host's own agents. VERIFIED by reading.
  - **First-time adoption looks broken.** `.agents/model-map.conf` is not in the manifest (`kit-manifest.conf:85-100`), and `mirror-agents.sh:56` dies without it. `update-kit.sh:164` runs that script under `set -e`, so files get copied and then mirror generation aborts on a clean project. VERIFIED by reading, not executed (brief forbids running it).
  - "Unchanged files are skipped" is true only for `file=` entries; `dir=` is a blind `cp -R` (`update-kit.sh:122,136`), and `--dry-run` then shows only the directory. VERIFIED.
  - "Mirrored byte-for-byte" (`README.md:34`): every mirrored SKILL.md differs from canon, by design, because guardrails are expanded (`mirror-skills.sh`; confirmed with `diff`). VERIFIED.
  - `AGENTS.md:58` says `.ps1` twins must be byte-identical and CI's guard depends on it. CI only parses `.ps1` (`agent-harness.yml:147-171`), and only if `pwsh` exists. VERIFIED.

## 2. Take

Framework has nothing equivalent unless stated. Apache-2.0 throughout, but items 1-3 are better rewritten than copied, because the source has the bugs in section 6.

| # | Item | Mechanism and `path:line` | Framework part it changes | Why better | Effort | Copy / idea |
|---|---|---|---|---|---|---|
| 1 | Ownership manifest, push-style updater, nothing maintainer-only ships | `.agents/kit-manifest.conf:85-100` is data read by `update-kit.sh`; ADRs, changelog, version and updater stay in the kit (`kit-manifest.conf:38-83`). CHANGELOG [0.2.0] stripped `(ADR-000N)` citations from shipped files so nothing depends on them | Copy-in distribution; "template history leaks"; the 22 selftest failures after deleting ADRs | Separates framework from project files and gives an upgrade path. Add what this repo lacks: a lock file with version and per-file hash, so upstream deletions and local edits are detected (section 6). Keep all framework files under one namespace | M | Idea; rewrite |
| 2 | Red baseline: tests must fail before implementing, for the right reason, written by someone else | `test-writer.md` ("Errors ≠ valid red"); `implementor.md` hard rules: never writes or weakens tests; `phase-3.7-tests.md`. Prose only here | `Check:` commands, which `gate.sh` runs only post-edit. No red phase exists in `gate.sh` (VERIFIED by grep). Addresses "weaken a check" | Make it mechanical: at claim, run `Check:` commands and record a hash plus failing exit in the claim commit. A check that passes before any change proves nothing, so `advance` rejects it (or requires `check_kind: regression`). The hash also closes "Check: is mutable" | S-M | Idea |
| 3 | Amendment is an explicit transition that invalidates downstream evidence | `SKILL.md:172-212`: "Record, then flip" writes the change to Pending Amendments before reverting Status, then "Cascade the reopen" re-runs downstream phases | "Contract fields are mutable after claim" | Script it: `gate.sh amend NN` is the only legal way to change tier, `Check:` or scope. It records the reason, voids stamps and critic reports, and needs a human on any weakening. CI compares contract fields with the claim commit | M | Idea |
| 4 | Spec-gap findings are first class, and the reviewer checks every category | `code-reviewer.md:59-84` reviews spec conformance, boundaries and test integrity, not just changed lines. `code-reviewer.md:119-135` forces a per-category table before the verdict; `artifact-analyzer.md:78-83` recites requirements one at a time | `bound_findings` (`lib.sh:481`), `agentic-critic`. A *missing* behaviour has no added line to cite, so it cannot exist as a finding today | Add `F1: contract:<item>` as a valid anchor. Require a `## Checks` table with fixed rows and reject the report on any malformed `F` line, so nothing drops silently. The table is shape evidence, not proof of a reviewer | S-M | Idea; the anti-skim wording is copyable |
| 5 | Severity ends the loop; stuck findings go to a human | ADR-0004 (`docs/adr/0004...:64-82`): zero findings at *all* severities never converged, since a reviewer told to report nits finds new ones each pass. Only top severities gate. `phase-5-review.md:48`: a finding surviving two rounds goes to a human. `code-reviewer.md:95`: `Kind` picks the fixer | `findings_judged` (`gate.sh:254-272`), where every finding is equal and `declined` needs no reason | Grounded failure lesson. Add `Blocker/Should-fix/Nit`; only Blocker needs fixed-or-reasoned-decline; decline of a Blocker on HIGH needs a human; a repeat finding halts `advance`. `Kind` is optional | S | Idea |
| 6 | Condensed sensor output | `scripts/quiet.sh`: PASS line on success; on failure, first relevant error plus up to 40 lines and a log path; timeout | `verify.sh:85` prints full output to the agent | Direct token saving and a hang guard. Must fix the macOS bug first (section 6) | S | Copy with fix |
| 7 | Inputs are paths, not text | `phase-1-specify.md:9` "paths, not rule text"; `SKILL.md:101-103` "a file they can read is a durable input, a remark in this conversation is not" | Critic brief; future `--json` | Clean contract for any orchestrator and fresh subagent. `next --json` should list role, model and input paths | S | Idea |
| 8 | Rule packs as data with stable IDs | `.agents/extensions/README.md`: paired rules and opt-in files, `SEC-01` IDs with a Verification list, cited in findings; no opt-in file means always on | `agentic-security`, `agentic-api`, `agentic-migrate`, `craft_skills` | Attach packs by `risk_paths` glob, not by human opt-in. Shrinks skills to data and gives findings citable rule IDs | M | Idea; `security-baseline.md` copyable as a starting list (self-described as directional) |
| 9 | Test-intent docstrings | `test-writer.md:59`: each test names its requirement ID and why it matters | Done Contract, `floor-guard.sh` | Tells "wrong test" from "regression" in a fresh context. Prose-level, cheap. Could lint for an ID on tests in the diff | S | Idea |
| 10 | Tier map applied at generation time | `model-map.conf` plus `map_lookup` in `mirror-agents.sh`; an unknown tier is a hard error | Dead `models.*` | Only worth it if subagents multiply; today the framework has one (`agentic-evaluator`, identical in `.claude` and `.cursor`). Otherwise delete `models.*` | S | Idea |

Small extras, S effort: CI check that canonical files end in a newline, because "agent prompts have shipped cut off" (`agent-harness.yml`); `bash -n` over shell scripts; propose-only `AGENTS.md` corrections when a documented command proved wrong (`implementor.md`, "AGENTS.md corrections").

## 3. Challenges

- **Bash and files as the runtime (vs a prose orchestrator). Framework is right, and this repo is the best evidence for it.** Its history is prose patching agent misbehaviour:
  - `cb12e76` adds "Never approve your own work", so agents were approving.
  - `e376a88` adds the "rigid two-value enum" (`SKILL.md:229`) because a third Status value "can silently pass through gate detection".
  - `02ffd4d` tells the agent to "literally" re-read Status headers because it carried stale conclusions.
  - `684a775` adds checkbox reconciliation.
  - Each is a state-machine bug fixed with more prose, and the file grew to 345 lines. In the framework most of these cannot occur. INFERRED that these commits reflect real failures; the messages say "defect" and "fixed".
- **A human at every gate vs the framework's single acceptance.** This repo has 3-4 human stops per feature, plus route approval, plus a human commit per story. ADR-0002 and ADR-0003 themselves name rubber-stamp risk. The framework's one acceptance is cheaper, and neither allows unattended work. Keep the gate at intent, make it policy-based, and do not copy this gate count. This repo is no better on enforcement: `Approved — <who>` and the `Approved by` column are agent-written text with no check (`SKILL.md:221-223`). VERIFIED.
- **Risk lanes vs tracks.** Tracks A-D scale *planning artifacts*; framework tiers scale *verification*. The framework is right to derive tier from path floors. Here the agent proposes the track with no floor, so an auth change can be proposed as Track A; only a human reading the one-line proposal stops it. Planning depth is a real second axis, but the framework already has `agentic-interview` and `agentic-idea`. No change.
- **Review limited to changed lines. This repo is right on scope.** Conformance to intent cannot always be anchored to an added line. Its re-check pass ("re-read only the files touched", `code-reviewer.md:177`) is the sensible place for narrowness. See Take 4.
- **Ticket as unit.** Feature, then story, then task, with TDD per story, gives smaller review diffs but needs decision-log parsing to resume, which is its fragile part. Keep flat tickets and split big work into tickets.
- **Copy-in. Both agree on copy-in.** ADR-0007 rejects a package because files must live in the project. Correct for skills and hooks, and the updater is what was missing. But its removal of version tracking is wrong (section 6).
- **18 skills vs 7 skills + 9 agents. Split, but do not chase the count.** The role rule is clean: a skill runs at top level and can talk to a human; an agent runs fresh and returns one report (`docs/guardrails.md`, commit `a90ca0f` removing agent-to-agent calls). Its prompt prose (2,819 lines) is about three times the framework's 956 (skills, `AGENTS.md`, `judgment.md`). Framework's `NEXT` output is better progressive disclosure than "read this phase file now".
- **One hook set for three tools.** This repo has none, so it has no opinion worth weighing. Per-agent `tools:` lists give it some real restriction on Claude and possibly Codex. `code-reviewer` still has `Bash`, so "read-only" is advisory; on Copilot `tools` is dropped entirely (`mirror-agents.sh:235-243`; `.github/agents/code-reviewer.agent.md`). VERIFIED. Framework's approach stands.
- **Mirrors vs symlinks.** Framework's symlinks (`.claude/skills/* -> .agents/skills/*`) beat four copies. Every fix here touches four directories. Generate only where formats differ.
- **Selftest as proof.** Framework's is far ahead of this repo's nothing. Neither measures outcomes. ADRs here say "in practice" without data.

## 4. Delete or simplify

- `models.*` config, unless a generator applies it (Take 10).
- `agentic-status`: named by no script, by `AGENTS.md`, or by any other skill (heuristic grep), and `gate.sh next --all` does the job.
- Run this repo's **reachability audit** on framework skills and docs. Its 0.2.0 release deleted 5+ docs because none was referenced from a live shipped file (KIT-CHANGELOG `[0.2.0]` Removed). My name grep finds 12 of 18 framework skills unnamed by `scripts/` or `AGENTS.md`, though most are named by another skill or are user-invoked, so this is a lead, not a verdict. VERIFIED counts, conclusion INFERRED.
- Ship no ADRs and no framework `CONTEXT.md`; make ship independent of them (Take 1).
- Do not build per-file partial ownership: `partial=` and `KIT:BEGIN/END` merging was built and removed here (ADR-0007 revision). Whole-file ownership only.
- Do not build `tracker` or Windows twins speculatively. `.ps1` twins add 496 lines with no parity test.

## 5. Orchestration

- Standalone: conversational only, with a human driving every stop. As a plug-in it offers nothing today: no CLI, no JSON, agents never commit (`phase-3.7-tests.md:31`), "stop for approval" everywhere.
- Useful shapes:
  - Phase-to-role table with fresh subagent per phase and path-only inputs (Take 7).
  - The orchestrator owns all loops, since sub-agents cannot call each other (`phase-5-review.md:14-16`). That maps directly onto an external orchestrator.
  - An escalation request is a structured return value (`implementor.md`, "Escalation"), which suggests `blocked: {reason, needs}` in `next --json`.
  - `decision-log.md` is effectively an event log. An orchestrator would want it as JSONL with signed or external actor identity, not a markdown table.
- Resume rule worth keeping: real state beats recorded state. Run the test; a `[x]` box with a red test is a regression (`implementor.md`, step 1). Framework's evidence freshness already follows this.

## 6. Do not copy

- The prose state machine, including decision-log rows as story state (`SKILL.md:148-162`). Parsing an LLM-written table for control flow is exactly what the framework avoids.
- **Track B resume bug.** `step-0-scaffold.md:50` deletes `plan.md`, yet resume requires all three documents `Approved` (`SKILL.md:141-146`) and otherwise goes to the first non-approved phase. A Track B feature cannot reach the story loop on resume by the letter of the protocol. INFERRED from reading. Same family: `tasks.template.md` marks `plan.md` "required".
- `quiet.sh:47` calls `timeout`, absent on stock macOS (none on this machine, `command -v` checked). Default `QUIET_TIMEOUT=300` means every wrapped command would report exit 127 as FAIL. INFERRED from reading plus that check, not executed. The author fixed other macOS bugs but not this one.
- CI vs hook contradiction: `aedad1f` lets Draft specs with markers commit (`pre-commit:47-59`), while CI fails on any marker in `specs/` (`agent-harness.yml:47`). VERIFIED.
- Dropping version tracking (ADR-0007 revision). "Never deletes" plus no installed version means removed files linger forever, and ADR-0007 admits the project cannot tell its version. Fix with a lock file, not by removal. Also `update-kit.sh` targets paths like `docs/README.md` and `scripts/`, so a collision is silent.
- Dangling distribution: `test-writer.md:39` cites `tests/README.md` and `phase-5-review.md` relies on `.githooks/pre-commit`; neither ships. `phase-3.7-tests.md:10` says Track A test-first is "enforced in the commit message", which enforces nothing. VERIFIED.
- Coverage floor and static analysis "deterministic gates" run by the LLM reviewer (`code-reviewer.md:32-57`). Those belong in scripts; a model's report of them is not evidence.
- Reviewer "ideally pinned to a different model family" (`code-reviewer.md:11`): unenforced, and the shipped map uses one family per tool.
- The Codex output shape (`[agent]` table, `instructions`, `tools`) may not match what Codex reads. ASSUMED risk, unverified; check before adopting any generator.
- No suspicious or injection-style content found.

## 7. If you rebuilt the framework

Keep the `gate.sh` decision table, evidence stamps, hooks and floor-guard: this repo shows what happens without them. Change the shape at the edges. Make everything framework-owned live under one namespace, declared by a manifest and tracked by a lock file, with maintainer history kept out. Make contract state immutable after claim except through `amend`, record a red baseline at claim, and let reviewers anchor findings to contract items with graded severity so the loop terminates. Express domain rules as path-triggered packs instead of skills. Reduce skills to those reachable from `NEXT`, with `next --json` naming role, model and input paths.

## 8. Coverage

Read in full: `README.md`, `AGENTS.md`, `CLAUDE.md`, all bash scripts (`update-kit`, `mirror-*`, `quiet`, `start-feature`), `.githooks/pre-commit`, `agent-harness.yml`, `kit-manifest.conf`, `model-map.conf`, `develop-feature` SKILL plus all 8 references, agents `code-reviewer`, `implementor`, `test-writer`, `artifact-analyzer`, all 7 ADRs, `docs/guardrails.md`, `.agents/extensions/README.md`, decision-log, learnings and tasks templates.

Partly read: `init-project` (first 120 lines), `spec.template.md`, `security-baseline.md` (2 of 7 rules), `KIT-CHANGELOG.md` (first 150 lines), `git log` subjects with diffs for 3 commits and stats for 7.

Not read: `.ps1` scripts, `planner`, `specifier`, `task-decomposer`, `debugger`, `docs-writer` bodies (only greps and commit diffs), `clarify-spec`, `check-spec`, `amend-constitution`, `sync-agents-md`, `create-adr`, `agents.template.md`, `constitution.template.md`.

Framework read: `README.md` (first 60 lines), `config.yml`, `verify.sh`, parts of `gate.sh` and `lib.sh`, plus greps. Nothing from the repo was executed.

Confidence: high on what the code does and on the framework comparison; medium on items marked INFERRED; `model-map.conf` and `timeout` failures rest on reading, not a run.
