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
