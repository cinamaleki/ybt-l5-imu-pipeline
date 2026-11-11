# Descriptive feature variation and processing sensitivity

This extension audits the existing features without fitting or retuning the direction/reach models. It separates repeated-execution variation from processing sensitivity. Results are exploratory; they do not establish clinical reliability, SEM/MDC, intervention effects, or external model accuracy.

## Run

After an authorized private study run:

```bash
ybt-l5 robustness --input-dir private_data --analysis-dir output/pilot --output-dir output/feature_audit
```

Or after generating the entirely synthetic demonstration:

```bash
ybt-l5 demo --output-dir demo_output
ybt-l5 robustness-demo --analysis-dir demo_output --output-dir output/robustness_demo
```

Outputs include a standalone Persian HTML explanation with embedded scientific plots, feature summaries, participant/cell-level tables, matched boundary comparisons, rejected perturbations, dependency versions, and input-table checksums. These generated outputs are ignored and remain outside source commits. A new output directory must be empty. The source feature table is reconciled to recomputed full-record-filtered features at rtol=atol=1e-9 before continuing.

## Repeated executions

A cell is one participant/session/stance leg/direction with exactly three trials. The median of its three absolute pair differences is retained in original units and divided by the feature's observed-trial 6 Hz IQR. Cells are first summarized within participants; the median participant is then reported. Both sessions of one person remain one person. Proposal-inclusive repeats are a separate sensitivity table, not part of the primary ranking.

Repeated movement variation includes true strategy changes, practice/fatigue, sensor error and processing error. The present design does not isolate those sources. PRE/POST are not interchangeable test-retest sessions. No ICC, SEM or MDC is inferred from these descriptive calculations. For the distinction between agreement and consistency in reliability design, see Koo & Li (2016), https://doi.org/10.1016/j.jcm.2016.02.012.

## Fixed processing scenarios

- Entire windows shifted by -0.10, +0.10, -0.25, +0.25 seconds.
- Each end trimmed or expanded by 0.10 or 0.25 seconds.
- Invalid recording bounds, overlapping windows or fewer than 40 samples are rejected without clipping; every rejection is exported.
- All original descriptors, including duration and initial-relative orientation, are recomputed after perturbation.
- Full-record 4 and 10 Hz filters are compared with 6 Hz at the same observed boundaries.

The previous pipeline refilters gyroscope and sensor-acceleration streams. It does not refilter vendor Roll/Pitch or quaternion streams. Filter sensitivity is consequently marked not applicable for their descriptors and duration, rather than interpreted as perfect robustness. The combined exploratory rank covers only the ten gyro/acceleration descriptors to which all three audit questions apply.

Reference IQR is calculated once across the 198 observed 6 Hz trial values for each feature. It includes between-person and between-condition variability and is not a clinical tolerance or percentage of the reach score. A zero IQR yields undefined scaled diagnostics (NaN/N/A), never division by zero. Raw-unit differences remain available. Median changes are participant-weighted; P95 diagnostics and Spearman ranking correlations are pooled trial descriptions, not independent-participant inference.

## Detector boundaries

Existing signal-detector proposals are matched one-to-one to observed intervals by maximum-total-IoU assignment. Both all matched pairs and the selected IoU>=0.5 subset are reported. The selected subset excludes difficult overlaps and must not be used to claim accuracy on missing-marker files. This uses the same-pilot marker-hidden development outputs; no independent validation/reference has been added. Recovered boundaries remain proposals even after human review.

## Exploratory ordering

Within the ten applicable descriptors, three ascending ranks receive equal weight: repeated-execution dispersion, worst boundary-scenario median change, and worst filter-scenario median change. Their average is a descriptive navigation aid, not a validated score or preregistered feature-selection rule. Five rows are highlighted for readability; there is no evidence-based five-feature acceptance threshold. Weights, IQR scaling and the small participant sample affect the ordering. High-tail errors are shown separately. The ordering is not used to optimize the original model results.

The private pilot analysis completed on 11 November 2026 covered 198 observed trials in 66 complete three-repeat cells; 54 proposals were retained separately. No artificial boundary scenario required rejection in this dataset. Gyroscope p95 was the first exploratory candidate, but its substantial repeated-execution variation and large high-tail boundary changes prevent a claim of established reliability. The sensor-frame acceleration derivative was particularly filter-sensitive. Any future model based on these exploratory choices needs participant-level independent evaluation.
