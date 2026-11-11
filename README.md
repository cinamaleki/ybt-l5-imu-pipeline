# YBT-L5 IMU Pipeline

Exploratory research software for lumbar (L5) IMU recordings collected during the Y-Balance Test. The focus is transparent signal processing, explicit provenance of uncertain movement boundaries, and evaluation with whole participants held out.

**Status:** research prototype, software v0.2.0. Seven IMU participants; no external validation. This is not a clinical decision tool. The public repository contains code, aggregate pilot findings, and a synthetic demonstration. Participant-level recordings, scores, predictions, and real-data viewers are excluded.

[راهنمای فارسی](README.fa.md) · [Methods](docs/METHODS.md) · [Model card](docs/MODEL_CARD.md) · [Data availability](docs/DATA_AVAILABILITY.md) · [GitHub setup](docs/GITHUB_SETUP.md)

## Quick start

Python 3.11 or 3.12 is supported by the CI configuration; the local release was tested on Python 3.12.14. From the repository directory:

```bash
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .
ybt-l5 demo --output-dir demo_output
python -m unittest discover -s tests -v
python tools/check_public_tree.py
```

The demo generates **entirely simulated** recordings, performs recovery validation, extracts descriptors, evaluates grouped models, and writes CSV tables, segmentation figures, and `demo_output/SYNTHETIC_REPORT.html`. Open that report locally. Its scores demonstrate execution only and are not scientific evidence. No downloads or credentials are needed after installation.

For the exact direct dependency versions used locally:

```bash
python -m pip install -r requirements-reproducible.txt
python -m pip install --no-deps .
```

## Feature variation and robustness audit

Version 0.2 adds a separate descriptive audit of repeated executions, eight fixed boundary perturbations, filter sensitivity and signal-detector boundaries. It does not retune the previous models or establish clinical reliability. [Methods and limits](docs/FEATURE_AUDIT.md).

```bash
ybt-l5 robustness-demo --analysis-dir demo_output --output-dir output/robustness_demo
# Authorized private analysis, after the normal study workflow:
ybt-l5 robustness --input-dir private_data --analysis-dir output/pilot --output-dir output/feature_audit
```

The generated standalone `YBT_Feature_Audit_FA.html` explains results in Persian. Gyro/acceleration descriptors are compared across all three audit questions; filter comparisons for unfiltered vendor orientation and duration are marked not applicable. Rankings are exploratory and sample-dependent. Generated human-data reports and tables remain private.

## Authorized private-data analysis

```bash
ybt-l5 run --input-dir private_data --output-dir output/pilot
# Optional reviewed boundaries exported by the private viewer:
ybt-l5 run --input-dir private_data --output-dir output/reviewed --review-csv private_data/review.csv
```

The private input contract is study-specific: seven `subject N.zip` archives with paired PRE/POST exports and the two scoring workbooks. See [input schema](docs/INPUT_SCHEMA.md). The pipeline checks the 200 Hz common time grid used by its computations. Other devices, rates, cohort sizes, export schemas, or protocols require explicit adaptation. Generated output includes private participant data; keep it outside the public repository.

## Workflow

1. Audit exported streams, pulse counts, identity mapping, and conventional scores.
2. Preserve 36-pulse recordings as observed start/end pairs. Keep signal-only and single-extra-event hypotheses as recovery proposals.
3. Validate marker-hidden recovery while excluding both sessions of each test participant from fitting boundary corrections and classifiers.
4. Filter complete recordings, extract fixed descriptors, and compare direction and concurrent reach models using leave-one-participant-out evaluation.
5. Retain primary observed-only analyses separately from sensitivity analyses including recovery proposals.
6. Recompute the separate 39-person conventional YBT analysis with the confirmed group corrections.

## Aggregate findings from the private pilot

These values come from the private-data analysis completed on 4 November 2026, **not** from the synthetic demo. Public code cannot independently reproduce these numerical findings without authorized access to the original inputs.

| Quantity | Result | Interpretation |
|---|---:|---|
| IMU participants / PRE–POST recordings | 7 / 14 | Small exploratory pilot |
| Observed intervals / recovery proposals | 198 / 54 | Proposals remain outside the primary analysis |
| Marker-hidden matched intervals, IoU ≥ 0.5 | 160/198 (80.8%) | Pooled internal development result; not accuracy on missing-marker files |
| Correct deletion in artificial extra-pulse tests | 55.0% of 220 | Insufficient for automatic event repair |
| Direction balanced accuracy: dummy / directional logistic / forest | 33.3% / 36.5% / 39.7% | Participant-average, observed intervals, 6 Hz |
| Concurrent normalized-reach MAE: protocol mean / Ridge | 10.10 / 8.61 percentage points | Participant-average; no future-outcome claim |

Protocol labels assume the cycle `R ANT, L ANT, R PM, L PM, R PL, L PL`, repeated three times; R/L is the stance leg. The last `L PM` in a later message was interpreted as a typing error for the earlier `L PL`; label-dependent results remain conditional on this interpretation. Groups: participant 3 → group 2; participant 4 → group 1. No trial-level video verification is asserted.

## Repository contents

| File | Purpose |
|---|---|
| `ybt_l5_cli.py`, `ybt_synthetic.py` | Installed command and generated demonstration |
| `run_complete_ybt.py` | Private study orchestration and reviewed-boundary import |
| `ybt_imu_audit.py` | Export QC and corrected conventional scores |
| `ybt_complete_pipeline.py` | Segmentation, recovery hypotheses, and held-out validation |
| `ybt_complete_analysis.py` | Features, grouped models, and mixed ANOVA |
| `build_complete_deliverables.py` | Private offline viewer and report generation |
| `ybt_feature_audit.py`, `ybt_feature_report.py` | Repeat/processing audit and private standalone explanation |
| `tests/` | Numerical, provenance, input-validation, and integration contracts |
| `.github/workflows/ci.yml` | Installation, unit tests, synthetic smoke run, and public-tree checks |

Source organization deliberately retains the working study scripts rather than presenting this prototype as a general-purpose biomechanics framework.

## Citation and license

Use `CITATION.cff` to cite this software. No DOI or accepted publication is claimed. Source code is under the MIT license; this grants no rights to withheld participant data or third-party material. See [references](docs/REFERENCES.md), [contributing](CONTRIBUTING.md), and [release checklist](docs/RELEASE_CHECKLIST.md).
