# Thermal input ablation: results

Does the frozen SigLIP 2 backbone, trained on photographs, need thermal frames
prepared differently? Three ways of feeding a single-channel thermal frame in
were compared on the thermal view, at 10% and 100% of the training labels, on
all four site-day folds, with the head, runner and scoring unchanged
(issue #68).

## Answer

No. Replicating the grey channel three times, the default, is as good as
anything tried. A learned input stem changed mean `ap_iou25` by −0.009 at 10%
and +0.007 at 100%, both within the spread across folds. Histogram
equalisation made detection worse: −0.050 at 10% and −0.137 at 100%, lower on
three of the four folds at each fraction. Thermal does not need input
adaptation at this stage. If it needs adapting, that is a job for the
backbone, the next epic, not for the input.

## The arms

| Arm | What changes | How it is trained |
|---|---|---|
| replicate (A) | nothing: the grey frame copied to three channels | the 2,000-step head from #66, on the existing cache |
| equalise (B) | PIL histogram equalisation of the grey frame, then replicate | the same 2,000-step recipe, on its own equalised cache |
| replicate-warm (control) | nothing | the A head trained 120 more steps on the cache |
| stem-warm (C) | a residual two-layer conv stem (3→16→3) before the frozen backbone, zero-initialised so step 0 equals A | the same A head plus the stem, trained 120 more steps through the frozen backbone |

A cold stem arm, trained like A from scratch, costs about 6 hours per run on
the laptop, because every step runs the full backbone forward and back. So the
stem starts from A's trained head and is compared with a control that gets the
same 120 extra steps without the stem. The comparison then measures the stem,
not the extra training. Both warm arms evaluate at steps 60 and 120 on the full
validation split and keep the better one.

## Results

Thermal, test `ap_iou25` / `ap_iou50` per fold, mean ± sd over the four folds,
and the mean per-fold change in `ap_iou25` against the arm's control
(replicate for equalise; replicate-warm for stem-warm).

### 10% of labels

| Arm | MtErie | Carnation | FHL | Baker | `ap_iou25` | `ap_iou50` | change |
|---|---|---|---|---|---|---|---|
| replicate | 0.229 / 0.010 | 0.001 / 0.000 | 0.121 / 0.011 | 0.165 / 0.008 | 0.129 ± 0.096 | 0.007 ± 0.005 | – |
| equalise | 0.205 / 0.017 | 0.004 / 0.001 | 0.036 / 0.002 | 0.073 / 0.001 | 0.079 ± 0.088 | 0.005 ± 0.008 | −0.050 ± 0.046 |
| replicate-warm | 0.269 / 0.019 | 0.001 / 0.001 | 0.119 / 0.012 | 0.258 / 0.020 | 0.162 ± 0.127 | 0.013 ± 0.009 | – |
| stem-warm | 0.274 / 0.020 | 0.001 / 0.000 | 0.112 / 0.009 | 0.226 / 0.020 | 0.153 ± 0.122 | 0.012 ± 0.009 | −0.009 ± 0.016 |

### 100% of labels

| Arm | MtErie | Carnation | FHL | Baker | `ap_iou25` | `ap_iou50` | change |
|---|---|---|---|---|---|---|---|
| replicate | 0.313 / 0.057 | 0.003 / 0.000 | 0.202 / 0.030 | 0.692 / 0.247 | 0.302 ± 0.290 | 0.083 ± 0.111 | – |
| equalise | 0.279 / 0.029 | 0.011 / 0.000 | 0.127 / 0.020 | 0.246 / 0.039 | 0.166 ± 0.122 | 0.022 ± 0.017 | −0.137 ± 0.209 |
| replicate-warm | 0.332 / 0.077 | 0.003 / 0.000 | 0.193 / 0.030 | 0.696 / 0.228 | 0.306 ± 0.293 | 0.084 ± 0.101 | – |
| stem-warm | 0.336 / 0.072 | 0.003 / 0.000 | 0.200 / 0.035 | 0.713 / 0.251 | 0.313 ± 0.300 | 0.090 ± 0.111 | +0.007 ± 0.007 |

Every run picks its step on the fold's full labelled validation split,
whatever its label fraction.

## Reading the results

- **Equalisation hurts.** In raw thermal a person is a warm spot on a cooler
  background. Equalisation spreads the intensities evenly, which lifts the
  background and flattens that contrast. The loss is largest where the
  replicate head was strongest (Baker at 100%: 0.692 to 0.246). Carnation is
  the exception, but every arm scores near zero there, so its gain means
  nothing.
- **The stem learns almost nothing useful in 120 steps.** Its per-fold
  changes go both ways at 10% (+0.005, 0.000, −0.007, −0.032) and are small
  and positive at 100% (+0.004, 0.000, +0.007, +0.017). With one seed and a
  per-fold spread of 0.12 to 0.30, a mean change of under 0.01 is not
  evidence either way. It does rule out a large, easy gain from adapting the
  input.
- **Extra training helps the 10% heads.** 120 more steps on the cache, the
  control, raised the 10% mean from 0.129 to 0.162 (Baker 0.165 to 0.258);
  the 100% mean barely moved (0.302 to 0.306). The #66 recipe may stop the
  small-label heads too early, so the bar at 1% to 10% may be set too low.
  This is tracked separately; it is why the stem had to be compared with the
  control and not with A.
- **Carnation stays near zero for every arm**, as in #66. Whatever is wrong
  with that held-out site-day is not the input handling.

## How these numbers were made

- 32 thermal runs, seed 7, one seed each, all `completed` and not scratch:
  - replicate: the #66 runs, `main` at `f93dc3c`. A re-run of thermal /
    MtErie / 10% from `main` at `f0af3c2` reproduced it exactly: the same
    `ap_iou25` (0.22935…) and a byte-identical `head.pt`.
  - equalise and replicate-warm: `main` at `f0af3c2`.
  - stem-warm: `main` at `dfe1a25`. The commits between `f0af3c2` and
    `dfe1a25` add the detector baseline (#89) and move the head's frame
    selection into a shared function unchanged; the review of #89 confirmed
    the move is verbatim.
- The equalised cache: 14,837 thermal frames, about 25 minutes, checked
  complete with `check-cache --camera thermal`.
- Stem-warm runs took about 23 to 33 minutes each. The laptop's GPU was shared
  with another project's training during this window, so these times are
  slower than an idle laptop. One stem run skipped one step for non-finite
  gradients (the fp16 loss scaling); none skipped more.
- Differences between the warm arms' recipes, listed by `head-table`, are the
  stem's own settings only: micro-batch 4 with exact people-weighted
  accumulation, loss scale 256, stem width 16, evaluation batch 16.

```bash
C=outputs/features/siglip2-base-naflex-1024tok
D=outputs/detection-head/siglip2-base-naflex-1024tok
uv run aerial-search cache-features siglip2-base-naflex --camera thermal --thermal-input equalise --part 1/2   # and 2/2
uv run aerial-search train-head thermal --fold $F --percent $P --input-handling equalise --cache $C-equalise
uv run aerial-search train-head thermal --fold $F --percent $P --cache $C --init-head $D/thermal-$F-${P}pct-seed7 --steps 120 --eval-every 60
uv run aerial-search train-head thermal --fold $F --percent $P --cache $C --init-head $D/thermal-$F-${P}pct-seed7 --input-handling stem --steps 120 --eval-every 60
uv run aerial-search head-table --ablation $D $D-equalise $D-warm $D-stem-warm --camera thermal --percent 10 --percent 100
```

## Limits

- One seed per run. The fold spread is as large as the mean, so only the
  equalisation result, consistent across folds and fractions, is firm.
- The stem was trained for 120 steps from a converged head. A stem trained
  from the start, for the full recipe, was not tried; it does not fit the
  laptop.
- Two input alternatives were tested. Others (a fixed colour map such as
  ironbow, per-frame normalisation, adapting the backbone) were not.
