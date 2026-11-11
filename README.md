# Rail

Rail keeps coding agents on a railroad: it says what is legal next, what counts as done, and when a person
must act. The agent writes the code; the engine owns ticket state. It is built for git, GitHub and Claude
Code, on macOS and Linux, with Python 3.11 or newer.

## Install

```bash
git clone https://github.com/timur-makarov/throw-away-repo ~/rail && ~/rail/install
```

`install` links `rail` into `~/.local/bin` and tells you if that folder isn't on your `PATH`. There is no
package.

## Set up a project

```bash
cd /path/to/project && rail init
```

`rail init` copies the engine into `.rail/`, adds a `## Rail` section to `AGENTS.md`, merges hooks and guard
rules into `.claude/settings.json`, and adds the `rail` workflow. It never overwrites a file of yours. Then
open Claude Code in the project and ask it to run `rail next`: the first answer is the init task, which
proposes the project's checks, its map and its risk paths for you to confirm. Commit the result.

## Use it

Write a ticket like `.rail/tickets/TEMPLATE.md` and run `rail add <file>`, or label a GitHub issue `rail`
and run `rail intake github`. Then tell Claude Code to work through the backlog: it runs `rail next`, does
what the brief says, and runs `rail advance`, until a ticket needs you.

Everything else is in the docs that ship with the engine: `rail docs`, then `rail docs loop`.

## This repository

`engine/` is copied into each project by `rail init`; `seed/` holds the files it copies once; `packs/` holds
optional features; `tests/` holds the end-to-end tests (`python3 -m unittest discover -s tests`).
`research/PLAN.md` is the plan, and `CHANGELOG.md` says why each change was made.
