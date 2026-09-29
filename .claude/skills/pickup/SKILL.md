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
3. Read the board. If a `gh project` command fails with `unknown owner type`,
   run it again.
   ```bash
   gh project item-list 1 --owner graylayer-labs --format json --limit 100
   gh pr list --state open
   ```
4. Read the current epic: the issue labelled `epic` that is In Progress. Its
   "Decisions so far" list is the short history of the milestone, and its
   "Order of work" section says what comes next. The epic itself is not a
   task.
5. For each item that is **In progress**, read the issue and its comments with
   `gh issue view <number> --comments`. The last handoff comment says where
   the work stopped.
6. Report to the owner, briefly:
   - What is in progress and where it stopped. If no task is in progress, say
     so.
   - What is ready to start next, following the epic's order of work.
   - Anything that looks wrong, such as a branch with no issue or an issue in
     progress with no branch.
7. Pick the next issue and say which one and why. Start on it unless it is
   labelled `needs-owner` or falls under "Ask the owner first" in
   `CLAUDE.md`. Its `agent:` label names the model; the tiering table in
   `CLAUDE.md` says which agent to run.
8. Check that the task's data is reachable before starting. See "Data" in
   `CLAUDE.md`.

## Rules

- Trust the issue comments and `git log` over anything you recall, including
  a summary of an earlier part of this conversation. Do not redo work whose
  commits already exist.
- Finish or hand off in-progress work before starting something new.
- If the board and the repo disagree, say so. Do not pick one silently.
