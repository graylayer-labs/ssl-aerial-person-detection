# Blog

Short posts that lead with a result, for a recruiter or a senior engineer
skimming. "Here is the foundation model." "Here is the detector in action."

The process behind a post lives in the [guide](../guide/README.md): the data,
the design choices, the mistakes, the commands. A post links to it for the
detail and does not repeat it.

## Rules

- **One post per milestone,** written when the milestone closes, from the
  milestone note and the guide. The first draft is `2026-10-trusted-ground.md`, for milestone 1.
- **Shape:** a one-paragraph hook, one figure, the result, what it means for
  search and rescue, and a link to the guide. Use
  [`TEMPLATE.md`](TEMPLATE.md).
- **Every number links to its source** in the guide, an issue, or a note under
  `docs/`. A number that cannot be sourced is cut.
- **A negative result is a result.** Say what was expected, what happened, and
  why.
- **Figures are finished, not drafted:** see "Diagrams" in `CLAUDE.md`.
- **A draft is for the owner to edit.** Nothing here is published by an agent.
  Publishing a post is on the "Ask the owner first" list in `CLAUDE.md`.
- **Acknowledge DINO** where the post reports results from DINOv3, as its
  licence asks ([`docs/model-and-dataset-review.md`](../model-and-dataset-review.md)).

Name a post `YYYY-MM-DD-<slug>.md`. Run `/blog <milestone>` to draft one.
