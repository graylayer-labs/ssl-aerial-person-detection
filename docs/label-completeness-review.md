# Label completeness review

Issue [#37](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/37).
How often does a visible person have no WiSARD box? No label was changed; this
is an estimate of label quality.

**Status: first pass only.** The reviewer was a Claude agent. 21 of the 198
sampled frames are marked unsure and still need the owner. Every number below
is provisional until they are checked.

## Method

- Sample: 99 labelled frames per camera, 9 from each of the 11 clips of that
  camera, simple random within the clip, seed 37. Empty-label frames were not
  forced in or out: 14 RGB and 21 thermal frames in the sample have an empty
  label file, and they were reviewed like the rest.
- One review sheet per frame: the whole frame with its boxes in red, and a
  zoomed crop of each quarter. Sheets, `tally.json` (seed and sample) and
  `review.json` (the judgement per frame) are in `outputs/label-check/`, which
  is git-ignored.
- Per frame the reviewer recorded the number of people seen with no box, and
  `sure` or `unsure`. Objects with a box that are not people (hats, sleds,
  bags) were not counted as misses. Dogs and other animals were not counted.
- Thermal rule: a warm shape counted as a person only if it had a head and
  body outline or stood with others in a way that fits people. A lone warm
  blob on rock was marked `unsure`, never `sure`.
- Interval: Wilson 95% binomial interval on frames, treating frames as
  independent. They are not: frames of a clip are neighbours, so the true
  interval is wider. The people-missing interval is the same naive Wilson
  interval on people, and is wider still in reality because people cluster in
  frames.
- Estimates use `sure` frames only. The unsure frames are bracketed
  separately.

Regenerate: `uv run python tools/label_completeness.py sample data/raw/wisard-full data/manifests/wisard-full outputs/label-check --seed 37`,
then `summarise` after `review.json` is filled in. `review.json` is the
reviewer's judgement and is not reproducible from the seed.

## Result

| | RGB | Thermal |
|---|---|---|
| Frames sampled | 99 | 99 |
| Unsure (excluded, pending owner) | 10 | 11 |
| Sure frames | 89 | 88 |
| Sure frames with at least one unlabelled person | 1 | 2 |
| Share of frames, point and 95% interval | 1.1% (0.2 to 6.1) | 2.3% (0.6 to 7.9) |
| Same, if every unsure frame is a miss | 6.3% to 18.8% | 7.8% to 21.2% (interval bounds) |
| People missed, in sure frames | 2 | 10 |
| People labelled, in sure frames | 201 | 167 |
| Share of people missing | 1.0% (0.3 to 3.5) | 5.7% (3.1 to 10.1) |
| Frame share weighted by clip size | 1.6% | 4.5% |

Where the misses are:

- RGB: one frame in `210924_FHL_Enterprise_0407` with two people on the shore
  and an empty label file.
- Thermal: two frames, both from `210924_FHL_Enterprise_0403`, with 5 people
  each and no boxes. This clip has 1201 of 1417 frames with an empty label
  file in the manifest, and nothing in the 9 sampled frames was labelled. In
  the thermal sample all 10 missed people come from this one clip. The
  clip-level problem, not a random thinning of boxes, drives the thermal
  number.

The unsure frames mostly hold a small dark or warm shape near boxed people (a
second person, a pack, a dog) or a person cut by the frame edge. The owner's
sighting of unboxed people on RGB contact sheets was not reproduced as a
common event in this sample: 1 of 89 sure RGB frames, with an unsure
bracket up to about 19%.

## Limits

- The sample is 99 frames per camera. A rate near 1 to 2% is barely
  measurable, and the interval says so.
- One reviewer, one pass, and the sheets are downscaled. A person under about
  15 px at sheet scale can be missed, which would bias the rate down. The
  quarter crops were meant to prevent this; they did not remove it.
- Part of the RGB pass had to be redone because some images were not
  displayed to the reviewer the first time. Only entries judged with the
  sheet visible are in `review.json`.
- Clips are unequally sized; equal allocation over-represents small clips.
  The weighted row shows the effect.

## What to keep in mind when reading recall and false-alarm figures

Treat recall as measured against an incomplete list and false alarms as
possibly including real people. On this sample the effect on RGB looks small
(about 1% of people), but on thermal it is concentrated in a few clips, above
all `210924_FHL_Enterprise_0403`, so per-fold thermal figures that include that
clip carry a false-alarm floor that no detector can remove. Quote these
figures with the unsure bracket until the owner has checked the 21 frames.

## Thermal clip FHL_0403 (issue #49)

Issue [#49](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/49).
The first pass found all ten thermal misses in `210924_FHL_Enterprise_0403`.
This section measures that clip alone. No label was changed.

### Measurement

- Clip: thermal directory `210924_FHL_Enterprise_IR_0404` (pairs with VIS 0403),
  1,417 labelled-manifest frames, 1,201 with an empty label file (84.8%).
- Sample: 60 frames at equal spacing through the clip from a random start,
  seed 49 (`tools/label_completeness.py sample ... --seed 49 --per-stratum 60
  --clip 210924_FHL_Enterprise_0403 --camera thermal`). Sheets, `tally.json`,
  `review.json` and `summary.json` are in `outputs/label-check-fhl0403/`
  (git-ignored). Reviewer: one Claude agent, one pass, same method and thermal
  rule as above.
- Labelling stops about 215 frames in: the first 9 sampled frames (to DJI frame
  203) have boxes, all 51 later frames have an empty label file. Every boxed
  frame was reviewed too and had no unboxed person.

| | Count | Share, 95% Wilson interval |
|---|---|---|
| Sampled frames | 60 | |
| Empty-label frames in the sample | 51 | |
| Of those, sure with at least one unboxed person | 30 | |
| Of those, sure with none | 5 | |
| Of those, unsure | 16 | |
| Sure empty-label frames with an unboxed person | 30 of 35 | 85.7% (70.6 to 93.7) |
| All 60 frames, sure only | 30 of 44 | 68.2% (53.4 to 80.0) |
| Empty-label frames, if every unsure one is clean | 30 of 51 | 58.8% (45.2 to 71.2) |
| Empty-label frames, if every unsure one is a miss | 46 of 51 | 90.2% (79.0 to 95.7) |

- People: 86 unboxed in the sure frames against 39 boxed, all in the first nine
  frames. Where people are visible there are usually 2 to 5, standing on the
  beach or on the rocks of the point.
- Scaled to the clip, that is roughly 1,030 of the 1,201 empty-label frames
  (850 to 1,125 at the interval); even the strict floor, unsure frames counted
  clean, is about 700.
- The 5 sure frames with no person are real empties: dark water, driftwood,
  or the closing frames panning away from the shore.
- **16 frames are unsure and are left for the owner.** Listed by DJI frame
  number: 250, 297, 321, 344, 391, 462, 557, 793, 1100, 1147, 1218, 1312, 1336,
  1360, 1383, 1407. They hold small warm blobs or faint figures at the edge of
  what the sheets resolve (blurred, overexposed, or a single bright vertical
  shape). Each is `unsure` in `review.json` with a note; the rule was to err
  towards unsure for lone warm shapes.
- Limits as above: one reviewer, one pass, frames of one clip are neighbours
  so the interval is optimistic, and a person under about 15 px can be missed
  or invented. The main result does not depend on the unsure frames: the
  strict floor is still a majority of the empty-label frames.

Conclusion: the clip is a labelling gap, not random thinning. Labelling stops
partway through and the same people stay in view for the rest of the clip.

### Proposal (the lead decides)

Three ways to treat the 1,201 empty-label frames of this clip. They only
matter for FHL, where this clip is part of the FHL test fold, and for every
other fold, where it is training data.

| Option | For | Against |
|---|---|---|
| **A. Exclude the empty-label frames from thermal evaluation and training** | Removes a false-alarm floor that no detector can beat, and stops the detector being taught that visible people are background. Cheap: a filter on the manifest. Keeps the 216 labelled frames of the clip. | Selection by an empty label file is selection by the thing being doubted: other clips have genuinely empty frames (the 5 sure empties here), and the filter would drop those from this clip too. Shrinks the FHL thermal test set by 1,201 of its 5,420 frames and shifts it toward frames with people, so it overstates precision. The fold sizes in `docs/site-folds-review.md` change. |
| **B. Keep them in the data but treat them as unlabelled** | Fits the project premise that labels are scarce: these frames become pseudo-labelling or SSL input rather than negatives. Throws nothing away. | Needs a way to mark them in the manifests and the loaders, so more code and a new field. For evaluation it is the same as A (they cannot score recall or false alarms), so it is the same test set as A. |
| **C. Keep them as they are and state the floor** | No change to folds or data, and the stated number is simple: at least about 59% and likely about 86% of this clip's empty-label frames hold unboxed people. | Thermal false-alarm figures on the FHL fold are not interpretable: the floor is a large share of any detection. Training treats visible people as background, which probably lowers recall in every fold where the clip is in the training set. |

Recommendation: B for evaluation and training (exclude from scoring and from
negative sampling, keep as unlabelled data), because it removes the damage in
both places and keeps the frames for the semi-supervised stages. A is the
cheaper step if B's field is not wanted now, and it gives the same numbers.
C is the fallback if the folds must not change; if chosen, quote thermal FHL
figures only with the floor beside them. The 16 unsure frames do not change
the choice, and the owner can check them first if they want tighter bounds.
Whichever is chosen is a change to the folds, which #49 lists as out of scope,
so it needs its own issue.

Decision (lead, 2026-10-01), applied in issue
[#53](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/53):
option B. The clip's 1,201 empty-label thermal frames are in no thermal
manifest and stay in the unlabelled pool; see "Label overrides" in
`docs/site-folds-review.md`.
