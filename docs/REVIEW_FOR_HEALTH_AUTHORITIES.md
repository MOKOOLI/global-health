# What a WHO / CDC / ECDC reviewer would likely object to, and where we stand

This is the author's own critical review, not an endorsement by any agency. Status is as of this version.

| Concern a reviewer would raise | Status |
|---|---|
| Statistical signals could be mistaken for official declarations (PHEIC, pandemic, epidemic) | Mitigated: every signal page and feed says it is a statistical pattern in reported data, not a declaration; no "pandemic predicted" claims; back-tested forecasts labelled with skill vs naive |
| Modeled estimates shown as if they were counts | Mitigated: every value carries a data-type badge (reported / estimated / modeled / synthetic); the Q&A engine states the type in its sentence |
| League tables imply quality ranking | Mitigated: a note beside "Highest values" says reporting capacity drives values. Not solved: no reporting-completeness indicator exists |
| Map boundaries and names (disputed territories) | Partly: a standard disclaimer sits under every map. Not solved: boundaries come from a simplified public dataset; names/borders have not been reviewed by a geographer, and some territories are missing or merged |
| Licensing of WHO/IHME/other data | Not solved: the register is all `verified: false`. WHO GHO may carry a non-commercial licence; IHME needs permission for commercial use. Needs a human to read each provider's terms |
| Data currency | Mitigated: data age is shown on the home signal strip and on surveillance pages. Depends entirely on running the ETL on schedule |
| Case definitions and comparability across countries | Partly: measure definitions are shown; disease-specific case definitions (confirmed vs probable, notification rules) are not |
| Age structure confounding | Partly: ASR calculator provided for the user's own numbers; displayed country values are not age-standardised unless the source already is |
| Clinical misuse | Mitigated: disclaimers on every page, no treatment advice, Q&A refuses clinical questions. Not independently tested with clinicians |
| Accessibility (WCAG) and language coverage | Partly: keyboard use, text alternatives, reduced motion. No audit; Persian and English only |
| Governance, review process, correction policy, advisory board | Not solved: placeholders on the Trust page; needs real people |
| Security and privacy | Mitigated: no accounts, hashed API keys, bandit/pip-audit clean at last run. No penetration test |
| Reproducibility and citation | Done: data-version hash, datapackage, snapshot with checksums, APA/BibTeX. DOI minting is up to the operator |

Before approaching an agency: verify licences, have a clinician and a geographer review the content, form an advisory group, and run the ETL on a schedule with monitoring.
