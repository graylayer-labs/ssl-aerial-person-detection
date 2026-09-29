---
name: tidy
description: Audit the repository for drift and clutter, then apply the safe clean-ups on a branch. Use at the end of a milestone, or when docs, code, and board have drifted apart.
---

# Tidy

## Steps

1. Delegate the audit to the `repo-janitor` agent. It is read-only and returns
   a report grouped by check.
2. Sort its findings into three groups:
   - **Safe:** lint fixes, broken links, stale paths in docs, unused imports,
     merged local branches.
   - **Needs a decision:** deleting docs or code, changing a quoted number,
     removing a dependency.
   - **Needs owner:** deleting data, anything on the remote, anything
     irreversible.
3. Show the owner the three groups. Apply the safe group without waiting. Ask
   about the other two.
4. Make the changes on a branch named `chore/tidy-<date>`, one logical change
   per commit.
5. Run `uv run pytest` and `uv run ruff check .`.
6. Ask the `reviewer` agent to check the branch if it touches anything under
   `src/`.
7. Summarise what changed and what was left, and offer to open a draft PR.

## Rules

- Tidy does not add features or change behaviour.
- A number in a doc that cannot be traced to a run is removed, not corrected
  by guesswork.
- Delete superseded files. Do not move them to an archive folder.
