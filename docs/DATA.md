# Data provenance and scope

## Motor pricing

Source: Christophe Dutang and Arthur Charpentier (2026), CASdatasets: Insurance datasets, version 1.2-1, DOI 10.57745/P0KHAG. The data files were acquired from the maintainers' public GitHub repository on 15 October 2026. File hashes and Git blob identities are recorded by the audit script.

- [Maintainer documentation](https://dutangc.github.io/CASdatasets/reference/freMTPL.html)
- [Package, citation and GPL >= 2 declaration](https://dutangc.github.io/CASdatasets/index.html)

`freMTPL2freq` records policy risk features, exposure in years and claim count; `freMTPL2sev` contains linked claim amounts. Documentation describes an unidentified private French insurer, approximately 2011–2013. Some amounts follow the IRSA-IDA claim convention. Individual observation dates are not supplied: a policy split must not be represented as chronological validation. Current documentation says 11 columns but its own example says 12; inspect the actual schema. `IDpol` is the join key; a severity-field description calling it an occurrence date is inconsistent with the documented relationship.

The package declares GPL >= 2. This repository distributes its own audit code and aggregate findings, with attribution; raw source files are downloaded separately. No claim of public-domain status or an independently negotiated insurer license is made.

## Loss reserving

The private-passenger auto file was accessed from the [Casualty Actuarial Society research page](https://www.casact.org/publications-research/research/research-resources/loss-reserving-data-pulled-naic-schedule-p), as compiled for CAS by S&P Global Market Intelligence. The page labels the current files updated December 2025, with a March 2026 download path. Earlier data was compiled by Glenn Meyers and Peng Shi; those earlier files are not substituted here.

The current file covers accident years 1998–2007 and development lags 1–10. Paid and incurred losses are net of reinsurance; bulk/IBNR and premium fields have separate meanings. The source describes squaring historical triangles with subsequent observations for retrospective evaluation. This is not proof that revised values were available at every historical valuation date.

The original CAS file supplies a documented current version of the insurer-panel data family underlying the planned reserving case study. No external derivative copy is needed. The source requests acknowledgement in resulting research. Raw files are not republished in this repository. Absolute currency units must be established before interpreting monetary levels; dimensionless ratios alone do not resolve that documentation gap.

These samples do not represent a combined insurer, Indian motor or health experience, a commercial engagement or a regulatory certification.
