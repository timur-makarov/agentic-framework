# sondera-ai/sondera-coding-agent-hooks

Nothing from this repo was built or run. Every label below rests on reading the code plus `git log` and `grep`. "Host" behaviour (what Claude Code or Codex does on a timeout) is the repo's claim, not something I tested.

## 1. What it really is

- A Rust security monitor for coding agents, not a workflow framework. 78.9k lines of Rust, 384 files, 92 commits. It has no tickets, gates, review or state machine (VERIFIED). Most of it is one squash, `c9d0626` (2026-08-03); since then, mostly dependency bumps, so history teaches little.
- Flow: `sondera hook <agent>` normalizes an event, sends gRPC to a long-running `sondera serve`, which runs a YARA scan, optional LLM classifiers and Cedar, and answers Allow/Deny/Escalate (`crates/policy/cedar/src/lib.rs:316`, `transform.rs:539`). Ten host adapters, a TUI, a Turso store, an MCP server.
- The engineering around failure is careful and heavily tested (about 1,430 test attributes). The policy corpus is much weaker than the engine.
- README claims the code does not support:
  - **"Reference monitor."** Nothing is tamperproof. No rule covers `.sondera/`, `.claude/` or the hook settings (VERIFIED, grep across all `.cedar` files). `docs/deployment.md:5` admits that whichever process binds the port first controls adjudication, and neither surface authenticates.
  - **Structured shell matching.** The tree-sitter parser feeds only 5 of the 46 shell rules. The other 41 are raw `like` globs (VERIFIED). `forbid-git-rebase-no-verify.cedar` matches `*git commit --no-verify*`, so `git commit -m x --no-verify` passes; no YARA rule mentions `no-verify`. Framework `guard.sh:214` catches this case. On this point the framework is better.
  - **Secure-code policy guardrail.** It fills `context.policy`, and 0 of 110 policies read it (VERIFIED). It costs one model call per template per event and has no effect on any shipped decision.
  - **`Mode` (Monitor/Govern/Steer).** Stored at `cedar/src/lib.rs:230`, never consulted when deciding (VERIFIED). Comments at `lib.rs:334` describe a Monitor deployment that does not exist in code.
  - **Escalate.** Fully wired, with `@escalate` on 0 policies (VERIFIED). No shipped rule can ask. Codex "ask" in the README table is really deny (`crates/hooks/codex/src/hooks.rs:159`).
  - **IFC with no key.** The quick start says no provider is needed. Without one every label is `Public` (`transform.rs` `classify_label`, near line 75), so all label rules are dead. Labels also fail open, despite the "fail closed" headline.
  - **Coverage.** No policy targets `PreToolUse`, `ToolOutput` or `ShellCommandOutput` (VERIFIED), so MCP tools, Task and the output of Bash and Grep have no rule at all. At most 4 of 109 forbid ids appear by name anywhere in Rust (VERIFIED), so the corpus is mostly untested.

## 2. Take

License: `LICENSE` is MIT (Sondera, Inc.). The repo is **not listed in `MANIFEST.tsv`** (0 matches); I relied on the file itself. The framework is bash, so everything is an idea port unless noted.

| Item | Mechanism and `path:line` | Framework part | Why better | Effort | Copy |
|---|---|---|---|---|---|
| 1. Catch-all matcher, default allow, always recorded | `crates/hooks/claude/src/install.rs:112` uses `"matcher": "*"`; unknown tools become a recorded `ToolCall` (`hooks.rs:~355`); `Glob`/`Grep` map to file reads (`hooks.rs:307`). `crates/hooks/README.md` states the rule: a name not mapped is a name not governed, and the failure is silent | `.claude/settings.json:19`, `.codex/hooks.json`, `adapt.sh:85` (`*) exit 0`) | Closes the verified Grep/Glob gap at the root: a new host tool is seen rather than skipped. Copy with a fix: Sondera checks only Grep's `path`, so `glob: "*.pem"` or a `path` of `.` escapes. Also check `glob` and the output | S | Idea (MIT) |
| 2. Hook decision log with rule ids | Every event plus a `Control::Adjudicated` record, caused-by link, policy id (`cedar/src/lib.rs:380-420`), written to per-run JSONL (`crates/storage/src/file.rs:39`). Refused bodies are stored redacted (`crates/types/src/trajectory/redact.rs:72`) | `audit.sh` logs only completed shell commands, no denies. `guard.sh` denies carry no rule id | Cheapest real answer to "not measured". Gives per-rule fire counts, rules that never fire, deny rate per ticket and a cost for the ceremony. Requires an id on every `deny`/`ask` | S | Idea |
| 3. `@`-mention re-derivation | `crates/hooks/core/src/mention.rs` (module doc): `@file` is inlined into the prompt, no tool call fires, so `UserPromptSubmit` re-parses and checks each path | Not in the brief. Framework has no `UserPromptSubmit` hook; `@.env` skips `protect.sh` (INFERRED from the host claim; test on Claude Code first) | New gap in the secret guard. Small hook reusing the `secret_re` list from `guard.sh:153` | S | Idea |
| 4. Fail-closed matrix test | `assert_fail_closed_matrix` (`crates/hooks/core/src/runner.rs:266`): every command × every error variant must deny, or must not deny | `selftest.sh:409` tests one bad-input case | One table proves all hooks and failure modes (missing jq, bad JSON, no git, unset var, non-repo cwd). Also catches over-blocking | S | Idea |
| 5. Hook budget under the host deadline | `runner.rs:40-55`: a killed hook writes no decision, the host reads "no opinion", the action proceeds. So a single budget covers stdin, connect and call, and sits below the host timeout | `guard.sh` reads stdin with unbounded `cat`, then runs git. Host timeouts 10-15s in the configs | Timeout is a fail-open path the `ERR` traps do not cover (INFERRED; depends on host). Fix: bound the stdin read and git calls with `timeout`, and test it | S | Idea |
| 6. Strict config, layered | `deny_unknown_fields` (`crates/settings/src/lib.rs:656`), project over user key by key, with the reason stated: a mistyped key in a governance config must fail at startup | `.agentic/config.yml` parsed with awk; `tracker`, `exception_max_days` are dead and silent | Stops dead config recurring. A short key allowlist in `env-lint.sh` does it without a YAML parser | S | Idea |
| 7. Managed-hook installer | `HookConfigInstaller` (`crates/hooks/core/src/install.rs:51,140,216`): timestamped backup, refuses a non-object config, splices only its own entries, keeps user hooks. `RETIRED_MANAGED_HOOK_SUBCOMMANDS` (`claude/src/install.rs:53`) removes old hooks on upgrade | Copy-in only; a host with its own `.claude/settings.json` conflicts | Shows that wiring is a merge, not a copy, with install, uninstall and upgrade steps. Use `jq`/`python3` | M | Idea |
| 8. Capability table per host | `crates/hooks/README.md` matrix: block/ask/steer/redact/terminate per adapter and hook group. Rule: a host lacking a verb gets the nearest safe one, so Escalate on Codex is deny (`codex/src/hooks.rs:159`, tested at `:920`). Typed `HOOK_MATRIX` keeps unsupported events visible with a reason (`claude/src/event.rs`) | `adapt.sh:44` turns `ask` into allow on Codex and leaves the decision to the sandbox | Contradicts the framework's choice. Make ask-to-deny the default on such hosts for the irreversible `ask` rules (`reset --hard`, `clean -f`, `rm -r` outside the repo), with a config opt-out. Put one table in the docs and have `env-lint.sh` check it | S | Idea |
| 9. Codex coverage via `PermissionRequest` | `crates/hooks/README.md` note †: Codex `PreToolUse` fires for Bash only, `PermissionRequest` with `*` carries the rest (`codex/src/install.rs:37` region) | `.codex/hooks.json` has no Read path | Possible route for the verified Codex gap. Host claim, ASSUMED; verify against the Codex version in use | S | Idea |
| 10. Tool-name and argument normalization | `normalize_tool_name` (`core/src/tool.rs:45`), `file_path_arg` (`:90`), post mapper defined as "the builder would produce one" (`:323`) | `adapt.sh` matches literal names; `protect.sh` has its own key list | A wrong key gives an empty path, which `protect.sh` allows silently (`[ -n "$path" ] \|\| allow`). Make empty path on a known file tool a deny | S | Idea |
| 11. Parsed shell view, if `guard.sh` stays | `shell_parse.rs`: program, flag and arg sets; wrapper table (`:41`), `-c`/`eval` re-parse (`:144`, `:700`), ANSI-C decoding (`:926`), bundled-flag split, `ok:false` falls to a conservative branch. Policy pattern in `forbid-rm-rf.cedar` | `guard.sh` regex, 250 lines | Catches `/bin/rm`, `sudo -u x rm`, `xargs rm`, `$'\x72m'`. Does **not** catch `python -c` (`SHELLS` omits interpreters; VERIFIED), so the headline bypass stays. Python `shlex` version; do it after evidence is unforgeable, since that matters more | M | Idea; Rust is MIT but not usable in bash |
| 12. Rule proof: deny plus near-miss | `.agents/skills/autoformalize/references/behavioral-check.md`: must deny citing the id, near-miss must allow. Commit `c9d0626` deleted 25 comment-only policy files that documented controls never built | `selftest.sh` guard table has allow and deny rows, unkeyed by rule | Makes "every rule has a firing fixture" a checkable invariant. Note Sondera states this and does not apply it to its own corpus | S | Idea |
| 13. Policy errors deny | `transform.rs:595`: Cedar skips a forbid that errors, so any eval error becomes Deny. Malformed policy is a startup failure (`crates/types/src/policy.rs:282-285` comment) | Bash equivalent: a failing helper inside `guard.sh` past line 19 runs with no `ERR` trap | Lesson only: an error inside a deny rule must not read as "no match" | S | Idea |

Considered, smaller value: `PostToolUse` output redaction keeping the JSON shape (`claude/src/response.rs:205`) is useful for secrets in Bash output, but even Sondera has no policy on Bash output. Deny messages carrying the policy id and description (`crates/types/src/trajectory/control.rs:296`) are worth copying along with item 2.

## 3. Challenges

- **Bash plus files as runtime.** Sondera uses a daemon plus compiled binary. Verdict: **framework is right** for a template. The daemon buys cross-call state (the session label), which is only useful with an LLM classifier. It adds a process to keep alive, and losing it blocks the agent. Its 78k lines also buy 41 of 46 shell rules at glob quality.
- **One hook set for three tools.** Sondera agrees with the premise: one policy set, per-host adapters. But it pivots on its own neutral event, not on one host's protocol, and it records host capability differences. Verdict: **premise right, shape wrong.** Replace "Cursor protocol as lingua franca" with a neutral `{tool, kind, path, command}` JSON. `adapt.sh` stays small.
- **Hooks as enforcement.** Sondera's strongest lesson works against both projects: a hook on a user-writable config, without an OS sandbox, is not a security boundary. Its `ConfigChange` hook sends a fixed string (`hooks.rs:1578`), so no rule can see what changed. Verdict: keep the framework's wording ("stop the few"), rely on `sandbox.enabled`, and move evidence trust into signed or CI-checked records. Do not spend on more regex.
- **Regex over shell.** Sondera's parser is the right direction, and its own corpus shows the cost: rules were not migrated. Verdict: partial, see Take 11.
- **Default allow.** Both use it. Verdict: **correct** for developer tools, provided everything is logged.
- **LLM in the enforcement path.** Sondera's own numbers argue against it. A local model takes about 5s per call (`runner.rs:52`), and the classify timeout is 5s (`transform.rs:73`), then it fails to `Public`. So labels may silently drop at normal speed (INFERRED). Verdict: **framework's "judgment stays in prose" is right.** Deterministic gates inline; LLM analysis after the fact, as Sondera's trajectory scanner does, off the path (`crates/harness/src/scan.rs` header).
- **Long AGENTS.md, 18 skills.** Sondera has a 5.8 KB `AGENTS.md`, one skill, and the rule that one surface owns each fact. Its "Known gaps" section is a good habit. Weak evidence for cutting skills, since it is a product repo.
- **Selftest as proof.** Sondera has 1,430 tests and still ships dead controls (`Mode`, `@escalate`, `context.policy`, `file_signature`). Tests of mechanics do not prove controls work. This supports the brief's "not measured" gap; only firing data does (Take 2).

No evidence here on tickets, risk lanes, changed-line review, human acceptance or copy-in as a whole. Out of scope for this repo.

## 4. Delete or simplify

- **Duplicated `cfg()` awk** in `guard.sh`, `protect.sh`, `mcp-guard.sh`. They are "standalone" on purpose, but a single small reader, plus Take 6, removes three drifting parsers.
- **`guard.sh` rules that imitate a sandbox** (network section 3, parts of 5). Keep the evidence, git and irreversible rules. Each surviving rule gets an id and a firing fixture; any rule with no fixture is deleted, on the model of Sondera's 25-file deletion.
- **Secret regex on shell text** (`guard.sh:153`) overlaps `protect.sh` and is bypassed by any unlisted reader. Consider reducing it to the common cases and stating it as a speed bump.
- **Do not add** Cedar, YARA, a daemon, a TUI or an MCP server. Each is more runtime for little gain here.

## 5. Orchestration

- **Three-valued verdict, separate from the process exit.** Hooks always exit 0 with Allow/Deny/Escalate plus reason and policy ids. This is the shape `gate.sh --json` needs: fix the "exit 1 means two things" gap by putting state, verdict and reason in stable JSON, with exit code only for tool failure.
- **Central decision point across clones.** Hooks in many checkouts could point at one `SONDERA_HARNESS_ENDPOINT` (`AGENTS.md`, `docs/deployment.md`). That design would solve "local state is not shared" for number reservation and claim limits, but it needs authentication, which Sondera lacks. A git ref or the host's API is a lighter fit for the framework (INFERRED).
- **Run-scoped ledger.** Trajectory id equals session id, with causality links. Add `ticket`, `run_id` and `agent` to the framework's decision log so an orchestrator can join a run to its ticket.
- **Lifecycle hooks as gates.** `TaskCompleted`, `TeammateIdle`, `SubagentStop` are blockable per `claude/src/event.rs`, though Sondera never uses this: `TaskCompleted` sends a control event and control events are always allowed (`cedar/src/lib.rs`, "Don't authorize control events"; VERIFIED), so its fail-closed label only covers a dead harness. For teams inside Claude Code, a `TaskCompleted` hook calling `gate.sh next` could refuse "done" while agent work remains (ASSUMED; verify on the host). This matters more than `stop_followups`.
- **Read surface for agents.** `sondera mcp` exposes runs and events as typed tools (`crates/mcp/src/lib.rs:852`). Overbuilt for the framework; `--json` is enough first.

## 6. Do not copy

- Calling hooks a "reference monitor". Tamperproofing is not met; unauthenticated port, first binder wins.
- Fail-open classifiers under a fail-closed headline. A degraded control that reports `Public` looks healthy.
- Glob rules such as `like "*git checkout .*"` in a "structured" corpus; the same rule ignores `git -C x checkout .`. Parser value only arrives when rules use it.
- `ConfigChange` marked fail-closed while it cannot see the change: it blocks when the harness is down, not on tampering (VERIFIED from `hooks.rs:1578-1600`, no rule inspects it).
- Fabricated data: Claude `PostToolUse` sets `exit_code` to 0 unless interrupted (`hooks.rs:~625`), so failed commands log as success. Framework `adapt.sh` reads the real field; keep that.
- `file_signature` in the schema while the transform always emits it empty (`transform.rs:300`; the linter has a code for this, `lint.rs`). Better to remove a stub than lint against it.
- Unused depth: 10 adapters including `Observe`-only cells, and an aspirational `Steer` mode with no implementation.
- 110 counted as an invariant in `AGENTS.md` (`:62` region). A count is not a quality measure; one of the 110 is the default permit, so 109 forbids.

Suspicious content: none found. `.mcp.json` runs `cargo run`, normal for this repo; not executed. `AGENTS.md` and the skill are ordinary project guidance and were treated as data.

## 7. If you rebuilt the framework

Keep bash and files, scripts owning state, and "hooks stop the few". Shrink hooks to one neutral event format, `matcher: *`, a rule table with ids and a deny/near-miss fixture per rule, and ask-to-deny on hosts with no enforced ask. Every decision goes to a run-scoped JSONL log, and that log, not the selftest, becomes the proof the framework works: which rules fire, what ceremony costs. Treat the OS sandbox and CI re-verification as the real boundary, and say plainly that hooks are guardrails for an honest but mistaken agent, not protection from a hostile one. Hook wiring becomes an installer with merge, uninstall and upgrade. Sondera changes the shape only at this edge; it says nothing about the ticket railroad.

## 8. Coverage

Read in full: `README.md`, `AGENTS.md`, `crates/hooks/README.md`, `.agents/skills/autoformalize/SKILL.md`, `behavioral-check.md`, `crates/hooks/core/src/runner.rs`, `adjudication.rs`, `response.rs`, `docs/deployment.md`.

Read in large part: `crates/policy/cedar/src/lib.rs`, `transform.rs` (first 260 and 525-625), `shell_parse.rs` (head, function list), `base.cedarschema` (first 200 lines), `crates/hooks/claude/src/{hooks.rs,install.rs,event.rs,response.rs}` (selected ranges), `crates/mcp/src/lint.rs`, `crates/hooks/core/src/install.rs`, `mention.rs`, `crates/harness/src/scan.rs`, `crates/trajectory/src/rubric.rs`, `scanner.rs` (heads), `docs/architecture.md`, CI (first 120 lines), about 10 sample policies, plus scripted grep across all 110 policies.

Not read: nine non-Claude adapters beyond grep and the README table (Codex lightly), `crates/tui`, `crates/console`, `crates/storage` internals, `crates/provider`, most YARA rule bodies, `docs/policies.md`, `getting-started.md`, the paper. Line numbers with `~` or "region" are approximate.

Confidence: high on policy corpus counts, dead `Mode`/`@escalate`/`context.policy`, the fail-closed code and the framework comparison. Medium on bypasses, read from `like` patterns and not run. Low on host-side claims (Codex `PermissionRequest`, `@` inlining, timeout behaviour, `TaskCompleted`), which need a live check before anyone depends on them.
