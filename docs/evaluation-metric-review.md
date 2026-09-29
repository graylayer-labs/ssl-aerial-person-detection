# Evaluation metric review

How detectors are scored in this project, and why. The code is
`src/aerial_search/evaluation/detection.py`; the tests with hand-worked
answers are `tests/test_detection_evaluation.py`. Issue:
[#4](https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/4).

## What is reported

| Metric | Definition | Role |
|---|---|---|
| `ap_iou25` | Average precision where a detection counts as a hit if its IoU with an unmatched person is at least 0.25. | **Primary** |
| `recall_at_fppi` | The best recall reachable at a score cutoff whose false alarms per image are at most 0.01, 0.1, or 1, with hits judged at IoU 0.25. | The search team's number |
| `ap_iou50` | The same average precision with the IoU threshold at 0.5. | For comparison with other work |
| `ap_coco` | The mean of average precision over IoU 0.50, 0.55, ..., 0.95. | For comparison with other work |

Every metric is given overall, by modality, by flight, and by person size.
A group with no people has undefined AP and recall, written as `null`.

Average precision is COCO's 101-point interpolation: the mean, over recall
levels 0.00, 0.01, ..., 1.00, of the highest precision reached at that recall
or above, with 0 for levels never reached.

## Why AP at IoU 0.25 is the primary metric

People in aerial search footage are a few pixels across. AI-TOD, an aerial
tiny-object dataset, has a mean object size of 12.8 pixels ([Wang et al.,
2021](https://arxiv.org/abs/2110.13389)). At that size IoU punishes errors that
do not matter to a searcher. Worked from the definition:

| Person | Detection error | IoU | Hit at 0.5? | Hit at 0.25? |
|---|---|---|---|---|
| 12 x 12 | shifted 3 px right and 3 px down | 81 / 207 = 0.39 | no | yes |
| 8 x 8 | shifted 2 px right and 2 px down | 36 / 92 = 0.39 | no | yes |
| 8 x 8 | shifted 3 px right and 3 px down | 25 / 103 = 0.24 | no | no |
| 12 x 12 | box drawn 18 x 18 around it | 144 / 324 = 0.44 | no | yes |

A box two pixels off still puts a searcher's eyes on the right spot. At 0.5 it
is both a miss and a false alarm. The NWD paper makes the same point: a 6 x 6
object's IoU falls from 0.53 to 0.06 under a shift that moves a 36 x 36
object's IoU only from 0.90 to 0.65.

TinyPerson, the closest benchmark in purpose, evaluates at IoU 0.25 as well
as 0.5 and gives the reason directly: many tiny-person applications, such as
shipwreck search and rescue, care more about finding people than locating
them precisely ([Yu et al., WACV 2020](https://arxiv.org/abs/1912.10664)).
0.25 still rejects a detection that merely lands near a person: the third
row above fails it.

## Why recall at false alarms per image

A search team asks: if a person is in the frame, how likely is the system to
flag them, and how many false alarms per image must I accept for that? AP does
not answer this. Recall at fixed false alarms per image (FPPI) does. It is the
standard measure in pedestrian detection, where the Caltech benchmark
summarises miss rate over FPPI from 0.01 to 1 ([Dollár et al., TPAMI
2012](https://doi.org/10.1109/TPAMI.2011.155)). The three points reported
span that range.

Definition, as implemented:

- Sort all detections in the group by score. Each distinct score is a cutoff.
- At each cutoff, recall = hits / people, and FPPI = false alarms / images.
  Images count whether or not they contain people.
- Recall at FPPI f is the highest recall over cutoffs with FPPI <= f. Keeping
  no detections (recall 0, FPPI 0) is always allowed.

Detections with equal scores form one cutoff, because no threshold can keep one
and drop the other. Hits and false alarms come from the same pycocotools
matching that produces AP, so the two metrics never disagree about what a hit
is.

At FPPI 0.01 the estimate rests on few false alarms: on 500 test images it is
decided by the first 5. Treat it as noisy on small splits.

## Matching rules

These are pycocotools' rules. The tests pin each one.

- Within an image, detections are taken highest score first. Each takes the
  unmatched person with the highest IoU, provided that IoU is at least the
  threshold. IoU exactly equal to the threshold counts.
- A person is matched once. A second detection of the same person is a false
  alarm (a duplicate), unless another unmatched person overlaps it enough.
- When a detection overlaps two people, it takes the one with the higher IoU,
  not the first listed. Equal IoU goes to the person listed later.
- Every detection on an image with no people is a false alarm.
- For AP, equal scores are ordered by image, then by the order the model gave
  them (a stable sort). This can change AP when a hit and a false alarm share a
  score; with real-valued scores that is rare. FPPI is not affected.
- There is no cap on detections per image. pycocotools caps at 100 by default
  and silently drops the rest; the scorer sets the cap to the largest count
  present.

## Input format

- `GroundTruth(image_id, boxes, modality, flight)`, one per image, including
  images with no people. This list defines the images evaluated.
- `Prediction(image_id, boxes, scores)`, one per image at most. A missing image
  has no detections. A prediction for an image not in the ground truth is an
  error.
- Boxes are `(x1, y1, x2, y2)` in pixels, origin top-left, continuous
  coordinates with the far edge exclusive: a box over pixel columns 5 to 9 is
  `x1=5, x2=10`. Labels stored as inclusive pixel indices need 1 added to `x2`
  and `y2`. Boxes with zero or negative width or height are rejected.

The format depends on nothing from the model code, which will be rebuilt.

## Size buckets

On the square root of box area, half-open, following AI-TOD's edges:
`very_tiny` [0, 8), `tiny` [8, 16), `small` [16, 32), `medium_plus` [32, inf).
COCO's buckets would put nearly every person in "small". Inside a bucket,
people of other sizes are ignored, as are unmatched detections of other sizes
(the pycocotools rule). A person's bucket comes from the ground-truth box.

## Library choice

pycocotools, used directly.

- It accepts custom IoU thresholds, recall levels, area ranges and detection
  caps, and exposes its per-image matches (`evalImgs`), from which recall at
  FPPI is computed.
- It is a single small package with wheels for our platforms.

Considered and not used:

- **torchmetrics `MeanAveragePrecision`**: wraps pycocotools or
  faster-coco-eval, so it adds a dependency without removing one. Its area
  ranges are fixed to COCO's, its detection caps are a list of exactly three,
  and it exposes no per-image matches, so FPPI could not be computed from it
  ([source](https://github.com/Lightning-AI/torchmetrics/blob/master/src/torchmetrics/detection/mean_ap.py)).
- **Writing AP from scratch**: short, but a second implementation of a
  standard metric is where silent disagreements with published numbers come
  from.

Two pycocotools behaviours are corrected, each pinned by a test that fails
without the correction:

- Its recall levels come from `np.linspace`, which puts ten of them one float
  step above k/100 (0.35, 0.41, 0.47, 0.57, 0.69, 0.70, 0.82, 0.83, 0.94,
  0.95). A recall of exactly 0.7 then misses level 0.70. The scorer uses exact
  k/100. This can move AP by at most one level's precision divided by 101,
  compared with stock pycocotools.
- Its area ranges are closed at both ends, so an 8 x 8 person would fall in
  two buckets. The scorer steps each upper edge down by one float step, making
  buckets half-open.

## Considered and not used as the primary metric

- **AP at IoU 0.5 or COCO 0.5:0.95 as primary.** Too strict for people a few
  pixels across; see the table above. Both are still reported.
- **Normalised Wasserstein distance (NWD) as the matching measure.** Designed
  for label assignment, NMS and the loss, not evaluation. It needs a constant C
  that the authors tie to the dataset's mean object size, so scores would not
  compare across datasets ([Wang et al., 2021](https://arxiv.org/abs/2110.13389)).
  AI-TOD itself still evaluates with IoU-based AP.
- **Centre-distance matching.** Scale-free at a fixed pixel radius, but the
  radius is a new free parameter and no aerial person benchmark uses it, so
  results could not be compared.

## Judgement calls that could move a headline number

- The 0.25 threshold. At 0.5, AP on tiny people will be much lower.
- The FPPI points. Denominators include empty images, so a test split with
  more empty frames shows lower FPPI for the same detector.
- 101-point interpolation rather than the all-point area under the curve. A
  detector with precision 1 up to recall 0.5 scores 51/101, not 0.5.

## Sources

- Wang, Xu, Yang, Yu. A Normalized Gaussian Wasserstein Distance for Tiny
  Object Detection. 2021. <https://arxiv.org/abs/2110.13389>
- Yu, Gong, Jiang, Ye, Han. Scale Match for Tiny Person Detection. WACV 2020.
  <https://arxiv.org/abs/1912.10664>
- Dollár, Wojek, Schiele, Perona. Pedestrian Detection: An Evaluation of the
  State of the Art. TPAMI 2012. <https://doi.org/10.1109/TPAMI.2011.155>
- pycocotools `cocoeval.py`. <https://github.com/ppwwyyxx/cocoapi/blob/master/PythonAPI/pycocotools/cocoeval.py>
- torchmetrics `mean_ap.py`. <https://github.com/Lightning-AI/torchmetrics/blob/master/src/torchmetrics/detection/mean_ap.py>
