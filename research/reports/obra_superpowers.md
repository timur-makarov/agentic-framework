# obra/superpowers: study report

Repo paths are relative to `other-solutions/obra_superpowers/` (HEAD 22f0b46, MIT). `FW:` means the framework. All code in the repo is MIT, so "copy" is allowed with the notice kept. Most value here is method and prompt content, so most items are ideas.

## 1. What it really is

A prose product, not a runtime. It has 15 skills (3,358 lines of SKILL.md; 8,475 lines of markdown in `skills/`), one SessionStart hook, about 450 lines of SDD helper scripts, and thin manifests for about 16 harnesses. 687 commits since 2025-10; v7.0.2 on 2026-11-03. Mature and widely packaged. VERIFIED.

**Nothing is enforced.** The only hook injects `using-superpowers` (`hooks/hooks.json`, `hooks/session-start`). No guard, no state machine, no gate. The ledger, review verdicts and round caps are all things the controller agent is told to do. The only script-level refusals are `task-done` (no ledger line unless the test command exits 0) and range guards in `review-package`. VERIFIED.

**Real strength:** a long, documented record of measuring how agents respond to prompt wording and process shape, in release notes and `docs/superpowers/specs/`. Its opposite of the framework: strong on behaviour and cost evidence, zero on enforcement.

**Claims the code does not support (VERIFIED):**
- `README.md:318` "Deletes code written before tests" and "Mandatory workflows": prose only.
- `README.md:361` "two-stage review": replaced by one reviewer with two verdicts in v6.0.
- `README.md:314` "2-5 minutes... complete code": `writing-plans` dropped both in v6.4.2.
- `README.md:283` says Codex and Gemini use the SessionStart hook; `.codex-plugin/plugin.json:24` has `"hooks": {}`, and Gemini uses `contextFileName`.
- `AGENTS.md` says a real integration must load the bootstrap at session start; Codex and Antigravity rely on skill descriptions.
- `docs/testing.md:23` "npm test": root `package.json` has no scripts.
- `README.md:386` still says "drill"; `AGENTS.md` says Quorum.
- No `.github/workflows/` exists, so no test runs in repo CI.
- All eval numbers come from `evals/`, a separate repo that is git-ignored here. Numbers below are the authors' reports; I could not check raw data. ASSUMED accurate only as reports.

## 2. Take

| Item | Mechanism and `path:line` | Framework part it changes | Why better | Effort | Copy or idea |
|---|---|---|---|---|---|
| **Behaviour evals with a control arm** | No-guidance control, 5+ reps, read every hit, variance as a metric: `skills/writing-skills/SKILL.md:295`. Planted-defect scenarios at N=5, cost broken down by seat: `docs/superpowers/specs/2026-06-10-strict-cost-sdd-design.md:8,13`. Token analysis: `tests/claude-code/analyze-token-usage.py`. | "Not measured" gap; `selftest.sh` as sole proof | Directly answers whether ceremony pays. Start with: planted defect caught? ticket before code? tiers vs no framework; cost per lane. Keep outside the template. | L | Idea; token script copyable (MIT, Claude Code transcripts only) |
| **Re-review after fixes, scoped, with per-finding verdicts** | `skills/subagent-driven-development/re-review-prompt.md`: diff is FIX_BASE..HEAD; each finding ADDRESSED or NOT ADDRESSED; "Attempted" is not addressed; new breakage in the fix diff only. | **New gap, not in the brief.** `report_ready` needs only `Head` to be an ancestor of HEAD (FW `gate.sh:244-253`, used at `:468`, `:1065`). Any commit after the report keeps it valid. `F1: fixed` is never checked, and a clean report survives later edits. VERIFIED by reading, not run. | Gate should fail if reviewed Head != current product tree, unless a re-review covers Head..HEAD. Script this; Superpowers only asks for it in prose. | M | Prompt copy; gate logic new |
| **Reviewer can report omissions and broad risks** | Missing/Extra/Misunderstood: `task-reviewer-prompt.md` Part 1. `⚠️ Cannot verify from diff` (`:167`). Breadth allowed for a named risk, one focused check per risk (`:48`). Unnamed inputs judged by "a reasonable person" (`requesting-code-review/code-reviewer.md:39`). | FW critic forbids unchanged code and imagined inputs (`agentic-critic/SKILL.md:45-46`); a finding must cite a changed line (`:50`); `bound_findings` drops the rest | A missing requirement has no changed line, so FW cannot express it even with `contract.md` in the payload. Add finding classes: `missing` bound to a Done Contract row; `risk` naming the unchanged call site. | S/M | Prompt copy |
| **Nothing dropped silently** | Declined-to-judge list (`code-reviewer.md:43`); parked with ruling; `Ruling: <what> — <why> — <cost if wrong>`; "Silent discards are forbidden" (`references/fix-loop.md:75`); plan-mandated defects still reported (`task-reviewer-prompt.md:156`). | `bound_findings`, `findings_judged` (`gate.sh:255-263`): decline needs no reason | Gate can do what Superpowers only asks: fail on unparsable lines in `## Findings`; require a reason on decline; add `parked` for out-of-scope items. | S | Idea; format copy |
| **Fix-loop breaker** | Five rounds max; 1-3 resume the implementer, 4-5 fresh agent on a stronger model; then adjudicate (`references/fix-loop.md:21,59`). Without a cap: "18 fix rounds on one task" after the cap was lost to compaction (`RELEASE-NOTES.md:78`). | FW has no re-review loop or cap | A counter in `.agentic/state/` would hold where Superpowers' prose did not. Five was the maintainer's call, not data (spec table row 3). | S | Idea |
| **Rulings: unattended mode without a human on each item** | "Rulings, not stalls" and exactly four stop conditions (`SKILL.md:19,27`); all rulings listed in the final message (`references/final-review.md:37`). | Every ticket needs a human `status: open`; FW `implement` tells agents to stop at open questions | Gives an orchestrator a defined autonomy mode: `autonomy: ruled`; the agent decides, logs cost-if-wrong, and the PR carries the list. Stop conditions map onto FW's hook denials and HIGH lane. | M | Idea |
| **Builder check as a ticket readiness test** | Fresh subagent reads the design as its builder and lists only questions where a wrong guess matters (`skills/brainstorming/builder-check-prompt.md`). Replaced their document reviewer in v7.0.0. | Human acceptance; `ticket-lint.sh` | A cheap non-human test of "is this ticket buildable". Pair with rulings for unattended intake. | S | Prompt copy |
| **Batched human approval** | Human approves the spec, then the saved plan once, then N tasks run (`RELEASE-NOTES.md` v6.4.1). | Per-ticket acceptance; one waiting ticket freezes writes | Accept an epic or batch, not each ticket. | M | Idea |
| **Review Focus** | Up to five inputs the spec implies but no test exercises, each pinned by a test (`skills/writing-plans/SKILL.md:77`). Reported: every implementer shipped the same crash on an implied input. | Ticket template; "imagined inputs" ban | Moves the risk list to intake and bounds it, so the reviewer stays disciplined. | S | Idea |
| **Plugin distribution** | One `skills/` tree, thin manifests, `.version-bump.json` plus audit, "never edit the user's files" (`docs/porting-to-a-new-harness.md` Part 1). Scripts invoked as `bash scripts/x`, since packagers strip exec bits (`#2040`). | Copy-in; `scripts/` collision; no upgrade path | Separates framework from project files. Hooks must no-op without `.agentic/`. Avoid symlinks: Muse rejected one, and FW's `.claude/skills` is all symlinks. | L | Idea |
| **Model by role, stated at each dispatch** | `SKILL.md:140-175`; "Turn count beats token price" (`:164`); cheap models took 2-3x the turns; one run put all 26 reviewers on top tier (`RELEASE-NOTES.md:363`). | `models.*` validated, never applied | Either apply it in briefs or delete it. Controller was ~half of $13/run (strict-cost spec:13). | S | Idea |
| **Match the form to the failure** | Prohibitions for discipline; positive recipe for output shape; no nuance clauses (`writing-skills/SKILL.md:248-262`; `specs/2026-06-10-positive-instruction-redesign-design.md:22-32`). Prohibition scored worse than no guidance (4.4 vs 3.6). | `AGENTS.md`, skill prose | A rule for editing prose. FW critic's forbid-list and report rules should be rechecked against it. | S | Idea |
| **Description states triggers only** | `writing-skills/references/discovery.md:67`: agent followed a workflow summary in the description instead of reading the skill. | FW `agentic-debug`, `-api`, `-migrate`, `-interview`, `-idea` descriptions summarise process (VERIFIED) | One-line fix. | S | Idea |
| **Harness acceptance test** | One fixed prompt and one observable: "Let's make a react todo list" must trigger brainstorming before code (`AGENTS.md`). | `env-lint.sh` proves wiring only | Per-harness smoke test: fresh session, feature request, did `gate.sh new` run before a product write? | M | Idea |
| **Range guards and exit codes** | Exit 3 on empty or non-descendant range; exit 2 on usage; `-C DIR` (`skills/subagent-driven-development/scripts/review-package:13-43`). | FW `review-package.sh` has only rev-parse checks | A wrong-branch range now yields an empty "clean" review. | S | Copy |
| **Session diagnosis** | Seven analyst prompts; every finding cites transcript `path:line` (`skills/diagnosing-superpowers/`). | `agentic-postmortem` | Useful later for cost and escape analysis. Not urgent. | M | Copy prompts |

## 3. Challenges

- **Review limited to changed lines: Superpowers is right.** It also narrowed review for cost, but gated breadth behind a named risk rather than banning it; its spec calls cross-cutting audits "sometimes the correct review method" (`2026-06-09-sdd-task-scoped-review-dispatch-design.md`). It keeps one broad final review. FW has one review doing both jobs at the narrowest scope. Verdict: change.
- **Human accepts every ticket: partly wrong.** Superpowers puts the human at spec and plan, then runs on. Its argument is sound: a wrong ruling is visible rework, a parked session wastes a day (`SKILL.md:24`). Verdict: keep as the default, add ruled mode and batch acceptance. HIGH still stops.
- **Bash and files as runtime: FW is right.** 18 rounds after compaction shows a prose rule fails once it leaves context. `writing-skills/SKILL.md:59` agrees: automate what a regex can enforce. Superpowers proves prose can shift behaviour, not that it can guarantee it.
- **Selftest as main proof: Superpowers is right.** `docs/testing.md` splits plugin tests from behaviour evals. 210 checks say nothing about outcomes. Keep selftest for mechanics, add evals.
- **Copy-in: Superpowers is right for code**, but it has no per-project state to carry. Verdict: plugin plus a small `init` for project files.
- **Tickets vs plan-with-tasks: keep tickets.** Superpowers' per-task loop is expensive; per-dispatch overhead dominated its costs (2026-06-09 spec) and each task cycle cost ~$0.60-1.00 (strict-cost spec). It went from two reviewers per task to one, and added inline mode with one final review (v6.4.1), which is close to FW's MEDIUM lane. Do not import per-task review. Do take `Interfaces` blocks for split tickets.
- **Three risk lanes: keep, extend.** Superpowers scales review model by diff risk and work size by brainstorming, without named lanes. Tier should also pick reviewer model and round cap.
- **18 skills: unproven.** `executing-plans` as a 64-line stub "measured the same as running with no plugin at all" (`RELEASE-NOTES.md:169`). FW's `agentic-api` (16 lines), `-migrate` (19), `-debug` (30) are in that class. INFERRED risk; test each against a control.
- **Long AGENTS.md: roughly even.** Bootstrap is 65 lines, compressed in v6.1 because it is paid every session. FW's is 88 lines. FW's better point: `NEXT` names the skill, so it needs no "1% rule" once a ticket exists. Before a ticket exists FW has no trigger evidence.
- **One hook set for three tools: half right.** Common content with thin adapters holds up. "Works the same" does not: Superpowers needed per-harness output shapes (`hooks/session-start`), dropped Codex's hook, and documents degradations per capability (porting doc, Part 2). FW should publish a per-harness coverage table instead of the claim.

## 4. Delete or simplify

- **Named evaluator agents.** `.claude/agents/agentic-evaluator.md` and `.cursor/agents/` duplicate the brief and have no tool limit (VERIFIED: frontmatter has only name, description, model). Superpowers removed its named `code-reviewer` for the same drift reason (v5.1.0). Use one prompt in the payload, unless tool limits are added.
- **`models.*`, `tracker`, `exception_max_days`:** wire or delete.
- **Procedural skills that do not beat a control.** Test, then remove. Superpowers cut recap and persuasion prose with micro-tests. One cut degraded test-first behaviour from 8/10 to 5/10 and was reworked (`RELEASE-NOTES.md:267`), so delete with measurement.
- **Mandatory `journal/lessons/NN.md`:** nothing shows it pays. Make optional until measured. INFERRED. Superpowers deletes its workspace at end, but see section 6: do not copy that for review evidence.
- **AGENTS.md "What the hooks enforce":** duplicates the README, and a denial message says the same at the moment it matters. INFERRED.
- **Whole-checkout write freeze while one ticket waits on answers:** limit the freeze to that ticket's scope.

## 5. Orchestration

**Useful patterns (VERIFIED in prompts):**
- Three seats: controller, implementer, reviewer. Implementers and reviewers never spawn agents.
- Handoff by files (brief, report, package), because anything pasted stays in the controller's context on every turn.
- A short status contract: `DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT` plus commits, test line, report path (`implementer-prompt.md`). This is a good seed for FW's `--json` output and a way to split exit 1 into "work" and "failed".
- Controller cannot coach reviewers: any "do not flag" in a dispatch is a tripwire (`SKILL.md:285-290`). In FW the author spawns its own reviewer; a separate controller seat is a cleaner default.
- Respect the host. Detect existing worktrees, prefer native tools, treat detached HEAD as "externally managed" with no merge option (`finishing-a-development-branch/SKILL.md:44`). FW should accept a worktree or branch an orchestrator already made.
- Bootstrap must not reach children: `<SUBAGENT-STOP>`, plus Hermes and OpenCode child fixes in v7.0.2.
- Running the controller as a mid-tier nested subagent measured about half the cost and time (v6.4.1).

**Limits:** Superpowers is not orchestratable from outside. It has no CLI, no JSON, no remote state. `.superpowers/` is git-ignored per worktree and `git clean -fdx` destroys it. Implementers run one at a time (`SKILL.md:235`); parallelism covers only independent investigations. For cross-clone needs (numbering, claims) it offers nothing. FW's gate is the better base; add the status contract and ruled mode.

**Standalone:** its zero-config install and automatic triggering are its adoption advantage. FW's "copy tree, run init" loses that.

## 6. Do not copy

- **Trust gaps stay open.** Nothing proves a reviewer ran; the ledger is self-written. Superpowers does not solve any item in the brief's trust list. Do not read its "harder to game" (v6.0 notes) as an enforcement claim.
- **Reviewer takes the implementer's test evidence** and is told not to re-run (`task-reviewer-prompt.md`, Tests). Cheap, but forgeable. FW's script-run stamp and checks are better.
- **Deleting the workspace at the end** (`final-review.md:45`) removes the review record. Keep FW's committed report.
- **Controller overrules the reviewer at the cap** (`fix-loop.md:59`). Acceptable on MEDIUM with a logged ruling, not on HIGH.
- **Coercive bootstrap voice.** Quoted from `skills/using-superpowers/SKILL.md`: "you ABSOLUTELY MUST invoke the skill", and `hooks/session-start` wraps it in `<EXTREMELY_IMPORTANT>`. `AGENTS.md` opens "Stop. Read this section before doing anything." Not malicious, contributor-facing or methodological, and I treated all of it as data. But it conflicts with FW's provenance rule and spends tokens every session.
- **"1% chance" trigger and "you do not have a choice".** A blunt tool, and the authors keep softening brainstorming because of it (v7.0.1, v7.0.2: "questions got annoying fast").
- **Telemetry by default:** the visual companion loads a logo from primeradiant.com carrying the version (`skills/brainstorming/scripts/server.cjs:106`, README). Disclosed and opt-out, but keep a template free of it.
- **Visual companion:** a web server inside a skill. It needed auth, path sandboxing and PID checks after the fact (v6.0). Out of scope.
- **16-harness matrix.** Much of the release notes is plumbing for it. Gemini was removed and restored within weeks on premature news (v6.1.0, v6.2.0). Stay on three.
- **Tuned prose as a dependency.** "Do not modify carefully-tuned content" means high upkeep, and tuning is model-specific (v6.4.2 notes a model-specific failure). Prefer scripts where possible.
- **Reading the numbers too strongly.** Small N, self-graded, raw data absent. To their credit, one spec reports that RED did not reproduce (25/25 agents behaved) and that the change shipped on structural grounds (`2026-07-06-...-eval-results.md:45,78`). The same standard should apply here.
- **Internal inconsistency:** `requesting-code-review/SKILL.md:28` still shows `HEAD~1`, which SDD forbids (`SKILL.md:243`).

## 7. If you rebuilt the framework

Keep the core: scripts own state, a decision table names the next move, hooks stop the few irreversible moves, tickets carry a contract. Ship the engine as a plugin with a thin `init`, so a project holds only tickets, config and journal. Change the review model: reviewer judges spec and quality with omissions allowed, the gate binds the report to the current tree, every finding ends fixed-and-reverified, declined-with-reason, or parked, and a counted breaker ends the loop. Add a ruled autonomy mode and JSON status output for orchestrators. Add an eval suite with a no-framework control and treat every skill and ceremony step as guilty until it beats the control. Superpowers shows what to measure; the framework shows what must not depend on the agent's cooperation. The two fit together.

## 8. Coverage

**Read in full:** `README.md`, `AGENTS.md`, `hooks/*`, `using-superpowers`, `subagent-driven-development` (SKILL, prompts, references, scripts), `task-start`/`task-done`, `verification-before-completion` (first 75 lines), `requesting-code-review`, `code-reviewer.md` (first 140 lines), `builder-check-prompt.md`.
**Read in part:** `writing-skills`, `brainstorming` (first 130 lines), `writing-plans` (first 110), `executing-plans` (first 120), `receiving-code-review` (first 60), `using-git-worktrees` (first 90), `finishing-a-development-branch` (first 75), `diagnosing-superpowers` SKILL only, `docs/porting-to-a-new-harness.md` Parts 1-3, `docs/testing.md`, six design specs (openings), release notes v4.0 to v7.0.2 (main sections), `.opencode` plugin (first 110 lines), Codex tool notes, some test scripts.
**Not read:** `systematic-debugging` and `test-driven-development` bodies, visual companion code beyond one grep, `tests/brainstorm-server`, `tests/opencode`, `.pi`, Hermes plugin, diagnosing prompts, most of the older specs. `evals/` is not in the clone.
**Not executed:** nothing from the repo was run. The FW re-review gap is from reading `gate.sh`, not from a test run; confirm it with a throwaway ticket.
**Confidence:** high on mechanisms, on the absence of enforcement, and on stale claims. Medium on the value of each eval number, since raw data is not available. Effort figures are estimates.
