---
name: pickup
description: Start a session by recovering project state from the GitHub board and issues. Use at the beginning of every session, or whenever you are unsure what is in progress.
---

# Pickup

Recover the project's state from the board. Do not rely on memory of earlier
conversations.

## Steps

1. Read `INTENT.md`.
2. Check the local state:
   ```bash
   git status -sb
   git branch --no-merged main
   ```
   Uncommitted changes or unmerged branches usually mean a previous session
   stopped mid-task.
3. Read the board:
   ```bash
   gh project list --owner graylayer-labs
   gh project item-list <number> --owner graylayer-labs --format json
   gh pr list --state open
   ```
4. For each item that is **In progress**, read the issue and its comments with
   `gh issue view <number> --comments`. The last handoff comment says where
   the work stopped.
5. Report to the owner, briefly:
   - What is in progress and where it stopped.
   - What is ready to start next, in board order.
   - Anything that looks wrong, such as a branch with no issue or an issue in
     progress with no branch.
6. Recommend one issue to work on and say which model tier it suggests. Wait
   for the owner to confirm before starting.

## Rules

- Finish or hand off in-progress work before starting something new.
- If the board and the repo disagree, say so. Do not pick one silently.
