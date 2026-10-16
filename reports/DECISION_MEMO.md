# Decision memo — insurance model selection

Prasanna K · 16 October 2026

**Pricing decision:** select the boosted frequency–severity model for this
historical research comparison. On 135,198 held-out policies,
it reduces the prespecified annual-loss deviance by **1.82%** against
the development-calibrated Poisson/Gamma GLM. Paired difference and 95% bootstrap
interval: **-1.449756 [-2.235887, -0.612689]**.

**Reserve decision:** retain Mack as the transparent reference. On 43 held-out
entities at year-end 2007, the positive stochastic simulation's interval-score
difference is **+0.001709 [-0.002275, +0.006535]**. The evidence does not establish an
improvement. Both methods cover only **36/43 (83.7%)** of outcomes with
nominal 95% intervals. The secondary 2009 view also under-covers.

**Application boundary:** the pricing result does not approve a live tariff.
The HGB aggregate observed/predicted ratio is
0.948; its under-21 age-group ratio
is 4.721. Its severity-component deviance is
worse than the GLM's. These conditional-calibration failures and heavy claim
tails require fresh validation before practical pricing decisions. The reserve
findings require explicit uncertainty and assumption review before anyone
relies on nominal coverage. No commercial savings or regulatory adequacy is
inferred.

**What makes the evidence defensible:**

- Reconciled 677,991 policies and 26,444 claims; preserved all recorded exposures
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
