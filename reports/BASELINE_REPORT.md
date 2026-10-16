# Actuarial baselines — development results

16 October 2026 · Prasanna K · M.A. Actuarial Economics, Madras School of Economics

**Milestone complete:** both actuarial baselines are implemented, checked and
evaluated on development data. The analysis protocol was committed before
fitting. Final holdouts remain unscored. This is an intermediate research
result, not a finished insurance project or a deployment recommendation.

## Pricing: useful segmentation, unresolved calibration

The frequency–severity GLM reduces development annual-loss Tweedie deviance
by **6.76%** relative to a constant tariff estimated from training
data. Its severity component is worse on Gamma deviance, and total observed
loss is **1.130 times predicted loss**.
The positive combined score does not establish adequate calibration or profit.

| Development diagnostic | Constant tariff | Poisson × Gamma GLM |
|---|---:|---:|
| Frequency Poisson deviance ↓ | 0.490312 | 0.470746 |
| Severity Gamma deviance ↓ | 1.710603 | 1.727572 |
| Annual loss Tweedie deviance, power 1.5 ↓ | 88.965885 | 82.952528 |
| Aggregate loss observed / predicted (ideal 1) | 1.051168 | 1.129513 |

The split contains 406,976 training,
135,817 development and
135,198 final-test policies. Their claims stay
with the same policies. Training preprocessing produces 60
design columns; development has no unseen categories. Poisson and Gamma solvers
converged in 106 and 72
iterations with no convergence warnings. All 1,224 exposures above one year,
and all uncapped claim amounts, remain in the data.

The prespecified development calibration multiplier is
**1.129513**. It is saved for
later final-test use. Applying it makes the development aggregate ratio one
by construction; that is not evidence of out-of-sample calibration.

The data supplies no reliable per-policy dates for a temporal split. Findings
concern historical recorded French motor risk attributes and claim costs,
not commercial profitability, causal effects or an Indian insurance tariff.

## Reserving: normal intervals substantially under-cover

At year-end 2007, 143 entities have visible data; 121 have complete historical
triangles and 96 meet the strictly positive cumulative-paid domain. Negative
net increments are retained. Of these 96, 53
are development entities and 43 are held out.
All development endpoints are observed; no future endpoint availability was
used to choose the eligible cohort.

| Nominal interval | Covered development outcomes | Empirical coverage | Mean normalized width | Mean normalized interval score ↓ |
|---|---:|---:|---:|---:|
| 80% | 35 / 53 | 66.0% | 0.0646 | 0.1782 |
| 95% | 41 / 53 | 77.4% | 0.0988 | 0.3945 |

The baseline predicts remaining net paid loss through development lag 10,
not unobserved ultimate losses. Each score and width is divided by that
entity's observed latest total paid loss before averaging. Mean absolute
normalized prediction error is 3.08%;
mean signed error is 0.94%. One development
entity has negative realized remaining paid loss, which is preserved.

The 95% coverage shortfall is a development finding. It motivates the already
specified parametric simulation comparison but does not establish that the
challenger will improve coverage or interval score. Small sample size,
calendar shocks and possible corporate dependence limit inference across
entities. Mack's moment estimates do not themselves guarantee normal intervals.

The fitted uncertainty includes dependence between accident-year reserve
estimates through common development factors. Exact export currency units
remain unverified, so comparisons are dimensionless and no dollar reserve
amount is claimed. Later compilation of the source prevents a claim of
genuine historical data-vintage availability.

## Checks and next gate

Eleven focused tests passed: published RAA/Mack numerical agreement; dependence
in total reserve uncertainty; invariance to currency scaling; analytic exposure
weighting; grouped-versus-individual severity likelihood; policy/claim linkage;
feature exclusion and R-header compatibility; future-information isolation;
missing history; calendar/key errors; and preservation of signed net losses.

The Mack numerical check agrees, to published rounding, with the authors'
[ChainLadder reference](https://mages.github.io/ChainLadder/articles/ChainLadder.html):
remaining loss 52,135.23 and standard error 26,909.01. This validates a specific
calculation; it is not independent review of the complete study.

Code, source hashes, split hashes, coefficients and aggregate outputs are saved.
Raw records, entity-level forecasts and fitted model files are excluded from
git. See [protocol](../docs/PROTOCOL.md), [pricing output](pricing_baseline.json),
[reserve output](reserve_baseline.json) and [verification](verification.json).

Next: implement the two fixed challengers and their development checks, then
run the frozen final comparisons. No hyperparameter search or new project is
needed. Final-test evaluation, decision reports, demonstration and release
remain open acceptance gates.
