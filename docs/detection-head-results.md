# Detection head on frozen SigLIP 2 features: results

The first measured result of the "Off-the-shelf bar" epic: how well a small
head finds people on features from a frozen, unadapted SigLIP 2 model, at
1%, 5%, 10% and 100% of the training labels. Design and limits are in
`detection-head-design.md`.

## How these numbers were made

- 32 runs: 2 cameras × 4 folds × 4 label fractions, seed 7, one seed each.
- All from `main` at commit `f93dc3c`, clean tree, every `run.json`
  `completed` and not scratch. 2 to 3.5 minutes per run on the laptop.
- Each fold holds out one site-day as the test set. Scores are on that
  site-day only.

```bash
uv run aerial-search train-head <rgb|thermal> --fold <site-day> --percent <1|5|10|100>
uv run aerial-search head-table outputs/detection-head/siglip2-base-naflex-1024tok
```

**Read the label fractions with care.** Every run picks its best step on the
fold's full labelled validation split. "1% of labels" means 1% of the
training labels plus all validation labels (RGB, test site-day MtErie: 70
training frames at 1%, 1,339 validation frames).

## RGB

Test `ap_iou25` / `ap_iou50` per fold, then mean ± sample sd over the four
folds. FPPI is false positives per image.

| labels | MtErie | Carnation | FHL | Baker | ap_iou25 | ap_iou50 | recall @0.1 FPPI | recall @1 FPPI |
|---|---|---|---|---|---|---|---|---|
| 1% | 0.031 / 0.001 | 0.079 / 0.003 | 0.026 / 0.002 | 0.038 / 0.001 | 0.044 ± 0.024 | 0.001 ± 0.001 | 0.016 ± 0.015 | 0.073 ± 0.032 |
| 5% | 0.062 / 0.001 | 0.089 / 0.004 | 0.082 / 0.009 | 0.144 / 0.004 | 0.094 ± 0.035 | 0.004 ± 0.003 | 0.024 ± 0.014 | 0.137 ± 0.026 |
| 10% | 0.077 / 0.002 | 0.115 / 0.008 | 0.045 / 0.002 | 0.216 / 0.012 | 0.113 ± 0.075 | 0.006 ± 0.005 | 0.029 ± 0.016 | 0.155 ± 0.047 |
| 100% | 0.226 / 0.030 | 0.150 / 0.026 | 0.086 / 0.007 | 0.540 / 0.163 | 0.250 ± 0.201 | 0.056 ± 0.072 | 0.094 ± 0.051 | 0.304 ± 0.166 |

By person size (square root of box area in pixels: very tiny under 8, tiny
8–16, small 16–32, medium-plus 32 and over), mean over the n folds that have
people of that size:

| labels | very tiny | tiny | small | medium-plus |
|---|---|---|---|---|
| 1% | 0.000 / 0.000 (n=2) | 0.000 / 0.000 (n=2) | 0.020 / 0.000 (n=3) | 0.068 / 0.002 (n=4) |
| 5% | 0.000 / 0.000 (n=2) | 0.000 / 0.000 (n=2) | 0.028 / 0.002 (n=3) | 0.127 / 0.006 (n=4) |
| 10% | 0.000 / 0.000 (n=2) | 0.000 / 0.000 (n=2) | 0.011 / 0.000 (n=3) | 0.154 / 0.008 (n=4) |
| 100% | 0.000 / 0.000 (n=2) | 0.003 / 0.000 (n=2) | 0.034 / 0.005 (n=3) | 0.299 / 0.063 (n=4) |

## Thermal

| labels | MtErie | Carnation | FHL | Baker | ap_iou25 | ap_iou50 | recall @0.1 FPPI | recall @1 FPPI |
|---|---|---|---|---|---|---|---|---|
| 1% | 0.063 / 0.001 | 0.000 / 0.000 | 0.028 / 0.003 | 0.168 / 0.002 | 0.065 ± 0.073 | 0.001 ± 0.001 | 0.011 ± 0.008 | 0.080 ± 0.069 |
| 5% | 0.177 / 0.004 | 0.001 / 0.000 | 0.076 / 0.012 | 0.276 / 0.012 | 0.132 ± 0.120 | 0.007 ± 0.006 | 0.034 ± 0.023 | 0.161 ± 0.123 |
| 10% | 0.229 / 0.010 | 0.001 / 0.000 | 0.121 / 0.011 | 0.165 / 0.008 | 0.129 ± 0.096 | 0.007 ± 0.005 | 0.042 ± 0.030 | 0.167 ± 0.116 |
| 100% | 0.313 / 0.057 | 0.003 / 0.000 | 0.202 / 0.030 | 0.692 / 0.247 | 0.302 ± 0.290 | 0.083 ± 0.111 | 0.126 ± 0.130 | 0.360 ± 0.294 |

| labels | very tiny | tiny | small | medium-plus |
|---|---|---|---|---|
| 1% | 0.000 / 0.000 (n=2) | 0.079 / 0.000 (n=4) | 0.033 / 0.002 (n=4) | 0.125 / 0.003 (n=4) |
| 5% | 0.000 / 0.000 (n=2) | 0.072 / 0.000 (n=4) | 0.088 / 0.004 (n=4) | 0.277 / 0.016 (n=4) |
| 10% | 0.000 / 0.000 (n=2) | 0.089 / 0.004 (n=4) | 0.096 / 0.007 (n=4) | 0.321 / 0.031 (n=4) |
| 100% | 0.000 / 0.000 (n=2) | 0.089 / 0.006 (n=4) | 0.287 / 0.054 (n=4) | 0.482 / 0.163 (n=4) |

## What the numbers say

1. **The bar is low.** With every training label, mean `ap_iou25` is 0.25
   (RGB) and 0.30 (thermal). The design note expected 0.05–0.2 for RGB and
   0.2–0.5 for thermal before any run. Thermal landed inside its range and
   RGB just above. The note also expected thermal `ap_iou50` to sit close
   to `ap_iou25`; it does not (0.08 against 0.30).
2. **Labels matter a great deal.** From 100% to 1% of training labels the
   mean falls from 0.25 to 0.04 (RGB) and from 0.30 to 0.07 (thermal). This
   gap is what later epics try to close with unlabelled footage.
3. **The site matters more than the label count.** At 100% labels the folds
   range from 0.09 to 0.54 (RGB) and 0.003 to 0.69 (thermal). The spread
   over folds is as large as the mean. One pooled number would have hidden
   this.
4. **Small people are not found.** People under 16 px score zero in RGB at
   every fraction, where one feature cell covers about 91 px of a
   1920-wide frame. Thermal, with 36 px cells, reaches 0.09 on 8–16 px
   people and zero under 8 px.
5. **Boxes are loose.** `ap_iou50` is at most about a third of `ap_iou25`
   (Baker, the best fold) and usually far less. The head places people roughly and sizes them poorly.
6. **Thermal with Carnation held out fails outright** (0.003 at 100%). In a
   scratch run of the same setting, validation reached 0.51 while test
   stayed at 0.003; both go through the same scoring code. Of that site's
   1,714 thermal test people, 1,615 are under 16 px, 14% share a sub-cell
   with another person and a further 26% cannot survive the peak test (see
   "Limits" in the design note). Small, crowded people at an unseen site.

## What not to conclude

- **One seed.** Differences of a few hundredths are not evidence. RGB FHL
  scores 0.082 at 5% and 0.045 at 10%; thermal Baker 0.276 at 5% and 0.165
  at 10%. More labels did not hurt; one seed at small fractions is noisy,
  as issue #3 found earlier. Seeds are an open item on the epic.
- **Not a ceiling for SigLIP 2.** The features were pooled 2×2 at a
  1,024-token budget to fit the laptop. A larger token budget or no pooling
  gives smaller cells and may help small people.
- **Not a comparison between cameras.** RGB and thermal test sets differ in
  frames, people and sizes.

## Step selection check (#91)

At 1% to 10% of labels most of the runs above pick step 250, the first
evaluation, and validation falls from there. So the heads peak early and
then overfit; they are not under-trained. To see whether the coarse
evaluation grid understated the bar, the 24 runs at 1%, 5% and 10% were
repeated with 500 steps and an evaluation every 25 steps, from `main` at
`223dc31` (all `completed`, not scratch, `outputs/head-eval25`).

Most runs now pick a step between 25 and 150. Test scores barely move:

| mean `ap_iou25` / `ap_iou50` | RGB, 2,000 steps, every 250 | RGB, 500 steps, every 25 | thermal, 2,000 steps, every 250 | thermal, 500 steps, every 25 |
|---|---|---|---|---|
| 1% | 0.044 / 0.001 | 0.051 / 0.002 | 0.065 / 0.001 | 0.063 / 0.002 |
| 5% | 0.094 / 0.004 | 0.089 / 0.006 | 0.132 / 0.007 | 0.136 / 0.006 |
| 10% | 0.113 / 0.006 | 0.112 / 0.006 | 0.129 / 0.007 | 0.139 / 0.010 |

Every change is within the spread over folds. The bar stands. The rise from
0.129 to 0.162 that the matched control showed in #68 (a restarted schedule,
best of two noisy evaluations) does not come from catching an earlier peak.
