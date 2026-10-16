# Analysis protocol — fixed before model fitting

Recorded 16 October 2026. The source audit preceded this protocol; no pricing
model or reserve forecast had been fitted. Two independent studies, each with
one actuarial baseline and one challenger. No hyperparameter search, additional
country, or outcome-driven replacement is included. `config.json` records the
numeric settings; any correctness amendment must be documented before rerunning.

## 1. French motor pricing

**Question.** Does a bounded nonlinear frequency–severity model improve the
prediction and calibration of annual expected claim cost over an interpretable
actuarial tariff? This is loss-cost modelling, not observed commercial profit or
a deployable Indian tariff. Expenses, competition, retention and treaty costs
are not observed.

**Population and split.** Use all reconciled policy records. Preserve actual
exposure, including values above one year. Join individual claims to policy IDs
before splitting. No cap on counts, exposure or claims. Hash the exact policy
ID string using the namespaced SHA256 procedure in `config.json`; first 60% of
the hash range is training, next 20% development, last 20% final test. Policies
and all their claims stay together. This is a reproducible policy split, not
chronological validation; unseen dates or customer identities are not invented.

**Targets.** Frequency is count / exposure, weighted by exposure. Severity is
mean claim amount for a positive-count policy, weighted by its number of claims.
Their product is annual expected loss cost. This severity likelihood is
equivalent in model parameters to using the individual claims with repeated
policy features. Zero-claim policies have zero aggregate loss and no observed
severity response. All monetary amounts retain the documented source scale.

**Baseline.** Log-link Poisson GLM for frequency and log-link Gamma GLM for
severity, with fixed L2 penalties in config. Features: driver-age bands
<21, 21–25, 26–35, 36–50, 51–65, 66–80, >=81; vehicle-age bands <2, 2–5,
6–10, 11–20, >=21; categorical vehicle power, brand, fuel, area and region;
continuous BonusMalus and log(1 + density). Fit category vocabulary and numeric
scaling only on training policies. Unknown categories map to the omitted
reference pattern and their counts are reported. ID, count, exposure and loss
are not predictors. Frequency uses the exposure offset through the weighted
rate likelihood. Also report the training-only constant tariff as a diagnostic.

**Challenger.** Histogram gradient boosting, Poisson frequency and Gamma
severity. Use the same information, with unbinned driver/vehicle ages, native
categorical vehicle power, brand, fuel, area and region, and continuous
BonusMalus/log density. Category vocabulary is learned on training policies;
unknown categories are missing. Fixed 200 iterations, learning rate 0.05,
15 leaves, L2 10, minimum leaf 200 for frequency / 50 for severity. No early
stopping, tuning grid, outcome-guided feature additions or resampling of claims.

**Calibration and comparison.** Fit both families on training data only. Record
uncalibrated development metrics. For each family, estimate exactly one pure
premium multiplier from development observed aggregate loss / predicted
aggregate loss. Freeze that multiplier and both fitted families before final
test evaluation. No test calibration or retraining on development data.

Primary final contrast: exposure-weighted mean Tweedie deviance (power 1.5),
challenger minus baseline, using the calibrated annual loss predictions.
Use 1,000 paired policy bootstrap samples for a 95% percentile interval. Adopt
the challenger in the study's recommendation only if the interval's upper end
is below zero and no unresolved data/implementation defect invalidates the
comparison. Otherwise retain the GLM. This is predictive evidence, not proof
of higher profit.

Secondary diagnostics: uncalibrated/calibrated observed-to-predicted cost,
Poisson frequency deviance, count-weighted Gamma severity deviance, exposure
weighted absolute loss error, training-derived predicted-risk bands, and
descriptive age/region calibration. Report small groups rather than asserting
fairness or lawful pricing. Show results with the ten largest realized-loss
policies omitted as a labelled tail sensitivity; it cannot change the primary
decision. No capped-target performance can replace the uncapped primary result.

## 2. U.S. net paid-loss reserving

**Question.** How well do a conventional Mack uncertainty estimate and a
specified positive stochastic simulation describe subsequent paid runoff?
Amounts are net of reinsurance. The target is cumulative paid loss at lag 10
minus paid loss known at valuation; it is not the unobserved ultimate loss.
Tail factor 1 means no extrapolation beyond the observable ten-year endpoint.

**Information boundary.** Primary valuation is year-end 2007, accident years
1998–2007. Only records with development year <= 2007 are supplied to the model.
The 55 expected cells define observed completeness. The set of insurers is
drawn from those visible records, not complete future 100-cell panels. The
allowlist contains entity key, accident/development years, lag and cumulative
paid only. Incurred loss, bulk reserves, premiums and `PostedReserves2007` are
excluded. No future values enter model eligibility or fitting.

**Domain.** Fit the Mack baseline to complete observed triangles whose
cumulative amounts are strictly positive. Non-monotone positive cumulative
histories and negative net increments remain eligible. Zero or negative
cumulative amounts are reported as outside this model's domain, not repaired
by clipping. The as-of audit finds 143 visible entities: 121 complete and 96
with strictly positive cumulative paid. Of the 121, only 25 also have no
negative increments. An overdispersed-Poisson bootstrap that silently discards
negative increments would substantially narrow the study; it is not used here.

**Entity split.** Hash GRCODE with the reserving namespace and seed in config.
First half of the hash range is development, second half final test. Each
model is fitted to its own entity's historical triangle; the entity split
separates benchmark development from final comparison. It is not a claim to
predict an insurer with no observed history. Common corporate relationships
and calendar shocks can limit independence across entities.

**Baseline.** Volume-weighted chain-ladder factors with Mack process and
parameter mean-square-error estimates. Variance at each development age uses
the observed weighted squared factor residuals and n - 1 degrees of freedom.
For the final factor, with one pair, extrapolate variance as
min(previous variance, preceding variance, previous variance squared /
preceding variance), with zero when the minimum preceding variance is zero.
Include covariance from shared factor estimates when summing across accident
years. Report central 80% and 95% normal predictive approximations for total
remaining paid loss. Do not truncate negative bounds. Mack supplies moments;
normality is an added approximation, not a distribution-free coverage guarantee.

**One stochastic challenger.** Use the same fitted factors/variances, plus
2,000 positive parametric simulations. For each replicate, draw one shared
factor at each age from a lognormal distribution with mean fitted factor and
variance sigma-squared / observed denominator. Conditional on that draw and
the simulated current cumulative loss C, draw the next cumulative loss from
a lognormal distribution with mean C times drawn factor and variance
sigma-squared times C. Use zero variance as a deterministic transition. Shared
factor draws preserve parameter dependence between accident years; process
draws are independent conditional on factors. Quantiles of simulated total
lag-10 loss less the observed diagonal define intervals. No clipping of net
increments is necessary. This is a moment-based parametric approximation,
not the classical ODP bootstrap, an exact posterior, or a proven calibrated
predictive distribution. Its assumptions and higher-order differences from
Mack's approximation are part of the comparison.

**Evaluation.** Freeze both methods before inspecting final-test runoff.
Primary metric: mean 95% interval score, divided within each entity by its
strictly positive sum of observed latest paid amounts. Interval score is width
plus 2/alpha times each exceedance outside the interval. Report the paired
challenger-minus-baseline contrast and 1,000 entity-bootstrap 95% intervals.
Use the challenger only if its primary score contrast has an upper bound
below zero; report coverage, interval width and small-sample uncertainty
alongside it. Secondary: 80% intervals, signed/absolute normalized runoff
error and year-end 2009 repeat using the same accident-year window and entity
assignment. Eligibility for that later view uses only then-visible values and
cannot change the primary 2007 cohort. Do not treat the two dates as independent
replicates. Report missing endpoints separately without relabelling or silently
removing their original forecast eligibility. Preserve negative realized
runoff or negative later cumulative amounts in evaluation.

**Units and vintage.** NAIC Schedule P instructions describe dollars in
thousands, but a direct statement of units for this exact CAS/S&P export is
not yet verified. Retain source units internally and publish normalized errors
and ratios; do not convert amounts or assert dollar-valued reserves. The file
was compiled later: masking later development creates a computational as-of
backtest, not proof of historical release-vintage availability. No Indian
insurer, regulatory compliance or commercial reserve certification is implied.

## 3. Verification and finite completion

Required checks cover policy/claim separation, exposure offset, claim-weighted
severity, training-only preprocessing, future-data invariance, missing-history
handling, signed net losses, known chain-ladder/Mack numerical examples,
variance aggregation and currency-scale invariance. Save source/config hashes,
split hashes, solver convergence and aggregate outputs. Raw rows, per-policy
predictions and serialized fitted models stay private and outside git.

This checkpoint's execution scope is the two baselines with development-only
diagnostics. Challenger fitting, final holdout evaluation, recruiter-facing
decision reports, demonstration and tagged release are later acceptance gates.
No deployment recommendation follows from development scores alone.

## Primary methodological references

- scikit-learn contributors, [insurance frequency–severity GLM example](https://scikit-learn.org/stable/auto_examples/linear_model/plot_tweedie_regression_insurance_claims.html).
- Gesmann and collaborators, [ChainLadder package vignette](https://mages.github.io/ChainLadder/articles/ChainLadder.html), 13 August 2026; RAA numerical reference and Mack implementation documentation.
- Braun (2004), [prediction error and dependence of run-off triangles](https://actuaries.org/app/uploads/2025/07/Braun_Bergen2004.pdf).
- NAIC, [Schedule P instruction materials](https://content.naic.org/sites/default/files/inline-files/2025-07BWG.pdf); filing-unit evidence, not independent verification of this CSV export.

Source provenance and reuse boundaries remain in `DATA.md`. The simulation
specification above is this study's explicit modelling choice, not a method
claimed to have been implemented or endorsed by those references.
