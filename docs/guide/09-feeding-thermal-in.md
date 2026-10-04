# 9. Feeding thermal in

*Last updated 2026-10-04 from issue [#68]. Its tooling issue, #86, is not
covered separately.*

## What we set out to do

SigLIP 2 learned from photographs. A thermal frame is a single-channel heat
map. Does the frozen backbone need thermal frames prepared differently? We
compared three ways to feed one in, on the thermal view, at 10% and 100% of
the labels, on all four folds, with the head and scorer unchanged
([results note][abl]).

| Arm | What changes |
|---|---|
| replicate | nothing: the grey channel copied three times (the default) |
| equalise | histogram equalisation first, on its own cache |
| stem | a small learned two-layer input stem before the frozen backbone |

We expected equalisation to help a little, since it is the usual "make thermal
look like a photo" step, and the stem to help a little more ([#68 handoff][i68-handoff]
gives the outcome; see "What we would do differently" for what we did not test).

## What we found

**No arm beat copying the grey channel.** Mean thermal `ap_iou25`
([#68 handoff][i68-handoff]):

| Arm | 10% | 100% |
|---|---|---|
| replicate | 0.129 | 0.302 |
| equalise | 0.079 (-0.050) | 0.166 (-0.137) |
| replicate-warm (control) | 0.162 | 0.306 |
| stem-warm | 0.153 (-0.009 vs control) | 0.313 (+0.007 vs control) |

`ap_iou50` and the per-fold numbers are in the [results note][abl].

- **Equalisation hurts.** It was lower on three of four folds at each fraction
  ([results note][abl]). In raw thermal a person is a warm spot on a cooler
  background. Equalisation lifts the background and flattens that contrast.
  This is the note's explanation; we did not test it.
- **The stem did nothing measurable.** Its changes, -0.009 and +0.007, are
  within the spread over folds ([results note][abl]).
- **The control was a finding in its own right.** 120 more steps lifted the 10%
  heads from 0.129 to 0.162 ([#68 handoff][i68-handoff]). Comparing the stem
  with the cold head would have credited it with that. This is why chapter 7
  ends with a check of whether the bar was set too low. It was not.
- **Carnation stays near zero for every arm,** as in chapter 7 ([#68 handoff][i68-handoff]).

## The mistakes

Review caught two bugs that would have biased the stem arm before any run
([#68 handoff][i68-handoff]: two reviewer passes, the first found two blockers).

1. The stem split each batch into micro-batches to fit memory, and weighted
   each by its frame count. The loss divides by the number of people in the
   batch it is given, so frame weights did not reproduce a full batch. The fix
   weights each micro-batch by its share of the batch's people
   ([decisions][decisions]).
2. The stem drew random numbers before the head was built, so its head started
   from different weights at the same seed as its control ([milestone note][milestone]).

All tests passed in both cases ([milestone note][milestone]).

## Decisions and why

- **The stem starts from the trained #66 head and is compared with a control
  given the same 120 extra steps without the stem.** A cold stem run costs about
  6 h on the laptop, because every step runs the whole backbone forward and
  back ([decisions][decisions]). The control separates "the stem helps" from
  "more steps help".
- **Equalisation is its own cache,** part of the cache's identity, so arms
  cannot be mixed ([decisions][decisions]).
- **Both warm arms pick their step on the full validation split.** A stride of
  40 for the stem arm was dropped because it would have selected on a different
  split from the control ([#68 handoff][i68-handoff]).
- **Channel replication stays the default** ([decisions][decisions]).

## How to reproduce it

Needs the thermal cache (chapter 6). The 32 runs took about 4.5 h of laptop
time in all, with the stem runs slowed by another project sharing the GPU
([#68 handoff][i68-handoff]). A re-run of one chapter-7 cell (thermal, MtErie,
10%) from a later `main` reproduced `ap_iou25` and a byte-identical `head.pt`
([#68 handoff][i68-handoff]). I did not re-train any arm. On 2026-10-04 I ran
the table command below against the finished runs, writing to a scratch file. It
printed the same numbers as the results note, with a warning that the arms come
from three commits.

```bash
C=outputs/features/siglip2-base-naflex-1024tok
D=outputs/detection-head/siglip2-base-naflex-1024tok
uv run aerial-search cache-features siglip2-base-naflex --camera thermal --thermal-input equalise --part 1/2   # and 2/2
uv run aerial-search train-head thermal --fold $F --percent $P --input-handling equalise --cache $C-equalise
uv run aerial-search train-head thermal --fold $F --percent $P --cache $C --init-head $D/thermal-$F-${P}pct-seed7 --input-handling stem --steps 120 --eval-every 60
```

```bash
uv run aerial-search head-table --ablation $D $D-equalise $D-warm $D-stem-warm --camera thermal --percent 10 --percent 100
```

The control's command is in the [results note][abl].

## What we would do differently

- Train a stem from the start for the full recipe. It did not fit the laptop
  ([results note][abl]).
- Try other inputs: a fixed colour map, per-frame normalisation, or adapting
  the backbone. None was tested ([results note][abl]).
- Time the stem runs on an idle laptop ([#68 handoff][i68-handoff]).

[#68]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/68
[i68-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/68#issuecomment-5972858571
[abl]: ../thermal-input-ablation.md
[decisions]: ../decisions.md
[milestone]: ../milestones/off-the-shelf-bar.md
