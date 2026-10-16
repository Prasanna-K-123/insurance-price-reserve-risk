# Computational details fixed before final evaluation

16 October 2026. These details implement the existing protocol; they do not
change the model budgets, split, targets or decision rules.

- scikit-learn 1.8.0 supplies the Poisson/Gamma HGB log links. Five training-only
  categorical vocabularies are encoded as integers and declared categorical;
  unseen categories map to missing. Continuous driver/vehicle age, BonusMalus
  and log(1+density) complete the nine-feature design. No early stopping.
- Each reserve entity and valuation has an independent deterministic stream:
  first 64 bits of SHA256 of `reserve-simulation:seed:valuation:entity`.
  Factor uncertainty is shared across origins at each development age;
  conditional process draws are separate. The point forecast is the common
  chain-ladder mean; the simulation changes intervals, not the selected mean.
- Reserve currency rescaling must leave normalized comparisons unchanged.
  Monte Carlo quantile noise remains part of the finite 2,000-draw procedure;
  no seed search, simulation-budget search or outcome-based clipping is allowed.
- Bootstrap seeds are base seed +101 for pricing, +200 for reserve development,
  +201 for the 2007 final comparison and +202 for 2009. Resampling uses the
  same selected policy/entity indices for both methods. The pricing statistic
  recomputes its exposure denominator within each resample.
- Pricing risk-decile thresholds come from training-policy predictions using
  the development-frozen calibration multiplier. They are frozen before
  final-test scoring. Age/region summaries are descriptive; fewer than 30
  claims are explicitly marked sparse. The top-ten-loss removal is the
  predeclared tail diagnostic, not a second model-selection result.
- The final-evaluation script checks configuration, protocol, computational
  source and fitted-artifact hashes against `reports/model_freeze.json`.
  Private reserve forecasts for both dates are sealed before test endpoints
  are scored. The same calculation checks the seal again after evaluation.
- Wilson coverage intervals are descriptive binomial intervals; common
  calendar/corporate dependence can invalidate an independence interpretation.
  Paired bootstraps condition on the fitted models and calibration, and do not
  include training-sample or model-selection uncertainty.

The dependency behavior was checked against the [official versioned HGB API](https://scikit-learn.org/1.8/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html).
