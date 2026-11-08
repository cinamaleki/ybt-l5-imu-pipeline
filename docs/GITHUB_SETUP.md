# GitHub repository and maintenance

The private repository is `cinamaleki/ybt-l5-imu-pipeline`. Its initial README was created by the owner; the reviewed source snapshot is added by a subsequent commit. Participant-level files are excluded.

## Work on the existing repository

```bash
gh auth login
gh repo clone cinamaleki/ybt-l5-imu-pipeline
cd ybt-l5-imu-pipeline
python -m pip install .
python -m unittest discover -s tests -v
# Make a focused change on a branch, then inspect and commit it.
git switch -c describe-your-change
git add .
python tools/check_public_tree.py
git diff --cached --stat
git commit -m "Describe the concrete change"
git push -u origin describe-your-change
```

Check the Actions tab for hosted Python checks. Repository visibility remains private until the owner decides to publish it. Real participant data and generated private reports must stay outside commits. Never put an access token in repository files or a chat message.

## Suggested About information

Description: `Exploratory L5 IMU Y-Balance analysis with provenance-aware recovery, participant-held-out evaluation, and synthetic examples.`

Topics: `biomechanics`, `imu`, `y-balance-test`, `motor-control`, `python`, `reproducible-research`, `machine-learning`.

Pin the repository to your GitHub profile after the README and hosted CI have been reviewed. Use this accurate portfolio sentence:

> Developed a reproducible Python workflow for lumbar-IMU Y-Balance recordings, including exported-signal QC, provenance-aware event-recovery proposals, participant-held-out segmentation validation, and exploratory direction/reach models.
