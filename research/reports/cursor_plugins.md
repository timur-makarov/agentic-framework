# cursor_plugins (cursor/plugins)

Labels: VERIFIED (read in code or checked), INFERRED, ASSUMED. Paths are relative to the cloned repo unless they start with `fw:` (framework). "Harness" means `harness/pstack/`, the generated Claude Code copy of `pstack/`, so I read the pstack skills it ships.

License: the repo root has no license file, and `MANIFEST.tsv` has no row for this repo. As assigned, everything below is **idea only; no code is copied**. VERIFIED: 17 first-party plugin dirs do carry their own MIT `LICENSE` (15 Cursor, plus Lauren Tan for `pstack/`, Dylan Gattey for `dyl-stack/`). If you want code later, those dirs would allow it with notice. That is your call, not assumed here.

## 1. What it really is

A marketplace repo: 740 commits since 2026-01-22, 130 plugins (VERIFIED, marketplace count). Most are manifests pointing at an MCP server. Key usage across 130 manifests: `mcpServers` 106, `skills` 24, `variables` 22, `agents` 8, `rules` 4, `hooks` 3 (VERIFIED). Only three plugins use hooks: `continual-learning`, `advisor`, `ralph-loop`.

Three things are real: the packaging (2 JSON schemas, 154-line validator, 188-line generator), `orchestrate` (7,978 lines of TS plus 5,946 lines of tests), and pstack's skills. The rest of my list is prompts.

README or skill claims the code does not support:
- `continual-learning/README.md:45` says trial mode is "enabled in this plugin hook config". `hooks/hooks.json:6` sets no env, the code defaults it off, and commit `1966e52` removed the flag. VERIFIED stale.
- `pr-review-canvas/README.md:30` lists local refs and Graphite as sources. `skills/pr-review-canvas/SKILL.md:23` forbids a local `git diff` fallback. VERIFIED contradiction.
- `docs-canvas` calls itself a placeholder (`SKILL.md:16-19`, `README.md:7`). VERIFIED.
- Advisor's "one to three consults" and "higher quality on complex tasks" (`README.md:4,77`) have no data behind them anywhere in the repo. No plugin I read carries outcome evidence. VERIFIED absence, within what I read.
- `orchestrate` has about 6k lines of tests, but CI never runs them: `.github/workflows/validate-plugins.yml` has no orchestrate path or test step. VERIFIED.

## 2. Take

All items: idea only, under the rule above.

| Item | Mechanism and `path:line` | Framework part | Why better | Effort | Copy |
|---|---|---|---|---|---|
| Portability contract test | `scripts/generate-pstack-harness-trees.mjs:28-51` holds `TERMS`, regexes for Cursor-only names. `:69-85` scans each skill. `:99-102` fails if a used term has no adapter row. `:167-178` `--check` fails CI on drift. | `.agents/skills`, packs `claude/codex/cursor` | fw shares skills by symlink (`fw:.claude/skills/*`) and nothing checks that the text suits each tool. This makes "this skill names a tool the adapter does not map" a build failure | S | Idea |
| Evidence strength ladder | `orchestrate/.../scripts/schemas.ts:43-50` enum; `prompts/verifier.md:45-49`; `core/handoff.ts:62-71` parses it; a later verifier overrides the self-report (`references/handoffs.md:140`). Legacy `pass` maps to the weakest honest value (`handoff.ts:152-160`) | `review/v1` rows, receipts | Second axis next to RECOMMENDATIONS trust levels. Trust says who ran it; this says how strong the evidence is. `verifier-blocked` separates "could not run" from "failed", so an env failure cannot look like a thin pass | S | Idea |
| Pack envelope | `schemas/plugin.schema.json`: only `name` required, `additionalProperties: false` (`:7-8`), component globs, `variables` as JSON Schema for user config, `minClientVersions` per client with literal `never` (`:137-164`) | `packs/` manifest | Small, closed, per-client availability in one field. See section 9 for what it lacks | S | Idea |
| Always produce a result artifact | `core/failure-handoff.ts` and `references/handoffs.md:23-67`: a dead worker gets a synthetic handoff with `failureMode`; each mode has a retry policy; 2 retries then abandon. `:69-71` covers "finished but malformed" | Gate-launched reviewer, attempt budget | Fail-closed gets a typed reason. `next` can print a mode-specific action, and budgets count by mode | S | Idea |
| Run-to-checkpoint exit code | `core/loop.ts:9,85-98` exits 100 after state sync when time runs out and work remains; `:13-18` exit-on-first-new-error; idempotent rerun reattaches (`:49-54`) | `run` verb, exit table | RECOMMENDATIONS has no "stopped on purpose, rerun me" code. Add it to `--exit-code`. An orchestrator can then restart without parsing text | S | Idea |
| Script re-measures numeric claims | `measurements.ts:128-140` compares claim to re-run with 10% tolerance and unit match; outcomes `:105-110`; run in a fresh clone (`agent-manager.ts:472-560`) | Done Contract | `Check:` is pass/fail. This adds "LOC 412 → 354" style claims a script can confirm. Note it only logs to `attention.log`; it does not block, and the framework should block | M | Idea |
| Removed-field tombstones | `schemas.ts:19-26,665-678` rejects named deleted fields with a message saying what to use instead | `config.yml` loader, `upgrade` | Better than silent ignore or a generic "unknown key". Makes "no reader, no field" safe to apply across upgrades | S | Idea |
| Mistake-to-structure ladder | `pstack/skills/correct/SKILL.md:15-30`: a class counts after two hits; fix at architecture, then types, then lint naming the fix, then test, then docs; prove the check fails on a real past mistake; keep a rule-to-enforcer table | `agentic-archive`, lessons | fw lessons already prefer an enforcing cite (`fw:.agents/skills/agentic-archive/SKILL.md`). This adds the ordering, the two-hit bar and the proof, and ties lessons to the cheat set | S | Idea |
| Upstream relay | `references/handoffs.md:75-84`: `dependsOn` pastes the upstream handoff into the downstream prompt | `context` verb, `blocked_by` | Makes dependency a context edge, not only a schedule. `blocked_by` should do both | S | Idea |
| Agent readiness review | `agent-compatibility/agents/validation-review.md`, `startup-review.md`, `docs-reliability-review.md`: try the path, score against anchors | `doctor` | A repo with no scoped validation loop cannot write good `Check:` lines. See section 9 | M | Idea |

## 3. Challenges

- **Plugins as a closed manifest vs. copy-in.** Plugin wins for optional parts. It does not replace the vendored engine: a plugin lives in the harness's cache (`pstack/skills/reflect/SKILL.md`: never edit under `plugins/cache/`), so it is not pinned per commit and CI cannot read it from the base ref. Keep the engine vendored; use a manifest for packs.
- **One neutral skill set vs. per-harness trees.** pstack writes Cursor names and translates through a prose adapter (`pstack/docs/harness/claude-code.md`), plus one injected line per skill (`generator:128-133`). That costs a file read per session and the mapping is honor-system. Verdict: take the check, not the method. Write skills in neutral words, keep the `TERMS` lint, and only generate where a real difference remains.
- **One hook set for three tools.** The repo agrees with RECOMMENDATIONS that tools differ: its hooks speak Cursor only, and the Claude tree ships no hooks at all (`harness/pstack/claude-code` has none, VERIFIED by file list). Nothing here solves multi-tool hooks.
- **Hooks as the trigger for optional behavior.** All three hook plugins add events to the harness, and each spawns a process per event. Verdict: packs should not register harness hooks. See section 9, "engine events".
- **Scripts own state.** Strong agreement: `orchestrate/.../SKILL.md:9` "Long-running agent loops drift; a script with a JSON state file keeps its footing". Slack is mirror only ("correctness does not change", `README.md:23`). Independent support for the framework's core premise from a team shipping parallel agents.
- **Evidence-free memory.** `continual-learning` bans evidence and confidence tags (`agents/agents-memory-updater.md:40`). The framework requires `cite:path needle:`. Framework is right for facts. Its own sibling agrees: `cursor-team-kit/skills/workflow-from-chats` rates each preference strong/medium/weak/contradicted and may choose no artifact. Plain bullets do cost fewer tokens, but they cannot be checked or expired.
- **Review scope.** `pr-review-canvas` orders by reviewer value, not by file, and asks for interactions between files. That supports dropping "changed lines only", and it suggests the human HIGH reviewer needs a different document from the machine `review/v1`.
- **`teach`'s "No quizzes"** (`pstack/skills/teach/SKILL.md:16`) vs. a learning system. I would not copy that rule whole. It suits a senior asking one question. It cannot show that anyone learned anything, and no plugin here can.

## 4. Delete or simplify

- `limits.stop_followups: 0`: `fw:scripts/hooks/stop.sh` is already a stricter Ralph, since the exit condition is a script (`gate.sh next`), not a tag the agent types. Turn it on with a small limit instead of deleting it. Copy advisor's guard: stay quiet when the turn ended with a question (`advisor/hooks/stop-hook.sh:33-40`). This gives IDE users the loop without `run`.
- `agentic-handoff`: the `recall` output contract (`recall/SKILL.md:24-33`) shows the useful part is derived status tags. This supports the plan to replace handoff with derived state.
- Skill count: `disable-model-invocation: true` marks 57 of pstack's 58 skills, and `orchestrate`. Rarely used skills then need no auto-routing. Use it for the optional-pack skills instead of dropping them outright. INFERRED: this cuts per-session listing cost; I did not measure it.
- `models.*`: the advisor is a genuine reader. If the advisor pack is installed, keep one `models.advisor`. Otherwise the deletion stands.

## 5. Orchestration

- `orchestrate` is a host, not a pack: Cursor cloud only (`@cursor/sdk`, `CURSOR_API_KEY`), with no local runner. It confirms RECOMMENDATIONS' "do not build fan-out": 8k lines before tests, including Slack, comment retry queues and SSE watchdogs (`agent-manager.ts:42-56`).
- Its contract is a good checklist for what a host wants from us. Each maps to a framework field: `pathsAllowed` is `scope_paths`, `acceptance` is the contract, `verify` is `Check:`, `verifies` is the review, `dependsOn` is `blocked_by`. A thin `frontier --json` to `plan.json` mapper would be enough. INFERRED; not tested.
- Worth stealing as defaults for any host pack: workers have no sideways channel; merges are ordinary tasks with `dependsOn` (`handoffs.md:168-183`); planners do no coding; the state file sits next to handoffs in the workspace; one writer only; `attention.log` for anything a human should read. Andon (`core/andon.ts`) is a human stop signal that pauses new spawns only. Worth a one-line `pause` for `run`, polling an origin ref, not Slack.
- Worker prompts are honest about crashes: "the orchestrator script writes a postmortem handoff on your behalf" (`prompts/worker.md`), so workers stop writing defensive last-gasp output.

## 6. Do not copy

- `ralph-loop`: unbounded by default (`README.md:27`, `hooks.json:12` `loop_limit: null`). Stops on an agent-typed `<promise>` (`hooks/capture-response.sh:40`). VERIFIED `stop-hook.sh` never reads `.status`, so an aborted or errored turn appears to be re-prompted (behavior INFERRED; Cursor's dispatch is not in the repo). `hooks.json:6,11` still uses `./hooks/...`, the exact bug `93b00b8` fixed in advisor ("fail with exit 127 from any other cwd"), so this plugin may not run at all outside the plugin dir. INFERRED.
- `continual-learning` as written. It feeds transcripts, which hold tool output and web text, into always-loaded `AGENTS.md` with no human review: a prompt-injection path into every later session. INFERRED risk, no filter in code beyond prose. Also `lastRunAtMs` is set when the prompt is sent, not when it succeeds (`continual-learning-stop.ts:221-224`); it needs bun for a stop hook; and "Keep only these sections" (`agents-memory-updater.md:37-39`) could be read as permission to drop the rest of the file (INFERRED).
- `agent-compatibility` scoring. `npx -y agent-compatibility@latest` runs an unpinned package; the scanner is not in the repo, so its 70% weight is unread. Prompts push scores up ("Do not score a repo in the mid-60s", `validation-review.md:49`) and the skill hides how the number was made (`SKILL.md:33`). Agents are `readonly: true` yet told to boot the repo. Take the review questions, drop the number.
- `docs-canvas`, `teaching`: nothing to take (section 9).
- Canvas renderers: bound to `~/.cursor/skills-cursor/canvas/`, which is not in the repo.
- Marketplace fields (`logo`, `keywords`, `category`, `tags`, `homepage`): no reader in a framework without a marketplace.
- Weak validator: the schema leaves `hooks` as `string|object`, and it does not check that component paths exist or stay inside the plugin; that is only prose in `create-plugin/rules/plugin-quality-gates.mdc`. If we define a pack manifest, the script must check these.
- pstack's long model-routing paragraphs repeated per skill, and hard-coded model slugs in prompts (churn visible in `git log`: Grok and Opus bumps).

Suspicious content: none. Skills are ordinary prompts. The only concern is the unpinned `npx` above.

## 7. If you rebuilt the framework

Keep the engine as designed. Add a very small pack contract: a closed `pack.json` modelled on `plugin.json` plus declared slots (triggers, reads, writes, data dir). Packs subscribe to engine events rather than harness hooks and add `next` rows through a declared extension point, so an uninstalled pack costs zero and an installed one is visible in `doctor`. Add `verification` as a second axis on receipts and a checkpoint exit code. Ship `explain` as an engine verb that returns evidence, and a `learn` pack that does the teaching on top.

## 8. Coverage

Read in full: both schemas, `validate-plugins.mjs`, the generator, the CI workflow, `.cursor-plugin/marketplace.json` (head and counts), all of `teaching`, `continual-learning`, `docs-canvas`, `pr-review-canvas`, `advisor`, `ralph-loop`, `agent-compatibility`, plus `core/loop.ts`, `core/handoff.ts`, orchestrate's `SKILL.md`, `references/handoffs.md`, worker and verifier prompts. In pstack: `teach`, `how` and its prompts, `recall`, `ketchup`, `correct`, `in-your-own-words`, `show-me-your-work`, the Claude adapter (most), `reflect` (first 60 lines).

Partly read: `core/andon.ts`, `measurements.ts`, `schemas.ts`, `agent-manager.ts` (index and measurement path), `failure-handoff.ts` (structure via docs), `planner.md`, `why` (first 70 lines plus epistemics), `statechart` (first 50 lines of SKILL, no code), `create-plugin`, `cursor-team-kit/skills/pr-review-canvas` and `workflow-from-chats`.

Not read and skipped as not relevant: `third_party/` (MCP manifests), `grok-voice`, `origin-apps`, `cursor-sdk`, `cli-for-agent`, `dyl-stack`, `thermos`, the rest of `cursor-team-kit`, pstack's principle leaves and playbooks, `pstack/automations`, the external `agent-compatibility` scanner, orchestrate's Slack adapter and most tests. `thermos` and the pstack review playbooks may hold more on review; a pstack-focused study could add to this report.

Nothing was executed. Confidence: high on packaging and the small plugins, medium on orchestrate internals, low on whether any capability helps people, because the repo holds no outcome data.

## 9. Capabilities

Round 1 did not study this repo (no report existed). Capabilities not named in the assignment but found: `teach`/`how`/`why` as a stack, `recall`, `correct`, `reflect`, `statechart`, the `TERMS` lint, the evidence ladder.

| Capability | Works? (evidence) | Slot in the framework | Needs from the engine | Always-on cost | Verdict |
|---|---|---|---|---|---|
| **Pack manifest** | Yes. CI-validated across 130 plugins (`scripts/validate-plugins.mjs:51-142`) | Trigger: `install`, `doctor`. Reads `pack.json`. Writes pack section of the sha256 manifest. Data in `.agentic/packs/<name>/` | Closed schema, path checks the repo lacks, `engine` min version, per-client `never` | None | **Core** |
| **Portability lint** (`TERMS`, `--check`) | Yes, in CI (`validate-plugins.yml`) | Dev-repo CI only; not in seed | Skill list and per-client adapter data | None in projects | **Core (dev repo)** |
| **Evidence ladder** | Parsed and stored (`handoff.ts:62-71`; has tests, which CI does not run) | Field in `review/v1` rows. `next` row: HIGH needs at least `unit-test-verified` | `review/v1`, one reader in `compute_next` | One enum field, with a real reader | **Core** |
| **Failure artifacts and modes** | Code and tests exist (`failure-handoff.ts`, `failure-handoff.test.ts`); classifier is a duration and regex heuristic | Trigger: reviewer or `run` step dies. Writes journal entry. `next` prints a mode action | Event log, attempt budget | None until a failure | **Core** |
| **Checkpoint exit** | Yes (`loop.ts:68-71,85-98`) | `run` and `--exit-code`, new code | Exit table | None | **Core** |
| **Tombstones** | Yes (`schemas.ts:665-678`) | Config loader, `upgrade` | Versioned config schema | None | **Core** |
| **`teach` / `how` / `why` stack: understanding** | Prose only, but the richest here. `teach:15-17`: pick takeaways from context, smallest answer first, build diagrams one part at a time; keep `why`'s confidence words. `how`: 2-4 explorers, one explainer. `why`: 5 confidence tiers (`references/epistemics.md`). Benefit: guide claims only (`docs/guide/03-understand.md:43-51`) | CLI verb `explain <path\|NN> --json` (engine) returns evidence. `learn` pack holds the skills. Trigger: user asks; optional `next` hint after a human takes a HIGH merge. Reads git, tickets, journal, ADRs. Writes nothing by default | **Ticket-to-code index**, derivable from `NN:` commit prefixes; closed tickets and critic journals stay readable; stable JSON | None when unused | **Optional pack**, with `explain` in core if it stays a thin read of git and tickets |
| **Better than "explain to me"** (my synthesis, not in repo) | Nothing here measures learning. No learner state in any plugin; `teaching` stores nothing | `learn` pack adds: predict-then-reveal from a real past ticket ("what breaks if this check is removed?"), checked against the frozen contract and critic findings, so the answer key is real project data. Trigger: `explain --check`, or an optional `human_wait` before HIGH merge. Writes `.agentic/packs/learn/<person>.jsonl` (gitignored) | Same index, plus findings as data | None | **Optional pack; test with evals before keeping.** ASSUMED benefit |
| **`recall`: context rebuild** | Prose (`recall/SKILL.md:17-33`). Good contract: status tags verified against `git`/`gh`, reverted fixes listed first-class. Does not cover hosts lacking transcripts | CLI verb `recall [topic]`. Reads tickets, branches, journal; transcripts through a per-client locator from the pack's adapter data. Output cites ticket numbers | Event log, status derivation, transcript path per client (mapping in `docs/harness/claude-code.md`) | None | **Optional pack.** The non-transcript half belongs in the core `status`/`context` verbs |
| **`correct`: mistakes to structure** | Prose, but sound and specific. Its "prove the check fails on a real mistake" is checkable | Trigger: `next` row when a lesson class repeats, using `memory-lint` data. Reads lessons, reverts, critic findings. Writes a ticket, not an edit | Lessons as data, class grouping, cheat-set runner | None; one conditional `next` row | **Core procedure inside `agentic-archive`**; the auto-trigger waits for evals |
| **`reflect`: session review** | Prose; 3 reviewers plus synthesizer, human approval required, structural fixes routed first (`reflect/SKILL.md`). Costly: 4 subagent calls per run | CLI verb, on request. Reads transcript. Writes proposed edits only | Transcript locator | None | **Optional pack**, after `correct` |
| **`continual-learning`: automatic memory** | Cadence gate is solid (turn, time, mtime, dedupe; `continual-learning-stop.ts:137-139,151,215-219`). Update step is an unverified prompt. Good ideas: 12-bullet cap, index of processed files, exact "no updates" reply | Trigger: engine event `ticket.shipped`, not a stop hook. Reads journal first, transcripts second. Writes a **proposed** diff to `CONTEXT.md` or lessons, through `memory-lint`, inside the ticket's PR | Event log, `memory-lint` citations, human gate on always-loaded files | None | **Optional pack, redesigned.** Automatic writes to always-loaded memory: skip |
| **Decision log** (`show-me-your-work`) | Small script with CSV-injection guard (`scripts/log.sh`); audited against the transcript at the end | Fold into the run log | Script-written events | Low | **Skip**: RECOMMENDATIONS' run log is better because it is not agent-written. Take the transcript audit for evals |
| **Advisor: second model at checkpoints** | Hooks read and sound: armed by edits, cleared by consult, once per batch, gated on a state file. Real history (`93b00b8`). Benefit unmeasured | Trigger: `next` hint on **stuck** (failure signature repeats; script detects it, better than advisor's prose), before HIGH claim, and before review. Verb `consult --checkpoint stuck`. Reads ticket, diff, check output, verbatim per `references/briefing-template.md`. Writes `journal/NN-advice.md`. Advisory, never a gate | Failure signatures, `models.advisor`, reviewer-launch path reused; read-only profile | None; no hook needed when `next` drives it | **Optional pack.** Evals must show it pays. Must not count as review |
| **`agent-compatibility`: readiness** | Prompts only; scanner unread. Questions are good | `doctor --agent`: deterministic part (is `verify.test` set, does it run, how long, is there a scoped path) in core; agent review as `agent_task` in a pack. Writes `.agentic/state/readiness.json` | `doctor --json`, time budget | None | **Deterministic: core. Agent review: optional pack.** No blended score |
| **Human review brief** (`pr-review-canvas`) | Canvas version is prose. `cursor-team-kit/skills/pr-review-canvas` has a 170-line HTML renderer (not read closely). Structure: core, wiring, boilerplate; pseudocode only for hard logic; old vs new trace on one input; rationed callouts | Trigger: `human_wait` at HIGH merge. Reads `review/v1`, diff, contract. Writes `journal/NN-brief.md`, or static HTML in a pack | Typed findings, contract items, file classification | None | **Optional pack**, Markdown first |
| **Docs canvas** | Placeholder | None | n/a | n/a | **Skip** |
| **`teaching` plugin** | Two generic prompts (34 and 28 lines), no code or state, not about a codebase | None | n/a | n/a | **Skip** |
| **Statechart** (TLA+ to Mermaid) | Large and tested (407 files, needs Java and TLC via mise). I read only the SKILL head. Idea: a diagram backed by a checked model, with shortest path to each broken rule | Dev repo: model `compute_next`, or a pack for projects with state machines | None from core | None | **Optional pack, later.** Possibly useful for proving the table in the dev repo. INFERRED |
| **Code to graph** | Not present. A grep for call graph, tree-sitter and knowledge graph found only passing mentions in prose (VERIFIED) | n/a | n/a | n/a | Nothing here |
| **Orchestrate** | Real; tests exist; CI skips them; last functional change June 2026 | External host. `frontier --json` to `plan.json` mapper | Stable JSON | None | **Skip as code**; optional thin host pack only if someone uses Cursor cloud |
| **Ralph loop** | Works in shape; defects in section 6 | Replaced by `stop_followups` plus `next` | n/a | n/a | **Skip** |

**Extension API this implies** (Judgment, combining the above):

```json
{"name": "advisor", "version": "1.0.0", "engine": ">=2.0",
 "clients": {"claude": "*", "cursor": "*", "codex": "never"},
 "skills": "skills/", "agents": "agents/", "verbs": {"consult": "bin/consult.py"},
 "on": {"ticket.shipped": "bin/on_ship.py"}, "next_hints": ["hints/stuck.json"],
 "config": {"type": "object", "properties": {"model": {"type": "string"}}},
 "reads": ["ticket", "diff", "checks"], "writes": ["journal/NN-advice.md"]}
```

- **Engine events, not harness hooks.** `advance` appends to the event log, then runs subscribed pack handlers. A pack adds no harness settings, so "no reader, no hook" holds and removal is clean. Hooks stay core and guard-only.
- **`next_hints`, not table edits.** A pack contributes advisory rows only, of kind `hint`. They can never change state, block a ship, or sit ahead of a core row. This keeps the first-match table auditable.
- **`reads`/`writes` are checked by the engine**, not just documented: a pack writing outside them fails `doctor`. Nothing in the Cursor format does this.
- **Conflicts.** None with a clean seed: packs live in `packs/` and data in `.agentic/packs/`. Each field above has a reader; the risk is `reads`, which is justified only if `doctor` truly enforces it. Drop it otherwise. A pack skill's description still costs tokens when listed, so optional skills should be explicit-invocation only.
- **Engine must provide:** stable JSON, event log, ticket-to-code index, findings and lessons as data, failure signatures, a per-client transcript locator, and a reviewer-launch path reusable for read-only agents.
