# ssl-aerial-person-detection

Read the intent first. It explains why the project exists and how decisions are
made, and it overrides anything below that conflicts with it.

@INTENT.md

## Who does what

Eoin is the Product Owner. Claude agents do the engineering and run the
project day to day. Act without asking, except in the areas listed under
"Ask the owner first".

The main session is the lead. It plans, delegates, judges results, and talks
to the owner. It does not do routine work itself.

- **Delegate and keep working.** Start agents in the background, each in its
  own worktree, and carry on with other things while they run.
- **Take back conclusions, not transcripts.** Every agent returns a short
  report. The detail goes on the issue, where the next agent can find it.
- **Run independent tasks in parallel**, up to three agents at a time. The
  epic's "Order of work" says which tasks are independent. One agent per
  issue.
- **Verify before trusting.** Re-run the checks an agent reports, and test
  its most important claim yourself.
- **Push after verifying.** Agents commit on their branch and stop. The lead
  pushes and opens the PR once it has re-run their checks.
- **Say who did the work.** The `agent:` label records the plan. If the lead
  does an issue itself, or a different model is used, the handoff says so
  and why.
- **Write the brief as if to a stranger.** An agent knows only what its
  prompt and the issue tell it.

## Every session

Agent sessions end and context is lost. The project board is the memory.

1. **Start** with `/pickup`. It reads the board and open issues and tells you
   what is in progress and what is next. Do not start work from memory of a
   previous conversation.
2. **Work** on one issue at a time: one issue, one branch, one PR.
3. **Record as you go.** Decisions, results, and dead ends go in a comment on
   the issue, not only in the conversation.
4. **End** with `/handoff`, even if the task is unfinished. The next agent
   should be able to continue from the issue alone.

If there is no issue for the work, create one from the task template.

## Leave a trail

Assume the next reader is an agent that has never seen this project. Every
finished issue gets a closing comment, written with `/handoff`, that states:

- what was done, with links to the PR and commits
- the evidence: commands run and their output, or the numbers and the config
  that produced them
- decisions made and why
- what was tried and did not work
- what was found but left alone, and the issue that now tracks it

Then add one line to the parent issue's "Decisions so far" list, linking to
the closed issue. The parent stays a short index; the detail stays in the
child.

## The board

- Board: https://github.com/orgs/graylayer-labs/projects/1 (project number 1,
  owner `graylayer-labs`). It is public.
- Issues: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues
- Status lives on the board only: Todo, In Progress, Done.
- **Epics** are parent issues labelled `epic`, one per milestone. Tasks are
  their sub-issues. The epics in order are the roadmap; there is no separate
  roadmap document.
- Only the current epic has sub-issues. Later epics hold a short description
  and get their tasks when the one before them closes.
- The current epic's body has an "Order of work" section. Follow it. The
  board does not rank tasks.
- An epic is In Progress for as long as any of its tasks is open. That row is
  not a task; look at its sub-issues.
- `gh project` commands fail now and then with `unknown owner type`. Run the
  command again.

```bash
# attach issue <child> to epic <parent> (needs the child's id, not its number)
CHILD_ID=$(gh api repos/graylayer-labs/ssl-aerial-person-detection/issues/<child> --jq .id)
gh api -X POST repos/graylayer-labs/ssl-aerial-person-detection/issues/<parent>/sub_issues \
  -F sub_issue_id=$CHILD_ID
```

```bash
gh project item-list 1 --owner graylayer-labs --format json --limit 100   # status
# to read one field, add --jq to this command. Piping its JSON into a
# separate jq can fail on control characters in issue text.

# read a task in full. `gh issue view <n> --comments` can omit the body.
gh issue view <n> --json title,body,labels,comments --jq \
  '.title, ([.labels[].name] | join(", ")), .body,
   (.comments[] | "--- comment " + .createdAt, .body)'

# move an item (get <item-id> from item-list)
gh project item-edit --project-id PVT_kwDOEDMalc4BlE5m --id <item-id> \
  --field-id PVTSSF_lADOEDMalc4BlE5mzhjzG-Q --single-select-option-id <option>
# options: Todo f75ad846 · In Progress 47fc9ee4 · Done 98236657
```

Labels in use: `agent:fable|opus|sonnet|haiku` (which model), `type:bug`,
`type:enhancement`, `type:documentation`, `type:experiment`, `epic`,
`needs-owner` (blocked on the owner), and `tooling-candidate`. The `data:`,
`model:`, `source:`, and `status:` labels come from the org template and are
not used here.

Two standing issues never close: "Reusable tooling candidates" (#9) and
"Audit log" (#24).

## Do freely

- Create branches, commit, push branches, open and update PRs.
- Create, edit, comment on, and close issues. Update the board.
- Merge PRs. `main` is protected: nothing is pushed to it directly, a PR
  merges only when the `checks` CI job passes, and every commit must be
  signed. No human review is required. Merge through GitHub and never
  locally.
  Set a PR to merge itself with `gh pr merge <n> --auto --squash`.
- Delete superseded code and docs. Git history is the archive.
- Delete and regenerate anything under `data/manifests/` and `outputs/`.
  These are produced by committed code.
- Short laptop runs.
- Free or near-free AWS: S3 storage for project data, and free-tier
  instances.

### Review before merge

CI proves the code runs. It does not prove a result is valid.

- Changes to logic under `src/`, to experiments, or to metrics: the
  `reviewer` agent checks the branch before auto-merge is set.
- Docs, config, and formatting-only changes: the main session reads the diff
  itself.
- Say in the PR which of the two happened.

## Ask the owner first

- Spending real money: paid cloud instances, SageMaker, or any paid service.
  Give the reason a laptop run will not do and a cost estimate.
- Deleting raw data under `data/raw/` or anything in S3, or anything else
  that cannot be recovered.
- Force-pushing, rewriting history, or deleting a remote branch that has
  unmerged work.
- Changing the purpose, standard, or non-goals in `INTENT.md`.
- Anything public beyond the repo itself: blog posts, releases, repo
  visibility or settings, making the board public.
- Installing third-party plugins, skills, hooks, or MCP servers.
- A laptop run expected to take over an hour. Prefer a cloud instance for
  long runs, which is a spending request.
- Merging a PR that the reviewer flagged.
- Changing branch protection or other repository settings.

`.claude/settings.json` backs these up with permission rules. The rules are a
safety net, not the definition; this list is.

### Record every approval

When the owner approves something on this list, quote their words and the
date in a comment on the issue, before acting. An approval that lives only in
a conversation is lost when the session ends.

### When a task needs the owner partway through

Some issues have one step only the owner can do, such as looking at a figure.
Do everything else first. Then add the `needs-owner` label, leave the issue
In Progress, open what they need to see, and ask them in the conversation.
Do not close the issue or tick that criterion yourself.

## Showing the owner

The owner sees only what is put in front of them. They do not browse the repo
or the board unprompted.

- When something needs their eyes, open it (`open <url>` or `open <file>`)
  and say what to look at and why.
- Put the key content in the message itself. Do not reply with only a path.
- Ask decisions as direct questions in the conversation. Do not leave
  placeholders in files for the owner to fill in.
- End each session with a short summary: what changed, what was decided, what
  needs them.

## Commit signing

Every commit is signed, on branches as well as on `main`. The repository's
local git config signs with an SSH key made for this project,
`~/.ssh/ssl_aerial_signing_ed25519`, which is registered on the owner's
GitHub account as a signing key. The key has no passphrase so that agents can
sign; it signs commits and nothing else.

- Agent worktrees share the repository's config, so they sign too.
- If a commit fails with a signing error, the key is missing: a fresh machine
  needs its own key, registered on GitHub, and the three `git config --local`
  lines in issue #27.
- Never copy the private key anywhere, and never commit it.

## Commands

```bash
uv sync --dev                  # install
uv run pytest                  # tests
uv run ruff check --fix .      # lint
uv run ruff format .           # format
uv run ty check                # types
tools/install_archify.sh       # one-time: install the Archify diagram skill
```

- CI runs all four checks: ruff check, ruff format, ty, and pytest.
- Inside an agent worktree, `uv run` warns that `VIRTUAL_ENV` does not match.
  It is harmless. Prefix the command with `env -u VIRTUAL_ENV` to silence it.
- A fresh worktree has no environment. Run `uv sync --dev` first.

## Diagrams

- **Mermaid** for drafts and working documents. It costs few tokens and GitHub
  renders it.
- **Archify** for finished figures: the README, milestone write-ups, and blog
  posts. Figures and their source JSON live in `docs/figures/`, for example
  `pipeline.svg` and `pipeline.archify.json`.
- Install once with `tools/install_archify.sh`. It fetches a pinned, verified
  commit into `.claude/skills/archify/`, which is git-ignored, and refuses to
  install if the commit differs. `--force` replaces an existing install.
- Limits, enforced in `.claude/settings.json`:
  - No brand URLs in a diagram. Brand capture fetches from the network.
  - Never pass `--open`.
  - Never run `preview`.
- Archify has no command-line SVG export. Export from the viewer's Export menu,
  and commit only the SVG and its JSON, never anything from `.archify/`. Check
  the SVG for absolute paths first.

## Data

`data/` is git-ignored, so a fresh clone or worktree has none.

| What | Where |
|---|---|
| Raw WiSARD images and labels, 41 GB | `data/raw/wisard-full/` in the main checkout |
| Manifests, regenerable | `data/manifests/wisard-full/` in the main checkout |
| The same dataset, as the durable copy | S3 bucket `ssl-aerial-person-detection-data-eu-west1`, region `eu-west-1`, under `wisard/raw/wisard-full/`. Versioning is on. Checked equal to the local copy by path and size on 2026-09-29 |

- The main checkout is the first path printed by `git worktree list`.
- Agent worktrees get `data/` as a symlink to the main checkout's copy, set in
  `.claude/settings.json`. If `data/` is missing, read it from the main
  checkout by absolute path.
- If a task needs data you cannot reach, stop and say so. Do not invent
  figures or regenerate from nothing.
- The dataset exists once on the laptop and once in S3. If a directory is ever
  missing locally, fetch it from S3; do not look for another copy.

### AWS

- Agents use the AWS profile `ssl-aerial`, set as `AWS_PROFILE` in
  `.claude/settings.json`. It assumes the role
  `ssl-aerial-person-detection-agent`, which can list, read, and write objects
  in the project bucket and nothing else. It cannot delete objects or
  versions, or change bucket settings.
- Do not name another profile. The owner's own sign-in has administrator
  access and is not for agents.
- A fresh machine needs the profile added to `~/.aws/config`: `role_arn` of
  the role above, `source_profile` of the owner's sign-in, region `eu-west-1`.
- The sign-in behind the profile is temporary. If AWS commands fail with an
  expired token, ask the owner to sign in again.
- Anything that costs money needs the owner's approval. See "Ask the owner
  first".

### Pairing

Which RGB frame goes with which thermal frame is decided in
`src/aerial_search/data/wisard.py`, and the evidence is in
`docs/wisard-pairing-review.md`. Only directory pairs listed in
`WISARD_COLLECTIONS` are paired. Pairs are 0 to 2 frames apart in time; the
cameras drift. Regenerate the manifests and the contact sheets with:

```bash
uv run aerial-search prepare data/raw/wisard-full --output data/manifests/wisard-full
uv run aerial-search folds data/raw/wisard-full data/manifests/wisard-full
uv run aerial-search check-folds data/raw/wisard-full data/manifests/wisard-full
uv run python tools/pairing_contact_sheets.py data/raw/wisard-full \
  data/manifests/wisard-full/all_pairs.jsonl outputs/pairing-check
```

## Layout

```
src/aerial_search/   package: data/, models/, experiments/
tests/               tests for the package
notebooks/           analysis notebooks, numbered
docs/                milestone write-ups and decision notes
tools/               one-off scripts that are worth keeping
data/                datasets and manifests (git-ignored)
outputs/             run artefacts (git-ignored)
```

## Documentation

Keep it short, and keep one home for each fact.

| Fact | Home |
|---|---|
| Why the project exists | `INTENT.md` |
| How to work here | this file |
| What is planned or in progress | the board |
| What changed that a reader should know | `CHANGELOG.md`, key items only |
| Why a technical choice was made | `docs/decisions.md`, one line each |
| The evidence behind a decision, when it is long | `docs/<topic>-review.md` |
| What a milestone found | `docs/milestones/<name>.md`, created with the first write-up |
| How the project was built, step by step, with its mistakes | `docs/guide/`, kept current with `/guide` |
| A short, result-led post for a general reader | `docs/blog/`, drafted with `/blog` for the owner to edit |

Write a decision down when a future agent would otherwise have to guess or
re-derive it. Format: `YYYY-MM-DD · chose X over Y · reason`.

### Changelog

`CHANGELOG.md` is for a reader who wants the project's history in two
minutes. Add an entry in the same PR as the change when the change is one of
these:

- a finding that changes what can be trusted, such as a bug in the data
- a result, positive or negative
- a change of direction or method
- a new capability, dataset, or model
- a rule that changes how work is done or merged
- something tried and dropped

Leave out routine fixes, refactors, and wording changes. Group entries by
epic and date, newest first. Each entry is one or two sentences with a link
to its issue or PR. No version numbers.

## Experiments

- **No "works on my machine".** A run whose result is quoted anywhere comes
  from a commit on `main`, with a clean working tree. Merge the code first,
  then run it.
- A run from a branch or a dirty tree is a scratch run. Use it to debug. Never
  quote its numbers.
- Every run is defined by a committed config and a seed, and writes to
  `outputs/<run-name>/` with a `run.json` that records the commit, the config,
  the seed, and the machine. `src/aerial_search/run.py` (`start_run`) enforces
  this: it refuses a normal run unless the tree is clean (untracked files
  count) and `HEAD` is on the local `origin/main`, and it fails closed if git
  cannot tell. It never fetches, so run `git fetch` first. Pass `--scratch` to
  `train-ssl` or `train-detector` for a debugging run: it writes to
  `outputs/scratch-<run-name>/` with `"scratch": true` in `run.json`. A run
  directory is never overwritten; pick another `--run-name`.
- The run directory is the only place an experiment writes (there is no
  `--output`). `start_run` inspects the repository that holds the running
  code, not the current directory, and refuses a normal run from a
  non-editable install. Tracked files hidden by skip-worktree or
  assume-unchanged also refuse a normal run. `run.json` records the SHA-256
  of every input (manifests, checkpoint). A normal run given
  `--ssl-checkpoint` needs a `run.json` beside it with `scratch` false,
  `status` completed, and the same `fold` and `view`; the parent's name and
  commit are recorded.
- A normal run is quotable only if its `run.json` has `"status": "completed"`.
  `"started"` means it crashed or is still running; `"failed"` records the
  error. Known limit: files ignored through `.git/info/exclude` are not seen.
- Size runs for the laptop first. Aim for under 30 minutes.
- Any number quoted in a doc or README must be reproducible from a committed
  config. If a number cannot be traced, remove it.
- Report negative results. State what was expected, what happened, and the
  most likely reason.
- Always compare against a baseline on a held-out split. Splits are by
  site-day (every clip from one site on one date), never by clip or frame,
  because neighbouring frames are near-duplicates and clips from one site-day
  share terrain and people. Each labelled site-day is the test set of one
  fold. Report every result per fold and as the mean and spread over the
  folds, never as one pooled number. See `docs/site-folds-review.md`.
- Every published table or figure that shows `ap_iou25` shows `ap_iou50`
  beside it. The lower threshold is the primary metric for tiny people, and
  the reader must be able to see how much it contributes. See
  `docs/evaluation-metric-review.md`.

## Tests

Test what would silently corrupt results: pairing, splits, label handling,
metrics. Skip tests that only restate the implementation.

## Model tiering

The owner pays for usage. Use the cheapest model that can do the job well.

Each issue carries an `agent:<model>` label. It names the model, and the
table says which agent to run on it.

| Label | Kind of work | Who does it |
|---|---|---|
| `agent:fable` | Milestone design, experiment analysis, final judgement | The main session |
| `agent:opus` | Implementation where a wrong answer is costly, hard debugging | `implementer`, with the model set to Opus |
| `agent:sonnet` | Implementing a well-specified issue | `implementer` |
| `agent:haiku` | Mechanical edits | `implementer`, with the model set to Haiku |
| `agent:haiku` | Read-only audits | `repo-janitor` |

- To set the model, pass `model` on the Agent call, for example
  `subagent_type: "implementer", model: "opus"`. Without it, `implementer`
  runs on Sonnet.
- Where a label fits two rows, the issue's "Suggested model" section says
  which agent to use.

Agents that are not tied to a label:

| Agent | Model | Use |
|---|---|---|
| `reviewer` | Opus | Reviews a branch before merge. Never implements |
| `researcher` | Sonnet | Surveys with cited sources. Changes nothing |
| `process-auditor` | Sonnet | Checks that protocols were followed; fixes process records |
| `repo-janitor` | Haiku | Reports drift and clutter in the repo. Changes nothing |
| `guide-writer` | Sonnet | Keeps `docs/guide/` current from closed issues; drafts blog posts. Writes only under `docs/guide/` and `docs/blog/` |

## Keeping the project honest

| Skill | Checks | Run it |
|---|---|---|
| `/tidy` | The repo: stale docs, dead code, stray files | End of every epic |
| `/audit` | The process: trails, evidence, reviews, board, agent files | End of every epic, and after every five closed issues |
| `/coldstart` | The instructions: can a new agent orient itself | After any change to this file, an agent, or a skill |
| `/guide` | Nothing; it updates `docs/guide/` from closed issues, every number linked to its source | End of every epic, after the milestone write-up |
| `/blog` | Nothing; it drafts a post from the guide and the milestone note, for the owner to edit and publish | End of every epic, after `/guide` |

## Reusable tooling

When you do something by hand that a future agent or another project would
repeat, add a comment to issue #9: what the step was, and whether it fits a
skill, a command, an agent, or a hook. Do not build it on the spot unless the
current issue asks for it.
