# A frozen foundation model lost to an ordinary detector when labels were few

*2026-10-04 · Milestone: Off-the-shelf bar · Draft for the owner to edit*

We are building a person detector for search and rescue from drone footage,
with few labels. The idea was that a large pretrained model, SigLIP 2, kept
frozen, would give a head start when labels are scarce. We measured it. At the
same input size, an ordinary COCO-pretrained detector fine-tuned on the same
labels beat it at 1%, 5% and 10% of the labels, on both the RGB and the thermal
camera, and tied it at 100% ([supervised-baseline results][base-results]).
That is a negative result for our own premise, and it sets the bar for
everything we try next.

![Mean test AP over four held-out site-days, frozen head against fine-tuned detector, at 1%, 5%, 10% and 100% of labels.](../figures/off-the-shelf-bar.svg)

## The result

Every number is `ap_iou25` / `ap_iou50`, a mean over four folds. Each fold
tests on one site and day never seen in training. One seed per run
([milestone note][milestone]).

| Labels | RGB, frozen head | RGB, fine-tuned detector | Thermal, frozen head | Thermal, fine-tuned detector |
|---|---|---|---|---|
| 1% | 0.044 / 0.001 | 0.064 / 0.009 | 0.065 / 0.001 | 0.153 / 0.072 |
| 5% | 0.094 / 0.004 | 0.152 / 0.051 | 0.132 / 0.007 | 0.228 / 0.112 |
| 10% | 0.113 / 0.006 | 0.163 / 0.046 | 0.129 / 0.007 | 0.256 / 0.137 |
| 100% | 0.250 / 0.056 | 0.204 / 0.060 | 0.302 / 0.083 | 0.294 / 0.176 |

- **We expected the opposite.** The premise was that pretrained features would
  matter most when labels are fewest ([supervised-baseline results][base-results]).
- **The direction holds fold by fold.** At 1% to 10% the detector is ahead in
  all six camera-and-fraction cells and in 22 of 24 per-fold cells
  ([supervised-baseline results][base-results]). Thermal at 10%, per fold
  (MtErie, Carnation, FHL, Baker): the head scores 0.229 / 0.010, 0.001 / 0.000,
  0.121 / 0.011 and 0.165 / 0.008. The detector scores 0.311 / 0.129,
  0.002 / 0.000, 0.186 / 0.078 and 0.527 / 0.341 ([same note][base-results]).
- **The spread is as large as some means.** At 100% the two are level, and the
  head's lead there comes from one fold, Baker ([same note][base-results]).
  Carnation scores near zero in thermal for every method
  ([milestone note][milestone]). Four site-days is a small test, and one seed
  is a small sample.
- **It is not because the detector sees more.** It reads the same resized
  image, and its finest feature map is coarser than the head's grid
  ([same note][base-results]).
- **Resolution matters more than either.** One run on the full 4K frame
  scored 0.779 / 0.448 on one site-day, against 0.213 / 0.065 at the shared
  input size ([#67 handoff][i67-handoff]). It is one run.
- **We checked that the head was not just under-trained.** Finer choice of
  training step moved its mean `ap_iou25` by between -0.005 and +0.010
  ([#91 handoff][i91-handoff]). It overfits within 25 to 150 steps.
- **Thermal needs no special input handling.** Histogram equalisation made it
  worse (-0.050 at 10%, -0.137 at 100% in mean `ap_iou25`), and a learned input
  stem was within noise of its control ([#68 handoff][i68-handoff]).

Two bugs were caught by review, not tests. In the detector, the anchors gave 3
shapes per location while the pretrained head predicts 15, so about 80% of the
outputs were never trained. In the thermal stem arm, batches were weighted by
frames while the loss divides by people. Every test passed in both cases, and
either bug would have tilted a result towards the conclusion we expected
([milestone note][milestone]).

## What it means for search and rescue

For a team with few labelled flights, the lesson is practical: start from an
ordinary fine-tuned detector, and feed it the highest resolution you can, since
people a few pixels wide vanish when a frame is shrunk. A frozen foundation
model is not a shortcut here, at least not at this input size. This does not
show that foundation models are useless, only that this one, frozen, did not
help. Whether one helps once it can adapt is the next question. The result says
nothing about sites or cameras outside these four site-days.

## The detail

The step-by-step account, with the commands and the mistakes, is in the
[follow-along guide](../guide/README.md): chapters
[7, the head](../guide/07-a-head-on-frozen-features.md),
[8, the baseline](../guide/08-the-baseline-that-won.md) and
[9, thermal input](../guide/09-feeding-thermal-in.md).

[milestone]: ../milestones/off-the-shelf-bar.md
[base-results]: ../supervised-baseline-results.md
[i67-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/67#issuecomment-5976496144
[i68-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/68#issuecomment-5972858571
[i91-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/91#issuecomment-5976931108
