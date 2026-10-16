# Insurance loss modelling: prediction, calibration and reserve uncertainty

Prasanna K · M.A. Actuarial Economics, Madras School of Economics · 16 October 2026

## Decisions supported by this study

Select the boosted frequency–severity model as the historical pricing
benchmark under the prespecified rule. Its final-test annual-loss deviance is
**1.82% lower** than the development-calibrated GLM's, with paired
difference **-1.449756 [-2.235887, -0.612689]** (95% bootstrap interval). Retain Mack as the
transparent reserve reference: the positive simulation did not establish a
lower interval score. Both reserve methods substantially under-cover.

These conclusions support model comparison within the studied data. The
pricing model has substantial conditional calibration errors and the reserve
intervals fall short of their nominal coverage. Neither case supports live
tariff approval, a commercial reserve certification, profit uplift or a claim
about a current Indian insurer.

![Held-out age calibration and reserve interval coverage](validation_diagnostics.svg)

The left panel displays descriptive age-group ratios after the frozen
development calibration. Claims are heavy-tailed; these points do not carry
group-specific confidence intervals. The right panel shows identical empirical
coverage for both reserve methods, with descriptive Wilson intervals whose
independence assumption may fail. The two valuation dates share entities and
historical information.

## Data, information boundaries and provenance

The pricing case uses CASdatasets' French motor policy and severity files:
677,991 policies, 26,444 linked claims and exact reconciliation between each
policy's claim count and its severity rows. Exposure remains in years, including
1,224 records above one year. Claim amounts and counts are uncapped. Individual
dates are unavailable, so the SHA256 assignment is a policy split rather than
a chronological test. It yields 406,976 training, 135,817 development and
135,198 final-test policies. Every claim remains with its policy. Repeated
unobserved customers cannot be separated beyond the supplied policy key.

The independent reserve case uses the original current CAS/S&P private-passenger
auto panel, accident years 1998–2007 and development lags 1–10. At the primary
2007 valuation, only then-visible paid-loss cells enter eligibility or fitting.
There are 143 visible entities, 121 complete observed triangles, and 96 in the
positive cumulative-paid domain. Negative increments remain eligible: 30 of
43 held-out primary entities have them. Twenty-two incomplete histories and
25 complete histories outside the positive-cumulative domain remain disclosed.
No future complete-panel or forecast-performance filter is used.

Fifty-three eligible entities form the development comparison and 43 the
primary test. The 2009 secondary view has 42 eligible test entities; additional
then-visible history places one outside the model domain. That change does not
rewrite the 2007 cohort. All forecasted test endpoints are observed. The
target is additional net paid loss through lag 10, not an unobserved ultimate.
Tail factor 1 indicates the finite endpoint, rather than proof of complete
settlement. Incurred/bulk reserves, premiums and posted reserve estimates
are excluded from the paid-loss models.

Source bytes, field definitions and reuse restrictions are recorded in
[DATA.md](../docs/DATA.md) and the aggregate audit. The datasets describe
different populations and are never joined. NAIC filing conventions suggest
USD thousands, but the precise CAS/S&P export scale is not directly verified;
public reserve comparisons therefore use dimensionless ratios. The later
compiled file supplies a computational as-of backtest, not verified historical
release-vintage availability.

## Frozen experiment and methods

The [protocol](../docs/PROTOCOL.md) was committed before baseline fitting at
`c0722d07944037c8cc30e1f315b9b5ef11847cf8`. The final computational methods,
calibration factors and private forecasts were sealed before test scoring at
`e10394de482c65c41b374904b97a3709974167a0`. Models and code passed hash checks
both before and after evaluation. No test refitting, recalibration, feature
search, seed search or outcome-driven substitution occurred.

The baseline tariff multiplies a log-link Poisson frequency GLM by a log-link
Gamma severity GLM. Frequency is claim count divided by exposure with exposure
weights; severity is policy mean claim amount with claim-count weights.
The latter has the same parameter likelihood as repeated individual claims
sharing the policy's attributes. The GLM uses fixed age bands, categorical
vehicle/area/region features and continuous BonusMalus/log density. Both
preprocessing and coefficients are estimated from training policies only.

The single challenger uses Poisson/Gamma histogram boosting with the same
information, unbinned ages, native categorical features, 200 fixed iterations,
15 leaves and no early stopping or tuning. Its frequency and severity models
have minimum leaf sizes 200 and 50. Unknown categories map to missing; none
were encountered on the final test. A single aggregate-loss multiplier per
family is estimated on development data: GLM **1.129513**,
HGB **1.417368**. These are held fixed on test data.

The reserve baseline uses volume-weighted development factors and Mack process
and parameter prediction error, including shared-factor covariance across
accident years. Normality is an added interval approximation. The challenger
uses 2,000 positive parametric simulations per entity. It draws a shared
lognormal factor at each age with the fitted mean and factor-estimation
variance, followed by conditionally separate lognormal cumulative-loss
transitions matching the fitted process moments. Net increments may be
negative. Both methods share the theoretical chain-ladder point mean. This
is a specified moment-based approximation, not an exact posterior or a
classical ODP bootstrap. Full numerical details and stream definitions are in
[IMPLEMENTATION_NOTES.md](../docs/IMPLEMENTATION_NOTES.md).

## Pricing: final-test evidence

The final sample contains 135,198 policies, 5,303
claims and 71,404.40 exposure-years. Smaller
deviance is better. The primary metric is exposure-weighted Tweedie deviance
at power 1.5 for annual expected loss cost, after frozen development calibration.

| Held-out diagnostic | GLM | HGB |
|---|---:|---:|
| Calibrated annual-cost Tweedie deviance ↓ | 79.631024 | 78.181268 |
| Calibrated aggregate observed / predicted loss | 0.952964 | 0.947556 |
| Uncalibrated frequency Poisson deviance ↓ | 0.460261 | 0.449653 |
| Uncalibrated severity Gamma deviance ↓ | 1.627417 | 1.763188 |

The paired HGB-minus-GLM contrast is **-1.449756 [-2.235887, -0.612689]**. It uses 1,000
policy bootstraps with the same policy indices for both models and a
recomputed exposure denominator. The interval lies below zero, meeting the
fixed selection rule. This interval conditions on fitted models and calibration;
it excludes training-sample and model-selection uncertainty.

The gain concerns the combined loss-cost target. HGB's severity-component
deviance is worse, and its uncalibrated total loss is materially underpredicted.
Development calibration improves the combined comparison but does not deliver
uniform calibration: the test observed/predicted aggregate ratio is
**0.948**, and the under-21 group is
**4.721** across 138 claims.
No fairness, causal or legal-pricing conclusion follows from these descriptive
age/region diagnostics. Application requires fresh validation of conditional
calibration, observation timing and business costs.

The ten largest-loss policies account for
**24.74%** of test
losses. The prespecified diagnostic excluding them retains a negative paired
deviance difference, **-1.552493**.
It is an outcome-selected sensitivity; the uncapped result remains primary.
Training-defined risk-decile, age and region summaries—including sparse-group
flags—are preserved in [pricing_final.json](pricing_final.json).

## Reserving: interval realism and transport across valuations

Interval score combines interval width and a penalty for missing the observed
endpoint; smaller is better. Each entity's score and width are divided by its
latest observed total paid loss, then averaged equally across entities. This
avoids interpreting an unverified absolute currency scale and avoids letting
large entities alone determine the primary comparison.

| Valuation | Method | Entities | 95% interval coverage | Mean normalized score ↓ | Mean normalized width |
|---|---|---:|---:|---:|---:|
| 2007 primary | Mack-normal | 43 | 36/43 (83.7%) | 0.193866 | 0.104902 |
| 2007 primary | Positive simulation | 43 | 36/43 (83.7%) | 0.195575 | 0.104775 |
| 2009 secondary | Mack-normal | 42 | 32/42 (76.2%) | 0.111253 | 0.050089 |
| 2009 secondary | Positive simulation | 42 | 32/42 (76.2%) | 0.112918 | 0.050094 |

The primary 2007 simulation-minus-Mack score contrast is
**+0.001709 [-0.002275, +0.006535]**, using 1,000 paired entity bootstraps. It does not meet
the improvement rule, so retain Mack as the reference. Both methods cover
36/43 outcomes with nominal 95% intervals and 23/43 with nominal 80% intervals.
The 95% coverage Wilson interval is
[70.0%,
91.9%], under an independence
interpretation. Nominal coverage is not achieved empirically.

The secondary 2009 contrast is
**+0.001664 [-0.002029, +0.005917]** and cannot
change the primary decision. Both methods cover 32/42 outcomes with nominal 95%
intervals and 24/42 with nominal 80% intervals. The shared point prediction's
mean absolute normalized error falls from 3.13%
at 2007 to 1.20% at 2009 as more
development is observed; this is not an independent sample comparison.

Resampling entities treats them as sufficiently independent. Corporate links
and common calendar shocks may invalidate that approximation. The finite
2,000-draw quantiles carry Monte Carlo noise; the simulation's mean absolute
normalized Monte Carlo mean error is
0.000384 in the primary
sample. This measures mean error, not quantile error. No additional simulations
or parameter search were chosen after inspecting final outcomes.

## Verification, outputs and reproduction

Eighteen focused tests pass. They cover policy linkage, exposure weighting,
claim-weighted severity equivalence, training-only category vocabulary,
future-cell invariance, missing-history and signed-loss handling, R-header
compatibility, a published Mack numerical reference, shared-factor covariance,
currency-scale invariance, lognormal moments, deterministic transitions,
paired metric behavior and rejection of changed frozen artifacts.
Saved final predictions reproduce the reported pricing scores using the
reference scikit-learn metric; direct arithmetic reproduces the reserve
coverage and interval scores. The original source hashes and experiment
settings remained unchanged. These checks are implementation evidence, not
an independent external review.

A separate source directory, downloaded from the committed GitHub source,
regenerated ten analysis outputs byte-for-byte, including both final reports
and the model/forecast seal. The run rebuilt fitted models and forecasts from
the checksum-verified cached raw bytes in the same Python environment. It did
not retest fresh network acquisition or establish cross-platform reproduction.
See [reproduction evidence](reproduction_verification.json) and the
[reproduction guide](../docs/REPRODUCE.md).

Source and aggregate evidence are in the repository; raw observations,
serialized models and row/entity-level outputs remain excluded. The interactive
explorer reads these aggregate findings and distinguishes hypothetical price
assumptions from measured results. Publication status is maintained in the
[README](../README.md). See [final verification](final_verification.json),
[model freeze](model_freeze.json), [reserve outputs](reserve_final.json) and
the [decision memo](DECISION_MEMO.md).

The primary sources and methodological references are linked in DATA.md and
PROTOCOL.md. No commercial engagement, realized savings, current Indian
experience or regulatory certification is claimed.
