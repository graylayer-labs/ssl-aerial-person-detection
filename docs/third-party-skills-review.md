# Review: Matt Pocock's skills and Superpowers

Reviewed 2026-09-29. Question: should we install either collection of Claude
Code skills in this project?

## Verdict

| Collection | Recommendation | Main reason |
|---|---|---|
| Matt Pocock's skills | Do not install the bundle | 27 skills, mostly for product and TypeScript work; nearly all overlap with what this repo already has |
| Superpowers | Do not install | Injects mandatory instructions into every session and writes plan files into the repo |

Nothing was installed. Three ideas were borrowed and written into our own
agents (see "Ideas applied").

## What they are

| | Matt Pocock's skills | Superpowers |
|---|---|---|
| Source | https://github.com/mattpocock/skills | https://github.com/obra/superpowers |
| Author | Matt Pocock (Total TypeScript, AI Hero) | Jesse Vincent |
| Licence | MIT | MIT |
| Stars | about 272,000 | about 293,000 |
| Last push | 29 Sep 2026 | 27 Sep 2026 |
| Size | 27 skills in the plugin | 14 skills |
| Install | Plugin (whole bundle), or an `npx` installer that copies chosen skills | Plugin (whole bundle only) |
| Runs code automatically | No | Yes, a hook at every session start |

Both are listed in Anthropic's official plugin marketplace.

## Why Superpowers does not fit

Superpowers is a complete working method, and it is designed to be followed
in full.

- **It takes over every session.** A session-start hook injects a block
  telling the agent it must invoke a skill before any response, even before a
  clarifying question. That adds about 700 tokens to every session and
  competes with our `/pickup`-first start.
- **It conflicts with how you want decisions made.** Its execution mode tells
  the agent not to pause and to make rulings itself, stopping only for a short
  list of cases. Our rule is a written list of areas where the agent must ask.
- **It writes into the repo.** Plans and specs go to `docs/superpowers/`, and
  a progress ledger goes to `.superpowers/`. We keep that state on the board.
- **It is expensive.** Its main mode uses a fresh agent per task plus two
  reviews per task. On a fixed plan that adds up quickly.
- **Its worktree layout differs from yours.** It creates `.worktrees/` inside
  the repo; you use sibling `<repo>.worktrees/` folders.

Skills cross-reference each other, so picking out one or two would break them.

## Why Matt Pocock's bundle does not fit

The skills are well made and modular, but they solve problems we have already
solved or do not have.

| His skill | What it does | Why we skip it |
|---|---|---|
| `wayfinder` | Plans large work as a map issue with child tickets | Competes with our board, `/pickup`, and `/handoff` |
| `handoff` | Writes a handoff note to the system temp folder | A temp file does not survive to the next session; ours writes to the issue |
| `code-review` | Two parallel reviewers: standards and spec | We have the `reviewer` agent; its smell list is aimed at object-oriented code |
| `tdd` | Red-green loop, asks the user to confirm test seams | You already enforce test-first with a hook |
| `implement-spec`, `to-spec`, `to-tickets` | Spec to tickets to parallel implementation | Conflicts with one issue, one branch, one PR; templates are product-oriented |
| `domain-modeling`, `prototype`, `teach`, `wizard`, and others | Glossaries, UI prototypes, teaching workspaces | Not relevant to ML research, or they add files to the repo |

## The one skill worth considering

**`diagnosing-bugs`** (Matt Pocock) covers something we lack: a discipline
for debugging.

Its method:

1. Build a command that reliably reproduces the failure before forming any
   theory.
2. Shrink the reproduction to the smallest case.
3. Write three to five ranked hypotheses, each one falsifiable.
4. Change one thing per test.
5. Tag temporary debug output so it can be removed with one search.

This suits silent ML failures such as a loss that becomes NaN, a leak between
splits, or a metric that drifts. Its examples are aimed at web code, so I
recommend writing our own ML version (fixed seeds, overfitting a tiny subset,
a fixed batch) the first time we hit a real training bug. It is on the
tooling list in issue #9.

## Ideas applied

These are in this repo now, written in our own words.

| Idea | Seen in | Where it went |
|---|---|---|
| No claim of success without the command that shows it, including metric claims | Superpowers | `implementer` agent |
| Reviewer re-runs checks itself, and flags tests that compute the expected value the same way the code does | Both | `reviewer` agent |
| Trust the issue and `git log` over memory; never redo work whose commits exist | Superpowers | `/pickup` |

## Ideas held for later

| Idea | Seen in | Possible use |
|---|---|---|
| Audit the agent setup itself: oversized instructions, rules that should be a lint check or hook | Matt Pocock `retro` | A `/retro` step inside `/tidy` |
| Label each task as a throwaway spike, a bounded change, or an architectural one | Superpowers `brainstorming` | A field on the issue template |
| Copy experiment invariants (splits, seeds, metrics) word for word into every task | Superpowers `writing-plans` | The issue template |
| List the top untested failure modes for each plan | Superpowers `writing-plans` | The `reviewer` checklist |
| Keep a parent issue as an index of one-line decisions linking to detail | Matt Pocock `wayfinder` | Milestone tracking issues |
| End a handoff with pointers to existing material, never copies of it | Matt Pocock `handoff` | `/handoff` |

## Security findings

Nothing malicious was found in either collection.

**Matt Pocock's skills**
- The plugin contains no hooks, no servers, and no commands that run on their
  own. It is text plus a few script templates.
- Some skills create issues and open PRs when invoked.
- The `npx` installer was not reviewed. It downloads and runs a third-party
  package, so copying files by hand is the safer route.

**Superpowers**
- Installs a session-start hook. The script only reads one of its own files
  and injects it as instructions. It makes no network calls.
- Bundles scripts that write into `.superpowers/` in the repo.
- Includes an optional local web server for a visual brainstorming tool,
  bound to this machine only. That tool loads a logo from the author's
  website, which reports the Superpowers version. It can be switched off.
- One skill can push a branch or delete one, each behind a confirmation.

## How far to trust this review

- **Checked by me against GitHub:** both repos exist, their owners, licences,
  star counts, last push dates, and that Superpowers ships a hooks folder.
- **Reported by the research agent from reading the source:** what each skill
  says, the hook's behaviour, the security findings, and the marketplace
  listing. I did not re-read these line by line.
- **Estimated:** token costs.
- **Not reviewed:** the `npx` installer, the Superpowers hook wrapper script,
  and some supporting files. No skill was run.

Both projects change quickly, so this review will go out of date. Re-check
before relying on it later.

## If you want to overrule this

- For one skill: I copy `diagnosing-bugs` by hand into `.claude/skills/` and
  add an ML section.
- For a full bundle: installing third-party plugins is on the list of things
  I ask you about first, so say the word and I will do it.
