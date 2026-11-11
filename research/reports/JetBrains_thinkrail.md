# JetBrains/thinkrail

I read a shallow clone at commit `924783f` (2026-11-10). Paths are relative to that clone. `PLAN §N` refers to `research/PLAN.md`.

The license is Apache-2.0, so code may be copied with the notice kept. All Take items are ideas: the code is TypeScript and tied to pi.

A subagent read the code and wrote a factual report. I checked its main claims myself:
- the reviewer's tool list includes `bash` (`packages/server/src/host/reviewerRole.ts:3-12`);
- review and auto-fix are off by default (`packages/contracts/src/domain.ts:1836-1837`);
- the host commits with `--no-verify` (`packages/server/src/git/git.ts:95`);
- no script or workflow runs `validateGraph` over the repo's specs (grep).

## 1. What it really is

**It's a product: an "agentic IDE".**
- It ships two launchers around one host, `packages/server`: an Electrobun desktop app and a `thinkrail` CLI that opens the same web UI (`architecture.md:10-40`).
- It is about 734 commits old, created 2026-07-08, with 8k stars and the JetBrains incubator badge.

**It runs only the pi agent, in-process.**
- "pi is the only engine" (`goal-and-requirements.md:55`).
- It cannot drive Claude Code. It reads Claude Code *skills* as one source of skills, and nothing more.

**How it works:**
- Every task gets a git worktree "workspace".
- A planning interview writes a temporary task-spec.
- Todos double as plan steps, and the host commits each step.
- An LLM reviewer can review each step.
- Opening a PR and merging are user clicks in the UI.

**The process is mostly prompt text.** The workflow is "skills-only (no YAML pipelines, DAG tools, or stage sessions)" (`packages/pi-thinkrail-workflow/skills/SPEC.md:74-75`). Code enforces commit attribution, the reviewer's output contract and the PR/merge guards.

**CI checks code, not process.** Nothing in CI checks that a spec, plan or review existed (`.github/workflows/ci.yml`).

## 2. Take

| Item | Mechanism and `path:line` | Plan part | Why better | Effort | Copy |
|---|---|---|---|---|---|
| A failure-mode checklist in the reviewer prompt | The prompt opens with "Generated code fails differently from human code". Its review order: intent match; scope drift, including pasted secrets and debug code; verifying the worker's verification claim, watching for "CI gaming" such as weakened tests, `\|\| true` or `as any`; checking that every API called really exists; edge cases; tracing each piece of state from set to clear; checking the module's spec invariants (`packages/server/src/host/reviewerRole.ts:14-88`). Each finding needs a concrete failure scenario, checked against the real code | PLAN §8 reviewer prompt, whose list has four kinds of problem | These are the specific ways agent code fails. Add one block of about 5 lines to `reviewer.md`: weakened or deleted checks, APIs that don't exist, state that is set but never cleared, debug code left in, and a doc the change makes wrong. The default rules (§12) already catch new suppressions on added lines, so the prompt names only what a rule can't see | S | Idea |
| Delete remote branches only if unchanged | The host deletes the remote branch with `git push --force-with-lease=… --delete`, never `gh --delete-branch`. After a merge it reads the PR again, because `gh` also exits 0 when it only queued the merge (`packages/server/src/pr/reviewActions.ts:31-33,207-212`) | PLAN §7, leftovers | The leftover cleanup deletes remote branches of merged and dropped tickets. If someone pushed to a dropped ticket's branch afterwards, that work would be lost. Through REST: read the ref, and delete it only if its sha is the one the journal last saw. Otherwise list it as a leftover with the reason "moved since drop". Merged state is already derived from the squash commit on base, so the re-read is covered | S | Idea |
| Merge queues | Their CI runs on `merge_group` (`ci.yml`). The host only clicks merge, and GitHub queues it | PLAN §7, Merge row; §14 `doctor` | **INFERRED, not tested:** when a merge queue is required, the REST merge endpoint can't merge directly, and adding to the queue needs GraphQL, which cloud sessions block. Add a `doctor` check: if the ruleset requires a merge queue, auto tiers stop at `merge-ready`, with "merge through the queue" as the human act | S | Idea |
| Agent pass/fail decided by deterministic signals | A harness drives a real agent through the skills with scripted users. Pass and fail come from event signals, such as "skill loaded" detected as a `read` of its `SKILL.md`, and "an LLM never decides pass". It runs on demand because it spends tokens (`e2e/workflows/SPEC.md`, `ci.yml:3-4`) | PLAN §22, end-to-end railroad tests | It is the shape for the plan's railroad tests with a live agent. Run `next` on a fixture repo, and assert on journal events and git, never on the model's text. Keep it out of CI, run per phase | M | Idea |
| Pin the key sentences of printed procedures | Unit tests assert that key phrases stay in the skill text, for example that every merge state is named (`packages/pi-thinkrail-workflow/index.test.ts:105-169`) | PLAN §6, procedures printed by `next` | A cheap guard against edits that quietly drop a step from a brief. Optional; a few assertions per procedure | S | Idea |
| A registry of host workarounds | `pi-compatibility.md` lists every workaround for pi with its "removal gate", and rechecks them on each pi upgrade (`AGENTS.md:11-14`) | PLAN §25 limits; `doctor` | The plan now depends on Claude Code details with version gates: `--safe-mode`, the `AGENTS.md` plugin ID (renamed in v2.1.285), `omitClaudeMd`, `terminalSequence`. Keep them as one list in the framework's docs, each with its minimum version and what `doctor` checks | S | Idea |

**Confirmed, nothing to add:**
- Strict verdict parsing. Invalid output counts as a failed review, and `request_changes` with no findings is rejected. The plan's `--json-schema` does the same.
- Approval is blocked while earlier findings are open. The plan's `merge-ready` needs every finding answered.
- One automatic fix cycle, then the person decides. The plan has a review budget.
- Notify only when no one is looking. The `notify` hook fires on `idle_prompt`.

## 3. Challenges

- **Per-module `SPEC.md` files, or one `## Areas` table (PLAN §13)?**
  - Thinkrail has 114 SPEC.md files, linked by `parent` and `depends-on`, with seven agent tools to search and manage them (`packages/spec-graph/SPEC.md:63-71`). Its own evidence argues for the plan's restraint:
    - no check requires a SPEC.md or its sections;
    - `spec_validate` never runs on the repo itself;
    - `implements: [task-open-pr]` (`packages/server/src/pr/SPEC.md:8`) points at an id no file defines;
    - the import-boundary checker hard-codes its rules (`scripts/check-module-boundaries.ts:20-60`) and doesn't read the specs that describe those boundaries.
  - The one doc that stays true is the one a check enrols: `public-surface-checked`, 28 specs compared against the exports (`scripts/specSurface.ts:191-257`).
  - Verdict: the plan is right. Keep one file, capped, with `doc-lint`. Thinkrail is a case of the correction ladder: a doc earns trust only where a check reads it.
- **A planning interview for every change, or tiers?**
  - Thinkrail makes the interview the default "however small" the change. When the agent judged for itself whether work was already specified, most work skipped the spec and the graph drifted (`skills/SPEC.md:270-286`).
  - That supports the plan's choice of floors the agent can't lower (`risk_paths`, size caps), rather than letting the agent judge.
  - It doesn't argue for an interview on LOW tickets, because the plan has no spec graph that could drift.
  - Verdict: the plan holds.
  - One small borrow: "an alternative the agent considered and rejected… is shown… never decided silently" (`:283-285`). A HIGH PR's `## Look at` could name the rejected approach in one line. It's a sentence in the ship procedure, not a field.
- **Tickets?**
  - Thinkrail v1 used a ticket/board workflow as a Claude plugin to build thinkrail itself. v2 doesn't port it, because the product has "no board or ticket system to run against" (`packages/pi-thinkrail-workflow/SPEC.md:120-124`).
  - That is a product-scope reason, not evidence against tickets.
- **Optional review, or required?**
  - Out of the box, review starts from a button, and findings wait for the person (`domain.ts:1836-1837`).
  - The plan requires review on MEDIUM and HIGH, and CI checks it is bound to the patch.
  - The plan is stronger. Thinkrail's Open PR isn't even gated on review: `isPlanReady` only changes the button's style (`apps/web/src/panels/PlanPane.tsx:1204-1213`).

## 4. Delete or simplify

Nothing in the plan gets smaller from this repo. It does show the cost of what the plan has already declined:
- a durable DAG engine (`pi-dag`, built but "not bundled into ThinkRail");
- spec-graph tooling;
- per-step commit attribution. That needs a four-part ownership gate (`packages/server/src/todos/SPEC.md:119-133`), because several chats share a worktree. The plan gives each ticket its own worktree, so the problem doesn't arise.

## 5. Orchestration

- Thinkrail is a host, not something a host can drive. It runs pi in-process and has no CLI or JSON surface for another tool.
- What it teaches about hosts:
  - keep the agent runtime's sessions behind the host;
  - leave PR and merge as deterministic host actions, never agent actions;
  - keep a "Committed outside the plan" section, so unattributed work is shown and never hidden.
- The plan's equivalents: the engine writes the PR and merges, and `status` lists leftovers.

## 6. Do not copy

- **Prompt-only gates presented as a workflow.** The router, the "no implementation before design approval" gate, and every `shipping-a-pr` gate are text.
- **A reviewer called read-only while it has `bash`.** The plan says plainly that the reviewer may run commands, and resets the worktree afterwards.
- **`--no-verify` on host commits** (`git.ts:95`). The plan's guard denies it.
- **A spec graph with link types nothing validates.**
- **Product-only parts:** UI review chats, hunk revert, the Tailscale phone access, and the desktop shell.

## 7. If you rebuilt the framework

The shape stays. Thinkrail is the mirror image of the plan:
- **Its strengths are in code that sits around the agent:** commit attribution, the reviewer's output contract, and the PR and merge guards.
- **Its weak spots are in the process:** prompts, with no CI enforcement.
- **The plan puts the process in the engine and CI.**

The borrowings are small:
- a failure-mode block in the reviewer prompt;
- a lease on branch deletion;
- a `doctor` check for merge queues;
- the deterministic-signal harness for live-agent railroad tests;
- one registry of Claude Code version gates.

## 8. Coverage

**How it was read:**
- A subagent read the core packages: workflow skills, spec-graph, todos, subagents, delegation, pr, changes, workspaces, the review host, CI, `AGENTS.md`, and the goal and architecture docs. It cited `path:line` for each claim.
- I checked four claims myself (top of this file), plus the v1 ticket-workflow note and the skill rationale.

**Not read:** most of `apps/web`, the e2e specs beyond the workflow harness, the website, and the i18n and theme modules.

**How it was checked:** I ran nothing. There is one commit, so there's no history.

**Confidence:**
- High on the mechanisms and on what is enforced versus prompt-only.
- Medium on the merge-queue inference, which needs a test against GitHub.
