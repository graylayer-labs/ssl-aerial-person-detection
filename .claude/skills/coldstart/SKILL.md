---
name: coldstart
description: Test whether a new agent with no context can orient itself from the repository alone. Use after any change to CLAUDE.md, INTENT.md, an agent, or a skill.
---

# Cold-start test

The author of instructions cannot see what they left out. This test starts an
agent that knows nothing and asks it what confused it.

## Steps

1. Make sure the change under test is merged to `main`. The test agent starts
   from `origin/main`.
2. Start a `general-purpose` agent on Sonnet, in its own worktree, with the
   prompt below. Add nothing about the project to the prompt.
3. Fix what it reports. Group the fixes in one PR.
4. Run the test again if any finding was a contradiction or a broken command.

## Prompt

```text
You have just been started in this git repository. You know nothing about it
and have no earlier conversation to draw on. This is a test of whether the
repository explains itself, so your honest confusion is the useful output.

A normal session would have CLAUDE.md at the repository root loaded
automatically, with anything it imports. Read CLAUDE.md and its imports, then
do what they tell a new session to do. If they name a skill, read its file
under .claude/skills/ and carry out its steps by hand.

Rules: read only. Do not edit, create, or delete files. Do not commit, push,
or branch. Do not create, edit, comment on, or close any issue or pull
request. Do not change the board. Do not start any task.

Use only what the repository, its issues, and its board tell you. If
something is not written down, that is a finding.

Answer:
1. What is this project for, and what standard is the work held to?
2. Which single task would you start now, and where is the order written?
3. Which agent and model should do it, and how would you start that agent?
4. Where is the data the task needs? Can you reach it from here?
5. What may you do without asking, and what must you ask about first?
6. Run every documented command for reading state and for checking the code.
   Which failed, and do the docs explain the failure?

Report: your answers in one to three sentences each, quoting the source; a
list of problems, most serious first, each marked contradiction, missing
information, broken command, unclear rule, or stale content; and the mistake
you would most likely have made. Do not praise the setup. If an area has no
problem, do not invent one.
```
