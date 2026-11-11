# disler_super-simple-software-factory (SSSF)

Paths are relative to `.claude/skills/sssf/` in the clone. `AM/` = `templates/adws/adw_modules/`. `FW/` = the framework. All claims are VERIFIED by reading unless labelled.

## 1. What it really is

A single Claude Code skill that stamps a Python harness into a repo. Real size: 2,396 lines of harness modules (`AM/`), 881 lines across 12 workflow scripts ("ADWs"), plus a Vue trace UI. It has one public commit on `main` (2026-08-02), one on `origin/example` (2026-08-04), and no tests of the harness at all.

The idea is sound and the code is clean: a Python script owns the loop and spawns a headless agent per phase, parses a typed JSON envelope, runs gates, re-prompts the same session on failure, and streams everything into SQLite. It is a demo and teaching kit ("a starting point, not a product", `README.md:375`), not a ready-to-use framework. It runs Pi only (`AM/agent_cc.py:11` raises) with no sandbox, no branches, no human gate.

README claims the code does not support:
- "The builder does not get to edit its own grader" (config comment, `templates/sssf.config.yaml:71`): false, see section 6.
- `diff_matches_claims` (`README.md:243`) and "declared changes appear in the diff" (`references/handoff.md`): the gate only checks that the file exists (`AM/gates.py:61-68`). No diff is read.
- "The real traces" on the `example` branch (`README.md:21`): `git ls-tree -r origin/example` shows no db, `sessions/` or jsonl; they are gitignored.
- "Read-only UI" (`README.md:271`): the server has one `UPDATE sessions SET archived` (`apps/visualizer/server/db.ts:147`). Trivial.
- `make_adw.py`, the ADW generator, emits `return 0 if run.succeeded else 1` (`scripts/make_adw.py:55`), but that property was removed (`AM/runner.py:122`). Every generated ADW should raise AttributeError at the end. INFERRED from code; I did not run it. Same on `example`.

## 2. Take

License: MIT. Copying is allowed with the notice, but almost nothing should be copied literally: the language differs, it is Pi-specific, and the permission code has holes.

| Item | Mechanism and `path:line` | Framework part it changes | Why better | Effort | Copy or idea |
|---|---|---|---|---|---|
| **Code spawns the reviewer; the report is captured stdout, not a file** | `AM/agents.py:127-137` calls `agent_pi.run`; `AM/agent_pi.py:243-266` tails the child's stdout; the verdict is the last assistant message; the driver reads `review.approved` in memory (`templates/adws/adw_simple_sdlc.py:119-122`) | Mode A; `FW/scripts/gate.sh:235-241` (`report_sha_ok` passes with no record), `report_ready`, `.cursor`/`.claude` evaluator agents | Closes the "self-written critic ships" gap by construction: the author has no channel into the verdict. A file plus a sha can never prove who wrote it; process ancestry can. Mode B (`gate.sh:971-992`) already has this shape, so promote it to default and record `reviewer_ran` from the gate itself. Keep Mode A only as an explicitly unattested path that needs human sign-off | M | Idea |
| **Outer driver: code calls the agent in a loop** | `templates/adws/adw_simple_sdlc.py:82-171`: phases, bounded `for` loops, `run.finish(accepted=...)` | New `gate.sh run NN` over `compute_next`/`step_advance` (`gate.sh:1198-1226`) | `advance` already stops exactly where an agent is needed. Add about 100 lines: on exit 1, spawn `agent.command` with NEXT as the prompt, loop with a bound. That gives unattended mode, per-role prompts and an orchestrator entry point without touching the decision table. Note `stdin=DEVNULL` (`AM/agent_pi.py:237-243`: a child with inherited non-TTY stdin hung silently, per the author) | M | Idea |
| **Single spawn adapter boundary** | `PiRequest`/`PiResult` (`AM/data_types.py:373-385,436-447`) and a one-function `run()`; `--session-id` create-or-continue (`AM/agent_pi.py:218-230`) | `critic.command` examples; `models.*` config that is validated but never applied | One small contract per tool (`claude -p`, `codex exec`, Cursor CLI): prompt, system, session id, tools, cwd in; text, tokens, cost, exit out. It makes `models.*` live, per role, instead of dead | M | Idea |
| **Typed review verdict plus self-consistency gate, fail closed** | `ReviewFinding{requirement, met, evidence}` and `ReviewOutput{approved, findings, blocking}` (`AM/data_types.py:107-120`); `verdict_consistent` (`AM/gates.py:71-95`); parse retry then raise (`AM/agents.py:267-287`) | `bound_findings`, `findings_judged` (`gate.sh:255-263`), `## Findings` text format | A malformed line is re-prompted, then the phase dies; today it silently vanishes. `approved=true` with blocking items is refuted without reading code. Python stdlib `json` can do this without pydantic | S-M | Idea |
| **No author "decline": rejections loop to the builder, bounded, then the run fails** | `adw_simple_sdlc.py:116-129`, `MAX_REVISION_LOOPS` | `F1: declined` in `NN-critic-response.md` (`gate.sh:262`) | Removes the unreasoned decline. If declines stay, require a reason and have the reviewer, or a human, rule on it | S | Idea |
| **Requirement-coverage review as a second question** | `templates/prompt_engineering/reviewer/system.md:9-14`: rule on each requirement against the plan, from the code on disk | Critic brief; "changed lines only" | A missing requirement has no changed line, so today's critic cannot report it. Feed it the Done Contract and exempt `met:false` from line binding | S | Idea (prompt is short) |
| **Per-call change-set audit, by role** | `snapshot`/`enforce` (`AM/permissions.py:50-68,163-185`), `writes:` per agent; reversions count as changes | Part of `protect.sh`/`guard.sh`; adds to `gate.sh:647-653` | Language-agnostic: catches `python -c`, which the regex hooks miss. Check after each spawned call, not only at ship. Implement it correctly: hash a temp-index `git write-tree` of the whole tree plus HEAD; see section 6 | S | Idea only, do not copy the code |
| **Phase trace with token and cost accounting** | Seven-table schema (`AM/tracer.py:17-90`), usage folded per turn (`AM/agent_pi.py:261-276`, `AM/data_types.py:388-433`), gate evidence `{item, ok, note}` (`AM/data_types.py:252-283`) | `audit.sh` (commands only, no outcome link); the "not measured" gap | Cost per ticket, gate failures, retry rounds and tier become queryable. This is telemetry, not an eval, but no judgement about ceremony is possible without it. JSONL per run plus a `gate.sh report` command is enough; SQLite is optional | M | Idea; schema is a good start |
| **Polling read path instead of a server** | `select ... where adw_id=? and rowid>? order by rowid limit 500` (`README.md:264`), WAL | No stable output today | Live view and history are the same query. An orchestrator needs no API, only a stable file and a cursor | S | Idea |
| **Namespaced stamp with skip-and-report** | All into `adws/`; `install.py:36-48` skips existing files, so a rerun lists drift | Copy-in, top-level `scripts/` collision | Stops host collisions and floors on `scripts/**`. Add what SSSF lacks: a manifest separating framework from project files | M | Idea |

## 3. Challenges

- **Who owns the loop (agent reads `gate.sh next` vs code calls agent).** SSSF is right about trust: evidence the agent cannot reach needs no hooks to defend it, and most Trust gaps in the brief exist because the author runs inside the loop that judges it. The framework is right about durability: SSSF's position lives on the Python stack, so a crash restarts the ADW. `--adw-id` rejoins contexts and dirs but re-runs phases (`AM/runner.py:52`, `AM/agents.py:228-232`). Verdict: keep state derived from repo files, and make code the default outer loop. Interactive use stays as a second caller of the same table.
- **Hooks as the enforcement layer.** SSSF has none, only post-call comparison. Verdict: partly right. Regex over shell cannot defend scope or evidence, and post-call checks can. Post-hoc cannot stop `curl | sh`, a force-push or a secret read. Shrink hooks to irreversible acts only.
- **Bash plus files as the runtime.** A 183-line readable chain versus a 1,242-line bash table favours a real language, and typed parsing is where bash is weakest. But SSSF pays with `uv`, pydantic, Pi and bun. Verdict: move to stdlib Python (already a dependency); keep files and git as the store.
- **Tickets as the unit of work.** SSSF's unit is a prompt with an `adw_id`: no scope, no Done Contract, no backlog. Its acceptance is whatever the script hard-codes. Verdict: framework is right. Add run and phase as sub-units under a ticket.
- **Three risk lanes.** SSSF replaces lanes with a chain picked by a person or orchestrator (`cookbooks/run_adw.md:15`). Nothing floors risk by path. Verdict: keep lanes and `risk_paths`, but express each lane as data, a phase list, which is how SSSF makes chains cheap to read.
- **Review limited to changed lines.** Verdict: SSSF is right for missing work and the framework is right for keeping noise out. Keep the bound for defects; exempt requirement findings.
- **A human accepts every ticket.** SSSF has no approval at all; the `engineer` phase only logs (`adw_simple_sdlc.py:78-80`). Its README lists this as a gap, not a design (`README.md:390`). Verdict: neither. Make acceptance policy, for example auto-accept LOW from an authenticated orchestrator, and keep humans on HIGH. Write acceptance outside the agent's reach.
- **Copy-in distribution.** SSSF is also copy-in and proudly fork-and-own; `--force` overwrites config and prompts (`README.md:83`). Verdict: this fails the owner's "ready to use" goal. Copy the namespacing, not the upgrade story.
- **18 skills and a long AGENTS.md.** SSSF: one 76-line `SKILL.md`, 9 lazy cookbooks, and role prompts of 13-21 lines. Under a driver each role reads only its own prompt. Its startup rule is worth keeping: list, then wait, because "volunteered state is guessed state" (`SKILL.md:26-28`). Verdict: under a driver, condensed judgment prose can move into role prompts. INFERRED; no evidence on outcomes either way.
- **One hook set for three tools.** SSSF avoids the problem by supporting one tool. An adapter at the process boundary is still a smaller surface than translating hook protocols, for headless use only. IDE use still needs hooks.
- **A selftest as main proof.** SSSF has zero tests and shipped a broken generator, which supports the framework. Worth adding from SSSF: `just demo` (`templates/justfile:29-34`), a cheap real-agent smoke run through the whole path.

## 4. Delete or simplify

- With a harness-run reviewer: `reviewer-*.sha`, Head line parsing, `## Findings` text parsing, and most of the Mode A branches in `compute_next` (`gate.sh:464-488`).
- `stop.sh` and `stop_followups` (default 0 does nothing): a driver replaces re-prompting from a stop hook.
- Scope-enforcement regexes in hooks, once the per-call audit runs: keep the deny list for irreversible acts.
- `NN-critic-response.md` as a separate prose file: replaced by a loop or a structured ruling.
- Hand-written lane branches: one phase list per tier.
- `models.*`: apply it through the adapter or delete it. `tracker` and `limits.exception_max_days` have no reader; delete them. SSSF adds no argument for keeping them.

## 5. Orchestration

Worth learning, as a plug-in shape:
- One CLI per workflow, with a pinned id: `<prompt or file> --adw-id X --config Y` (`templates/adws/adw_simple_sdlc.py:177-183`). Idempotent join by id (`AM/tracer.py:139-143`).
- A `processes` table maps run to pid with the command stored, so a caller can find and stop a stuck run (`AM/tracer.py:71-79`, `AM/session.py:21-35`).
- `run.finish` settles exit code, db status and banner in one call (`AM/runner.py:114-142`), after a real bug where a red run showed green in the trace. The phase-versus-run split maps to the framework's overloaded exit 1: separate `step_failed`, `agent_work` and `rejected`. SSSF itself only offers 0/1.
- A meta-agent skill that launches and watches but never does the work, and rewrites prompts for clarity without changing intent (`cookbooks/how_to_prompt_for_the_eng.md:9-19`).
- `SSSF_CONFIG` swaps the whole roster per run.

What SSSF lacks, and the framework would need:
- Per-run isolation. All runs share one tree. Two concurrent ADWs would attribute each other's changes and roll them back (INFERRED from `AM/permissions.py:174-179`). The framework's branch and worktree model is ahead here.
- Timeouts: none on agent calls, and the README admits a hang goes quiet (`README.md:359`). Add an idle watchdog.
- Budgets: cost is measured, never enforced.
- Durable phase resume, a human-approval phase, cross-clone number reservation.
- `--json` is unnecessary if a stable event file exists, but the schema must be versioned. SSSF's is not, beyond additive ALTERs (`AM/tracer.py:94-99`).

## 6. Do not copy

**The permission layer does not deliver what it claims.** I reproduced the first two with plain git in a scratch repo, using none of SSSF's code:
- Fingerprints are `numstat` counts plus the literal word `untracked` (`AM/permissions.py:59-67`). A same-count edit of a dirty file and any edit of an untracked file are invisible. At review time the build is uncommitted, so `writes: []` does not stop the reviewer from quietly changing the builder's work.
- It diffs against `HEAD`. If an agent runs `git commit`, the change leaves the diff. A builder can commit an edit to `adws/adw_modules/quality.py` and nothing fires. VERIFIED: the after-snapshot came back empty.
- `data_dir` is always writable (`AM/permissions.py:124,129`) and is broader than the session runtime the docs describe. `adws/adw_data/` also holds the tracked prompts and pi extensions, which are not in `protected_files`. Any agent can rewrite `reviewer/system.md`, which is re-read on the next call (`AM/agents.py:89-90`), or `subagents.ts`, which pi loads as code. The builder can also rewrite `context_handoff/plan.md`, the reviewer's spec (`reviewer/system.md:9`). VERIFIED by reading, not run.
- Writes outside the repo and to gitignored paths or `.git/hooks` are never seen (INFERRED from the snapshot method).
- Tests are not protected, and nothing like `floor-guard.sh` exists, so a builder can weaken a test to get green.

**Other failures:**
- Secrets: `.env` loads into `os.environ` (`AM/utils.py:13`), passes to every agent (`AM/utils.py:31`, `AM/agent_pi.py:246`), and prompts say credentials "are already live" (`reviewer/system.md:15`). Any agent's bash can read every provider key.
- `git add -A` on the current branch (`AM/git_helper.py:49`) sweeps operator WIP into the "plan" commit; there is no branch per run.
- Fix loops: `adw_simple_sdlc.py:97-112` and `adw_build_test.py:52-67` run the last fix and never test it, wasting that fix. `adw_plan_build_test_quality.py` has the `if i == MAX_FIX_LOOPS: break` guard, so the bug is known but not fixed everywhere. Review also runs after a red suite, spending tokens on a run already doomed (`adw_simple_sdlc.py:114-122`).
- Fails open by default: stamped test commands are `echo` and exit 0 (`AM/quality.py:49-52`), so a fresh install reports verified. The README is honest, but the framework's ticket lint refusing a vacuous check is the better design.
- Reviewer independence: a second review resumes the same session (`AM/agents.py:228-232`), works in the live tree, and is handed the builder's envelope. Keep the framework's fresh seat and throwaway worktree.
- `AM/agent_pi.py:243-280`: stderr is a pipe drained only after stdout ends, so heavy stderr could deadlock (INFERRED). A non-zero exit with any text is accepted (`:284`). The prompt travels in argv, so it is visible in `ps` and size-limited.
- `ph.call` puts agent text straight into prompts by sequential `replace` (`AM/prompts.py:10-11`), so an envelope containing `{{...}}` is expanded.
- Overbuilding: a large Vue UI (`PhaseDetail.vue` alone is 1,265 lines) for what `sqlite3` already answers; `subagents.ts` at 593 lines for recon fan-out. Bun server sets no hostname (`server/index.ts:113`); ASSUMED it binds all interfaces and exposes prompts and tool output.
- Doc rot: `SKILL.md:65` says gates return `list[str]`; `SKILL.md:76` says the visualizer ships later; `just kill` and `just rosters` (`cookbooks/run_adw.md:31,111`) are absent from the stamped justfile; `install.py:10` says 4 agents, there are 5.
- Outcome evidence: none. `VALUE.md` on `example` quotes one run's tokens and an inferred 2.3x cache saving. No comparison exists.

Suspicious content: no prompt injection found. The README promotes a paid course (`README.md:423`). The skill was auto-listed by my tooling; I did not invoke it.

History: one commit, so `git log` teaches nothing. Docstrings carry incident notes, which are the author's claims and unverified: a builder ran `git checkout adws/` on its own check (`AM/permissions.py:6-8`), red runs recorded green (`AM/runner.py:123-130`), pi hung on stdin (`AM/agent_pi.py:237-242`), `.pyc` files were committed (`scripts/install.py:27-30`).

## 7. If you rebuilt the framework

Keep tickets, the Done Contract, frozen scope, risk floors, script-run checks, derived state, floor-guard, worktrees and the selftest. Change the shape: a stdlib-Python core where a ticket's lane is a data-defined phase list and a driver spawns each role headless through a small adapter, in its own worktree. Reviewer verdicts and check results return as validated JSON the author never touches, and each phase appends to a versioned event log with tokens and cost. Hooks shrink to a short deny list for irreversible acts; the interactive path calls the same state table but is marked unattested. SSSF contributes the inversion and the envelope, not its code or its permission model.

## 8. Coverage

Read in full: all of `AM/` except `console.py`; `adw_simple_sdlc.py`, `adw_build_test.py`; the loop of `adw_plan_build_test_quality.py`; `install.py`, `make_adw.py`, `make_config.py`; `SKILL.md`; config; justfile; reviewer, builder and planner prompts; `README.md`; `cookbooks/run_adw.md`.

Partly read: `references/handoff.md`, `references/config.md`, `how_to_prompt_for_the_eng.md`, `subagents.ts` (first 130 lines plus grep), `apps/visualizer/server` (grep), `VALUE.md`, `example` (file list and selected files).

Not read: the other 9 ADWs (table and docstrings only), `console.py`, scout and documenter prompts, `references/observability.md`, the create and update cookbooks, the Vue frontend.

Nothing from the repo was executed. The numstat and commit checks used my own git commands in a scratch repo. Framework comparison used `README.md`, the `gate.sh` lines cited, `audit.sh` and `config.yml`.

Confidence: high on mechanism and permission holes, medium on the rebuild direction, since neither system has outcome data.
