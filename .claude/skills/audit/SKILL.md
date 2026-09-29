---
name: audit
description: Audit finished work and the agent setup against the project's protocols. Use at the end of an epic, after several issues have closed, or when the owner asks whether the rules are being followed.
---

# Audit

## Steps

1. Find issue #24, "Audit log". Its newest comment marks where the last
   audit stopped.
2. Delegate to the `process-auditor` agent. Tell it the date and nothing else;
   it finds its own scope. Do not tell it what you expect it to find.
3. Read its report. For each finding marked "needs lead", fix it or open an
   issue. Put each "needs owner" finding to the owner as a direct question.
4. If the report names a pattern, change the instruction it points to. A rule
   that keeps being broken is written badly or sits in the wrong place.
5. Tell the owner: how many findings, what was fixed, and what needs them.

## When to run

- At the end of every epic, before the milestone write-up.
- After every five closed issues.
- After any change to `CLAUDE.md`, an agent, or a skill, together with
  `/coldstart`.
