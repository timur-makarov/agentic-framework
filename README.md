# Rail

Rail keeps coding agents on a railroad: it says what is legal next, what counts as done, and when a person
must act. The agent writes the code; the engine owns ticket state. It is built for git, GitHub and Claude
Code, first of all for Claude Code cloud sessions, and for macOS and Linux, with Python 3.11 or newer.

## Start in a Claude Code cloud session

A cloud session is Rail's standard place to work. Open one on your repository and say:

> Set this repository up for Rail, from https://github.com/timur-makarov/agentic-framework

Claude clones the framework, runs `rail init`, writes the project's checks, map and risk paths, installs what
the checks need, and opens one pull request. Then three things are yours:

1. Merge the pull request.
2. Make three settings on GitHub, which a cloud session can't change: import `.rail/ruleset.json` as a
   ruleset, allow squash merging only, and delete merged branches. `rail doctor` links each page.
3. Approve the environment's setup script when Claude proposes it, so later sessions start ready.

After that, hand work over: say what you want in a session, or label a GitHub issue `rail`. Claude runs
`rail next`, does what the brief says, and runs `rail advance`, until a ticket needs you. Tickets that need
you carry the label `rail:needs-you`, and you answer with the label `rail:go`. `rail docs cloud` covers
running with no session open.

## Start on your own machine

```bash
git clone https://github.com/timur-makarov/agentic-framework ~/rail && ~/rail/install
```

```bash
cd /path/to/project && rail init
```

`install` links `rail` into `~/.local/bin`; there is no package. `rail init` copies the engine into `.rail/`,
adds a `## Rail` section to `AGENTS.md`, merges hooks and guard rules into `.claude/settings.json`, and adds
the `rail` workflow. It never overwrites a file of yours. Then open Claude Code in the project and ask it to
run `rail next`: the first answer is the init task, which proposes the project's checks, its map and its
risk paths for you to confirm. On your own machine Rail installs nothing: you install the tools the checks
need, and the guard asks before `sudo` and other commands that could hurt your machine.

## Use it

Write a ticket like `.rail/tickets/TEMPLATE.md` and run `rail add <file>`, or label a GitHub issue `rail`.
Then tell Claude Code to work through the backlog.

Everything else is in the docs that ship with the engine, readable before `rail init` too: `rail docs`,
then `rail docs cloud` and `rail docs loop`.

## This repository

`engine/` is copied into each project by `rail init`; `seed/` holds the files it copies once; `packs/` holds
optional features; `tests/` holds the end-to-end tests (`python3 -m unittest discover -s tests`).
`CHANGELOG.md` says why each change was made.
