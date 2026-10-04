# 8. The baseline that won

*Last updated 2026-10-04 from issue [#67]. Its tooling issue, #88, is not
covered separately.*

## What we set out to do

"A frozen foundation model with few labels" means little unless it beats the
ordinary approach: an off-the-shelf detector fine-tuned on the same labelled
frames, scored by the same code, on every fold, camera and label fraction
([results note][base-results]).

The premise was that a frozen foundation model gives a head start when labels
are scarce, because pretrained features should matter most there
([results note][base-results]). That is not what happened.

## What we found

**At the same input size, the fine-tuned detector beats the frozen head at 1%
to 10% of labels, on both cameras.** At 100% they are level. The detector is
a COCO-pretrained Faster R-CNN with a MobileNetV3 backbone. Mean `ap_iou25`
([#67 handoff][i67-handoff]):

| Labels | RGB head | RGB detector | Thermal head | Thermal detector |
|---|---|---|---|---|
| 1% | 0.044 | 0.064 | 0.065 | 0.153 |
| 5% | 0.094 | 0.152 | 0.132 | 0.228 |
| 10% | 0.113 | 0.163 | 0.129 | 0.256 |
| 100% | 0.250 | 0.204 | 0.302 | 0.294 |

`ap_iou50` and the per-fold numbers are in the [results note][base-results].
The detector's `ap_iou50` is up to 0.18; the head's is under 0.09 at every
fraction, so the detector's boxes are tighter ([results note][base-results]).

- **It is not a one-fold fluke.** At 1% to 10% the detector is ahead in all six
  camera-and-fraction cells, and in 22 of 24 per-fold cells. The exceptions
  are RGB MtErie at 1% and RGB Baker at 10% ([results note][base-results]).
- **At 100% the difference is inside the spread.** RGB 0.204 against 0.250,
  thermal 0.294 against 0.302; the head's lead comes from one fold, Baker
  ([results note][base-results]).
- **The detector did not win by seeing more.** It reads the same resized image,
  and its finest feature map is coarser than the head's grid: a 32-pixel
  stride against 16-pixel cells ([results note][base-results]).
- **Resolution matters more than either method.** One run on the 4K frame
  (RGB, MtErie, 100%) scored `ap_iou25` / `ap_iou50` of 0.779 / 0.448, against
  0.213 / 0.065 at the shared size ([#67 handoff][i67-handoff]). It is one run.
  The other seven full-resolution runs were dropped: the first took 51
  minutes against a 30-minute limit ([#67 handoff][i67-handoff]).

## The mistakes

**The reviewer found a bug no test could.** The anchors gave 3 shapes per
location, but the pretrained proposal head predicts 15 ([results note][base-results]).
The loss then indexed the wrong outputs, and about 80% of them were never
trained ([milestone note][milestone]). Every test passed. Only building the
model and comparing shapes showed it. The fix was to scale the anchors down to
tiny people and keep the count the pretrained head expects
([results note][base-results]). The reviewer found two blockers in all. The
other was a default to the GPU (MPS), where Faster R-CNN hung or diverged
([#67 handoff][i67-handoff]). The milestone note says either bug would have tilted a
result towards the conclusion we expected ([milestone note][milestone]).

## Decisions and why

- **The fair row is at the head's input size** (672x384 RGB, 560x448 thermal).
  Full resolution is a second row, because a detector at native size would win
  on resolution alone ([decisions][decisions]).
- **MobileNetV3, not ResNet-50, on the CPU.** ResNet-50 costs about 4 s per
  step, about 8 h per resolution for the grid. On MPS the detector hung or
  reached a loss of 7e7 ([decisions][decisions]).
- **The comparison refuses runs that saw different frames.** Same seed, same
  manifests ([results note][base-results]).
- **The fine-tuned detector is the bar later epics must beat,** not the frozen
  head ([decisions][decisions]).

## How to reproduce it

The 32 runs took six hours on the CPU, overnight, from `main` at `223dc31`, all
`completed` and not scratch ([results note][base-results]). I did not retrain.
On 2026-10-04 I ran the comparison against the finished runs, writing to a
scratch file. It printed the same tables as the results note.

```bash
uv run aerial-search train-baseline <rgb|thermal> --fold <site-day> --percent <1|5|10|100> --device cpu
uv run aerial-search train-baseline rgb --fold 210417_MtErie --percent 100 --device cpu --input native
uv run aerial-search compare-table head=outputs/detection-head/siglip2-base-naflex-1024tok \
  baseline=outputs/detection-baseline/fasterrcnn_mobilenet_v3_large_fpn-cache
```

## What we would do differently

- Run the ResNet-50 check row. It was planned in `decisions.md` and not run
  ([#67 handoff][i67-handoff]).
- Train the baseline longer: validation was still rising at step 300, so it is
  if anything under-trained ([results note][base-results]).
- Test the frozen head on tiled full-resolution crops, suggested on the issue
  and not yet run ([#67 handoff][i67-handoff]).
- Give the baseline the same validation frames as the head. It selects its step
  on 100 evenly spaced frames, the head on all of them ([results note][base-results]).

[#67]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/67
[i67-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/67#issuecomment-5976496144
[base-results]: ../supervised-baseline-results.md
[decisions]: ../decisions.md
[milestone]: ../milestones/off-the-shelf-bar.md
