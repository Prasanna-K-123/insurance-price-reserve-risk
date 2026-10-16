"""Build explanatory reports and a static figure from frozen final aggregates."""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def interval_text(comparison, digits=6):
    lower, upper = comparison["ci95_percentile"]
    return f"{comparison['estimate']:+.{digits}f} [{lower:+.{digits}f}, {upper:+.{digits}f}]"


def make_figure(pricing, reserve):
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10,
        "axes.spines.top":False,"axes.spines.right":False,"svg.fonttype":"none",
        "svg.hashsalt":"insurance-risk-fixed-study-v1"})
    fig, axes = plt.subplots(1,2,figsize=(11.5,4.8))
    colors={"glm":"#2563a7","hgb":"#bd4d20"}
    age_keys=["[-inf, 21.0)","[21.0, 26.0)","[26.0, 36.0)","[36.0, 51.0)","[51.0, 66.0)","[66.0, 81.0)","[81.0, inf)"]
    for model in ["glm","hgb"]:
        lookup={row["group"]:row["observed_to_predicted"] for row in pricing["models"][model]["age_groups"]}
        axes[0].plot(range(7),[lookup[k] for k in age_keys],marker="o",linewidth=1.8,color=colors[model],label=model.upper())
    axes[0].axhline(1,color="#59636d",linestyle="--",linewidth=1)
    axes[0].set_xticks(range(7),["<21","21–25","26–35","36–50","51–65","66–80","81+"])
    axes[0].set_ylim(0,5.2)
    axes[0].set_title("Pricing: conditional calibration",loc="left",fontweight="bold",pad=14)
    axes[0].set_xlabel("Driver age (years)")
    axes[0].set_ylabel("Held-out observed / predicted loss")
    axes[0].legend(frameon=False)
    axes[0].text(6,1.1,"Ideal aggregate ratio = 1",ha="right",fontsize=8.5,color="#59636d")
    for index, year in enumerate(["2007","2009"]):
        evaluation=reserve["valuations"][year]["evaluation"]
        diagnostic=evaluation["mack"]
        coverage=diagnostic["coverage_95"]
        lower,upper=diagnostic["coverage_95_wilson95"]
        axes[1].errorbar(index,coverage,yerr=np.array([[coverage-lower],[upper-coverage]]),fmt="o",color=colors['glm'],capsize=5,markersize=7)
        axes[1].annotate(f"{diagnostic['covered_95']}/{evaluation['scored_entities']}",(index,coverage),xytext=(13,0),textcoords="offset points",va="center",fontsize=10)
    axes[1].axhline(.95,color="#59636d",linestyle="--",linewidth=1)
    axes[1].text(.5,.961,"Nominal 95%",ha="center",fontsize=9,color="#59636d")
    axes[1].set_xticks([0,1],["2007 · primary","2009 · secondary"])
    axes[1].set_xlim(-.45,1.45)
    axes[1].set_ylim(.55,1.005)
    axes[1].yaxis.set_major_formatter(PercentFormatter(xmax=1))
    axes[1].set_title("Reserving: coverage falls short",loc="left",fontweight="bold",pad=14)
    axes[1].set_ylabel("Held-out coverage of 95% intervals")
    axes[1].set_xlabel("Both methods have identical observed coverage")
    for ax in axes:
        ax.grid(axis="y",alpha=.18)
    fig.subplots_adjust(left=.075,right=.97,top=.84,bottom=.2,wspace=.35)
    fig.suptitle("Better average prediction does not establish adequacy",x=.075,y=.975,ha="left",fontweight="bold",fontsize=14)
    fig.text(.075,.055,"Development-frozen models. Age ratios are descriptive and tail-sensitive; Wilson intervals assume independent entities.",fontsize=8.5,color="#59636d")
    fig.savefig(ROOT/"reports/validation_diagnostics.svg",metadata={"Date":None},facecolor="white")
    fig.savefig(ROOT/"artifacts/validation_diagnostics.png",dpi=160,facecolor="white")
    plt.close(fig)


def main():
    pricing=json.loads((ROOT/"reports/pricing_final.json").read_text())
    reserve=json.loads((ROOT/"reports/reserve_final.json").read_text())
    freeze=json.loads((ROOT/"reports/model_freeze.json").read_text())
    glm,hgb=pricing["models"]["glm"],pricing["models"]["hgb"]
    p=pricing["primary_difference_hgb_minus_glm"]
    reduction=1-hgb["calibrated_tweedie_deviance"]/glm["calibrated_tweedie_deviance"]
    primary=reserve["valuations"]["2007"]["evaluation"]
    secondary=reserve["valuations"]["2009"]["evaluation"]
    r=primary["primary_interval_score_difference"]
    youngest=next(x for x in hgb["age_groups"] if x["group"]=="[-inf, 21.0)")
    make_figure(pricing,reserve)
    pricing_table="\n".join(f"| {label} | {g:.6f} | {h:.6f} |" for label,g,h in [
        ("Calibrated annual-cost Tweedie deviance ↓",glm["calibrated_tweedie_deviance"],hgb["calibrated_tweedie_deviance"]),
        ("Calibrated aggregate observed / predicted loss",glm["calibrated_loss_observed_to_predicted"],hgb["calibrated_loss_observed_to_predicted"]),
        ("Uncalibrated frequency Poisson deviance ↓",glm["uncalibrated"]["frequency_poisson_deviance"],hgb["uncalibrated"]["frequency_poisson_deviance"]),
        ("Uncalibrated severity Gamma deviance ↓",glm["uncalibrated"]["severity_gamma_deviance"],hgb["uncalibrated"]["severity_gamma_deviance"]),
    ])
    reserve_rows=[]
    for year,data in [("2007 primary",primary),("2009 secondary",secondary)]:
        for name,label in [("mack","Mack-normal"),("simulation","Positive simulation")]:
            d=data[name]
            reserve_rows.append(f"| {year} | {label} | {data['scored_entities']} | {d['covered_95']}/{data['scored_entities']} ({d['coverage_95']:.1%}) | {d['mean_normalized_score_95']:.6f} | {d['mean_normalized_width_95']:.6f} |")
    technical=f"""# Insurance loss modelling: prediction, calibration and reserve uncertainty

Prasanna K · M.A. Actuarial Economics, Madras School of Economics · 16 October 2026

## Decisions supported by this study

Select the boosted frequency–severity model as the historical pricing
benchmark under the prespecified rule. Its final-test annual-loss deviance is
**{reduction:.2%} lower** than the development-calibrated GLM's, with paired
difference **{interval_text(p)}** (95% bootstrap interval). Retain Mack as the
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
family is estimated on development data: GLM **{freeze['calibration']['glm']:.6f}**,
HGB **{freeze['calibration']['hgb']:.6f}**. These are held fixed on test data.

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

The final sample contains {pricing['policies']:,} policies, {pricing['claims']:,}
claims and {glm['uncalibrated']['exposure_years']:,.2f} exposure-years. Smaller
deviance is better. The primary metric is exposure-weighted Tweedie deviance
at power 1.5 for annual expected loss cost, after frozen development calibration.

| Held-out diagnostic | GLM | HGB |
|---|---:|---:|
{pricing_table}

The paired HGB-minus-GLM contrast is **{interval_text(p)}**. It uses 1,000
policy bootstraps with the same policy indices for both models and a
recomputed exposure denominator. The interval lies below zero, meeting the
fixed selection rule. This interval conditions on fitted models and calibration;
it excludes training-sample and model-selection uncertainty.

The gain concerns the combined loss-cost target. HGB's severity-component
deviance is worse, and its uncalibrated total loss is materially underpredicted.
Development calibration improves the combined comparison but does not deliver
uniform calibration: the test observed/predicted aggregate ratio is
**{hgb['calibrated_loss_observed_to_predicted']:.3f}**, and the under-21 group is
**{youngest['observed_to_predicted']:.3f}** across {youngest['claims']} claims.
No fairness, causal or legal-pricing conclusion follows from these descriptive
age/region diagnostics. Application requires fresh validation of conditional
calibration, observation timing and business costs.

The ten largest-loss policies account for
**{pricing['tail_sensitivity']['removed_actual_loss_fraction']:.2%}** of test
losses. The prespecified diagnostic excluding them retains a negative paired
deviance difference, **{pricing['tail_sensitivity']['paired_deviance_difference_remaining']:+.6f}**.
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
{chr(10).join(reserve_rows)}

The primary 2007 simulation-minus-Mack score contrast is
**{interval_text(r)}**, using 1,000 paired entity bootstraps. It does not meet
the improvement rule, so retain Mack as the reference. Both methods cover
36/43 outcomes with nominal95% intervals and 23/43 with nominal80% intervals.
The 95% coverage Wilson interval is
[{primary['mack']['coverage_95_wilson95'][0]:.1%},
{primary['mack']['coverage_95_wilson95'][1]:.1%}], under an independence
interpretation. Nominal coverage is not achieved empirically.

The secondary 2009 contrast is
**{interval_text(secondary['primary_interval_score_difference'])}** and cannot
change the primary decision. Both methods cover 32/42 outcomes with nominal95%
intervals and 24/42 with nominal80% intervals. The shared point prediction's
mean absolute normalized error falls from {primary['mean_absolute_normalized_error']:.2%}
at 2007 to {secondary['mean_absolute_normalized_error']:.2%} at 2009 as more
development is observed; this is not an independent sample comparison.

Resampling entities treats them as sufficiently independent. Corporate links
and common calendar shocks may invalidate that approximation. The finite
2,000-draw quantiles carry Monte Carlo noise; the simulation's mean absolute
normalized Monte Carlo mean error is
{primary['simulation_mean_absolute_mc_error_normalized']:.6f} in the primary
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
"""
    memo=f"""# Decision memo — insurance model selection

Prasanna K · 16 October 2026

**Pricing decision:** select the boosted frequency–severity model for this
historical research comparison. On {pricing['policies']:,} held-out policies,
it reduces the prespecified annual-loss deviance by **{reduction:.2%}** against
the development-calibrated Poisson/Gamma GLM. Paired difference and95% bootstrap
interval: **{interval_text(p)}**.

**Reserve decision:** retain Mack as the transparent reference. On43 held-out
entities at year-end2007, the positive stochastic simulation's interval-score
difference is **{interval_text(r)}**. The evidence does not establish an
improvement. Both methods cover only **36/43 (83.7%)** of outcomes with
nominal95% intervals. The secondary2009 view also under-covers.

**Application boundary:** the pricing result does not approve a live tariff.
The HGB aggregate observed/predicted ratio is
{hgb['calibrated_loss_observed_to_predicted']:.3f}; its under-21 age-group ratio
is {youngest['observed_to_predicted']:.3f}. Its severity-component deviance is
worse than the GLM's. These conditional-calibration failures and heavy claim
tails require fresh validation before practical pricing decisions. The reserve
findings require explicit uncertainty and assumption review before anyone
relies on nominal coverage. No commercial savings or regulatory adequacy is
inferred.

**What makes the evidence defensible:**

- Reconciled677,991 policies and26,444 claims; preserved all recorded exposures
  and uncapped losses; claims stay with their policy in the fixed split.
- Restricted reserve fitting to information visible at each valuation;
  retained negative net increments inside a declared positive-cumulative domain.
- Committed the protocol before fitting and sealed models, calibration,
  computational source and forecasts before final scoring.
- Used paired evaluation and preserved the result when the more elaborate
  reserve method failed to demonstrate an advantage. Eighteen numerical and
  information-boundary tests passed.

**A concise project explanation:** “I built two separate insurance studies:
French motor loss-cost modelling and U.S. net-paid reserving. I compared
exposure-aware GLMs with fixed boosting models, and Mack uncertainty with a
positive factor/process simulation. The held-out pricing score improved, while
conditional calibration remained weak; the reserve simulation did not improve
the primary interval score. I preserved those findings and documented why they
do not establish deployment readiness.”

[Technical report](TECHNICAL_REPORT.md) · [Protocol](../docs/PROTOCOL.md) ·
[Verified outputs](final_verification.json)
"""
    # Keep prose spacing intentional in the generated documents.
    for before,after in [("and95%","and 95%"),("On43","On 43"),("year-end2007","year-end 2007"),("nominal95%","nominal 95%"),("nominal80%","nominal 80%"),("secondary2009","secondary 2009"),("Reconciled677","Reconciled 677"),("and26,444","and 26,444")]:
        technical,memo=technical.replace(before,after),memo.replace(before,after)
    (ROOT/"reports/TECHNICAL_REPORT.md").write_text(technical)
    (ROOT/"reports/DECISION_MEMO.md").write_text(memo)
    print("Technical report, decision memo and validation figure generated from final aggregates")


if __name__ == '__main__':
    main()
