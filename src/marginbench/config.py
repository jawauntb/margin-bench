"""Validated configuration (SPEC 5, 17). Every parameter is synthetic (ASSUMPTIONS.md).

Configs are YAML. Experiment configs are overlays deep-merged onto ``configs/default.yaml``.
Unknown keys are rejected (``extra='forbid'``).
"""

from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from marginbench.hashing import canonical_hash

CATEGORIES: tuple[str, ...] = ("plumbing", "electrical", "hvac", "general")
SEVERITIES: tuple[str, ...] = ("minor", "moderate", "urgent")
Category = Literal["plumbing", "electrical", "hvac", "general"]

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "default.yaml"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Versions(Strict):
    sim_version: str
    policy_version: str
    metric_version: str
    proxy_version: Literal["proxy_v1"]
    stream_schema: str


class TimeCfg(Strict):
    warmup_days: int = Field(ge=1)
    decision_days: int = Field(ge=1)
    maturation_days: int = Field(ge=0)
    proxy_cutoff_offset_days: int = Field(ge=0)
    annual_discount_rate: float = Field(ge=0.0, le=1.0)
    deploy_variant: bool
    history_days: int = Field(ge=1)
    generation_days: int = Field(ge=1)

    @property
    def horizon_days(self) -> int:
        return self.warmup_days + self.decision_days + self.maturation_days

    @property
    def d0(self) -> int:
        return self.warmup_days

    @property
    def decision_end_day(self) -> int:  # last decision-window day (inclusive)
        return self.warmup_days + self.decision_days - 1

    @property
    def proxy_cutoff_day(self) -> int:  # end of this day is the cutoff
        return self.decision_end_day + self.proxy_cutoff_offset_days

    @property
    def delta(self) -> float:
        return (1.0 + self.annual_discount_rate) ** (-1.0 / 365.0)

    @model_validator(mode="after")
    def _gen_long_enough(self) -> "TimeCfg":
        if self.generation_days < max(self.horizon_days, self.history_days):
            raise ValueError("generation_days must cover the run and history horizons")
        return self


class PortfolioCfg(Strict):
    n_properties: int = Field(ge=1)
    units_per_property: int = Field(ge=1)
    property_risk_log_sd: float = Field(ge=0)
    condition_beta_a: float = Field(gt=0)
    condition_beta_b: float = Field(gt=0)
    condition_obs_noise_sd: float = Field(ge=0)
    tenant_report_beta_a: float = Field(gt=0)
    tenant_report_beta_b: float = Field(gt=0)


class ArrivalsCfg(Strict):
    base_rate_per_unit_day: float = Field(ge=0)
    rate_multiplier: float = Field(ge=0)
    shares: dict[str, float]
    seasonal: bool
    hvac_season_amplitude: float = Field(ge=0, le=1)
    hvac_season_peak_day: int
    heterogeneous: bool

    @field_validator("shares")
    @classmethod
    def _shares(cls, v: dict[str, float]) -> dict[str, float]:
        if set(v) != set(CATEGORIES):
            raise ValueError("shares must cover exactly the four categories")
        if abs(sum(v.values()) - 1.0) > 1e-9:
            raise ValueError("shares must sum to 1")
        return v


class SeverityCfg(Strict):
    probs: dict[str, tuple[float, float, float]]

    @field_validator("probs")
    @classmethod
    def _probs(cls, v: dict[str, tuple[float, float, float]]) -> dict[str, tuple[float, float, float]]:
        if set(v) != set(CATEGORIES):
            raise ValueError("severity probs must cover the four categories")
        for k, p in v.items():
            if any(x < 0 for x in p) or abs(sum(p) - 1.0) > 1e-9:
                raise ValueError(f"severity probs for {k} must be a distribution")
        return v


class ObsCfg(Strict):
    severity_accuracy: float = Field(ge=0, le=1)
    info_accuracy: float = Field(ge=0, le=1)
    info_delay_days: int = Field(ge=1)
    perfect: bool


class ContractorFixture(Strict):
    id: str
    price: float = Field(gt=0)
    success: float = Field(gt=0, lt=1)
    speed: float = Field(gt=0)
    capacity: int = Field(ge=1)
    eligible: tuple[str, ...]

    @field_validator("eligible")
    @classmethod
    def _elig(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if not v or not set(v) <= set(CATEGORIES):
            raise ValueError("eligible must be a non-empty subset of categories")
        return tuple(c for c in CATEGORIES if c in v)


class ContractorsCfg(Strict):
    fixtures: tuple[ContractorFixture, ...]
    logit_success_sd: float = Field(ge=0)
    price_sd: float = Field(ge=0)
    category_offset_sd: float = Field(ge=0)
    success_dispersion: float = Field(ge=0)
    speed_quality_corr: Optional[float] = Field(default=None, ge=-1, le=1)
    price_quality_corr: Optional[float] = Field(default=None, ge=-1, le=1)
    base_lead_days: dict[str, float]
    capacity_multiplier: float = Field(gt=0)
    unlimited_capacity: bool
    identical_quality: bool
    identical_quality_value: float = Field(gt=0, lt=1)
    identical_price: bool
    escalation_delay_minutes: int = Field(ge=0)
    job_duration_median_minutes: float = Field(gt=0)
    job_duration_log_sd: float = Field(ge=0)
    escalation_contractor: str

    @model_validator(mode="after")
    def _check(self) -> "ContractorsCfg":
        ids = [c.id for c in self.fixtures]
        if len(set(ids)) != len(ids) or ids != sorted(ids):
            raise ValueError("contractor ids must be unique and sorted")
        if self.escalation_contractor not in ids:
            raise ValueError("escalation contractor must exist")
        esc = next(c for c in self.fixtures if c.id == self.escalation_contractor)
        if set(esc.eligible) != set(CATEGORIES):
            raise ValueError("escalation contractor must be all-eligible (SPEC 5.13)")
        if set(self.base_lead_days) != set(CATEGORIES):
            raise ValueError("base_lead_days must cover the four categories")
        return self


class RepairCfg(Strict):
    b_sev: dict[str, float]
    condition_coef: float
    condition_center: float
    attempt_coef: float


class ReportCfg(Strict):
    complete_given_success: float = Field(ge=0, le=1)
    complete_given_failure: float = Field(ge=0, le=1)


class VerifyCfg(Strict):
    delay_days: int = Field(ge=1)
    cost: float = Field(ge=0)
    sensitivity: float = Field(ge=0, le=1)
    specificity: float = Field(ge=0, le=1)
    perfect: bool


class CallbacksCfg(Strict):
    m_sev: dict[str, float]
    m_sev_scale: float = Field(ge=0)
    m_close_unverified: float = Field(ge=0, le=1)
    no_suppression: bool
    delay_gamma_shape: float = Field(gt=0)
    delay_gamma_scale_days: float = Field(gt=0)
    benign_prob: float = Field(ge=0, le=1)
    benign_window_days: int = Field(ge=1)
    off: bool
    consume_capacity: bool


class SlaCfg(Strict):
    target_hours: dict[str, int]
    credit: dict[str, float]


class LossCfg(Strict):
    daily_hazard: dict[str, float]
    hazard_multiplier: float = Field(ge=0)
    median_amount: dict[str, float]
    log_sd: float = Field(ge=0)
    operator_negligence_share: float = Field(ge=0, le=1)
    off: bool


class RetentionCfg(Strict):
    annual_base_termination_prob: float = Field(ge=0, lt=1)
    beta_cb: float
    beta_br: float
    beta_sl: float
    beta_oc: float
    beta_multiplier: float = Field(ge=0)
    notice_days: int = Field(ge=0)
    null_scenario: bool

    @property
    def h0(self) -> float:
        return -math.log(1.0 - self.annual_base_termination_prob) / 365.0

    def betas(self) -> dict[str, float]:
        if self.null_scenario:
            return {"cb": 0.0, "br": 0.0, "sl": 0.0, "oc": 0.0}
        m = self.beta_multiplier
        return {"cb": self.beta_cb * m, "br": self.beta_br * m, "sl": self.beta_sl * m, "oc": self.beta_oc * m}


class FeesCfg(Strict):
    per_unit_month: float = Field(ge=0)


class CostsCfg(Strict):
    dispatch: float = Field(ge=0)
    callback: float = Field(ge=0)
    escalation: float = Field(ge=0)
    info: float = Field(ge=0)


class InvoiceCfg(Strict):
    base: dict[str, float]
    severity_multiplier: dict[str, float]


class WorkflowCfg(Strict):
    attempt_limit_failures: int = Field(ge=1)
    max_defers: int = Field(ge=0)


class ProxyCfg(Strict):
    closure_target_days: dict[str, int]
    opex_weight: float
    opex_scale: float = Field(gt=0)


class PlanningCfg(Strict):
    K: int = Field(ge=1)
    H_plan_days: int = Field(ge=0)
    myopic_safety_cap_days: int = Field(ge=1)
    p0_min_success: float = Field(ge=0, le=1)
    p0_prior_success: float = Field(ge=0, le=1)
    p5_loss_floor: float = Field(ge=0)
    p5_loss_slack: float = Field(ge=0)
    p5_sla_floor: float = Field(ge=0)
    p5_sla_slack: float = Field(ge=0)
    p5_close_max_unresolved: float = Field(ge=0, le=1)
    rollout_max_steps: int = Field(ge=4)


class BehaviorCfg(Strict):
    p0_prob: float = Field(ge=0, le=1)


class LimitsCfg(Strict):
    max_events_per_replication: int = Field(ge=1000)
    max_wall_seconds_per_experiment: int = Field(ge=1)


class SeedsCfg(Strict):
    dev: int
    train: int
    calib: int
    eval: int
    stress: int
    sens: int
    pilot: int
    nonce_key: int

    def master(self, partition: str) -> int:
        if partition not in PARTITIONS:
            raise ValueError(f"unknown partition {partition!r}")
        return int(getattr(self, partition))


PARTITIONS: tuple[str, ...] = ("train", "calib", "dev", "eval", "stress", "sens", "pilot")


class Config(Strict):
    versions: Versions
    time: TimeCfg
    portfolio: PortfolioCfg
    arrivals: ArrivalsCfg
    severity: SeverityCfg
    obs: ObsCfg
    contractors: ContractorsCfg
    repair: RepairCfg
    report: ReportCfg
    verify: VerifyCfg
    callbacks: CallbacksCfg
    sla: SlaCfg
    loss: LossCfg
    retention: RetentionCfg
    fees: FeesCfg
    costs: CostsCfg
    invoice: InvoiceCfg
    workflow: WorkflowCfg
    proxy: ProxyCfg
    planning: PlanningCfg
    behavior: BehaviorCfg
    limits: LimitsCfg
    seeds: SeedsCfg

    def config_hash(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))

    # Effective (ablation-aware) parameter accessors -------------------------------
    def sev_accuracy(self) -> float:
        return 1.0 if self.obs.perfect else self.obs.severity_accuracy

    def verify_rates(self) -> tuple[float, float]:
        if self.verify.perfect:
            return 1.0, 1.0
        return self.verify.sensitivity, self.verify.specificity

    def m_close_unverified(self) -> float:
        return 1.0 if self.callbacks.no_suppression else self.callbacks.m_close_unverified

    def m_sev(self, sev: str) -> float:
        return min(1.0, self.callbacks.m_sev[sev] * self.callbacks.m_sev_scale)

    def loss_hazard(self, sev: str) -> float:
        return 0.0 if self.loss.off else self.loss.daily_hazard[sev] * self.loss.hazard_multiplier

    def contractor_ids(self) -> tuple[str, ...]:
        return tuple(c.id for c in self.contractors.fixtures)


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict) and not k.startswith("="):
            out[k] = deep_merge(out[k], v)
        else:
            out[k.lstrip("=")] = copy.deepcopy(v)
    return out


def load_yaml(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    return data


def load_config(path: str | Path | None = None, overlays: list[dict[str, Any]] | None = None) -> Config:
    """Load default.yaml, then the file at ``path`` as an overlay (if it is not default), then overlays."""
    data = load_yaml(DEFAULT_CONFIG)
    if path is not None and Path(path).resolve() != DEFAULT_CONFIG.resolve():
        over = load_yaml(path)
        over.pop("experiment", None)
        data = deep_merge(data, over.get("overlay", over))
    for ov in overlays or []:
        data = deep_merge(data, ov)
    return Config.model_validate(data)


def config_from_dict(data: dict[str, Any]) -> Config:
    return Config.model_validate(data)


class PublicConfig(Strict):
    """What policies may see about the world: public contract and cost terms, the clock,
    the workflow rules and planning settings. No seeds, partitions, replication indices,
    or latent mechanism parameters (SPEC 11, 18.4)."""

    sim_minutes_per_day: int
    units_per_property: int
    contractor_ids: tuple[str, ...]
    categories: tuple[str, ...]
    severities: tuple[str, ...]
    fee_per_unit_day: float
    costs: dict[str, float]
    verify_cost: float
    sla_target_hours: dict[str, int]
    sla_credit: dict[str, float]
    closure_target_days: dict[str, int]
    opex_weight: float
    opex_scale: float
    invoice_base: dict[str, float]
    invoice_severity_multiplier: dict[str, float]
    escalation_contractor: str
    escalation_delay_minutes: int
    verify_delay_days: int
    info_delay_days: int
    max_defers: int
    attempt_limit_failures: int
    operator_negligence_share: float
    retention_windows: dict[str, int]
    notice_days: int
    planning: PlanningCfg
    annual_discount_rate: float


def public_config(cfg: Config) -> PublicConfig:
    return PublicConfig(
        sim_minutes_per_day=1440,
        units_per_property=cfg.portfolio.units_per_property,
        contractor_ids=cfg.contractor_ids(),
        categories=CATEGORIES,
        severities=SEVERITIES,
        fee_per_unit_day=cfg.fees.per_unit_month * 12.0 / 365.0,
        costs={"dispatch": cfg.costs.dispatch, "callback": cfg.costs.callback,
               "escalation": cfg.costs.escalation, "info": cfg.costs.info},
        verify_cost=cfg.verify.cost,
        sla_target_hours=dict(cfg.sla.target_hours),
        sla_credit=dict(cfg.sla.credit),
        closure_target_days=dict(cfg.proxy.closure_target_days),
        opex_weight=cfg.proxy.opex_weight,
        opex_scale=cfg.proxy.opex_scale,
        invoice_base=dict(cfg.invoice.base),
        invoice_severity_multiplier=dict(cfg.invoice.severity_multiplier),
        escalation_contractor=cfg.contractors.escalation_contractor,
        escalation_delay_minutes=cfg.contractors.escalation_delay_minutes,
        verify_delay_days=cfg.verify.delay_days,
        info_delay_days=cfg.obs.info_delay_days,
        max_defers=cfg.workflow.max_defers,
        attempt_limit_failures=cfg.workflow.attempt_limit_failures,
        operator_negligence_share=cfg.loss.operator_negligence_share,
        retention_windows={"cb": 90, "br": 90, "sl": 365, "oc": 90},
        notice_days=cfg.retention.notice_days,
        planning=cfg.planning,
        annual_discount_rate=cfg.time.annual_discount_rate,
    )
