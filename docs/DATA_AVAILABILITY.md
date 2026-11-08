# Data availability and privacy

No real participant-level dataset is included. The repository contains source code, prose aggregate results, and a generator for entirely synthetic signals and reach distances. No names, source archive paths, original checksums, scoring workbooks, real trial features, participant predictions, videos, or real-data HTML/PDF reports are shipped.

The original inputs are not available through a public download in this release. No ethics approval number, participant consent for public release, access-committee procedure, or clinical registration is invented. Any future sharing must follow the actual study consent, institutional requirements, and rights to the source data. A code license is not permission to release research data.

Keep private files in ignored `private_data/` and generated outputs in ignored `output/`. The private offline viewer embeds signals and annotations: it is data, even when distributed as an HTML file. Do not attach it to public issues or CI artifacts. If reporting a bug, use the synthetic demo or a newly constructed minimal artificial example.

`.gitignore` does not remove already-tracked files. Run `python tools/check_public_tree.py` on the staged/tracked tree before pushing and inspect `git diff --cached --stat`. The scanner rejects common private-data formats and obvious credentials but cannot certify anonymization of free text.
