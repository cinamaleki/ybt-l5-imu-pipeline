# Model card

- **Purpose:** exploratory methods development and reproducible research portfolio.
- **Unit of generalization:** participant, not individual repeated trials.
- **Data:** seven private IMU participants, paired PRE/POST, successful trials only; synthetic demonstration separately generated.
- **Outputs:** direction classes and concurrent normalized-reach estimates; boundary-recovery proposals with explicit provenance.
- **Evaluation:** leave-one-participant-out; observed-only primary and proposal-inclusive sensitivity analyses; fixed model specifications.
- **Aggregate pilot performance:** see README. Uncertainty is substantial with seven independent people; repeated trials do not increase the participant sample size [3].
- **Limitations:** same-pilot development, uncertain recovered boundaries, conditional protocol labels, unverified anatomical axes, unknown portability to other sensors or populations, no external validation and no calibrated clinical thresholds.
- **Prohibited interpretation:** clinical diagnosis, injury screening, treatment recommendation, future outcome prediction, or automatic acceptance of reconstructed boundaries.
- **Synthetic data:** deliberately simple simulated motions. High demo scores are expected and do not establish real-data validity.
- **Distribution:** no pretrained participant-derived model weights are distributed. Models fit locally for held-out evaluation.
- **Next evidence needed:** audited protocol labels, independent boundary reference/video where authorized, larger participant sample, preregistered external evaluation, uncertainty estimates and task-specific validity evidence.
