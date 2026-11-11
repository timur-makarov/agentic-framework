# Environments

Environments belong to the project. Rail touches each at one named point.

| Environment | What Rail does |
|---|---|
| Local | `setup` runs in each ticket's worktree with `RAIL_TICKET` set, so parallel tickets can name their own databases and ports. `verify` and the checks run at ship |
| Dev | Nothing at runtime: a ticket ends at its merge, and the project's CD deploys the base branch |
| Prod | Nothing. Releasing is a person's act, through the project's CD gate |

- The machine the agent runs on holds local and dev secrets only.
- Risky paths are HIGH, so a person sees them before they reach dev.
- People keep four acts: merging HIGH, deleting data, handling credentials, and releasing to prod.
