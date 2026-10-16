"""Render the baseline milestone from saved aggregate outputs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    pricing = json.loads((ROOT / "reports/pricing_baseline.json").read_text())
    reserve = json.loads((ROOT / "reports/reserve_baseline.json").read_text())
    constant, glm = pricing["development_constant_tariff"], pricing["development_uncalibrated_glm"]
    development = reserve["development"]
    reduction = 1 - glm["pure_premium_tweedie_deviance"] / constant["pure_premium_tweedie_deviance"]
    n = development["scored_entities"]
    table = "\n".join(
        f"| {label} | {constant[key]:.6f} | {glm[key]:.6f} |"
        for label, key in [
            ("Frequency Poisson deviance ↓", "frequency_poisson_deviance"),
            ("Severity Gamma deviance ↓", "severity_gamma_deviance"),
            ("Annual loss Tweedie deviance, power 1.5 ↓", "pure_premium_tweedie_deviance"),
            ("Aggregate loss observed / predicted (ideal 1)", "loss_observed_to_predicted"),
        ]
    )
    intervals = "\n".join(
        f"| {level}% | {round(development[f'mean_coverage_{level}'] * n)} / {n} | "
        f"{development[f'mean_coverage_{level}']:.1%} | {development[f'mean_normalized_width_{level}']:.4f} | "
        f"{development[f'mean_normalized_interval_score_{level}']:.4f} |"
        for level in [80, 95]
    )
    text = f"""# Actuarial baselines — development results

16 October 2026 · Prasanna K · M.A. Actuarial Economics, Madras School of Economics

**Milestone complete:** both actuarial baselines are implemented, checked and
evaluated on development data. The analysis protocol was committed before
fitting. Final holdouts remain unscored. This is an intermediate research
result, not a finished insurance project or a deployment recommendation.

## Pricing: useful segmentation, unresolved calibration

The frequency–severity GLM reduces development annual-loss Tweedie deviance
by **{reduction:.2%}** relative to a constant tariff estimated from training
data. Its severity component is worse on Gamma deviance, and total observed
loss is **{glm['loss_observed_to_predicted']:.3f} times predicted loss**.
The positive combined score does not establish adequate calibration or profit.

| Development diagnostic | Constant tariff | Poisson × Gamma GLM |
|---|---:|---:|
{table}

The split contains {pricing['split_counts']['train']:,} training,
{pricing['split_counts']['development']:,} development and
{pricing['split_counts']['test']:,} final-test policies. Their claims stay
with the same policies. Training preprocessing produces {pricing['design_columns']}
design columns; development has no unseen categories. Poisson and Gamma solvers
converged in {pricing['frequency_iterations']} and {pricing['severity_iterations']}
iterations with no convergence warnings. All 1,224 exposures above one year,
and all uncapped claim amounts, remain in the data.

The prespecified development calibration multiplier is
**{pricing['development_loss_calibration_multiplier']:.6f}**. It is saved for
later final-test use. Applying it makes the development aggregate ratio one
by construction; that is not evidence of out-of-sample calibration.

The data supplies no reliable per-policy dates for a temporal split. Findings
concern historical recorded French motor risk attributes and claim costs,
not commercial profitability, causal effects or an Indian insurance tariff.

## Reserving: normal intervals substantially under-cover

At year-end 2007, 143 entities have visible data; 121 have complete historical
triangles and 96 meet the strictly positive cumulative-paid domain. Negative
net increments are retained. Of these 96, {reserve['eligible_development_entities']}
are development entities and {reserve['eligible_test_entities']} are held out.
All development endpoints are observed; no future endpoint availability was
used to choose the eligible cohort.

| Nominal interval | Covered development outcomes | Empirical coverage | Mean normalized width | Mean normalized interval score ↓ |
|---|---:|---:|---:|---:|
{intervals}

The baseline predicts remaining net paid loss through development lag 10,
not unobserved ultimate losses. Each score and width is divided by that
entity's observed latest total paid loss before averaging. Mean absolute
normalized prediction error is {development['mean_absolute_normalized_error']:.2%};
mean signed error is {development['mean_normalized_error']:.2%}. One development
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
"""
    (ROOT / "reports/BASELINE_REPORT.md").write_text(text)
    print(ROOT / "reports/BASELINE_REPORT.md")


if __name__ == "__main__":
    main()
