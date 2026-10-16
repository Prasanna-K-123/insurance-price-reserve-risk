# Reproduction guide

## Verified result

On 16 October 2026, all 37 tracked source/report files at commit
`ad64ab66866d63e7e6bccb0000aa05692d36e269` were retrieved from GitHub into a
separate directory and checked against their Git blob hashes. That directory
had no fitted models or processed data. The three previously acquired raw
files were copied into `data/raw/`; the audit verified their pinned SHA256
hashes before parsing.

The audit, valuation boundary, 18 tests, both baseline fits, both challenger
comparisons and final scoring ran successfully. Ten regenerated outputs were
byte-for-byte identical to the committed evidence:

1. `reports/data_audit.json`
2. `reports/reserve_valuation_audit.json`
3. `reports/pricing_baseline.json`
4. `reports/reserve_baseline.json`
5. `reports/BASELINE_REPORT.md`
6. `reports/pricing_challenger.json`
7. `reports/reserve_challenger.json`
8. `reports/model_freeze.json`
9. `reports/pricing_final.json`
10. `reports/reserve_final.json`

The matching freeze also confirms matching fitted pricing artifact and private
reserve-forecast hashes. This is a fresh source/output-directory reproduction
in the **same Python environment**, not an independent audit or a new-machine
portability test. Fresh network acquisition was not retested. The recorded
elapsed time is specific to that environment, not a performance guarantee.
Full checksums and command exits are in
[reproduction_verification.json](../reports/reproduction_verification.json).

## Run from a fresh checkout

Use Python 3.12 and the exact core dependency versions in `requirements.txt`
and `requirements-data.txt`. A virtual environment is recommended. Transitive
dependencies and operating-system numerical libraries are not fully locked;
byte equality across other environments is not guaranteed.

```bash
python -m venv .venv
# Activate .venv using the command for your shell, then:
python -m pip install -r requirements.txt
python scripts/audit_data.py
python scripts/reserve_valuation.py
python -m unittest discover -s tests -v
python scripts/run_baselines.py
python scripts/report_baselines.py
python scripts/run_challengers.py
python scripts/evaluate_final.py
python scripts/check_reproduction.py
python scripts/report_final.py
python scripts/build_demo.py
```

The fitting commands execute the already specified models to reproduce the
study. They do not establish a new untouched experiment. Preserve the original
results and protocol if exploring extensions in a separate study.

The acquisition script uses the URLs in [DATA.md](DATA.md). If a source blocks
automated access, use its permitted download process and place the exact bytes
in `data/raw/`; do not substitute a similarly named dataset. Local files still
have to pass the pinned hashes. An upstream revision requires a separately
documented study; do not update hashes just to make an error disappear.

After fitting, the final evaluator refuses changes to the sealed computational
source, configuration, protocol or private artifacts. The published historical
verification records document their original checks; they are not regenerated
certificates of an independent review.

## Explorer and reports

`scripts/report_final.py` reads aggregate final evidence and writes the technical
report, decision memo and diagnostic SVG. `scripts/build_demo.py` embeds the
same aggregate reports into `docs/index.html`. Neither command fits a model.

Open `docs/index.html` in a browser. No server, account, API key or external
JavaScript is required. The pricing assumptions panel starts from an indexed
hypothetical loss cost of 100 and cannot alter the measured evidence. Reserve
controls choose among saved dates and nominal levels; they do not simulate a
new reserve distribution. See [release status](RELEASE.md) for browser and
publication verification.

Raw inputs, processed observations, policy/entity-level forecasts and fitted
models are intentionally excluded from source control. Respect each source's
terms when acquiring or using the data.

## Script-level explorer check

With Node.js installed, run `node tests/check_explorer.cjs`. It executes the
actual embedded script against a minimal DOM harness and checks 15 aspects of
evidence embedding, assumption arithmetic, model/group controls, date/level
controls and tab wiring. This is deliberately recorded as script-level
verification; layout, actual browser events and accessibility-tree behavior
still require rendered-browser checks. Its result is written to
`reports/demo_verification.json`. No browser installation is attempted by this
command.
