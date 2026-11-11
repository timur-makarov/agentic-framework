# Away from the desk

Rail never waits: a wait is a state on a ticket, and the agent takes other work meanwhile. To keep work
moving while you are away, use what Claude Code ships.

**The loop prompt:** for each ticket `rail next` lists as resumable, run `rail next --ticket NN`, which
finishes what an ended session left; then run `rail next` until it returns `rest` or only waits on a
person. Write it into `.claude/loop.md` to get it from a bare `/loop`. The resume step is for setups where
one runner works at a time.

- **`/loop`** reruns the prompt in one session, on an interval you give or one Claude picks. The machine
  must stay on.
- **A desktop scheduled task** survives restarts and starts a fresh session in the same clone each run.
- **A cloud scheduled task** runs with your machine off. Each run is a fresh clone; IDs and claims are
  taken on the remote, so two runs never take the same ticket, and a run resumes from the pushed branch.
- **`/goal`** works a backlog until it is empty.
- **Remote Control** lets you answer from another device.

Run unattended sessions with `--permission-mode auto`. `ask` rules still prompt there, so `sudo` or
`git reset --hard` pauses the loop until someone answers.
