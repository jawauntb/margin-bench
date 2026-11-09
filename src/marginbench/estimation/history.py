"""Historical data generation (SPEC 10.1).

Each history portfolio is a 365-day run under the behavior policy (P0's action with
probability 0.7, else uniform over legal actions, propensities logged). Only observable
records leave this module: events pass through the observation allowlist
(``observable_event``), plus the logging policy's own actions and propensities and
public entity attributes. No latent field is read.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any

from marginbench.config import Config, public_config
from marginbench.environment.arrivals import build_world
from marginbench.environment.engine import Engine, RunSpec
from marginbench.environment.observations import observable_event
from marginbench.environment.randomness import StreamFactory, run_nonce
from marginbench.policies.baseline import BehaviorPolicy, P0Baseline

DAY = 1440


def observable_dataset(out: Any, world: Any, cfg: Config, history_days: int) -> dict[str, Any]:
    """Converts a run into the observable record set used for estimation."""
    oevents = []
    for ev in out.events:
        oe = observable_event(ev.type, ev.tick, ev.request_id, ev.property_id, ev.payload)
        if oe is not None:
            oevents.append({"tick": oe.tick, "type": oe.type, "request_id": oe.request_id,
                            "property_id": oe.property_id, "data": dict(oe.data)})
    actions = [{k: a[k] for k in ("request_id", "tick", "stage", "type", "contractor", "propensity", "n_legal")}
               for a in out.action_records]
    props = {p.property_id: {"q_obs": p.condition_obs, "units": p.unit_count, "contract_id": p.contract_id}
             for p in world.properties}  # PUBLIC fields only
    contractors = {c.contractor_id: {"price": c.price_multiplier, "speed": c.speed, "eligible": list(c.eligible),
                                     "capacity": c.capacity} for c in world.contractors}  # PUBLIC
    return {"events": oevents, "actions": actions, "properties": props, "contractors": contractors,
            "history_days": history_days}


def _history_one(args: tuple[str, int, dict[str, Any]]) -> dict[str, Any]:
    partition, rep, cfg_json = args
    from marginbench.config import config_from_dict

    cfg = config_from_dict(cfg_json)
    days = cfg.time.history_days
    sf = StreamFactory(cfg.versions.sim_version, partition, cfg.seeds.master(partition), rep)
    world = build_world(cfg, sf, days)
    pub = public_config(cfg)
    beh = BehaviorPolicy(cfg.behavior.p0_prob)
    beh.reset(pub, None, None)
    p0 = P0Baseline(use_prior=True)
    p0.reset(pub, None, None)
    spec = RunSpec(f"hist-{partition}-{rep}", days, run_nonce(cfg.seeds.nonce_key, partition, rep), mode="history",
                   max_events=cfg.limits.max_events_per_replication)
    out = Engine(cfg, world, spec, beh, p0).run()
    if out.status != "VALID":
        raise RuntimeError(f"history run {partition}/{rep} {out.status}: {out.validation_errors[:3]}")
    ds = observable_dataset(out, world, cfg, days)
    ds["partition"] = partition
    ds["replication"] = rep
    ds["event_hash"] = out.event_hash
    return ds


def generate_history(cfg: Config, partition: str, n_portfolios: int, workers: int = 4) -> list[dict[str, Any]]:
    cfg_json = cfg.model_dump(mode="json")
    jobs = [(partition, r, cfg_json) for r in range(n_portfolios)]
    if workers <= 1:
        return [_history_one(j) for j in jobs]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_history_one, jobs))
