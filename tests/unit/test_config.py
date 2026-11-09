import pytest
from pydantic import ValidationError

from marginbench.config import CATEGORIES, PARTITIONS, deep_merge, load_config, public_config


def test_default_loads_and_hash_is_stable():
    a = load_config()
    b = load_config()
    assert a.config_hash() == b.config_hash()
    assert len(a.config_hash()) == 64
    assert a.time.horizon_days == 300
    assert a.time.d0 == 30
    assert a.time.decision_end_day == 119
    assert a.time.proxy_cutoff_day == 133


def test_unknown_key_rejected():
    with pytest.raises(ValidationError):
        load_config(overlays=[{"loss": {"bogus": 1}}])
    with pytest.raises(ValidationError):
        load_config(overlays=[{"not_a_section": {}}])


def test_shares_must_sum_to_one():
    with pytest.raises(ValidationError):
        load_config(overlays=[{"arrivals": {"shares": {"plumbing": 0.5, "electrical": 0.5, "hvac": 0.5, "general": 0.5}}}])


def test_probability_ranges_validated():
    with pytest.raises(ValidationError):
        load_config(overlays=[{"verify": {"sensitivity": 1.5}}])
    with pytest.raises(ValidationError):
        load_config(overlays=[{"obs": {"severity_accuracy": -0.1}}])


def test_overlay_changes_only_named_key():
    base = load_config()
    over = load_config(overlays=[{"callbacks": {"off": True}}])
    assert over.callbacks.off is True
    assert over.callbacks.m_sev == base.callbacks.m_sev
    assert over.config_hash() != base.config_hash()


def test_deep_merge():
    assert deep_merge({"a": {"b": 1, "c": 2}}, {"a": {"b": 3}}) == {"a": {"b": 3, "c": 2}}


def test_escalation_contractor_must_be_all_eligible():
    with pytest.raises(ValidationError):
        load_config(overlays=[{"contractors": {"escalation_contractor": "A"}}])


def test_partitions_and_seeds():
    cfg = load_config()
    for p in PARTITIONS:
        assert isinstance(cfg.seeds.master(p), int)
    with pytest.raises(ValueError):
        cfg.seeds.master("secret")


def test_retention_null_zeroes_betas():
    cfg = load_config(overlays=[{"retention": {"null_scenario": True}}])
    assert cfg.retention.betas() == {"cb": 0.0, "br": 0.0, "sl": 0.0, "oc": 0.0}


def test_public_config_has_no_seeds():
    pub = public_config(load_config())
    dumped = pub.model_dump()
    for forbidden in ("seeds", "master_seed", "partition", "replication", "nonce_key"):
        assert forbidden not in dumped
    assert tuple(pub.categories) == CATEGORIES
