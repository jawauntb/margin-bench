# LIMITATIONS

- **Synthetic validity only.** Every result is Level-1 (one declared configuration) or, at most, Level-2 (the declared sensitivity design and ablations). Nothing here is external (Level-3) validation, and no parameter is calibrated to real data.
- **No tenant move-outs.** Tenants never leave, so tenant dissatisfaction has no rent or vacancy channel.
- **No contract replacement.** A lost management contract is never replaced; the portfolio only shrinks.
- **First-order retention term in planning.** Economic policies value retention with the declared first-order formula (SPEC 9.1), not the true hazard dynamics.
- **No congestion shadow price.** Planning sees congestion only through observed queues and lead times; a dispatch's delay to other requests is not priced.
- **Censoring and selection in estimator labels.** The success model's SPEC labels come only from verified attempts or callbacks; callbacks are censored at 60 days; the report delay is fit on censored delays; the loss hazard uses a model-based exposure. The audit (`models/estimator_audit.json`) shows the remaining errors against truth: verification sensitivity is underestimated (about 0.76 vs 0.90), callback reporting and the severe-loss hazard are biased low, and the retention coefficients are weakly identified (about 70 terminations in history).
- **Tail estimation.** Severe losses are rare; tail metrics are bootstrapped and labeled unreliable when fewer than 20 replications contain a loss.
- **In-process isolation only.** The information boundary is a software contract enforced by tests (allowlist serializer, AST import check, reference-path introspection), not a security sandbox.
- **Open preregistration only.** The plan is committed before the locked runs and git history proves the ordering; the evaluation is not blind and the seeds are not secret.
- **No external calibration.** Arrival rates, contractor quality, reporting behaviour, verification accuracy, loss sizes, fees and retention are all fixtures.
- **Single-request planning.** Rollouts simulate one request at a time; portfolio-level interactions (capacity shared across requests, property-level retention coupling) enter only through observed state.
- **Handover simplification.** When a contract terminates, its open requests leave the system (DECISIONS D-05).
