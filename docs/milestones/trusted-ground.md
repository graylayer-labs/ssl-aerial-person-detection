# Milestone 1: Trusted ground

Written 2026-10-01 by the lead. The milestone ran from 2026-09-29 to
2026-10-01, picking up a repository that had been idle for five weeks.

**One sentence:** before training anything, every result's foundations were
checked, and most of them turned out to need fixing.

## What we set out to do

The project wants to show that a person detector for search and rescue can be
trained from plentiful unlabelled drone footage and a small fraction of
labels, and scored at a site it has never seen. Each part of that sentence
rests on something that has to be right: the frames of the two cameras must
be paired correctly, the test site must be unseen, the labels must be what
they claim, and a quoted number must be reproducible. This milestone was the
work of making those four things true, and of writing down what was found.

## What we found

| Foundation | Before | After |
|---|---|---|
| Frame pairing | Two manifest sets, both wrong. One paired by position and included 1,620 mismatched pairs; the other lost most of seven clips to a parser that read only 5 or 6 digit frame numbers | 14,834 pairs from 17 verified clip pairs; 5,739 labelled in both cameras. Verified by camera motion and by eye. [#2](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/2) |
| Test split | Empty, or one flight, chosen at random by clip | Four folds, each leaving one site-day out as the test set. An independent check reads the manifests back and found no leak. [#3](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/3) |
| Scoring | None for the model in use | Average precision at an overlap of 0.25, suited to people 8 to 12 pixels across, with the standard 0.5 figure beside it, and recall at fixed false alarms per image. Reviewed twice. [#4](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/4) |
| Reproducibility | Nothing recorded which code or data a run used | A run refuses to start unless the code is a clean commit on `main` and the data it reads matches a committed checksum list. [#23](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/23), [#38](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/38) |
| Labels | Assumed complete | About 1.0% of people in RGB and 5.7% in thermal have no box, on a sample of 198 frames. One thermal clip is largely unlabelled: about 86% of its "empty" frames show people. [#37](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/37), [#49](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/49) |
| Storage | The dataset three times over on a laptop with 20 GB free | Once locally, once in S3 with versioning; 81 GB freed. [#7](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/7) |
| Starting model | Undecided | SigLIP 2 (Google, Apache-2.0, no sign-up), with EVA-02 second and DINOv2 as a comparison. The owner chose a non-Meta model. [#5](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/5) |

Every number above has its source in the linked issue's closing comment or in
the review note it names. No model was trained, by design.

## Three things worth telling

**The failing tests were right.** On day one, two tests failed. They used
8-digit frame numbers, as much of the dataset does, and the pairing code read
only 5 or 6 digits. The tests were catching a real bug. Making them pass
without fixing the code would have hidden the problem.

**Passing acceptance criteria is not the same as being right.** The run
module and the evaluation module each passed every criterion in their issue
and every test, and each failed its review three ways. In both cases the
criteria described the thing to build and not the property it had to
guarantee. Issues now state the property.

**The reviewer's method found what the author's could not.** Every blocking
finding in this milestone came from a reviewer who worked cases out by hand
before running them, or who changed a line of code to see whether any test
noticed. Both methods are now written into the reviewer's instructions.

## How the work was done

Claude agents did the engineering; the owner directed and did the steps only
a person can do, such as looking at the paired frames and accepting licences.
A lead session delegated each issue to an agent on the cheapest model that
could do it, re-ran its checks, and sent anything that touches results to a
separate reviewer. Twenty-two issues closed through twenty-nine merged pull
requests, each merged by passing CI on a protected branch, with every commit
signed. A cold-start test, where a fresh agent with no context is asked to
orient itself, was run twice and fixed fifteen gaps in the instructions. A
process audit ran once.

The cost: about 2.7 million tokens of agent work on 2026-10-01 alone, which
reached 90% of the owner's plan in an afternoon. The rules now cap agents at
two at a time, default to the cheaper model, and allow one review per PR.

## What comes next

Epic #14, "Off-the-shelf bar": how far a frozen foundation model gets with 1%,
5%, 10%, and 100% of the labels, per camera, on the four folds. It is the
baseline every later technique has to beat. Before its first run, the design
has to choose a feature resolution that fits the disk: full-detail features
for the small model alone would take about 94 GB.

## Open at the close of the milestone

- The owner's check of 37 frames the agents could not decide on
  ([#37](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/37)).
- Treating the mostly unlabelled thermal clip's empty frames as unlabelled
  data in the folds
  ([#53](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/53)).

## Where to read more

- The follow-along guide: [`docs/guide/`](../guide/README.md).
- The review notes: pairing, evaluation metric, site folds, model and
  datasets, label completeness, all under `docs/`.
- Decisions, one line each: [`docs/decisions.md`](../decisions.md).
