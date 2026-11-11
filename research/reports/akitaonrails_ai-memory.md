# akitaonrails_ai-memory

Study round 2. Repo at `7066120d`, MIT (`other-solutions/MANIFEST.tsv`). `FW:` means `agentic-framework/`. Labels: VERIFIED, INFERRED, ASSUMED. Nothing from the repo was run. All numbers quoted from its benchmarks are the repo's own and were not reproduced.

**Verdict: idea source, with an optional thin compatibility pack only if a user already runs it. Not a framework dependency.**

## 1. What it really is

A self-hosted memory server: one Rust binary, an HTTP and MCP service, a git-backed markdown wiki as truth and SQLite as a rebuildable index. About 589k lines of Rust across 11 crates including inline tests, 7,544 test annotations, 5,587 commits from 2026-05-21 to 2026-11-05, one lead author plus several contributors, plugin version 3.4.2 (VERIFIED by count and `git shortlog`). 27 MCP tools (`docs/ARCHITECTURE.md:806`). It is real and heavily engineered, the most serious memory project in this study. It is also a product with its own daemon, auth, web UI and more than 30 agent integrations.

**Memory model (VERIFIED).** Four tiers: working, episodic, semantic, procedural (`docs/ARCHITECTURE.md`, "Memory tiers"). Pages are versioned by `is_latest` plus a `supersedes` chain. Tables worth noting: `observations` (sanitized lifecycle events), `handoffs`, `page_feedback`, `page_evidence`, `entities`, `links`, `agent_messages`, `audit_log`.

**Write path (VERIFIED).** Hooks post events (`hooks/claude-code/post-tool-use.sh`, 0.2 s budget at `hooks/_lib.sh:1043`), or a native client spools them with idempotency keys. At SessionEnd a rule-based page `sessions/<id>.md` is written and an automatic handoff opens. With no LLM, that page has prompt titles, tool counts and failed calls (`crates/ai-memory-hooks/src/synth.rs:819-900`), not extracted knowledge. Durable rules, gotchas and decisions only appear through an LLM (consolidation, auto-improve) or an explicit `memory_write_page`, which the skill limits to explicit user requests (`routing_skills/ai-memory-durable-pages/SKILL.md`). So the zero-LLM product is **session logs plus search**, not a compiled knowledge base.

**Retrieval (VERIFIED).** RRF fusion, k=60, of FTS5, entities, link graph, optional vectors and an observation stream, then a bounded authority adjustment (`crates/ai-memory-store/src/reader.rs:8378-8404`, `:8852`). Well built, with `explain` output.

**Invalidation (VERIFIED).** Supersession hides old versions. Time and access decay evict cold episodic pages (`crates/ai-memory-store/src/decay.rs:95-103`). `memory_feedback` flags `stale` or `wrong` and surfaces the page in lint, an agent or user act. `source_files: [{path, commit}]` on a page is stored, but no server, hook or CLI code compares it to the repo: grep finds no use in `ai-memory-cli`, `-hooks`, `-consolidate`, `-web`. The check is a sentence telling the agent to notice (`crates/ai-memory-mcp/src/server.rs:474`). Contradictions are flagged, never resolved. Nothing here verifies a claim against code. `FW:scripts/memory-lint.sh:145-172` does, by script.

**README claims the code does not support.**
- "Nothing is hard-deleted" (`README.md:80`). The default daily sweep (`crates/ai-memory-cli/src/commands/serve.rs:2230`, `config.rs:1985`) tombstones cold episodic pages and hard-deletes tombstones and their chain after 180 days (`crates/ai-memory-consolidate/src/sweep.rs:17-18`, `decay.rs:99-100`, `crates/ai-memory-store/src/ops.rs:4908`). `DATA_HANDLING.md:160-163` admits this. Git history may keep the file; the version chain does not survive. The README's list of "off by default" content-dropping features omits this one (`README.md:82`).
- "Memory compiles into readable pages" is not how zero-LLM recall works. Their own decomposition: at most 10.2% of questions had evidence reachable on the session page (`docs/benchmarks/longmemeval-s-decomposition-2026-10-12.md:120`). The 0.951 comes from ranking raw observations and lifting the session (`docs/benchmarks/README.md:164-169`).
- The headline 0.951 needs assistant-text capture, off by default. The harness sets it (`evals/src/retrieval/ingest.rs:208`, `server.rs:111`), the default is false (`crates/ai-memory-cli/src/config.rs:1486`). `evals/README.md:337` says so; the baseline table and README do not. Default-install recall is unmeasured.
- "Offer, don't claim" (`docs/design-handoff-offer-not-claim.md:3-6`) is implemented, but `claim_on_session_start` still defaults to `true` (`docs/config-properties.md:286`), so the destructive claim stays the default.
- "Validated (… eval gate)" (`docs/auto-improvement-loop.md:8-9`): the gate is disabled by default (`docs/ARCHITECTURE.md:50`). The confidence floor is the model's own number (`crates/ai-memory-consolidate/src/auto_improve.rs:2143-2147`).

**What the evals really prove (VERIFIED).**

| Eval | Proves | Does not prove |
|---|---|---|
| LongMemEval-S, 470 questions, hit@5 0.951 FTS, 0.940 local (`docs/benchmarks/longmemeval-s-3.4.0-release.md`) | A session holding the evidence ranks in the top 5, on chat corpus, one project per question | Answers, code work, agent behavior. Release runs skip QA |
| Decomposition: grep 0.887, pipeline 0.662 before stream, raw whole-session FTS 0.972 (`:66-70`) | Capture shape was the loss, not ranking | That compiled pages help. Raw FTS beats the shipped pipeline |
| `coding-v1`, 4 questions, 12 sessions each | Repeatability. Offline grep got the same scores (`evals/README.md:454`) | Quality. They say "regression probes" (`:407`) |
| Literal fidelity, 3 runs, 1 model | Small at-risk fact recovery | General summary quality |
| Abstention fixture | Regression probe, no calibrated threshold | Anything representative |

They state the key limit themselves: "Retrieving the correction does not prove that an agent follows it" (`evals/README.md:399`). The eval commands never run in CI (`:24`); they are run by hand per release. No eval compares agent outcomes with and without memory. I found no held-out split, and the ranker work targeted this same set (INFERRED). Local embeddings, which the default install downloads (87 MB, `DATA_HANDLING.md`), lose to plain FTS at hit@1 (0.764 vs 0.857) and hit@5.

**The first-round finding: memories are rarely read.** ai-memory does not solve it and does not measure it (VERIFIED).
- Pushed by default: the pending handoff, a profile digest (single-user), and notices. That is session continuity, not knowledge.
- The knowledge brief is off by default, for an honest reason: "the brief costs tokens on EVERY session start, so opt in per repo" (`docs/marker-file.md:174`, `crates/ai-memory-hooks/src/router.rs:2917`).
- Everything else is pull. The agent must call `memory_query`, steered by a 155-line always-loaded block (`AGENTS.md:1-155`, about 9 KB) plus skills. I found no hook that searches per prompt or per file. Their remedy when agents do not call it is "refresh the managed routing package" (`docs/mcp-install.md:1991`). More prose, same as `FW:` CONTEXT.md.
- They own a tool-selection eval as a gap (`docs/ARCHITECTURE.md:822`). `client_activity` counts reads and writes server-wide per day. I found no per-session recall rate.
- Path-triggered delivery, which ownmem already ships, is still being designed: the index exists (V99, opt-in), "the measurement and delivery are open" (`docs/design-file-path-index.md:3-6`), and `observations_for_file` has no production caller (`crates/ai-memory-store/src/reader.rs:4395`; callers are tests only).

So a 589k-line system lands where aommi and ownmem pointed: **delivery has to be wired to a moment, and it must be measured.** This reinforces `FW:` "lessons linted but barely read".

## 2. Take

All MIT, but the code is Rust and the framework is targeting stdlib Python, so these are ideas unless noted.

| Item | Mechanism and `path:line` | Framework part | Why better | Effort | Copy |
|---|---|---|---|---|---|
| **Pipeline vs component eval decomposition** | Same questions measured at each stage: grep, shipped pipeline, captured text only, raw whole docs, plus a reachability instrument for whether evidence survives to each surface (`docs/benchmarks/longmemeval-s-decomposition-2026-10-12.md:60-125`, `evals/src/retrieval/reachability.rs`) | RECOMMENDATIONS section 5, Phase 0 | It found a 31-point loss in one stage, which a single score hid. Same shape fits review: seeded defect, did it reach the payload, did the reviewer see it, did it block | M | Idea |
| **Pinned noise band in every report** | Dataset sha256, commit, hardware, an identical-candidate A/B, a stated ±0.005 band, questions that moved (`docs/benchmarks/longmemeval-s-3.4.0-release.md`, `evals/README.md:407-430`) | Three-arm evals | Prevents reading noise as a win. Proctor and repo-harness numbers in round 1 had none of this | S | Idea, report template |
| **Cover-first context packer** | Every page gets an excerpt first, leftovers deepen pinned then cheapest bodies, a body is whole or absent, overflow lists paths, then a count (`docs/marker-file.md:184-193`, `crates/ai-memory-hooks/src/brief_tiers.rs`, `router.rs:3504`) | New `context` verb | One long lesson cannot starve the others. It solves the budget half of the read path | S | Idea |
| **Script-derived crash snapshot** | When a harness dies with no SessionEnd, the next start renders recent activity from captured events, capped at 6,000 chars, and a metadata-only notice names the cut-off session (`router.rs:2663-2720`, `:2375-2400`) | `FW:agentic-handoff`, an agent-written file that a quota or crash skips | Survives the case that matters most. The framework needs only `git status`, the ticket, last events, derived at `next` | S | Idea |
| **Compaction anchor** | A compaction's SessionStart is detected, handoff is not re-claimed, a small anchor with first and latest operator prompts is injected (`crates/ai-memory-cli/src/commands/hook.rs:2183-2199`, `crates/ai-memory-hooks/src/recap.rs:1-4`) | `FW:scripts/hooks/session-start.sh:12-18`, which ignores `source` | After compaction inject the ticket's Done Contract and scope, not a generic header | S | Idea |
| **Fence plus marker escaping** | All delivered memory sits between start and end markers with a notice; stored text has markers escaped so it cannot close the fence (`router.rs:3469-3485`, `crates/ai-memory-core/src/workstream.rs:22`) | `next` output and remedies, already flagged (`gate.sh:416`) | Concrete shape for "remedies are sanitised", including the fence-breakout case | S | Idea |
| **Harness delivery table** | Per-harness predicates with sourced facts: Grok, Kimi, Zero, Hermes, Pool, DSH, Cline do not deliver SessionStart stdout; Kimi takes it on UserPromptSubmit; Grok on PostToolUse; Cursor envelope unverified (`crates/ai-memory-core/src/ids.rs:500-600`, `hook.rs:1150-1170`) | Phase 5 coverage matrix, `FW:adapt.sh` | Real data for a matrix. It also shows a destructive fetch must not run on a harness that drops the output | S | Facts plus idea |
| **Foreign-hook-safe config merge** | Drops only own entries, keeps third-party hooks on that event, atomic write, timestamped backup (`crates/ai-memory-cli/src/commands/install_hooks.rs:2293-2299`, `:12`); `setup --plan --json` changes nothing | `install`, `upgrade`, `doctor` | Directly opposite the aommi bug that wiped host hooks | S | Idea |
| **Token ledger from native transcripts** | Client reads the harness's own transcript with bounded batches, dedups by response id, publishes a cursor only after spooling (`crates/ai-memory-cli/src/commands/session_usage.rs:1-40`) | Run log, cost per ticket | Cost arrives script-derived, not self-reported, which is what section 5 requires | M | Idea |
| **Commit-pinned citations, checked by script** | `{path, commit}` on a page (`crates/ai-memory-mcp/src/server.rs:412`). ai-memory leaves checking to the agent; the framework should run it | `FW:memory-lint.sh` `cite:` | Add optional `commit:` to `cite:`. Needle miss says "gone", a diff since commit says "re-verify". Strictly stronger than their version | S | Idea |
| **Literal fidelity scoring** | Fixture `must_mention` and `must_not_mention`, split into lost before the model vs lost by the model (`evals/README.md`, "Literal fidelity") | Any generated summary or review brief | Cheap, zero-LLM half included. Also tests injection strings do not survive | S | Idea |

## 3. Challenges

- **"Write lessons at ship, read by convention" (framework). Wrong, and ai-memory does not fix it.** It has the same structure at huge scale: capture is automatic, knowledge reading is voluntary. Build one wired read path, then decide by ablation.
- **Cited, checked memory (framework) vs captured, decayed memory (ai-memory). Framework is right for project knowledge.** `memory-lint` proves a claim still matches a file. Decay proves only that nobody touched a page. Access-weighted retention also needs reads to work, and reads are the missing part. ai-memory is right for one narrower thing, searchable session history, which the framework lacks.
- **Bash plus files as runtime. Largely supported.** Even here markdown is truth and SQLite is derived. The daemon exists for multi-agent, multi-machine, multi-user sharing. The framework's git tree already shares across clones. No daemon.
- **One hook set for three tools. Split verdict.** One event model is right. Delivery differs per harness enough to need a table (section 2).
- **Selftest as main proof. Both are partial.** 7,544 tests did not reveal the 66% vs 97% gap; the eval did. But no eval here measures outcomes either. Keep mechanics tests and add evals, per RECOMMENDATIONS.
- **Human accepts everything vs auto-approve.** ai-memory auto-approves LLM edits, including rule promotion, by default (`docs/auto-improvement-loop.md:8-9`), with shared servers told to change it. For anything that steers agents, the framework's stance is right. Generated learning must arrive as a proposal or ticket.
- **Long AGENTS.md. Framework's short file is right.** Their design note puts the budget near 100 lines (`docs/design-rules-promotion.md:30-31`). Their own always-loaded block is 155.
- **Rule promotion.** Their design doc (not implemented, `:6-8`) makes promotion subtractive: a rule must evict one. `FW:agentic-archive` already goes further by promoting a lesson to a check. Keep that. Borrow only the eviction idea for `CONTEXT.md`.
- **Handoff as stored baton vs derived state.** Their own report: an unrelated session consumed a handoff (`docs/design-handoff-offer-not-claim.md:20-33`). This supports RECOMMENDATIONS: derive state, do not store a baton.

## 4. Delete or simplify

- `FW:agentic-handoff` can shrink to a script-derived snapshot plus one agent line, the open question.
- Do not add decay, salience, belief scores, vectors or a retention sweep. Belief is default 0 and unmeasured (`docs/benchmarks/longmemeval-s-decomposition-2026-10-12.md:317-321`). Their comparison admits "parity of mechanism, not a measured quality win" (`docs/comparison.md:219`).
- The lesson TTL with enforcing-cite exception stays. It replaces all of decay at about 40 lines.
- `Lessons: none` remains ceremony until the read path exists, as the earlier reports said.

## 5. Orchestration

- **Capture ownership is one env var.** `AI_MEMORY_CAPTURE_OWNER` tells hooks an orchestrator owns capture; delivery continues (`docs/external-lifecycle.md:11-46`). The framework's analogue: a single variable telling hooks who owns events, next to `AGENTIC_UNATTENDED`.
- **Warn about destructive reads.** Their doc says context delivery may claim a handoff even with capture suppressed. Any read that consumes must be labelled in the contract. `next` must stay pure.
- **Durable delivery lives in a companion.** `ai-memory-relay` keeps a local queue so events survive a down server (`companions/ai-memory-relay/README.md`). Stable per-event keys make retries safe (`docs/ARCHITECTURE.md`, "Steady-state loop"). The event log should carry a stable id from day one.
- **A claim is a guarded update** on `state='open'`, zero rows meaning lost (`crates/ai-memory-store/src/ops.rs:5627-5631`). Same shape as refs compare-and-swap.
- A shared server does solve "state across clones", at the cost of a service an orchestrator must host. Git refs remain the better fit for the framework.

## 6. Do not copy

- **Scale and surface.** 27 tools, over 30 agents, 7 companions, web UI, SSO, desktop and macOS apps.
- **Capture everything first.** Every prompt and tool output kept, `observation_retention_days = 0` meaning forever (`config.rs:151`, `DATA_HANDLING.md:164`), no encryption at rest (`:35`), sanitizer "best-effort" (`:99`). Eviction is not deletion, since raw observations stay. Fails "no reader, no field" unless a reader is proven.
- **Storing a field before its reader exists.** `observations.file_path` is the live example, though it is opt-in and the author says so plainly.
- **Auto-approval on model-reported confidence**, and a built-in scorer that only checks H1, placeholders and lists (`docs/auto-improve-eval-gates.md:33-44`).
- **Default-on 87 MB embedding download** that scores below FTS on their benchmark.
- **Mechanisms shipped dark.** Dream, belief, per-tier curves, residue: code exists with no measured gain.
- **`INSTALL_FOR_AGENTS.md`.** It is addressed to agents and tells them to pipe `curl` to `sh`. It is checksum-guarded, not malicious, but it is instruction-shaped text. Quoted fragment: "You are an AI coding agent". Treated as data. The routing block also tells agents to prefer it over harness-local memory (`routing_snippet.rs:92-95`), which steers behavior. Suspicious content: none beyond this.
- **Chat benchmark as a coding claim.** Do not cite 0.951 as evidence that memory helps coding.

## 7. If you rebuilt the framework

Keep files in git as the only truth, and keep cited, needle-checked memory. Add one read path: `context NN` selects lessons whose cite paths intersect the ticket's scope, packs them cover-first, fences them, and fires at claim and in the reviewer payload. Log which ids were delivered. Then run ablation. If history search is wanted, build a derived FTS index over journals and tickets with stdlib `sqlite3`, disposable and rebuilt on demand. Their data suggests plain FTS over raw text gets nearly all retrieval value, with no LLM, no vectors and no daemon (one chat dataset, so ASSUMED transferable). LLM learning arrives later, as a pack that writes proposals into tickets.

## 8. Coverage

Read: README (first 260 lines), `DATA_HANDLING.md`, `INSTALL_FOR_AGENTS.md`, `CLAUDE.md`, `evals/README.md`, benchmark 3.4.0, decomposition (parts), fidelity report, ARCHITECTURE sections (data flow, storage, MCP, invariants), parts of `docs/features.md`, `usage.md`, `design-*` docs for brief, handoff, file index, rules, aging; `routing_snippet.rs`, retrieval and durable-page skills, `hook.rs` session-start and subagent paths, `router.rs` brief and handoff renderers, `synth.rs` headers, `decay.rs`, `sweep.rs` header, `belief.rs` header, `auto_improve.rs` header and validation, `recap.rs` header, `session_usage.rs` header, `setup.rs` header, `install_hooks.rs` merge, `ingest.rs`, two Claude hook scripts, companion READMEs. Framework: `memory-lint.sh`, `session-start.sh`, `agentic-handoff`, `agentic-archive`, RECOMMENDATIONS, aommi and ownmem reports.

Not read: `run.rs`, `transcript.rs`, `jail.rs`, web crate, auth, LLM providers, importer, desktop, macOS, Nix, Windows paths, most of `install_mcp.rs`, `consolidator.rs` prompts, `workstream` internals, RRF body in detail, CHANGELOG. Skimmed by grep only: `capture_policy.rs`, `sanitize.rs`, `lint.rs`, `bootstrap.rs`.

Confidence: high on the read-path gap, invalidation, README mismatches and what evals cover. Medium on how good handoffs are in practice, since none was observed. The workstream and transcript-portability capability is reported from docs only. Effort sizes are ASSUMED.

## 9. Capabilities

Owner's named areas: **memory** is this repo's core. **Docs:** `bootstrap` seeds pages from git log, README and docs with an LLM (`crates/ai-memory-consolidate/src/bootstrap.rs:1-30`). **Diagrams:** none. **Code to graph: none.** Its link graph covers wiki pages, and it tells users to run a structural tool beside it, sharing nothing (`docs/usage.md:393-398`). Its `docs/research-codebase-memory-mcp.md` is a useful pointer for that track. Boundary worth keeping: memory says why, structure says where, tests say whether (`docs/usage.md:399-404`). **Learning:** auto-improve and the experience pass; these teach the wiki, not the human.

Missed by round 1 since the repo was not studied: token ledger, compaction recovery, cross-project profile, agent inbox, managed workstream launcher, wikisync.

| Capability | Works? (evidence) | Slot in the framework | Needs from the engine | Always-on cost | Verdict |
|---|---|---|---|---|---|
| Wired memory delivery (brief) | Yes, off by default (`router.rs:2909-2917`). No proof of benefit | `context NN` verb, called by `next` at claim and in the reviewer payload. Reads lessons, CONTEXT. Writes delivered ids to the run log | Ticket-to-path index (`scope_paths`), stable JSON, event log | Bounded chars per claim, nothing at rest | **Core** |
| Path-triggered delivery | Index only, no reader (`docs/design-file-path-index.md:3-6`) | PreToolUse on Edit, once per ticket per path, as in ownmem | Hook event, lesson cite index | Small per-edit lookup; no write if no hit | Optional pack, after `context` proves out |
| Commit-pinned cite | Field stored, check is prose (`server.rs:474`) | `memory-lint` at ship | `cite:` grammar | None | **Core**, S |
| Crash snapshot | Yes, per `router.rs:2663`, not run | `next` when branch has dirty or unreported work | Event log | None | **Core**, derived |
| Compaction anchor | Yes on verified harnesses (`hook.rs:2183`) | SessionStart `source=compact` | Harness table | One short injection on compaction | **Core**, S |
| Fence and escape | Yes (`router.rs:3469`) | All `next` and `context` output | Output formatter | None | **Core** |
| Session capture and FTS search | Yes for retrieval on chat corpus; agent use unproven | `pack: history`. Hook events append to a gitignored log; `search` verb builds disposable SQLite FTS | Hook event stream, redaction rules, `[capture]` excludes | Hook write on each event; privacy surface; zero if pack is off | Optional pack, lean on stdlib. Conflicts with "no reader" unless `search` ships with it |
| Cross-harness handoff | Yes, claim once (`ops.rs:5627`). Auto-claim misfires (`design-handoff-offer-not-claim.md:20-33`) | Replaced by derived state and snapshot | None | None | Skip the baton |
| Token ledger | Yes per code, verified on their transcripts (`session_usage.rs:14-17`) | `run` log and evals | Event log, per-tool parser | Parse on session end | Optional pack; evals need it |
| Harness capability table | Yes (`ids.rs:500-600`) | Engine data file for `doctor` and packs | Versioned schema | None | **Core** |
| Auto-improve learning | Yes with LLM. Default auto-approve. Outcome unmeasured. Telemetry report only | Schedule or post-ship; writes proposals as tickets or lesson drafts, never direct | LLM command config, intake verb | None if unused; one LLM call per session if on | Optional pack; idea only, change the default |
| Experience pass | Opt-in, needs LLM, no eval (`docs/experience.md`) | Weekly schedule; reads journals; opens tickets for repeated defects | As above | None if off | Optional pack, later |
| Decay, dedup, dream, belief | Math is tested; benefit unmeasured | None | None | N/A | Skip |
| Contradiction lint | Rule and band detection, needs embeddings or LLM (`lint.rs:520-577`) | None now | Embeddings | N/A | Skip |
| Doc bootstrap | Yes with LLM, one-shot (`bootstrap.rs`) | `install` option to draft `CONTEXT.md`, with cites required | LLM command, memory-lint | None | Optional pack. Must pass cite lint, else it writes unchecked claims |
| Wikisync `sync --check` | Exists; not traced beyond README | Not needed: memory is already in git | None | None | Skip; useful only in the compat pack |
| Compat pack for ai-memory itself | Hooks coexist (`install_hooks.rs:2293`). Needs a server | `packs/ai-memory`: docs and a marker with `[briefing]` on and `[capture]` excludes for `.env`, `.agentic/state` | Pack API, doctor check | Server, 9 KB block, hook latency, all borne by the user who opted in | Optional, low priority |
| Agent inbox, managed workstreams | Docs only, not traced | None. Host orchestrators own this | None | N/A | Skip |

**Extension API implications.** Stable JSON, an append-only event log with stable ids and delivered-memory ids, a ticket-to-path index, a hook event model with per-harness delivery facts, and a pack rule that any pack adding a write must ship its reader. Seed stays clean: everything above writes to project journals or gitignored state, and core adds no template content.
