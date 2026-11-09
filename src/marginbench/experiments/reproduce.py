"""`reproduce` and `audit` (SPEC 17.3, 20 Phase G)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marginbench.config import config_from_dict
from marginbench.economics.reconciliation import reconcile
from marginbench.economics.valuation import discounted_contribution_cents
from marginbench.experiments.runner import make_jobs, replication_job
from marginbench.hashing import write_json
from marginbench.schemas import EntryStatus, Event, LedgerEntry, Principal, make_data

REQUIRED_MANIFEST = ("run_id", "utc_started", "git_commit", "git_dirty", "lock_hash", "python", "platform", "sim_version",
                     "policy_version", "metric_definition_version", "config_hashes", "estimator_hashes", "plan_hash",
                     "partition", "seed_manifest", "random_stream_schema", "run_status", "reproducibility_status")


def _reps(d: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in (d / "replications.jsonl").read_text().splitlines()]


def reproduce_run(manifest_path: Path) -> dict[str, Any]:
    d = manifest_path.parent if manifest_path.name == "run_manifest.json" else manifest_path
    man = json.loads((d / "run_manifest.json").read_text())
    cfgs = json.loads((d / "config.json").read_text())
    estm = json.loads((d / "estimator_manifest.json").read_text())
    pols = json.loads((d / "policy_manifest.json").read_text())["policies"]
    stored = _reps(d)
    checks = {}
    ok = True
    for world, cj in cfgs.items():
        cfg = config_from_dict(cj)
        if cfg.config_hash() != man["config_hashes"][world]:
            ok = False
            checks[world] = {"config_hash": False}
            continue
        reps = sorted(r["replication"] for r in stored if r["world"] == world)
        if not reps:
            continue
        rep = reps[0]
        job = make_jobs(man["experiment"], world, cfg, estm["estimator_paths"][world], man["partition"], [rep], pols,
                        None, K=man.get("K_override"), H=man.get("H_override"),
                        deploy=bool(cfg.time.deploy_variant))[0]
        res = replication_job(job)
        st = next(r for r in stored if r["world"] == world and r["replication"] == rep)
        wc = {}
        for p, a in res["arms"].items():
            e = a["event_hash"] == st["arms"][p]["event_hash"]
            l = a["ledger_hash"] == st["arms"][p]["ledger_hash"]
            wc[p] = {"event_hash": e, "ledger_hash": l, "J_equal": a["J"] == st["arms"][p]["J"]}
            ok = ok and e and l
        checks[world] = {"replication": rep, "arms": wc}
    res = {"run_id": man["run_id"], "status": "REPRODUCED" if ok else "MISMATCH", "checks": checks}
    write_json(d / "reproduce.json", res)
    return res


def _load_trace(tdir: Path) -> tuple[list[Event], list[LedgerEntry]]:
    evs = []
    for line in (tdir / "events.jsonl").read_text().splitlines():
        e = json.loads(line)
        evs.append(Event(e["event_id"], e["tick"], e["priority"], e["type"], e["request_id"], e["property_id"],
                         make_data(**e["data"])))
    led = []
    for line in (tdir / "ledger.jsonl").read_text().splitlines():
        x = json.loads(line)
        led.append(LedgerEntry(x["entry_id"], x["run_id"], x["event_id"], x["tick"], Principal(x["principal"]), x["category"],
                               x["amount_cents"], x["contract_id"], x["request_id"], x["action_id"], EntryStatus(x["status"]),
                               x["reversal_of"]))
    return evs, led


def audit_run(d: Path) -> dict[str, Any]:
    man = json.loads((d / "run_manifest.json").read_text())
    cfgs = json.loads((d / "config.json").read_text())
    val = json.loads((d / "validation.json").read_text())
    findings: list[str] = []
    for k in REQUIRED_MANIFEST:
        if k not in man:
            findings.append(f"manifest missing {k}")
    if val["errors"]:
        findings.append(f"{len(val['errors'])} validation/reconciliation errors recorded")
    if man["run_status"] != "VALID":
        findings.append(f"run status {man['run_status']}")
    stored = {(r["world"], r["replication"]): r for r in _reps(d)}
    n_traces = 0
    for tdir in sorted((d / "traces").glob("*/rep_*/*")) if (d / "traces").exists() else []:
        world, rep, pol = tdir.parent.parent.name, int(tdir.parent.name.split("_")[1]), tdir.name
        cfg = config_from_dict(cfgs[world])
        evs, led = _load_trace(tdir)
        contracts = sorted({e.payload["contract_id"] for e in evs if e.type == "TERMINATION_NOTICE"} |
                           {l.contract_id for l in led if l.category == "fee_revenue"})
        cp = {f"K{i:02d}": f"P{i:02d}" for i in range(cfg.portfolio.n_properties)}
        errs = reconcile(evs, led, cfg, led[0].run_id if led else "", sorted(cp), cp, cfg.time.horizon_days * 1440)
        if errs:
            findings.append(f"trace {world}/{rep}/{pol}: reconciliation errors {errs[:2]}")
        daily = [0] * cfg.time.horizon_days
        for l in led:
            if l.principal == Principal.OPERATOR:
                daily[l.tick // 1440] += l.amount_cents
        J = discounted_contribution_cents(daily, cfg.time.d0, cfg.time.horizon_days - 1, cfg.time.delta) / 100.0
        st = stored.get((world, rep))
        if st is None or abs(st["arms"][pol]["J"] - J) > 1e-9:
            findings.append(f"trace {world}/{rep}/{pol}: J from ledger {J} != reported {st and st['arms'][pol]['J']}")
        n_traces += 1
    met = json.loads((d / "metrics.json").read_text())
    claims = json.loads((d / "claim_audit.json").read_text())["claims"]
    for c in claims:
        an = met["analyses"][c["scenario"]]["contrasts"][c["contrast"]]
        if an["dJ"]["mean"] != c["estimate"] or an["classification"] != c["classification"]:
            findings.append(f"claim {c['contrast']}/{c['scenario']} does not trace to metrics.json")
    res = {"run_id": man["run_id"], "experiment": man["experiment"], "traces_checked": n_traces,
           "claims_checked": len(claims), "findings": findings, "status": "PASS" if not findings else "FAIL"}
    write_json(d / "audit.json", res)
    return res


def audit_results(root: Path) -> dict[str, Any]:
    runs = [audit_run(p.parent) for p in sorted(root.rglob("run_manifest.json"))]
    status = "PASS" if runs and all(r["status"] == "PASS" for r in runs) else "FAIL"
    out = {"root": str(root), "status": status, "n_runs": len(runs),
           "failed": [r["run_id"] for r in runs if r["status"] != "PASS"], "runs": runs}
    write_json(root / "audit_summary.json", out)
    return out
