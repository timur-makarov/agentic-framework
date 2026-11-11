# Changelog

One line for each change, saying why.

- Add `research/`: the plan, the spec and the reasoning behind them, so each build session reads them from the repo it clones.
- Record the Phase 0 results in section 25 of the plan, so later phases build on what was checked in a cloud session.
- Make the ticket ID ref the branch `rail/id/NN` instead of the tag `rail/NN`, because the cloud proxy refuses tag pushes (Phase 0 check 1).
- Record Phase 0 check 2: the async merge endpoint merged the results PR from the cloud session.
- Add the Phase 1 engine in Python 3.11 with the standard library only: the first-match table, the verbs add, accept, next, advance, status, context and drop, state derived from git and the journal, claims with their own worktrees, and the local squash merge, so a ticket can run from add to merge on the new core.
- Add bin/rail, the launcher that runs the engine next to it and stops with one line on Python older than 3.11.
- Add the end-to-end railroad tests on fixture projects (tests/), so every Phase 1 rule is checked through the real launcher: run with python3 -m unittest discover -s tests.
- Leave branches named like tickets but holding no ticket file alone and list them in status, because the plan says such branches stay for the person.
- Make next --ticket NN run a failed setup again, read open ASSUMED rows from the worktree's copy of the ticket, and skip tickets next can't act on before deriving them again, so the briefs match what the agent sees and next stays fast.
- Show leftovers in the text output of next, advance and drop, so a person reading the terminal sees what was left for them.
- Split the framework into engine/ (copied into a project by rail init) and seed/ (copied once), so a project owns its engine and its starting files.
- Add install, which links rail into ~/.local/bin, and make bin/rail hand over to the project's own .rail/bin/rail, so a project's changes to its engine take effect.
- Add rail init: it copies the engine and seed, writes .rail/bin/rail and .rail/SOURCE, appends the ## Rail section to AGENTS.md, imports it from an existing CLAUDE.md, merges .claude/settings.json, adds the rail workflow and .gitignore lines, and never overwrites a project's file.
- Make the first rail next return the init task until the project's config is on its base branch, so the agent proposes setup, verify, areas, risk paths, rules and .worktreeinclude for the person to confirm.
- Add rail doctor, the SessionStart hook (PATH through CLAUDE_ENV_FILE and a snapshot of this session's ticket), and rail ci with the rail workflow, so CI repeats the ship checks and fails with "not shipped yet" before ship.
