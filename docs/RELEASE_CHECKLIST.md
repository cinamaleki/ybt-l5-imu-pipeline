# Release checklist

## Prepared and locally checked

- Source, CLI, synthetic generator, installation metadata, license and citation metadata.
- Input schema, methods, model card, data availability, bilingual README and contribution guide.
- Local unit tests, installed-command synthetic run and public-tree audit (see `VERIFICATION.md` for measured results).
- CI workflow and issue / pull-request templates.

## Remote review and optional public release

- Owner-created private repository and reviewed source snapshot: see repository commit history.
- Wait for hosted CI to pass; do not add a passing badge before it runs.
- Inspect the GitHub file list and synthetic outputs, then decide whether to make the code repository public.
- Repository URL is in citation metadata. Apply the suggested About description/topics if desired.
- Review owner name and MIT licensing choice before public release.
- Enable branch protection / required CI where the account plan permits it.
- Optionally create a v0.1.0 release after review. Archive to a DOI service only when the public release is ready; no DOI currently exists.

## Scientific follow-up

- Resolve the final-condition protocol caveat from an independent record where possible.
- Verify anatomical axes, sensor model and acquisition settings.
- Validate uncertain boundaries against independent evidence; keep primary/sensitivity separation.
- Obtain appropriate authorization before sharing any participant-level data.
- Use a larger independent sample for confirmatory evaluation; do not treat seven-person results as a validated clinical model.
