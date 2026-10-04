# 7. A detection head on frozen features

*Last updated 2026-10-04 from issues [#66], [#91].*

## What we set out to do

Train a small person detector on the cached SigLIP 2 features, per camera,
fold and label fraction, and report `ap_iou25` beside `ap_iou50`. This is the
first measured result of the project, and the first bar ([#66 handoff][i66-handoff]).

## What we found

Mean test `ap_iou25` / `ap_iou50` over the four held-out site-days, one seed
per run ([#66 handoff][i66-handoff]):

| Labels | RGB | Thermal |
|---|---|---|
| 1% | 0.044 / 0.001 | 0.065 / 0.001 |
| 5% | 0.094 / 0.004 | 0.132 / 0.007 |
| 10% | 0.113 / 0.006 | 0.129 / 0.007 |
| 100% | 0.250 / 0.056 | 0.302 / 0.083 |

Per-fold tables, with the spread and the split by person size, are in the
[results note][head-results].

- **The bar is low.** Before running we expected RGB `ap_iou25` of 0.05 to 0.2
  and thermal of 0.2 to 0.5 ([results note][head-results]). Thermal landed in
  its range and RGB just above it. We also expected thermal `ap_iou50` to sit
  near `ap_iou25`. It does not: 0.083 against 0.302 at 100%.
- **Boxes are loose and small people are missed.** People under 16 px score
  zero in RGB at every fraction ([results note][head-results]).
- **The site matters more than the label count.** At 100% the folds range from
  0.086 to 0.540 in RGB and 0.003 to 0.692 in thermal, and the spread over
  folds is as large as the mean ([results note][head-results]).
- **Thermal with Carnation held out fails outright:** 0.003 at 100%, while
  validation reached 0.51 in a scratch run. Of that site's 1,714 thermal test
  people, 1,615 are under 16 px ([results note][head-results]). We did not
  explain it further.
- **More labels sometimes scored lower.** RGB FHL scores 0.082 at 5% and 0.045
  at 10%. This is one seed at small fractions, which is noisy
  ([results note][head-results]).

**Two surprises from building it.**
- The 3840x2160 RGB frames are all of MtErie, where a feature cell
  covers 183 x 180 px. For most RGB frames (1920x1080) it is 91 x 90 px
  ([design note][design]). A "very tiny" RGB result exists for only 2 of the 4
  folds ([results note][head-results]).
- The "1% of labels" row is less scarce than it sounds. The best step is
  chosen on the fold's full validation split at every fraction, so RGB with
  MtErie held out trains on 70 frames at 1% and selects on 1,339
  ([design note][design]). We kept it so the fractions stay comparable, and
  said so beside the table ([#66 handoff][i66-handoff]).

## Was the head under-trained? (#91)

The matched control in the thermal ablation (chapter 9) lifted the 10% thermal
mean from 0.129 to 0.162 ([#91][i91]). That looked as if the bar was set too
low, and every later epic is measured against it. So we read the training
curves first. At 1% to 10%, 18 of 24 runs picked step 250, the first
evaluation, and validation then declined ([#91 handoff][i91-handoff]).

We re-ran those 24 runs with step selection every 25 steps. The test mean
`ap_iou25` changed by between -0.005 and +0.010 ([#91 handoff][i91-handoff]).
The heads overfit within 25 to 150 steps on 30 to 700 labelled frames. The
control's gain came from a restarted schedule plus the best of two noisy
evaluations ([#91 handoff][i91-handoff]). We kept the original recipe.

## Decisions and why

- **A CenterNet-style head on a grid four times finer than the features,**
  made by pixel shuffle. One feature cell is 37 px (thermal) to 183 px (4K RGB)
  and a person is smaller, so the head must say where in the cell the person
  is ([decisions][decisions]).
- **Best step on the full validation split** (above).
- **Review before results.** One reviewer pass found no validity blockers
  ([#66 handoff][i66-handoff]).

## How to reproduce it

Needs the cache from chapter 6. On 2026-10-04 I ran the table command against
the finished runs in the main checkout, writing to a scratch file. It printed
the same tables as the results note. I did not retrain: the 32 runs took about
80 minutes ([#66 handoff][i66-handoff]).

```bash
uv run aerial-search train-head <rgb|thermal> --fold <site-day> --percent <1|5|10|100>
uv run aerial-search head-table outputs/detection-head/siglip2-base-naflex-1024tok
```

The 32 runs came from `main` at `f93dc3c`, all `completed` and not scratch
([#66 handoff][i66-handoff]).

## What we would do differently

- Shrink the validation split with the fraction, so the 1% row is honest about
  scarcity. It was left open ([#66 handoff][i66-handoff]).
- Run more than one seed. Seeds are an open item on the epic
  ([#66 handoff][i66-handoff]).

[#66]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/66
[#91]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/91
[i66-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/66#issuecomment-5954632613
[i91-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/91#issuecomment-5976931108
[i91]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/91
[head-results]: ../detection-head-results.md
[design]: ../detection-head-design.md
[decisions]: ../decisions.md
