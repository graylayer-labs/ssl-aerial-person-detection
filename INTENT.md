# Intent

Why this project exists and how decisions get made. This file changes rarely.
Plans, tasks, and results live elsewhere (see "Where things live").

## Purpose

Build a system that takes drone footage from RGB and infrared (thermal) cameras
and detects people, for Search and Rescue (SAR).

## The problem

Drone footage is plentiful. Labels are not. A SAR team can record hours of
flights, but nobody has time to draw boxes on them. Any approach that needs
large labelled datasets does not transfer to the real world.

**Operating premise:** labels are scarce, even when a dataset happens to have
them. Where a public dataset is fully labelled, we deliberately hide most of the
labels and measure how far unlabelled footage takes us. The scarcity is the
thesis, whether or not the data on disk shows it.

## What value means

Value = learning + impressing people.

- **Learning:** the owner understands each technique well enough to explain why
  it worked or failed.
- **Impressing people:** a senior ML engineer reading the repo or a blog post
  sees sound engineering, honest evaluation, and current techniques.

Work that produces neither is out of scope, however interesting.

## Standard

Senior ML engineer. Half college thesis, half workplace:

- Thesis half: we have room to try things that fail, and failures are written
  up with the same care as successes.
- Workplace half: focus keeps returning to things that work and translate to
  the real problem. A claim needs a baseline, a held-out evaluation, and an
  honest statement of uncertainty.

## Technical direction

The direction, not the plan. Each step is a candidate for one or more
milestones, and the order can change as results come in.

1. **Foundation:** a pretrained vision foundation model adapted to aerial RGB
   and thermal imagery, so the system starts with a general understanding of
   what it is looking at.
2. **Self-supervised learning** on unlabelled drone footage, including the
   RGB-thermal pairing as a free training signal.
3. **Person detection** trained with few labels on top of those
   representations.
4. **Later:** deeper techniques as the project matures (semi-supervised
   labelling, video and temporal models, edge deployment).

Techniques should be at or near the current state of the art, if not at a given
milestone then at a later one. Older methods are welcome as baselines.

## How the work runs

- **Open-ended.** This project has no finish line. It advances in named
  milestones, each of which is presentable on its own and worth a blog post.
- **Not one-shot.** Small proven steps over big speculative ones.
- **Roles.** Eoin is Product Owner: sets direction, runs experiments, reviews.
  Claude agents do the engineering.
- **Agent continuity.** Every agent session ends. Anything a future agent needs
  must be in the repo or on the project board, never only in a conversation.
- **Testing.** Tests stay current and protect things that would silently
  corrupt results (data pairing, splits, metrics). No dense unit tests written
  for coverage.
- **Data.** WiSARD is the starting dataset. Other public datasets are welcome
  when they serve the purpose.

## Compute

- Prototype on the laptop (Apple M4, 24 GB). Laptop runs must be short; long
  multi-hour training on the laptop is out of scope.
- Cloud (SageMaker) is unlocked in stages, each stage justified by a working
  prototype. Cost is a personal expense and is treated as one.

<!-- TODO(human): the gate for cloud spend. What evidence unlocks a stage, and
     what is the spending ceiling per stage or per month? -->

## Non-goals

- A production SAR product or certified safety system.
- Leaderboard chasing without a link to the label-scarcity problem.
- Completing a fixed roadmap. Direction is revisited at every milestone.

## Where things live

| What | Where |
|---|---|
| Why (this file) | `INTENT.md` |
| How agents work in this repo | `CLAUDE.md` |
| What is planned and in progress | GitHub project board and issues |
| What happened and what we learned | `docs/` milestone write-ups |
