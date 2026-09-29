"""Detection scorer checked against answers worked out by hand.

Conventions used in the working below:

- Boxes are (x1, y1, x2, y2) in continuous pixel coordinates, so a box's
  width is x2 - x1 and IoU = intersection area / union area.
- AP is COCO's 101-point interpolated AP: the mean, over recall levels
  r = 0.00, 0.01, ..., 1.00, of the highest precision reached at any recall
  >= r (0 when recall r is never reached).
- Recall at a false-alarm rate f is the best recall over score cutoffs whose
  false alarms divided by the number of images is at most f.
"""

import json
import math
from pathlib import Path

import pytest

from aerial_search.evaluation.detection import (
    GroundTruth,
    Prediction,
    evaluate_detections,
)

A = (0.0, 0.0, 10.0, 10.0)  # a 10 x 10 person
B = (100.0, 100.0, 110.0, 110.0)  # another 10 x 10 person, far from A


def truth(image_id, boxes, modality="rgb", flight="f1"):
    return GroundTruth(image_id=image_id, boxes=boxes, modality=modality, flight=flight)


def test_perfect_predictions_score_one() -> None:
    truths = [truth("i1", [A]), truth("i2", [B])]
    preds = [Prediction("i1", [A], [0.9]), Prediction("i2", [B], [0.8])]

    m = evaluate_detections(truths, preds).overall

    # Every detection is a true positive: precision 1 at every recall level.
    assert m.ap_iou25 == pytest.approx(1.0)
    assert m.ap_iou50 == pytest.approx(1.0)
    assert m.ap_coco == pytest.approx(1.0)
    # No false alarms, so every budget reaches full recall.
    assert m.recall_at_fppi == {0.01: 1.0, 0.1: 1.0, 1.0: 1.0}
    assert (m.n_images, m.n_ground_truth, m.n_predictions) == (2, 2, 2)


def test_no_predictions_score_zero() -> None:
    # The empty prediction list also covers pycocotools' loadRes, which
    # crashes on an empty list.
    report = evaluate_detections([truth("i1", [A])], [])

    m = report.overall
    assert m.ap_iou25 == 0.0
    assert m.ap_iou50 == 0.0
    assert m.recall_at_fppi == {0.01: 0.0, 0.1: 0.0, 1.0: 0.0}
    assert m.n_predictions == 0


def test_detections_on_image_without_people_are_false_alarms() -> None:
    truths = [truth("people", [A]), truth("empty", [])]
    # The false alarm on the empty image outscores the true detection.
    preds = [
        Prediction("empty", [A], [0.95]),
        Prediction("people", [A], [0.9]),
    ]

    m = evaluate_detections(truths, preds).overall

    # Ranked: FP (0.95), TP (0.9); 1 person.
    # recall = [0, 1], precision = [0, 1/2]; envelope = [1/2, 1/2].
    # Every recall level r in [0, 1] gets precision 1/2, so AP = 0.5.
    assert m.ap_iou25 == pytest.approx(0.5)
    # 2 images. Cutoffs: none -> (recall 0, FPPI 0); >=0.95 -> (0, 1/2);
    # >=0.9 -> (1, 1/2). Budgets 0.01 and 0.1 allow only the empty cutoff.
    assert m.recall_at_fppi == {0.01: 0.0, 0.1: 0.0, 1.0: 1.0}
    assert m.n_images_with_people == 1


def test_only_images_without_people_leave_ap_undefined() -> None:
    report = evaluate_detections(
        [truth("empty", [])], [Prediction("empty", [A], [0.5])]
    )

    m = report.overall
    # With no people, recall has no denominator: AP and recall are undefined.
    assert math.isnan(m.ap_iou25)
    assert math.isnan(m.ap_coco)
    assert all(math.isnan(v) for v in m.recall_at_fppi.values())
    assert (m.n_images, m.n_ground_truth, m.n_predictions) == (1, 0, 1)


def test_duplicate_detection_of_one_person_is_a_false_alarm() -> None:
    truths = [truth("i1", [A, B])]
    preds = [Prediction("i1", [A, A, B], [0.9, 0.8, 0.7])]

    m = evaluate_detections(truths, preds).overall

    # Ranked: A (0.9) TP, A again (0.8) FP because A is taken, B (0.7) TP.
    # recall = [1/2, 1/2, 1], precision = [1, 1/2, 2/3]
    # envelope = [1, 2/3, 2/3]
    # r = 0.00..0.50 (51 levels) -> 1; r = 0.51..1.00 (50 levels) -> 2/3
    # AP = (51 + 50 * 2/3) / 101 = 253 / 303
    assert m.ap_iou25 == pytest.approx(253 / 303)
    # 1 image. Cutoffs: 0.9 -> (1/2, 0); 0.8 -> (1/2, 1); 0.7 -> (1, 1).
    assert m.recall_at_fppi == {0.01: 0.5, 0.1: 0.5, 1.0: 1.0}


def test_primary_threshold_accepts_shift_that_iou_half_rejects() -> None:
    # A 12 x 12 person and a box shifted 3 px right and 3 px down.
    # Intersection 9 * 9 = 81; union 144 + 144 - 81 = 207; IoU = 0.391.
    truths = [truth("i1", [(0.0, 0.0, 12.0, 12.0)])]
    preds = [Prediction("i1", [(3.0, 3.0, 15.0, 15.0)], [0.9])]

    m = evaluate_detections(truths, preds).overall

    assert m.ap_iou25 == pytest.approx(1.0)  # 0.391 >= 0.25: a hit
    assert m.ap_iou50 == 0.0  # 0.391 < 0.5: a miss and a false alarm
    assert m.ap_coco == 0.0
    assert m.recall_at_fppi[1.0] == 1.0


def test_iou_equal_to_threshold_counts_as_match() -> None:
    # Box twice as tall: intersection 100, union 200, IoU exactly 0.5.
    truths = [truth("i1", [A])]
    preds = [Prediction("i1", [(0.0, 0.0, 10.0, 20.0)], [0.9])]

    m = evaluate_detections(truths, preds).overall

    assert m.ap_iou50 == pytest.approx(1.0)
    # COCO AP averages thresholds 0.50, 0.55, ..., 0.95; only 0.50 hits.
    assert m.ap_coco == pytest.approx(0.1)


def test_detection_matches_the_overlapping_person_it_fits_best() -> None:
    # Two overlapping 10 x 10 people, P at x 0-10 and Q at x 4-14.
    p, q = (0.0, 0.0, 10.0, 10.0), (4.0, 0.0, 14.0, 10.0)
    first = (3.0, 0.0, 13.0, 10.0)  # IoU with P = 70/130 = 0.54, Q = 90/110 = 0.82
    # `first` must take Q. If it took P, `second` (exactly P) would be left
    # with Q at IoU 60/140 = 0.43 < 0.5 and become a false alarm.
    preds = [Prediction("i1", [first, p], [0.9, 0.8])]

    m = evaluate_detections([truth("i1", [p, q])], preds).overall

    assert m.ap_iou50 == pytest.approx(1.0)


def test_small_multi_image_case_and_breakdowns() -> None:
    truths = [
        truth("i1", [A, B], modality="rgb", flight="fA"),
        truth("i2", [(20.0, 20.0, 30.0, 30.0)], modality="thermal", flight="fA"),
        truth("i3", [], modality="rgb", flight="fB"),
    ]
    preds = [
        Prediction("i1", [A, (200.0, 200.0, 210.0, 210.0)], [0.95, 0.6]),
        Prediction("i2", [(20.0, 20.0, 30.0, 30.0)], [0.8]),
        Prediction("i3", [(5.0, 5.0, 15.0, 15.0)], [0.85]),
    ]

    report = evaluate_detections(truths, preds)

    # Overall, 3 people. Ranked: 0.95 TP, 0.85 FP, 0.8 TP, 0.6 FP (B missed).
    # recall = [1/3, 1/3, 2/3, 2/3], precision = [1, 1/2, 2/3, 1/2]
    # envelope = [1, 2/3, 2/3, 1/2]
    # r = 0.00..0.33 (34 levels) -> 1; r = 0.34..0.66 (33 levels) -> 2/3;
    # r = 0.67..1.00 never reached -> 0.  AP = (34 + 22) / 101 = 56/101
    o = report.overall
    assert o.ap_iou25 == pytest.approx(56 / 101)
    # 3 images. Cutoffs: 0.95 -> (1/3, 0); 0.85 -> (1/3, 1/3);
    # 0.8 -> (2/3, 1/3); 0.6 -> (2/3, 2/3).
    assert o.recall_at_fppi == pytest.approx({0.01: 1 / 3, 0.1: 1 / 3, 1.0: 2 / 3})

    # RGB (i1, i3), 2 people. Ranked: 0.95 TP, 0.85 FP, 0.6 FP.
    # recall = [1/2, 1/2, 1/2]; envelope = [1, 1/2, 1/3]
    # r = 0.00..0.50 (51 levels) -> 1; above 0.5 never reached. AP = 51/101
    rgb = report.by_modality["rgb"]
    assert rgb.ap_iou25 == pytest.approx(51 / 101)
    # 2 images. Cutoffs: 0.95 -> (1/2, 0); 0.85 -> (1/2, 1/2); 0.6 -> (1/2, 1).
    assert rgb.recall_at_fppi == pytest.approx({0.01: 0.5, 0.1: 0.5, 1.0: 0.5})
    assert report.by_modality["thermal"].ap_iou25 == pytest.approx(1.0)

    # Flight fA (i1, i2), 3 people. Ranked: 0.95 TP, 0.8 TP, 0.6 FP.
    # recall = [1/3, 2/3, 2/3]; envelope = [1, 1, 2/3]
    # r = 0.00..0.66 (67 levels) -> 1; above 2/3 never reached. AP = 67/101
    fa = report.by_flight["fA"]
    assert fa.ap_iou25 == pytest.approx(67 / 101)
    # 2 images. Cutoffs: 0.95 -> (1/3, 0); 0.8 -> (2/3, 0); 0.6 -> (2/3, 1/2).
    assert fa.recall_at_fppi == pytest.approx({0.01: 2 / 3, 0.1: 2 / 3, 1.0: 2 / 3})
    # Flight fB has no people: AP undefined, but its detection is counted.
    fb = report.by_flight["fB"]
    assert math.isnan(fb.ap_iou25)
    assert (fb.n_images, fb.n_ground_truth, fb.n_predictions) == (1, 0, 1)


def test_recall_of_exactly_seven_tenths_reaches_level_070() -> None:
    people = [(20.0 * k, 0.0, 20.0 * k + 10.0, 10.0) for k in range(10)]
    preds = [Prediction("i1", people[:7], [0.9] * 7)]

    m = evaluate_detections([truth("i1", people)], preds).overall

    # 7 hits of 10, no false alarms: precision 1 up to recall 0.7.
    # Levels 0.00..0.70 (71 levels) -> 1; the rest are never reached.
    # AP = 71/101. (pycocotools' default grid puts level 0.70 one ulp above
    # 0.7 and would give 70/101.)
    assert m.ap_iou25 == pytest.approx(71 / 101)


def test_size_buckets_are_half_open_on_sqrt_area() -> None:
    eight = (0.0, 0.0, 8.0, 8.0)  # sqrt(area) = 8: in [8, 16), not [0, 8)
    six = (20.0, 20.0, 26.0, 26.0)  # sqrt(area) = 6: in [0, 8)
    truths = [truth("i1", [eight, six])]
    preds = [Prediction("i1", [eight], [0.9])]

    by_size = evaluate_detections(truths, preds).by_size

    assert by_size["tiny"].n_ground_truth == 1
    assert by_size["tiny"].ap_iou25 == pytest.approx(1.0)
    # The one very tiny person is missed; the detection belongs to the
    # 8 x 8 person, so it is neither a hit nor a false alarm here.
    assert by_size["very_tiny"].n_ground_truth == 1
    assert by_size["very_tiny"].ap_iou25 == 0.0
    assert by_size["very_tiny"].recall_at_fppi == {0.01: 0.0, 0.1: 0.0, 1.0: 0.0}
    assert by_size["small"].n_ground_truth == 0
    assert math.isnan(by_size["small"].ap_iou25)


def test_tied_scores_form_one_operating_point() -> None:
    # A hit and a false alarm with the same score cannot be separated by any
    # threshold, whichever order they arrive in.
    far = (50.0, 50.0, 60.0, 60.0)
    for boxes in ([A, far], [far, A]):
        preds = [Prediction("i1", boxes, [0.5, 0.5])]
        m = evaluate_detections([truth("i1", [A])], preds).overall
        # 1 image. The only non-empty cutoff is 0.5 -> (recall 1, FPPI 1).
        assert m.recall_at_fppi == {0.01: 0.0, 0.1: 0.0, 1.0: 1.0}


def test_rejects_predictions_for_unknown_image() -> None:
    with pytest.raises(ValueError, match="not in the ground truth"):
        evaluate_detections([truth("i1", [A])], [Prediction("i9", [A], [0.5])])


def test_rejects_duplicate_image_ids() -> None:
    with pytest.raises(ValueError, match="more than once"):
        evaluate_detections([truth("i1", [A]), truth("i1", [B])], [])


@pytest.mark.parametrize(
    "box",
    [(5.0, 0.0, 5.0, 10.0), (10.0, 0.0, 0.0, 10.0), (0.0, 0.0, math.nan, 10.0)],
)
def test_rejects_degenerate_boxes(box) -> None:
    with pytest.raises(ValueError, match="box"):
        truth("i1", [box])


def test_rejects_score_count_mismatch() -> None:
    with pytest.raises(ValueError, match="scores"):
        Prediction("i1", [A, B], [0.5])


def test_report_writes_json_with_null_for_undefined(tmp_path: Path) -> None:
    truths = [truth("i1", [A], flight="fA"), truth("i2", [], flight="fB")]
    report = evaluate_detections(truths, [Prediction("i1", [A], [0.9])])

    path = report.write_json(tmp_path / "run-1")

    assert path == tmp_path / "run-1" / "detection_metrics.json"

    def reject(constant: str) -> None:
        raise AssertionError(f"non-standard JSON constant {constant}")

    data = json.loads(path.read_text(), parse_constant=reject)
    assert data["overall"]["ap_iou25"] == pytest.approx(1.0)
    assert data["by_flight"]["fB"]["ap_iou25"] is None
    assert data["overall"]["recall_at_fppi"]["0.1"] == 1.0
    assert data["config"]["primary_iou"] == 0.25
