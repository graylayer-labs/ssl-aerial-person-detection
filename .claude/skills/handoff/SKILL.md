---
name: handoff
description: End a session by writing the current state onto the GitHub issue so the next agent can continue. Use before stopping work, finished or not.
---

# Handoff

Write down what the next agent needs. Assume they have never seen this
conversation.

## Steps

1. Make sure the work is on a branch and committed in logical units. Do not
   commit broken code to make the tree clean; say in the handoff what is
   uncommitted and why.
2. Run `uv run pytest` and `uv run ruff check .` and note the result.
3. Draft a comment for the issue using the template below.
4. Show the owner the comment, then post it with `gh issue comment <number>`
   once they agree.
5. Update the issue's status on the board if it changed.
6. If the session surfaced follow-up work, list it as proposed issues for the
   owner. Do not create them without asking.

## Comment template

```markdown
## Handoff <date>

**State:** done | in progress | blocked

**Branch:** `<branch>` (pushed: yes/no)

**Done so far**
- ...

**Results**
- Numbers, with the config and command that produced them.

**Decisions and why**
- ...

**Tried and did not work**
- What, and the most likely reason.

**Next step**
- The single next action, specific enough to start on.

**Open questions for the owner**
- ...
```

## Rules

- Write whole sentences. Do not use shorthand or labels coined during the
  session.
- Include failures. A dead end that is not written down gets repeated.
