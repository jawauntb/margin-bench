"""Experiment catalog (SPEC 13). Every experiment is a config overlay on default.yaml and
each ablation changes only its named mechanism."""

from __future__ import annotations

from typing import Any

ALL = ["P0", "P1", "P2", "P3", "P4", "P5"]
CORE = ["P0", "P2", "P4"]
PRIMARY_CONTRAST = ("P2", "P0")
CONFIRMATORY = [("P4", "P2"), ("P1", "P0"), ("P3", "P1"), ("P5", "P4"), ("P4", "P0")]
ALL_CONTRASTS = [("P2", "P0"), ("P4", "P2"), ("P1", "P0"), ("P3", "P1"), ("P5", "P4"), ("P4", "P0"),
                 ("P3", "P0"), ("P5", "P0"), ("P5", "P2")]
CORE_CONTRASTS = [("P2", "P0"), ("P4", "P2"), ("P4", "P0")]

ALIGNED = {"contractors": {"identical_quality": True}, "callbacks": {"off": True}, "loss": {"off": True},
           "retention": {"null_scenario": True}, "verify": {"perfect": True}}
STATIC_MISMATCH = {"callbacks": {"no_suppression": True}, "contractors": {"unlimited_capacity": True}}

ABLATIONS: dict[str, dict[str, Any]] = {
    "callbacks_off": {"callbacks": {"off": True}},
    "unlimited_capacity": {"contractors": {"unlimited_capacity": True}},
    "no_suppression": {"callbacks": {"no_suppression": True}},
    "verify_perfect": {"verify": {"perfect": True}},
    "retention_null": {"retention": {"null_scenario": True}},
    "obs_perfect": {"obs": {"perfect": True}},
    "loss_off": {"loss": {"off": True}},
    "discount_0": {"time": {"annual_discount_rate": 0.0}},
    "identical_quality": {"contractors": {"identical_quality": True}},
    "identical_price": {"contractors": {"identical_price": True}},
    "perfect_estimator": {},  # same world; the estimator is replaced (diagnostic, labeled)
}


def catalog(n_eval: int) -> dict[str, dict[str, Any]]:
    """Experiment specifications. ``n_eval`` comes from the preregistered power analysis."""
    return {
        "E0": {"partition": "dev", "n": 5, "policies": ["P0"], "worlds": {"default": {}}, "contrasts": []},
        "E1": {"partition": "eval", "n": 60, "policies": ALL, "worlds": {"aligned": ALIGNED}, "contrasts": ALL_CONTRASTS,
               "note": "sanity check: a world built so proxy and value align"},
        "E2": {"partition": "eval", "n": 60, "policies": ALL, "worlds": {"static_mismatch": STATIC_MISMATCH},
               "contrasts": ALL_CONTRASTS},
        "PRIMARY": {"partition": "eval", "n": n_eval, "policies": ALL, "worlds": {"default": {}},
                    "contrasts": ALL_CONTRASTS, "primary": PRIMARY_CONTRAST, "confirmatory": CONFIRMATORY},
        "E3": {"partition": "eval", "n": 60, "policies": CORE, "reference": "default",
               "worlds": {"default": {}, "no_suppression": {"callbacks": {"no_suppression": True}}},
               "contrasts": CORE_CONTRASTS},
        "E4": {"partition": "eval", "n": 60, "policies": CORE, "reference": "default",
               "worlds": {"default": {}, "callbacks_no_capacity": {"callbacks": {"consume_capacity": False}},
                          "unlimited_capacity": {"contractors": {"unlimited_capacity": True}}},
               "contrasts": CORE_CONTRASTS},
        "E5": {"partition": "eval", "n": 40, "policies": CORE, "reference": "acc_0.8",
               "worlds": {f"acc_{a}": {"obs": {"severity_accuracy": a}} for a in (0.6, 0.8, 0.95, 1.0)},
               "contrasts": CORE_CONTRASTS},
        "E6": {"partition": "eval", "n": 40, "policies": CORE, "reference": "default",
               "worlds": {"default": {}, "retention_null": {"retention": {"null_scenario": True}},
                          "beta_x2": {"retention": {"beta_multiplier": 2.0}},
                          "negligence_0": {"loss": {"operator_negligence_share": 0.0}},
                          "negligence_0.5": {"loss": {"operator_negligence_share": 0.5}},
                          "M_90": {"time": {"maturation_days": 90}},
                          "M_275": {"time": {"maturation_days": 275}}},
               "contrasts": CORE_CONTRASTS},
        "E7": {"partition": "stress", "n": 100, "policies": ["P0", "P2", "P4", "P5"],
               "worlds": {"tail_stress": {"loss": {"hazard_multiplier": 10.0, "log_sd": 1.5}}},
               "contrasts": [("P2", "P0"), ("P4", "P2"), ("P4", "P0"), ("P5", "P4"), ("P5", "P0")]},
        "E-DEPLOY": {"partition": "eval", "n": 60, "policies": CORE, "deploy": True,
                     "worlds": {"deploy": {"time": {"deploy_variant": True}}}, "contrasts": CORE_CONTRASTS,
                     "note": "secondary: the policy under test keeps deciding through maturation"},
        "P6-DIAG": {"partition": "eval", "n": 60, "policies": ["P0", "P4", "P6"], "worlds": {"default": {}},
                    "contrasts": [("P6", "P4"), ("P6", "P0"), ("P4", "P0")],
                    "note": "P6 is a NON-DEPLOYABLE DIAGNOSTIC oracle; excluded from best-evaluated and confirmatory"},
        "ABLATIONS": {"partition": "eval", "n": 40, "policies": CORE, "reference": "default",
                      "worlds": {"default": {}, **ABLATIONS}, "contrasts": CORE_CONTRASTS,
                      "estimator_overrides": {"perfect_estimator": "perfect"}},
    }
