# coleam00_Archon

Paths are repo-relative. `sdlc/` means `.archon/workflows/sdlc/`. `fw:` means the framework. Labels: VERIFIED (read in code, or a git/grep check), INFERRED, ASSUMED. License: MIT (`LICENSE`), VERIFIED. `other-solutions/MANIFEST.tsv` has no row for this repo, so everything may be copied with attribution. Most of it is TypeScript on Bun, so in practice items are ideas to rewrite in the framework's own stack.

## 1. What it really is

A self-hosted workflow engine, not a project template. YAML DAGs of agent, bash, script, loop, wait and child-workflow nodes run Claude Code, Codex or Pi in git worktrees, with durable pauses, an attention queue, cost accounting, SQLite/Postgres or file storage, CLI, web console, chat adapters and a plugin system. On top sits `sdlc`, a large pack (35 markdown files, about 3,900 lines of YAML, about 11,700 lines of TS) running issue to merged PR.

Size is the opposite of "small core": about 280k non-test TS lines, 869 test files, `packages/workflows` alone about 88k (VERIFIED by count; includes some test helpers). Very active and very one-handed: 4,257 commits, 930 in October 2026, and of 646 commits between 1 and 19 October, 631 are authored by one person (VERIFIED, `git log`).

README claims: the engine, plugin kinds, worktree default and typed pauses match the code. "Of 524 PRs merged 1-19 October, 363 were built by Archon" cannot be checked from the repo: history shows 632 PR-numbered commits in that window and nothing separating Archon-built ones. "Governance": the state store says of a write that it does not record "who acted or whether a person or an agent did" (`packages/workflows/src/state-document-store.ts:44`). I did not run it.

## 2. Take

| Item | Mechanism and `path:line` | Framework part it changes | Why better | Effort | Copy |
|---|---|---|---|---|---|
| 1. Verdict comes from the runner, not from a file | Reviewer returns `output_format` JSON through the provider stream. A script, not the reviewer, stamps head and verdict: `sdlc/review/scripts/publish-review.ts:1-20`, `sdlc/.shared/review-comment.ts:17`. The round's commit is fixed before review from engine-observed HEAD: `sdlc/review/scripts/review-round.ts:1-16`. Synthesis requires a typed artifact per lens from an engine-written listing: `review-synthesize.md:18` | `report_sha_ok` passing with no record (fw `gate.sh:235-241`); Mode A | The author has no write path to the verdict record. Framework version: make Mode B the only mode, gate runs the reviewer, gate writes report and sha, and a missing sha fails | M | Idea |
| 2. Findings as JSON; scope is "touches the change" | "Natural language is not a wire format" (`AGENTS.md`). A defect on the changed path, made reachable by it, or a claim it falsifies is a finding even off the diff; an unrelated proved defect is a discovery (`review-synthesize.md:32-33`). Stable IDs carry across rounds, and every decline is judged by the next round (`review-synthesize.md`, Continuation) | `bound_findings` regex (fw `lib.sh:479-497`); free declines | Malformed lines cannot vanish, because a schema rejects them. Unchanged-caller defects survive. A decline needs evidence someone else checks | M | Idea |
| 3. Policy is read from the merge-base | `scripts/check-ratchet.ts:12-16`: both sides come from git, nothing committed as baseline, and scope is read from `merge-base:biome.jsonc` (`:423`), "so a change cannot exclude its own file". Waivers are commit trailers living only in that change (`:37-41`, `:288`) | Mutable `risk_tier`/`Check:`; stamp-based test ratchet; `floor_exceptions` and dead `exception_max_days` | Works in CI and fresh worktrees. In CI, read tier, checks, `config.yml` and `floor_ignore` from the claim commit or merge-base. Expiry problem disappears | S-M | Idea |
| 4. Stable machine output and honest exit codes | `workflow wait`: "Exit codes describe the command, not the run": 0 reported, 3 timeout, 1 the wait failed (`packages/docs-web/.../reference/cli.md:872` section). `state put` uses exit 3 for conflict (`sdlc/.shared/state.ts:11`). Stdout is only JSON; warnings go to stderr. Docs admit one gap: `run --json` without `--detach` is not parseable | fw `next_exit` (`gate.sh:532`), text output | Fixes "exit 1 means work or failure" directly. `$WHO` already exists internally (`gate.sh:318`), so `--json` is cheap | S | Idea |
| 5. Typed attention item | `what, why, recommendation{choice, why, evidence, confidence, would_change}, choices[], if_unanswered, links` (`sdlc/merge-queue/archon-merge-queue.yaml:102-125`). `--occurrence` refuses an answer aimed at a pause the run has left (`cli.md` `workflow wait`) | `blocked-on-answers`, Open questions, `/agentic-grill` | A human or orchestrator can answer without reading the transcript. `would_change` and `if_unanswered` are the valuable fields | S | Copy schema |
| 6. The run cannot change its own rules | Source is captured once and is the sole executable source; failure to capture fails the run: `packages/workflows/src/workflow-source.ts:1-30`. `packages/workflows/src/run-source.ts` | `gate.sh`, hooks and config live in the tree agents edit | Separates "the rules" from "the target". Framework version: CI runs gates and hooks from the base-branch copy; an installed framework lives outside the project tree | M | Idea |
| 7. Outcome measurement | Planted-defect bench on sealed, history-less clones with a separate judge run: `sdlc/review-eval/scripts/bench.ts:1-28`, `.archon/sdlc/eval/review/set.json` (5 cases, up to 5 variants). `scripts/lens-yield.ts` tallies sole findings per lens, "the measure that retired the comments lens". `sdlc.pr_merge_rate`, `sdlc.tests_unprotective`, with cohort comparison and intervals (`packages/workflows/src/metrics.ts`, `metrics-stats.ts`) | "Not measured" gap; selftest as main proof | First real path to "does the critic catch anything?". Start with review only and a committed case set. Warning: their intake bench took five PRs, never scored a batch and was deleted (`964fd2834`) | M-L | Idea |
| 8. A guard must earn its place | `sdlc/README.md` Guards: a guard "names the real run it would have saved, or it stands in front of an irreversible action. Otherwise it is a comment." History applies it: `13e29c8d0` removed 31 lines and 17 fixture stubs; `c7b358fe8` deleted a guard whose record was only false refusals | Every lint, gate row and hook | A deletion test the framework lacks | S | Idea |
| 9. Discoveries channel | Out-of-scope defects are recorded by producers, then verified, deduped and filed, tracked or dropped with a reason: `sdlc/discoveries/archon-discoveries.yaml:1-18` | Dropped findings | Nothing proved is lost, and scope stays tight. Framework version: append to `.agentic/journal/discoveries.jsonl`, `gate.sh` proposes tickets | S | Idea |
| 10. Pack distribution with receipts, eject and layered policy | `archon plugin add owner/repo[/path]@tag` freezes one commit under `ARCHON_HOME`, atomic receipt, `plugin copy` to eject (`cli.md`, `plugin`). Project policy overlays pack default: default read first, project line wins (`sdlc/CONSTITUTION.md` §12) | Copy-in; template history leaks; `scripts/` collision | Clean split of framework and project files. An upgrade is a re-pin. Project keeps only overrides | L | Idea |
| 11. Read-only is checked, not asked | `mutates_checkout: false` snapshots git status and content hashes around the node and fails it on change: `packages/workflows/src/dag/checkout-guard.ts:101-165` | Reviewer Mode A | Cheap, and works on tools with no tool restrictions | S | Copy logic |
| 12. Capability declaration with preflight | One `capabilities.ts` per provider; run fails before spend when a node needs what the provider lacks: `packages/provider-contract/src/capabilities.ts:1-8`, `packages/workflows/src/dag/capability-preflight.ts`; generated docs matrix | `env-lint`, the README tool table | States per tool which guards really hold (Codex `ask`, matcher holes) instead of implying parity | S-M | Idea |
| 13. One declarative fixture per outcome | `<name>.stubs.yaml` beside the workflow, with `expect`, `reached`, stubs: `packages/workflows/src/fixture-runner.ts:1-25`. Rule: one per outcome, no route or prose pins (`sdlc/CONSTITUTION.md` §5, §13) | `selftest.sh` (710 lines) | Table-driven checks for `compute_next`, shorter and easier to change | M | Idea |
| 14. Six-part brief | Problem, why, why now, outcome, invariants, acceptance; "Do not launch a run against an input missing any of the six" (`AGENTS.md`) | Ticket template, `ticket-lint` | Adds why-now and invariants, which the Done Contract lacks. Keep `Check:` commands too | S | Idea |

## 3. Challenges

- **"Scripts own everything; judgment stays in prose."** Archon says the reverse for its pack: "Agents first", determinism "after a failure, not before", and one agent judges CI (`sdlc/CONSTITUTION.md` §1, §2, §6). Partly right. Archon is right that a script over review or CI is a frozen guess. It can afford that because an engine owns ordering and the agent cannot skip a node. The framework has no engine, and `gate.sh` is what plays that role, so its state machine stays. Its report-format parsing and any guard with no named failure go.
- **Bash plus files as the runtime.** A durable engine took 88k lines. Do not chase that. Bash is fine for `compute_next`; awk YAML and regex over reports are the weak points. For durability, retries, cost and fan-out, plug into an engine. Who is right depends on scope, and the framework should stay a governor rather than become a runtime.
- **Ticket front matter as state.** Archon keeps run state and claims in a store written through a CLI with `--if-revision` (`sdlc/.shared/state.ts:1-7`), and work-item stages in forge labels. Archon is right on the key point: acceptance and status must not sit in a file the agent can write. Keep tickets as the contract; move acceptance to a place the agent cannot forge alone.
- **Three lanes.** Archon has no tiers. A small model picks lenses per diff (`sdlc/review/archon-review-block.yaml`, `route`), and merge rules are prose (`.archon/sdlc/policy/merge.md`). Neither side wins. An agent route has no hard floor, and `risk_paths` is better there. But an author-chosen tier is also weak. Compute the minimum tier from the diff and let humans only raise it.
- **Review limited to changed lines.** Archon is right (item 2). The framework's rule silently drops real defects. Keep delta-only review for later rounds only.
- **A human accepts every ticket.** Archon is right for unattended use: triage against a policy document, and a person is asked only when unclear (`sdlc/CONSTITUTION.md` §10-12, `.archon/sdlc/policy/merge.md`). Add policy-based acceptance as an option, keeping the human default for HIGH and for issues from untrusted authors. Note Archon does not prove a human answered either: "The answer ... does not have to come from a person" (`cli.md`, `workflow wait`), and I found no check stopping an agent running `workflow approve` (grep negative, INFERRED).
- **Copy-in.** Archon is right (item 10).
- **18 skills and ambient guidance.** Archon gives workflow nodes no ambient skills; a node gets what it names (`AGENTS.md`; `packages/providers/src/claude/node-config.ts:180`), and each step is a command file. Right for orchestrated runs, while standalone use still needs some router. Keep lifecycle skills, make craft skills optional, and write them so a node can use them as a command.
- **Long AGENTS.md.** Framework wins: 88 lines against 18.5 KB. Take only the pointer list ("Find current facts").
- **One hook set for three tools.** Archon has none: Claude runs `bypassPermissions` (`packages/providers/src/claude/provider.ts:336-337`) and Codex `danger-full-access` with `approvalPolicy: 'never'` (`packages/providers/src/codex/provider.ts:743-744`). Its own text says a worktree "is not an execution or security sandbox". The framework is right that tool-time guards have value, and Archon is right not to call them a boundary. Regex hooks are seatbelts; a real boundary is a sandbox or container.
- **Selftest as main proof.** Archon is right: tests prove mechanics, a bench proves value (item 7).

## 4. Delete or simplify

- `report_sha_ok`'s missing-record pass, `**Head:**` parsing, `bound_findings`, and Mode A, once the gate runs the reviewer and takes JSON.
- The stamp-based test ratchet. Replace with a merge-base computation or drop it. `extract_test_count` (fw `lib.sh:375`) is a text scrape of test output.
- Dead config: `tracker`, `exception_max_days`, unapplied `models.*`. Archon's rule fits: no configuration "without a current requirement or concrete failure mode".
- `floor_exceptions` in config, replaced by per-change commit trailers (item 3).
- `stop.sh` while `stop_followups: 0` is the default: enable it or remove it.
- Structural selftest checks. Apply item 8 to every gate row and lint; I did not audit which fail it.
- Optional craft skills move out of the default tree, along with template history (ADRs, framework `CONTEXT.md`) if the framework becomes an installed pack.

## 5. Orchestration

**Standalone lessons.** Archon separates lifecycle status from work outcome: `delivered:false` is a valid completion (`sdlc/ship/archon-ship-block.yaml:50-54`). A failure the pack has no answer for pauses with a class label, and a recurring class gets a handler (`sdlc/CONSTITUTION.md` §11). It refuses to guess lifecycle ownership: ambiguity surfaces, it never marks a run failed (`AGENTS.md`; `owner_lost` in `workflow wait`). All three transfer. `gate.sh` should say "failed step" and "work owed" separately, and should report unknown rather than guess.

**Plug-in verdict: realistic, as a workflow pack, on the Claude provider. Not as a provider or forge plugin.** A provider is an agent runtime speaking ACP plus `_archon/*` (`packages/provider-contract/README.md`), and a forge is a code host; the framework is neither. A pack is the right seam: a manifest with `kind: workflow-pack` and `entrypoints`, layout `<pack>/<workflow>/<file>.yaml` (`packages/docs-web/src/content/docs/guides/publishing-plugins.md:8-23`). `bash:` nodes need no Bun code from us. Effort estimate: a few gate tickets plus about 100 lines of YAML (INFERRED). Keep the pack in a separate repo or `integrations/archon/`, never in the template tree. Private repos cannot use `plugin add`, since the manifest is read unauthenticated (`cli.md`, `plugin`); they commit the pack to `.archon/workflows/` or use `plugin copy`.

**What the framework must expose:**

1. `gate.sh next NN --json` and `gate.sh advance NN --json`: versioned schema `{schema, nn, tier, status, branch, head, who: gate|agent|human|rest, kind, message, why, then, skill}`, JSON only on stdout. Archon certifies this with `output_format` and branches with `when:` (`packages/workflows/src/dag/nodes/exec/bash.ts:147-152`).
2. **Exit codes.** `advance` must exit 0 when the agent or a human is owed work. Non-zero stays for a failed step or gate bug, with a `reason` class. Today `next_exit` returns 1 for agent work (fw `gate.sh:532`), which Archon records as a failed node (`bash.ts:111-155`, subprocess rejection; INFERRED from the catch path).
3. `gate.sh accept NN --by <id> --evidence <ref>`, so a `wait: attention` approval can open a `blocked-on-answers` ticket, and an answer verb for open questions. Today this is a hand edit of `status`, which is also the verified forgery gap.
4. `gate.sh submit-review NN --kind critic|security --head <sha> --reviewer <run/node id> --json <file>`, taking schema-valid findings and writing report plus sha. The review is an agent node with `context: fresh`, `mutates_checkout: false` and `output_format`. Critic Mode B needs no change for a headless path, but then the pack gives up typed outputs and attention.
5. Lane fields in JSON: `kind` naming the step (edit, fix-finding, lessons, review, human-merge), so the agent node's prompt is chosen by data, not by parsing `NEXT`.
6. Idempotent steps after crash or re-run. `advance` looks close (`gate.sh:1198-1226`), but retry and `--resume` of a half-done step must be tested. Resume re-enters only incomplete nodes (ASSUMED from `dag-resume-snapshot.ts`, not read in depth).
7. `guard.headless: deny|allow`: what `ask` becomes with no human. Under `bypassPermissions`, what a PreToolUse `ask` does is unknown (ASSUMED risky). Unattended must mean deny.
8. Write roots. `protect.sh:105-111` denies file-tool writes outside the repo and temp dirs. Archon's `$ARTIFACTS_DIR` sits under `~/.archon/workspaces/...` (`packages/paths/src/archon-paths.ts:12`, `run-paths.ts`), so any SDLC pack command writing there via Write is blocked (INFERRED). Add `guard.extra_write_roots`, or have our pack avoid artifacts for agents.
9. `gate.sh doctor --json`, reporting which guards are live for the current tool. Needed because of the Codex posture below.
10. Limits and branch: document `--branch ticket/NN-slug` as the launch form. `step_implement` then sees it is on the ticket branch and skips checkout (fw `gate.sh:865-880`, INFERRED). Raise `limits.max_active_tickets`: Archon worktrees share one git dir, so `refs/agentic/nn` and claim checks do see each other (INFERRED), and default 1 would block parallel runs. This fixes "local state is not shared" only for worktrees on one clone. Separate clones still need pushed refs.
11. Skills as commands. Workflow nodes get `options.skills = nodeConfig.skills ?? []`, so `/agentic-*` are invisible unless named (`node-config.ts:180`), and Codex declares `skills: false` (`packages/providers/src/codex/capabilities.ts:12`). The pack must carry command files; skill bodies should work when inlined.

**What already works without changes (INFERRED).** Claude `settingSources` defaults to project and user (`packages/paths/src/skills.ts:139`), and the config comment says that includes hooks (`packages/providers/src/claude/config.ts:14-20`). So `.claude/settings.json` hooks should fire inside Archon. `AGENTS.md` is loaded natively. Hook denial under `bypassPermissions` was not tested.

**Codex inside Archon is not guarded.** Thread params force `danger-full-access` and `approvalPolicy: never`, overriding `.codex/config.toml` and `.codex/rules` prompts in effect (VERIFIED for params, INFERRED for effect). Capability `hooks: false` and `toolRestrictions: false` (VERIFIED). Whether app-server loads project `.codex/hooks.json` is unknown. Since adapt.sh maps `ask` to allow and leans on that Codex layer (fw `adapt.sh:10-13`), treat Codex-in-Archon as CI-gated only.

Pack sketch (untested):

```yaml
nodes:
  - id: rounds
    loop_group:
      max_iterations: 12
      fresh_context: true
      until_bash: 'who=$gate.output.who; test "$who" = rest'
      nodes:
        - id: gate
          bash: scripts/gate.sh advance $INPUTS.nn --json
          output_format: { type: object, properties: { who: {type: string}, kind: {type: string}, message: {type: string} }, required: [who, kind, message] }
        - { id: work, command: agentic-step, depends_on: [gate], when: "$gate.output.who == 'agent'" }
        - id: human
          depends_on: [gate]
          when: "$gate.output.who == 'human'"
          wait: { attention: "$gate.output.message", form: approval }
```

**Is it worth it?** Archon's SDLC pack already does plan, review, CI and merge, so the framework's value there is what Archon lacks: frozen scope, a tool-time deny list, floor-guard, a runnable Done Contract and path risk floors. A "guards only" mode, with hooks, floor-guard and lint under Archon's own workflows and `scope.strict: false`, may be the cheapest useful integration, needing only items 7-9 (INFERRED). Also, Archon says bundled workflows are "not a frozen compatibility surface", and the provider plugin protocol is already at version 3. Couple to the CLI and YAML language only. Build items 1-4 as a generic machine surface, with Archon as first consumer, not an Archon-specific feature.

## 6. Do not copy

- **Forgeable trust root.** The merge gate trusts a marked comment by a listed login (`sdlc/.shared/merge.ts:352-360`; `.archon/sdlc/policy/maintainers.json` has one). Agents run `gh` with credentials routed from the run's user (`packages/workflows/src/run-credential-env.ts:162`) and October commits land under that person's name. So an implementer could likely write or edit that comment (INFERRED, not exercised). It is better than the framework's Mode A but it is not proof. Use a separate identity, such as a CI-only key or a check run posted by an App.
- **Full-permission defaults** (above). Fine for an engine that disclaims isolation, wrong for a governance framework.
- **Engine scale and language surface.** `loop_group`, `compose-fan-out`, `include` plus `fan_out`, and a deprecated `approval:`/`on_reject` still carried. The constitution exists because this surface grows, and even so the code carries long historic comments (`schemas/exec-node.ts:5-37`).
- **Agent-judged merge policy in prose** as the only control for risky paths. No hard floor.
- **Eval modes threaded through production workflows.** Built and deleted (`964fd2834`). Keep eval outside the shipped path, as `review-eval` does.
- **Racing joins and fail-fast sibling cancel.** Adopted then rejected, as the case-law table records (`.archon/workflow-language-constitution.md`).
- **Telemetry on by default**, `curl | bash` install, and 276 KB changelog. Pack update from a default branch head is unsigned; binaries are checksummed (`packages/cli/src/commands/plugin-binary.ts:3`) but only against the same release.
- **Very long prompts.** `review-synthesize.md` and the deliver work text are heavy with history-specific rules.
- **Suspicious content:** none found aimed at a reader agent. `AGENTS.md` holds ordinary project instructions, such as "Do not add AI attribution"; all of it was treated as data.

## 7. If you rebuilt the framework

Keep the core idea: one read-only `next`, a decision table, frozen scope, risk floors from paths, floor-guard and runnable checks. Change the shape into a small installed governor plus a thin project overlay: rules live outside the project tree and CI reads them from the merge-base, so no change can edit its own gate. Every verb is JSON with honest exit codes, and reviewers return schema-valid findings to a gate that writes the record. Acceptance is a verb backed by policy or a named identity. Durability, retries, fan-out, cost and UI are not built; they come from a host such as Archon through a pack, and the framework runs alone with `gate.sh` as a plain CLI host. Add a planted-defect bench before adding more gates, and delete any guard that cannot name its run.

## 8. Coverage

Read: `README.md`, `AGENTS.md`, `.archon/architecture.md`, `.archon/direction.md` (first half), workflow-language constitution (rule, tests, most of case law), `sdlc/CONSTITUTION.md`, `sdlc/README.md` (first third and Metrics), provider contract README, `capabilities.ts`, parts of `node-config.ts`, `claude/provider.ts`, `codex/provider.ts` and `turn-params.ts`; `check-ratchet.ts` header, `lens-yield.ts`, `fixture-runner.ts` header, `checkout-guard.ts`, `workflow-source.ts` header, `bash.ts`; schemas for exec, wait, gate, retry, hooks; `archon-ship-block`, most of `archon-deliver-block` and `archon-review-block`, first half of `archon-merge-queue`, `gate.ts`, `merge.ts` gate section, `review-comment.ts`, `review-round.ts`, `publish-review.ts` (start), `state.ts`, `bench.ts` header, `review-synthesize.md` (first half); CLI docs for setup, plugin, run and wait; git log and selected commit bodies. For the framework: `README.md`, `config.yml`, parts of `gate.sh`, `lib.sh`, `protect.sh`, `adapt.sh`.

Not read: `packages/server`, `web`, `adapters`, `core` orchestrator, `isolation` internals, `container-gate`, DB layer, chat, most of `dag/run-layers.ts` and the resume code, most prompt files, build-queue and triage in depth, `.github/workflows`, telemetry code. Nothing was run. Inside-Archon behaviours marked INFERRED, especially hook firing and `ask` handling under `bypassPermissions`, need one live test before committing to the plan.

Confidence: high on mechanisms cited with lines; medium on the integration list until tested; low on quality of outcomes, since the repo has claims but no published bench results that I found.
