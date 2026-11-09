"""Claim audit (SPEC 19.2): every claim lists metric, contrast, scenario, cohort, horizon,
estimate, CI, units, run_id and artifact path. Generated only from analysis artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

SUPPORTED = {"REVERSAL_SUPPORTED", "ALIGNMENT_SUPPORTED", "VALUE_HIGHER_SUPPORTED", "VALUE_LOWER_SUPPORTED",
             "EQUIVALENCE_SUPPORTED"}

SENTENCE = {
    "REVERSAL_SUPPORTED": "{a} raised the proxy and lowered simulated operator contribution relative to {b}",
    "ALIGNMENT_SUPPORTED": "{a} raised the proxy and raised simulated operator contribution relative to {b}",
    "VALUE_HIGHER_SUPPORTED": "{a} had higher simulated operator contribution than {b}",
    "VALUE_LOWER_SUPPORTED": "{a} had lower simulated operator contribution than {b}",
    "EQUIVALENCE_SUPPORTED": "{a} and {b} were equivalent in simulated operator contribution within the materiality band",
    "PROXY_NOT_IMPROVED": "{a} did not improve the proxy over {b}, so no proxy-reversal claim is made",
    "INCONCLUSIVE": "the contrast {a} vs {b} was inconclusive",
    "INVALID": "the run was invalid; no claim",
    "UNVERIFIED": "required reproducibility or validation evidence is missing; no claim",
}


def build_claim_audit(run_id: str, exp_id: str, spec: dict[str, Any], analyses: dict[str, Any],
                      cross: dict[str, Any], out: Path, label: str) -> dict[str, Any]:
    claims = []
    t = None
    for world, an in analyses.items():
        for key, c in an["contrasts"].items():
            dj, dg = c["dJ"], c["dG"]
            cls = c["classification"]
            claims.append({
                "claim": SENTENCE[cls].format(a=c["a"], b=c["b"]) + f" (scenario {world}, experiment {exp_id})",
                "classification": cls,
                "strong": c["strong"],
                "supported": cls in SUPPORTED,
                "evidence_level": "Level 1 (synthetic, one declared configuration)",
                "label": c["label"],
                "metric": "J: discounted operator contribution, days 30-299 (or the scenario's window)",
                "proxy_metric": "G: proxy_v1",
                "contrast": key,
                "scenario": world,
                "cohort": "decision cohort (arrivals in the decision window)",
                "horizon": "business-value window per scenario config",
                "estimate": dj.get("mean"),
                "ci": [dj.get("ci_low"), dj.get("ci_high")],
                "ci_level": c["level"],
                "p_value": dj.get("p_value"),
                "dG_estimate": dg.get("mean") if dg else None,
                "dG_ci": [dg.get("ci_low"), dg.get("ci_high")] if dg else None,
                "materiality": c["materiality"],
                "n": dj.get("n"),
                "units": "USD (J), dimensionless (G)",
                "run_id": run_id,
                "artifact": str(out / "metrics.json"),
                "evaluation_label": label,
            })
    return {"run_id": run_id, "experiment": exp_id, "claims": claims,
            "cross_world_exploratory": cross,
            "never_claimed": ["Level 3 external validation", "real-world probability of any class",
                              "deployability of any oracle"]}
