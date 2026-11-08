# Private input contract

This release implements the original study export schema, not automatic ingestion of arbitrary IMU files.

## Files

- Seven archives with basenames matching `subject\s*(N)`, N=1..7; for example `subject 1.zip`.
- Each archive has separate PRE and POST subdirectories, with `pre` or `post` in their path.
- Required streams in each recording directory: `Pelvis-Gyroscope.csv`, `Pelvis-Sensor_Acceleration.csv`, `Pelvis-Orientation.csv`, `Pelvis-Roll.csv`, `Pelvis-Pitch.csv`. Optional exported streams include `Pelvis-Acceleration.csv`, `Pelvis-Tilt_Fwd.csv`, and `Switch_1.csv`.
- CSV format: metadata field names on line 1, metadata values on line 2, blank line 3, data header on line 4. Metadata includes `frequency`, `units`, `count`. First data column is `time` in seconds.
- Required signal time grids start at zero, are strictly increasing and regular at 200 Hz, and align exactly within tolerance. Gyroscope/acceleration have 3 value columns, quaternion has 4, Roll/Pitch/Switch have 1. Quaternion norms must be nonzero. Other audit-only streams may have different rates.
- Units: gyro degrees/second, Roll/Pitch degrees, sensor acceleration mG, quaternion dimensionless. These units are an input contract; automatic unit detection is not implemented.
- `Switch_1.csv` uses positive values while pressed; rising edges are events. Thirty-six pulses are accepted as 18 pairs; 37 triggers a single-extra-event hypothesis; no switch triggers signal-only recovery. Other pulse counts fail explicitly.

## Workbooks

`YBT_Clean_Scoring_Workbook-39 subjects.xlsx`: sheet `Raw_YBT`, one header row, 39 participant rows. Fields are `ID`, `Group`, `LegLength_cm`, and `Pre`/`Post` × `L`/`R` × `ANT`/`PM`/`PL` × `t1`/`t2`/`t3` (e.g. `Pre_R_ANT_t1`). Cached summary fields are `Pre_R_Max_ANT_cm`, `Pre_R_ANT_%`, `Pre_R_Composite_%`, following the same pattern. Formula cells must have cached numeric values for the audit comparison; openpyxl does not recalculate Excel formulas.

`YBT_Descriptive_with_ErrorBars.xlsx`: sheet `Descriptive_Means`, columns in order Measure, Group, Pre mean, Pre SD, Post mean, Post SD, Delta mean, Delta SD. This workbook is audited, not trusted as the analysis source; the original file's delta identities were inconsistent.

## Reviewed boundaries

CSV requires unique `recording`, `interval_index` keys and fields `start_s`, `end_s`, `user_reviewed`. Only rows marked true/1 are applied. Boundaries must be finite, nonoverlapping, ordered and within the recording. Source type and primary-analysis eligibility remain provenance-aware. Editing an observed interval retains eligibility but records `user_reviewed_observed`; a recovery remains excluded from the primary analysis.

The raw-data workflow emits participant-level products. Never run it as a public CI job with real study inputs.
