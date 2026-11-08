# Contributing

Use a branch and a pull request. Describe the scientific or implementation problem, the resulting behavior, and verification. Keep model specifications and provenance changes explicit. Never tune label ordering to increase model accuracy. New parameters need a clear training/validation separation.

Before submitting:

```bash
python -m pip install .
python -m unittest discover -s tests -v
ybt-l5 demo --output-dir demo_output
python tools/check_public_tree.py
```

Use synthetic examples in issues and PRs. Do not attach participant data, real-data reports, original archive names, or screenshots containing participant information. Report a suspected disclosure privately to the repository owner through their established contact route; no unverified email address is supplied here.
