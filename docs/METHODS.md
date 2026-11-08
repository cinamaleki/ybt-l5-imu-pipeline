# Methods and interpretation

## Study and provenance

Seven participants have paired PRE/POST L5 IMU exports. The separate conventional YBT workbook contains 39 participants. These are different analysis sample sizes. Participant numbers map directly between IMU and scoring files. Explicit group overrides are ID3→2 and ID4→1. Only successful trials were recorded, so failure detection cannot be evaluated.

Thirty-six rising Switch pulses are interpreted as 18 consecutive start/end pairs, based on researcher confirmation. A count of 36 does not independently verify individual boundaries. The six-condition sequence is R ANT, L ANT, R PM, L PM, R PL, L PL, repeated three times; R/L is stance leg. The final-condition typing-error interpretation is recorded in output annotations. This is the study's recorded sequence, not a claim that every standard YBT protocol uses this order.

## Recovery and internal validation

The fixed signal detector uses smoothed vendor Roll/Pitch excursion relative to a low-angular-speed baseline. Candidate peaks have prominence ≥3 degrees, minimum separation 1.25 seconds and width ≥0.3 seconds. Eighteen highest-prominence candidates are selected using the known protocol count. Obtaining 18 intervals is therefore not validation. Boundaries use 90%-prominence widths, training-participant median padding, and overlap clipping.

Padding and the fixed logistic boundary classifier exclude all recordings of the test participant. Matching uses maximum-total-IoU one-to-one assignment. IoU≥0.5 recall is an internal marker-hidden result. The detector specification itself was developed on this pilot; an untouched external sample is still needed [2,3].

For 37 pulses, all single-deletion hypotheses are ranked with local angular-speed and angle-change features. Exactly one spurious event is an assumption. Other acquisition errors may produce the same pulse count. Margins are not calibrated probabilities. Missing-switch recovery and single-extra-event proposals always have `include_primary=False`; human review does not turn reconstructed boundaries into observed Switch events.

## Features and models

Complete recordings are filtered before segmentation using fourth-order zero-phase Butterworth filters at 4, 6 and 10 Hz. Core sampling rate is fixed at 200 Hz and explicitly checked. Sensor acceleration is converted from mG to m/s² by 0.00980665. Accelerometer descriptors remain sensor-frame measures; anatomical AP/ML axes have not been verified. Its derivative includes gravity/orientation effects and is not a validated movement-smoothness measure. Vendor COM is not independent ground truth.

Four magnitude descriptors are angular-speed RMS/p95, centered acceleration RMS and sensor-acceleration derivative RMS. Twelve directional descriptors are initial-relative Roll/Pitch p05/p95, gyroscope axis RMS, centered sensor-acceleration axis RMS, quaternion excursion p95 and duration.

Direction specifications are fixed: most-frequent dummy, scaled magnitude logistic, scaled directional logistic (C=1, balanced classes), and directional random forest (200 trees, max depth 4, minimum leaf 3). No hyperparameter or label-order search is performed. Entire participants, including both sessions, are held out. Scalers and encoders fit training rows only [4,5].

Ridge (alpha=10) estimates concurrent reach/leg length ×100 from 12 descriptors plus encoded direction and stance leg. Its comparator is training-only direction/leg mean. Identity, group, session, measured reach, and absolute time are not predictors. It is not a future improvement or injury model.

## Conventional scores

Max-of-available successful reaches are normalized to recorded leg length. Both legs are averaged for direction outcomes and composite. A missing third POST right-PL entry for ID39 is flagged; no value is imputed. The balanced 2-time ×3-group ANOVA uses participant means for group effects and participant change scores for interaction, with a pooled residual for the time contrast. Holm correction is applied within each four-outcome effect family. All 12 private-data raw p values exceed .05; this is not evidence of equivalence or no effect.

The audit layer's per-candidate descriptors are explicitly provisional and are not the feature table used by the primary models. Use `trial_features_all_cutoffs.csv` for those models. Assumption diagnostics, prospective power planning and confirmatory inference are beyond this exploratory release.

See [references](REFERENCES.md), [model card](MODEL_CARD.md), and [data availability](DATA_AVAILABILITY.md).
