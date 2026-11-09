"""Generates CLAIMS.md and RESULTS_SUMMARY.md from run artifacts only (SPEC 19.2).
Every number printed here is read from a results file; nothing is typed by hand."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

RESULTS = "results"


def _j(p: Path) -> Optional[Any]:
    return json.loads(p.read_text()) if p.exists() else None


def _f(x: Any, nd: int = 0) -> str:
    if x is None:
        return "null"
    return f"{float(x):,.{nd}f}"


def _ci(d: dict[str, Any], nd: int = 0) -> str:
    return f"[{_f(d.get('ci_low'), nd)}, {_f(d.get('ci_high'), nd)}]"


def _contrast_line(c: dict[str, Any], scen: str, run_id: str, art: str) -> str:
    return (f"| {c['a']} vs {c['b']} | {scen} | {c['label']} | **{c['classification']}**{' STRONG' if c.get('strong') else ''} | "
            f"{_f(c['dJ']['mean'])} | {_ci(c['dJ'])} | {c['level']:.4f} | {_f(c['dG'].get('mean') if c['dG'] else None, 4)} | "
            f"{_ci(c['dG'], 4) if c['dG'] else 'null'} | {c['n_valid_pairs']} | `{run_id}` | `{art}` |")


def write_documents(root: Path) -> None:
    res = root / RESULTS
    runs = {}
    for p in sorted(res.rglob("run_manifest.json")):
        if "/dev/" in str(p) or "/calib/" in str(p):
            continue
        man = json.loads(p.read_text())
        runs[str(p.parent.relative_to(root))] = (man, json.loads((p.parent / "metrics.json").read_text()))
    write_claims(root, runs)
    write_results_summary(root, runs)


def write_claims(root: Path, runs: dict[str, Any]) -> None:
    sup, model_family, unsup = [], [], []
    hdr = ("| contrast | scenario | label | class | ΔJ mean (USD) | ΔJ CI | CI level | ΔG mean | ΔG CI | n | run_id | artifact |\n"
           "|---|---|---|---|---|---|---|---|---|---|---|---|")
    for d, (man, met) in runs.items():
        for scen, an in met["analyses"].items():
            for k, c in an["contrasts"].items():
                line = _contrast_line(c, f"{man['experiment']}/{scen}", man["run_id"], f"{d}/metrics.json")
                if c["classification"] in ("REVERSAL_SUPPORTED", "ALIGNMENT_SUPPORTED", "VALUE_HIGHER_SUPPORTED",
                                           "VALUE_LOWER_SUPPORTED", "EQUIVALENCE_SUPPORTED"):
                    sup.append(line)
                else:
                    unsup.append(line)
    sens = _j(root / RESULTS / "sensitivity" / "sensitivity_summary.json")
    lines = [
        "# CLAIMS",
        "",
        "Generated from `claim_audit.json` and `metrics.json` in each results directory by `marginbench report`. "
        "Metric: J = discounted operator contribution over the scenario's business-value window (USD); "
        "G = proxy_v1. Cohort: decision cohort. Every claim is synthetic Level-1 evidence for its named scenario only.",
        "",
        "## Supported synthetic findings (Level 1)",
        "",
        hdr, *sup, "",
        "## Supported model-family findings (Level 2)",
        "",
    ]
    if sens:
        sh = sens["class_shares"]["class_P2_P0"]
        lines += [f"Sensitivity design: {sens['n_points']} tested design points. Shares of tested points by class for P2 vs P0: "
                  + ", ".join(f"{k} {v['count']}/{sens['n_points']}" for k, v in sh.items()) + ".",
                  "A Level-2 claim needs one class across the declared design and the structural ablations. "
                  + ("The design points are not all in one class, so no Level-2 claim is made for P2 vs P0."
                     if len(sh) > 1 else "All tested points share one class; see the ablations before reading this as robust."),
                  ""]
    else:
        lines += ["No sensitivity results; no Level-2 claim is made.", ""]
    lines += ["## Unsupported or inconclusive", "", hdr, *unsup, "",
              "## Required external validation", "",
              "- Level 3 (external validation) is out of scope. No result here says anything about real property-management operators.",
              "- Every parameter is a synthetic engineering fixture. Calibrating arrival rates, contractor quality, tenant reporting, verification accuracy, retention hazards and loss sizes to real data would be required before any external claim.",
              "- The proxy (proxy_v1) is one dashboard definition; other proxies may behave differently.", ""]
    (root / "CLAIMS.md").write_text("\n".join(lines))


def write_results_summary(root: Path, runs: dict[str, Any]) -> None:
    prim = next(((d, m, met) for d, (m, met) in runs.items() if m["experiment"] == "PRIMARY"), None)
    lines = ["# RESULTS SUMMARY", ""]
    if prim is None:
        lines += ["The preregistered PRIMARY evaluation has not run. No result is reported.", ""]
        (root / "RESULTS_SUMMARY.md").write_text("\n".join(lines))
        return
    d, man, met = prim
    an = met["analyses"]["default"]
    c = an["contrasts"]["P2-P0"]
    lines += [
        f"**Question.** When P2, a policy that plans against the operational proxy, replaces P0, the operating baseline, does simulated long-horizon operator value go up, stay the same or go down? "
        f"**Primary result ({man['label']}, run `{man['run_id']}`, n = {c['n_valid_pairs']} paired replications, m = ${_f(met['materiality_dollars'], 2)}):** "
        f"P2 vs P0 is **{c['classification']}**{' (STRONG)' if c.get('strong') else ''}. "
        f"ΔJ = {_f(c['dJ']['mean'])} USD, 95% CI {_ci(c['dJ'])}; ΔG = {_f(c['dG'].get('mean'), 4)}, 95% CI {_ci(c['dG'], 4)}. "
        f"Run status {man['run_status']}, reproducibility {man['reproducibility_status']}.",
        "",
        "**Design.** Synthetic discrete-event simulation of a 20-property, 200-unit maintenance portfolio. Warm-up days 0-29 and continuation days 120-299 are decided by P0 in every arm; the policy under test decides days 30-119 and owns each decision-cohort request until its first closure. All arms share keyed randomness. J is discounted operator cash contribution, days 30-299. G is proxy_v1 (closure rate within target minus an opex penalty) at day 133. Evidence is Level 1: it holds for the declared configuration only.",
        "",
        "## Confirmatory secondary family (Holm)",
        "",
        "| contrast | class | ΔJ mean (USD) | CI | CI level | Holm α | p | stopped |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for k, x in an["contrasts"].items():
        if x["label"] == "CONFIRMATORY":
            lines.append(f"| {k} | {x['classification']}{' STRONG' if x.get('strong') else ''} | {_f(x['dJ']['mean'])} | {_ci(x['dJ'])} | "
                         f"{x['level']:.4f} | {x['holm']['alpha']:.4f} | {_f(x['dJ']['p_value'], 4)} | {x['holm_stopped']} |")
    gap = an.get("gap_to_best_evaluated_policy")
    if gap:
        lines += ["", f"Gap to best evaluated policy (not regret): best is {gap['best_evaluated_policy']}; gaps (USD) "
                  + ", ".join(f"{p} {_f(v)}" for p, v in gap["gaps_dollars"].items()) + "."]
    lines += ["", "## Secondary and exploratory results", ""]
    for dd, (m2, met2) in runs.items():
        if m2["experiment"] == "PRIMARY":
            continue
        for scen, a2 in met2["analyses"].items():
            items = "; ".join(f"{k}: {v['classification']} ({_f(v['dJ']['mean'])} USD {_ci(v['dJ'])})" for k, v in a2["contrasts"].items())
            if items:
                lines.append(f"- **{m2['experiment']} / {scen}** (`{m2['run_id']}`, status {m2['run_status']}): {items}.")
    e1 = next(((m2, met2) for _, (m2, met2) in runs.items() if m2["experiment"] == "E1"), None)
    lines += ["", "## E1 sanity outcome", ""]
    if e1:
        c1 = e1[1]["analyses"]["aligned"]["contrasts"]["P2-P0"]
        warn = " This is flagged as a model-validity warning (SPEC 13)." if c1["classification"] == "REVERSAL_SUPPORTED" else ""
        lines.append(f"In the aligned world, P2 vs P0 is **{c1['classification']}** (ΔJ {_f(c1['dJ']['mean'])} USD, CI {_ci(c1['dJ'])}).{warn}")
    else:
        lines.append("E1 has not run.")
    e9 = _j(root / RESULTS / "e9" / "e9_results.json")
    lines += ["", "## E9 gate comparison", ""]
    if e9:
        lines += ["| gate | false approval (Wilson 95%) | false rejection (Wilson 95%) | harmful approval | positives / negatives |",
                  "|---|---|---|---|---|"]
        for g, t in e9["table"].items():
            lines.append(f"| {g} | {_f(t['false_approval_rate'], 3)} {[_f(x, 3) for x in t['false_approval_wilson95']]} | "
                         f"{_f(t['false_rejection_rate'], 3)} {[_f(x, 3) for x in t['false_rejection_wilson95']]} | "
                         f"{_f(t['harmful_approval_rate'], 3)} | {t['n_positive_truth']} / {t['n_negative_truth']} |")
    else:
        lines.append("E9 has not run.")
    sens = _j(root / RESULTS / "sensitivity" / "sensitivity_summary.json")
    lines += ["", "## Sensitivity summary", ""]
    if sens:
        for key, sh in sens["class_shares"].items():
            lines.append(f"- {key}: " + ", ".join(f"{k} {v['count']} of {sens['n_points']} tested design points" for k, v in sh.items()) + ".")
        lines.append(f"- Largest |Spearman ρ| with ΔJ(P2, P0): {', '.join(sens['top_dimensions'])}. Shares are of tested design points, never real-world probabilities.")
    else:
        lines.append("Sensitivity has not run.")
    lines += ["", "## Limitations", "", "See LIMITATIONS.md. All parameters are synthetic; no result implies external (Level 3) validity.",
              "", "## Reproduce", "", "```", f"marginbench reproduce --manifest {d}/run_manifest.json", "```", ""]
    (root / "RESULTS_SUMMARY.md").write_text("\n".join(lines))
