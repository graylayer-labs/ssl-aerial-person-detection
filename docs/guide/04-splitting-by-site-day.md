# 4. Splitting by site-day

*Last updated 2026-10-01 from issues [#3], [#39] and [#45].*

## What we set out to do

Decide which images a model may train on, which it may tune on, and which it
is finally scored on, so that a good score means the model works at a place it
has never seen. A leak between splits would invalidate every later result
([#3]).

## What we found

**The old split was empty where it mattered.** With the first fixed seed, the
split put no labelled pair in test: 4,571 pairs in train, 1,168 in validation,
0 in test ([#2 handoff][i2-handoff]). It also assigned whole clips at random,
so clips from one site and day could land in different splits ([#3]).

**Only four site-days have labels** ([#3], from `data_quality.json`):

| Site-day | Clips | Pairs | Labelled in both cameras |
|---|---|---|---|
| 210417 MtErie | 3 | 708 | 708 |
| 210529 Carnation | 2 | 2,052 | 739 |
| 210812 Hannegan | 2 | 1,136 | 0 |
| 210924 FHL | 9 | 8,758 | 2,112 |
| 220109 Baker | 1 | 2,180 | 2,180 |

One fixed test set of several flights cannot be cut from four site-days. Baker
alone holds 38% of the pairs labelled in both cameras ([#3]).

**The unit that must not cross a split is the site-day.** Neighbouring frames
are near-duplicates, and clips from one site-day share terrain, light and
often the same people ([folds review][folds-review]).

**The gap inside a clip had to be 250 frames, not 50.** Where a site-day has
one clip, validation is a block at the end of it. The issue proposed dropping
50 frames before the block. We measured how alike frames k apart
are (correlation of 64x36 thumbnails, 1 means identical):

| Clip | Camera | 1 apart | 50 apart | 250 apart | Random pair, same clip |
|---|---|---|---|---|---|
| Baker 1 | rgb | 0.95 | 0.53 | 0.34 | 0.31 |
| Carnation 0023 | rgb | 0.95 | 0.60 | 0.36 | 0.36 |

At 50 frames, frames are still far more alike than random frames of the clip.
At 250 (50 seconds) they are not ([folds review][folds-review]). The cost:
Baker loses 250 of 2,180 frames and Carnation 0023 loses 250 of 739 in the
paired and thermal views.

**One-percent labels are a handful of blocks.** At 1%, a fold has 3 to 8 blocks
of 10 frames, which is 30 to 80 labelled frames. In five of the twelve
fold-views, the 1% subset holds only two of the three training site-days. At
5%, which is 130 to 370 frames, every subset holds all three
([folds review][folds-review]). A 1% result needs several seeds.

**What the test sets hold, by person size**, paired view, in boxes
([folds review][folds-review]):

| Fold | Camera | very_tiny | tiny | small | medium_plus |
|---|---|---|---|---|---|
| MtErie | rgb | 0 | 0 | 0 | 1,770 |
| MtErie | thermal | 0 | 419 | 915 | 490 |
| Carnation | rgb | 0 | 0 | 774 | 1,168 |
| Carnation | thermal | 613 | 1,002 | 97 | 1 |
| FHL | rgb | 0 | 164 | 2,118 | 1,762 |
| FHL | thermal | 193 | 2,645 | 1,801 | 228 |
| Baker | rgb | 0 | 0 | 27 | 5,985 |
| Baker | thermal | 0 | 95 | 1,263 | 3,903 |

A size bucket says something only on folds whose test set holds people of that
size. MtErie has no small RGB people at all.

## How we checked it

`aerial-search check-folds` reads the manifests back and verifies every rule,
independent of the builder. The lead ran it on `main` at `091caa2`
([#3 handoff][i3-handoff]):

```text
OK   folds: 210417_MtErie, 210529_Carnation, 210924_FHL, 220109_Baker; never a test set: 210812_Hannegan
OK   no image of a test site-day in training, validation, or unlabelled manifests (176,555 image references checked)
OK   every test set holds every labelled frame of its site-day
OK   training, validation, and test are disjoint in every view
OK   label fractions nested: 1% in 5% in 10% in 100%, all drawn from training
OK   training and unlabelled frames are more than 250 frames from validation in the same clip (closest: 251 frames)
OK   76 manifests rebuilt byte for byte from seed 7
```

The first version of the check was not enough. It trusted fields the builder
had written, so a corrupted record with faked fields passed. A reviewer tried
thirteen corruptions and found it. The check now reads the clip and frame from
the image path ([#3 handoff][i3-handoff]). A later change makes `folds` refuse
a manifest made with `--collection`, and `check-folds` now prints whether its
source was full ([#45]). When the check failed, it once printed its summary
lines unmarked, so one could read as a pass. [#39] fixed that
([#39 handoff][i39-handoff]).

## Decisions and why

([folds review][folds-review], [decisions](../decisions.md))

- **Leave one site-day out, not one fixed test split.** Four site-days cannot
  spare several for a fixed test, and the claim is about an unseen site-day.
  Each labelled site-day is the test set of one fold. Report per fold, and as
  mean and spread.
- **Hannegan has no labels,** so it is never a test set and is unlabelled data
  in every fold.
- **Three label views** (both cameras, RGB only, thermal only), with the same
  test site-day in all three.
- **Validation is a whole clip where one exists,** the smallest of a training
  site-day, so neighbouring frames never sit on both sides. A single clip
  gives its last 15%, after the 250-frame gap.
- **One unlabelled pool per fold,** leaving out the test site-day and every
  validation frame, so pretraining never sees the test site.
- **Label fractions of 1, 5, 10 and 100%** are nested prefixes of seeded
  blocks of 10 consecutive labelled frames (seed 7). Random frames spread over
  every scene, which is not what a label shortage looks like.
- **Wording:** claims say "unseen site-day". The dataset holds earlier flights
  at two of the sites, and some of the same people may appear at more than one
  site ([#3 handoff][i3-handoff]).

## How to reproduce

After chapter 2's `prepare` (each command takes about ten seconds):

```bash
uv run aerial-search folds data/raw/wisard-full data/manifests/wisard-full
uv run aerial-search check-folds data/raw/wisard-full data/manifests/wisard-full
```

On 2026-10-01, from a branch, `check-folds` printed the seven lines above
after one more, `OK   source manifests: full`. A run takes a fold as
`--fold 220109_Baker`, for example. See chapter 5.

## What four site-days can and cannot support

Four test scores, each from one site on one day. They can show whether a
method beats its baseline everywhere or only at some sites. They cannot give a
confidence interval worth the name. So a claim reads "better at all four sites
by these margins", never "better on average with an error bar"
([folds review][folds-review]). Validation inside a site-day is optimistic, so
it is for choosing settings and never for quoting.

## What we would do differently

- **Test the check, not just the builder.** The reviewer's corruptions caught
  what a green check did not ([#3 handoff][i3-handoff]).
- **Measure before fixing a number.** The 50-frame gap was a guess.
  [`tools/frame_similarity_lags.py`](../../tools/frame_similarity_lags.py)
  gave 250.
- **Known and left alone:** a block of 10 labelled records can span a hole in
  the labels of up to 148 frame numbers ([#3 handoff][i3-handoff]).

Next: [chapter 5](05-making-runs-traceable.md).

[#3]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/3
[#39]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/39
[#45]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/45
[i2-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/2#issuecomment-5893694772
[i39-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/39#issuecomment-5937158938
[i3-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/3#issuecomment-5936845727
[folds-review]: ../site-folds-review.md
