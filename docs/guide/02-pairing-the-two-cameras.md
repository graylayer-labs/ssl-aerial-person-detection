# 2. Pairing the two cameras

*Last updated 2026-10-01 from issues [#1], [#2], [#38] and [#39].*

## What we set out to do

The project's central idea is that an RGB frame and a thermal frame of the same
moment are a free training signal. That only works if each RGB frame is paired
with the right thermal frame. Two manifest sets of pairs existed on disk and
they disagreed ([#2]):

| Manifest set | All pairs | Labelled |
|---|---|---|
| `data/manifests/processed/wisard-full` | 16,459 | 7,359 |
| `data/manifests/wisard-full` | 8,759 | 4,021 |

The README and the exploration notebook quoted the first. The task was to find
out which was right, check alignment by eye, fix the code, and keep one set.

## What we found

**Both sets were wrong.** The reviewers reproduced both totals exactly by
running the two old versions of the code on the raw data
([pairing review][pairing-review]).

- The first set paired by position: the k-th RGB frame with the k-th thermal
  frame. It included the Airfield flight, 1,620 pairs, whose two cameras
  number frames at different rates. It also slipped where one camera skipped
  a frame: in `Carnation_0025` pairs after RGB frame 654 are up to 140 frame
  numbers apart ([pairing review][pairing-review]).
- The second set came from a parser that read only 5 or 6 digit frame numbers.
  Eight-digit names were not parsed, seven directory pairs collapsed to one
  arbitrary pair each, and three produced none ([pairing review][pairing-review]).

The parser bug was found while fixing the lint failures of [#1]. About 53% of
image files had names it could not read, and it raised no error
([#2 finding][i2-finding]). Files it could not read all landed on one key,
`None`, so a whole directory collapsed to one wrong pair. The counts in that
finding (39,226 files with 8 digit numbers, 52,388 with 5) include two copies
of the dataset, which [#7] later removed. The 53% is unaffected
([#7 finding][i7-finding]).

**The fixed rule** ([pairing review][pairing-review]):

- Only 17 listed directory pairs are paired. The camera writes the RGB and
  thermal video of one recording as consecutive clip numbers, so
  `..._VIS_0003` goes with `..._IR_0004`.
- Frame i of RGB pairs with frame i plus an offset of thermal. The offset is 0
  everywhere except `MtErie_0003`, where it is 1.
- The run stops on a missing directory, a duplicate frame number, a name with
  no frame number, or a pair that shares less than 95% of its frame numbers.
  The lowest share in the data is 907 of 909.

**The result:** 14,834 pairs, 5,739 labelled in both cameras. A further 6,658
are labelled in one camera only (3,352 RGB, 3,306 thermal), and 2,437 in
neither. The per-camera manifests carry 9,096 labelled RGB frames and 9,048
thermal ([pairing review][pairing-review], [#2 handoff][i2-handoff]).

**What was left out.** The Airfield flight (1,620 RGB and 6,874 thermal
frames). Its cameras run at different rates: the motion signals match only
when thermal frame = 1.834 x RGB frame + 6 to 9. One Baker thermal directory
(609 frames) has no RGB partner in the dataset ([pairing review][pairing-review]).

**Pairs are not exact.** The WiSARD paper says the two cameras drift, by "one
or two image" differences. Frames are 0.2 s apart, so pairs are 0 to 2 frames,
or 0 to 0.4 s, apart. We accepted that and fitted no per-clip correction,
because the tool that measures lag cannot choose between neighbouring lags
(for Baker, r is 0.74 at lag -1 and 0.77 at lag 0)
([pairing review][pairing-review], [#2 handoff][i2-handoff]).

## How we checked it

Three checks, each weaker alone ([pairing review][pairing-review]):

1. **Camera motion.** A pan moves both images at once, so the frame-to-frame
   shift is a signal the two cameras share. The best-matching lag is within two
   frames for the right clips. As a control, all 82 wrong RGB and thermal
   directory pairs from the same days score at most r=0.16 within two frames of
   lag 0.
2. **Clip numbers.** A test enforces that each thermal clip is the RGB clip
   plus one. It rejects all 115 wrong pairings of RGB and thermal directories
   on the same days.
3. **Contact sheets.** One image per clip, with RGB beside thermal at the
   start, middle and end. In all 17 the same people and terrain appear in
   both. The owner looked at them and accepted the pairing ([#2 handoff][i2-handoff]).

## Decisions and why

- **A listed set of directory pairs, not grouping by site name.** Position
  pairing slips where frames are missing, and cannot see that the Airfield
  cameras run at different rates ([decisions](../decisions.md)).
- **Accept pairs up to two frames apart.** Correcting per clip would fit noise.
- **Correct `MtErie_0003` by one frame.** Its numbering starts at 0 for RGB and
  1 for thermal.
- **Use the dataset's boxes as they are** ([#2 handoff][i2-handoff]).
- **Report and stop on anything odd.** Unparseable names and duplicate numbers
  raise an error. Nothing is paired silently.

## How to reproduce

On a clone with the dataset (chapter 1):

```bash
uv run aerial-search prepare data/raw/wisard-full --output data/manifests/wisard-full
```

A normal `prepare` is refused from a dirty tree or a commit off `origin/main`
and checks the raw files against the pinned list first (chapter 5). Expected
output. We reproduced it on 2026-10-01 from a branch, with `--scratch` and an
output path outside the repository: a check of the command, not a quotable run.

```text
Wrote 14,834 pairs to all_pairs.jsonl
Wrote 5,739 labelled pairs to full.jsonl
Wrote 9,096 labelled frames to rgb_labelled.jsonl
Wrote 9,048 labelled frames to thermal_labelled.jsonl
```

Then draw the contact sheets (17 JPEGs) and look at them:

```bash
uv run python tools/pairing_contact_sheets.py data/raw/wisard-full \
  data/manifests/wisard-full/all_pairs.jsonl outputs/pairing-check
```

`data_quality.json`, beside the manifests, lists every directory not paired.

## What came after

The second review found gaps that changed no number. [#39] closed them: a
subset cannot be mistaken for the full set, a `nan` or `inf` label raises, and
unlabelled clips show zeros in the box counts. The regenerated manifests had
the same totals, 14,834 and 5,739 ([#39 handoff][i39-handoff]).

## What we would do differently

- **Expect the first version to hide a failure.** The first version skipped a
  missing directory silently and would have lost 38% of the labels without an
  error ([#2 handoff][i2-handoff]). A rule meant to catch wrong pairings, that
  two directories share 95% of their frame numbers, passed 106 of the 115
  wrong ones in its first form ([#2 handoff][i2-handoff]).
- **Record the commit when the manifests are made.** `prepare` did not, and
  the lead wrote it down by hand ([#2 handoff][i2-handoff]). It now records
  its commit and refuses a dirty tree or a commit off `origin/main`, since
  [#38] ([CLAUDE.md](../../CLAUDE.md)).
- **Check the labels too.** Some visible people have no box ([#2 handoff][i2-handoff]).
  A first-pass estimate, by an agent on 99 frames per camera, found an unboxed
  person in 1.1% of the RGB frames it was sure about (95% interval 0.2 to 6.1)
  and 2.3% of the thermal ones (0.6 to 7.9). 21 of the 198 frames are unsure
  and still need the owner ([label review][label-review]). Issue [#37] is open.

## Next

[Chapter 3](03-scoring-tiny-people.md): how a detector is scored.

[#1]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/1
[#2]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/2
[#7]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/7
[#38]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/38
[#37]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/37
[#39]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/39
[i2-finding]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/2#issuecomment-5891003419
[i2-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/2#issuecomment-5893694772
[i7-finding]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/7#issuecomment-5892814551
[i39-handoff]: https://github.com/graylayer-labs/ssl-aerial-person-detection/issues/39#issuecomment-5937158938
[pairing-review]: ../wisard-pairing-review.md
[label-review]: ../label-completeness-review.md
