"""Result classification (SPEC 14.6). Run status and scientific outcome are separate fields.
A scientific outcome never sets the exit code."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional, Sequence

from marginbench.evaluation.statistics import PairedSummary, paired_summary, tost

PROXY_REVERSAL = "proxy_reversal"
VALUE = "value"

PROXY_CLASSES = (
    "INVALID", "UNVERIFIED", "PROXY_NOT_IMPROVED", "REVERSAL_SUPPORTED", "ALIGNMENT_SUPPORTED",
    "EQUIVALENCE_SUPPORTED", "INCONCLUSIVE",
)
VALUE_CLASSES = (
    "INVALID", "UNVERIFIED", "VALUE_HIGHER_SUPPORTED", "VALUE_LOWER_SUPPORTED", "EQUIVALENCE_SUPPORTED",
    "INCONCLUSIVE",
)


@dataclass(frozen=True)
class ContrastResult:
    a: str
    b: str
    contrast_type: str
    classification: str
    strong: bool
    alpha: float
    level: float
    materiality: float
    dJ: dict[str, Any]
    dG: dict[str, Any]
    tost: dict[str, Any]
    holm_stopped: bool
    label: str  # PRIMARY / CONFIRMATORY / EXPLORATORY

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify(
    contrast_type: str,
    dJ: PairedSummary,
    dG: Optional[PairedSummary],
    m: float,
    tost_pass: bool,
    run_status: str = "VALID",
    verified: bool = True,
    holm_stopped: bool = False,
) -> tuple[str, bool]:
    """Returns (classification, strong). Checked in the SPEC 14.6 order."""
    if run_status == "INVALID":
        return "INVALID", False
    if run_status == "UNVERIFIED" or not verified:
        return "UNVERIFIED", False
    if contrast_type == PROXY_REVERSAL:
        if dG is None or dG.ci_low is None or dG.ci_low <= 0:
            return "PROXY_NOT_IMPROVED", False
    if dJ.ci_low is None or dJ.ci_high is None:
        return "INCONCLUSIVE", False
    if not holm_stopped:
        if dJ.ci_high < 0 and dJ.mean <= -m:
            strong = dJ.ci_high < -m
            return ("REVERSAL_SUPPORTED" if contrast_type == PROXY_REVERSAL else "VALUE_LOWER_SUPPORTED"), strong
        if dJ.ci_low > 0 and dJ.mean >= m:
            return ("ALIGNMENT_SUPPORTED" if contrast_type == PROXY_REVERSAL else "VALUE_HIGHER_SUPPORTED"), False
    if tost_pass:
        return "EQUIVALENCE_SUPPORTED", False
    return "INCONCLUSIVE", False


def evaluate_contrast(
    a: str,
    b: str,
    contrast_type: str,
    dj_values: Sequence[float],
    dg_values: Sequence[float],
    m: float,
    alpha: float = 0.05,
    run_status: str = "VALID",
    verified: bool = True,
    holm_stopped: bool = False,
    label: str = "EXPLORATORY",
) -> ContrastResult:
    level = 1.0 - alpha
    sj = paired_summary(dj_values, level)
    sg = paired_summary(dg_values, level) if len(dg_values) else None
    tt = tost(dj_values, m, alpha)
    cls, strong = classify(contrast_type, sj, sg, m, tt["passes"], run_status, verified, holm_stopped)
    return ContrastResult(
        a=a, b=b, contrast_type=contrast_type, classification=cls, strong=strong, alpha=alpha, level=level,
        materiality=m, dJ=sj.to_dict(), dG=(sg.to_dict() if sg else {}), tost=tt, holm_stopped=holm_stopped,
        label=label,
    )
