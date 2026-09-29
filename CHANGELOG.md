# Changelog

Key changes to the project, newest first. Routine fixes and wording changes
are left out; the git log has those. Entries are grouped by epic and date, and
each links to the issue or pull request that holds the detail.

## Epic: Trusted ground (in progress)

### 2026-09-29

**Found**
- The code that pairs RGB frames with thermal frames reads only 5 or 6 digit
  frame numbers, and so misses about 53% of the image files in WiSARD. Every
  dataset figure quoted before this date is unverified. The bug is pinned by
  tests that are expected to fail until it is fixed.
  ([#2](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/2),
  [#12](https://github.com/graylayer-labs/ssl-aerial-person-detection/pull/12))
- The WiSARD paper reports that the two cameras drift by one or two frames
  over a flight, so equal frame numbers do not guarantee the same instant.
  ([#5](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/5))

**Changed**
- The project restarted after five weeks idle, with a new direction: start
  from a pretrained foundation model, adapt it with self-supervised learning
  on unlabelled footage, then detect people with few labels. The earlier plan
  to train small networks from scratch is dropped.
  ([INTENT.md](INTENT.md), [docs/decisions.md](docs/decisions.md))
- `main` is protected. Changes arrive by pull request, merge themselves when
  CI passes, and are squashed. No human review is required.
  ([#10](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/10))
- Results may be quoted only from a run on a clean commit on `main`.
  ([#23](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/23))
- Tests and lint pass on `main`, and CI runs both on every pull request.
  ([#1](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/1))

**Added**
- `INTENT.md` and `CLAUDE.md`: why the project exists, and how agents work in
  it.
  ([#10](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/10))
- A public project board, with six epics as the roadmap and tasks as their
  sub-issues.
  ([board](https://github.com/orgs/graylayer-labs/projects/1))
- Agents for implementing, reviewing, researching, auditing the process, and
  auditing the repo, each on the cheapest model that suits the work.
  ([#10](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/10),
  [#22](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/22))
- A cold-start test: a fresh agent with no context reports what the
  instructions failed to tell it. Two runs found and fixed fifteen gaps.
  ([#20](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/20))
- A process audit, with a standing log of its findings.
  ([#24](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/24))
- Archify, a third-party diagram skill for finished figures, installed by a
  script that checks a pinned commit and kept out of the repository. Its update
  check, brand fetch, and preview are blocked by settings. The README now shows
  the first figure, the pipeline.
  ([#30](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/30))

**Removed**
- The planning documents from the first attempt: `VISION.md`, `ROADMAP.md`,
  `ARCHITECTURE.md`, and `PROBLEM.md`. They remain in git history.
  ([#6](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/6))

**Decided against**
- Installing the Superpowers or Matt Pocock skill collections.
  ([review](docs/third-party-skills-review.md))
- Requiring signed commits on `main` while branch commits are unsigned. It
  blocked every pull request. Commits on `main` are still verified, because
  GitHub signs each squash merge.
  ([#22](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/22),
  [#27](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/27))

## Before the restart

### 2026-08-08 to 2026-08-26

- Project started. The WiSARD dataset was downloaded and paired, and a data
  exploration notebook was written. Its figures are unverified; see the first
  entry above.
- First experiment scripts for contrastive pretraining and grid detection.
  No results were recorded.
