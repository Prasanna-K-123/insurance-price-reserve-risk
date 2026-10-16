# Release status

The scientific analysis, explanatory reports and source reproduction are
complete. The repository is still a private working repository. **No public
demonstration or v1.0.0 release is claimed.**

Completed deliverables:

- Reconciled source audit and frozen protocol.
- Fixed actuarial baselines and bounded challengers.
- Prespecified final comparisons and failure diagnostics.
- Technical report, decision memo and diagnostic figure.
- Fresh source/output-directory reproduction: 18 tests and ten byte-identical
  regenerated analysis outputs in the same environment.
- Offline explorer of aggregate calibration, reserve coverage and explicitly
  illustrative pricing assumptions; 15 script-level checks pass.
- [Explorer verification evidence](../reports/demo_verification.json), which
  explicitly distinguishes script execution from rendered-browser QA.

Remaining release gates are bounded:

1. Verify the rendered explorer and its controls in a supported browser at
   desktop and mobile widths. Script-level checks do not replace this.
2. Make the approved repository public and enable GitHub Pages for `main/docs`.
3. Confirm the live demonstration and report links, then create and verify a
   v1.0.0 tag/release at the final checked commit.
4. Add the accurate project entry to the portfolio profile. Do not remove old
   material as a side effect of this release step.

The currently exposed GitHub connection can save source commits but does not
expose repository-visibility, Pages or release-creation operations. The browser
integration needed for the remaining checks is not currently available through
the supported managed-preview route. Existing credential-protection failures
must not be bypassed. These are publication/verification limits, not unresolved
model-fitting work.

## Prepared release description

Insurance pricing and reserve uncertainty: two independent research case studies.

- Audited 677,991 French motor policies and 26,444 linked claims.
- Compared exposure-aware Poisson/Gamma GLMs with fixed histogram boosting.
  The calibrated combined score improves by 1.82% on 135,198 held-out policies,
  while conditional calibration and severity-component limitations remain.
- Compared Mack-normal intervals with a positive shared-factor/process
  simulation on a valuation-separated U.S. paid-loss panel. Simulation does
  not establish an interval-score advantage. Both methods under-cover.
- Included the frozen protocol, numerical/boundary tests, aggregate evidence,
  source-reproduction checks, decision memo and offline explorer.

No commercial savings, live pricing approval, reserve certification or current
Indian insurer experience is claimed. Raw observations and fitted artifacts
are excluded. This description is prepared for a future release, not evidence
that publication has occurred.
