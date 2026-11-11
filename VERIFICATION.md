# Local verification — 4 November 2026

| Check | Observed result |
|---|---|
| Build/install using pyproject metadata | Wheel built and command installed successfully |
| Unit tests, Python 3.12.14 | 17 passed; also run with FutureWarning promoted to error |
| Installed CLI synthetic demonstration | Completed: 14 artificial recordings, 252 intervals, 756 feature rows |
| Synthetic exception provenance | 198 observed-boundary intervals; 54 recovery proposals; zero participant overlap in exported fold membership |
| Installed CLI private-data rerun outside source directory | Completed full audit, recovery, features, grouped models and private report generation |
| Private-data regression comparison | Seven key CSV result tables exactly matched the previous complete analysis |
| Public source audit | Only approved text/source formats; no real-data files or obvious credential patterns detected |
| GitHub-hosted CI | Configured for Python 3.11 and 3.12; see the repository Actions tab for current run status |

The seven regression-compared tables were interval provenance, trial annotations, feature values, direction summary, reach summary, corrected mixed ANOVA, and recomputed 39-person conventional scores. No participant-level table is included in this public source package.

Tests exercise fixed-rate rejection, CSV metadata validation, invalid/zero-norm signals, one-to-one IoU assignment, Switch-independent detection, training-only boundary correction access, cycle/normalization, group overrides, max-of-available scoring, reviewed-boundary constraints/provenance, physical acceleration units, independently computed ANOVA, and training-only reach baselines. Three release-guard tests additionally confirm allowed source acceptance, rejection of staged participant-data formats, and credential detection in the Git index even after a working-copy cleanup.

Installation used existing dependencies and `--no-deps --no-build-isolation` in the authoring environment. A fresh online dependency installation, Windows execution, Python 3.11 execution, actual browser rendering/downloads, and GitHub remote operations were not verified here. The dependency file pins direct packages only. The source audit is a conservative format/credential guard, not proof that arbitrary future additions contain no sensitive information.

## Repository preparation — 8 November 2026

Recovered the original 32-file source ZIP, verified its SHA-256 and every file listed in its source manifest, and confirmed write access to the owner-created private repository. Repository URLs were added to citation metadata; setup instructions now describe the existing repository. No participant inputs were needed for this step. Current local checks are repeated before the source commit.

## Feature audit extension — 11 November 2026

- Recovered the private complete analysis and all seven source archives through authorized access. Recomputed original features matched all existing descriptor values at rtol=atol=1e-9.
- Processed 198 observed trials (66 complete three-repeat cells), plus separate proposal-inclusive repeats. All eight fixed boundary scenarios were valid in this pilot; filter and one-to-one detector comparisons completed.
- All 24 local unit tests passed. New contracts cover physical perturbation bounds, no clipping/overlap, fixed observed-only scaling, three-repeat pair differences, keyed signed-feature comparisons, overlap-based detector assignment, and non-applicability of filtering vendor orientation.
- Source distribution builds successfully. Installed CLI synthetic analysis and the new feature audit both completed, with their outputs explicitly labelled entirely synthetic. Hosted Python 3.11/3.12 checks include both demonstrations; consult Actions for the current run status.
- Independent checks of three real repeat cells and two processing summaries matched the exported calculations. All seven source-archive hashes matched the earlier private audit. The standalone HTML contains three embedded figures and two result tables; figure layout was visually checked. An actual browser rendering was not verified.
- Findings remain descriptive same-pilot outputs. No participant-level table, trace, report or trained model was added to GitHub.
