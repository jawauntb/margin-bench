"""Self-contained HTML report (SPEC 19.1): inline CSS, base64 PNGs, no network, readable at
phone width. Every number comes from the run's artifacts."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from jinja2 import Environment

from marginbench.config import REPO_ROOT
from marginbench.reporting import charts

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>MarginBench {{ m.experiment }}</title>
<style>
:root{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--line:#e4e3df;--accent:#2a78d6}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--line:#34332f}}
:root[data-theme="dark"]{--bg:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--line:#34332f}
body{background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:0 16px 48px;max-width:960px;margin:auto}
h1{font-size:22px;margin:20px 0 4px}h2{font-size:17px;margin:28px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}
.meta{color:var(--ink2);font-size:12px;word-break:break-all}
.badge{display:inline-block;padding:1px 8px;border-radius:10px;border:1px solid var(--line);font-size:12px;margin-right:6px}
.tw{overflow-x:auto}table{border-collapse:collapse;font-size:12.5px;width:100%}th,td{border-bottom:1px solid var(--line);padding:4px 6px;text-align:left;white-space:nowrap}
img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:4px;background:#fcfcfb}
figure{margin:12px 0}figcaption{font-size:11px;color:var(--ink2)}
.note{background:rgba(127,127,127,.08);padding:8px 10px;border-radius:6px;font-size:13px}
</style></head><body>
<h1>MarginBench · {{ m.experiment }}</h1>
<p class="meta">run_id {{ m.run_id }} · {{ m.label }} · status <b>{{ m.run_status }}</b> · reproducibility <b>{{ m.reproducibility_status }}</b><br>
commit {{ m.git_commit }}{% if m.git_dirty %} (dirty){% endif %} · plan {{ m.plan_hash[:16] }} · estimator {{ est_hash[:16] }} · n = {{ m.n_replications }} · materiality m = ${{ '%.0f' % m.materiality_dollars }}</p>
<p class="note">Synthetic Level-1 evidence: results hold for the declared configurations only. All parameters are synthetic engineering fixtures, not market data. The evaluation is open and preregistered, not blind.</p>
{% for world, an in analyses.items() %}
<h2>Scenario: {{ world }} <span class="badge">{{ an.status }}</span></h2>
<div class="tw"><table><tr><th>contrast</th><th>label</th><th>class</th><th>ΔJ mean (USD)</th><th>CI</th><th>level</th><th>ΔG mean</th><th>ΔG CI</th><th>p</th><th>n</th></tr>
{% for k, c in an.contrasts.items() %}<tr><td>{{ k }}</td><td>{{ c.label }}</td><td><b>{{ c.classification }}</b>{% if c.strong %} STRONG{% endif %}</td>
<td>{{ fmt(c.dJ.mean, 0) }}</td><td>[{{ fmt(c.dJ.ci_low, 0) }}, {{ fmt(c.dJ.ci_high, 0) }}]</td><td>{{ '%.4f' % c.level }}</td>
<td>{{ fmt(c.dG.mean, 4) }}</td><td>[{{ fmt(c.dG.ci_low, 4) }}, {{ fmt(c.dG.ci_high, 4) }}]</td><td>{{ fmt(c.dJ.p_value, 4) }}</td><td>{{ c.n_valid_pairs }}</td></tr>{% endfor %}
</table></div>
<div class="tw"><table><tr><th>policy</th><th>J mean (USD)</th><th>G mean</th><th>closure</th><th>verified</th><th>true res.</th><th>callbacks</th><th>severe losses</th><th>SLA breaches</th><th>contracts lost</th></tr>
{% for p, s in summaries[world].items() %}<tr><td>{{ p }}</td><td>{{ fmt(s.J.mean, 0) }}</td><td>{{ fmt(s.G.mean if s.G else None, 4) }}</td>
<td>{{ pct(s.metrics_mean.closure_rate.mean) }}</td><td>{{ pct(s.metrics_mean.verified_resolution_rate.mean) }}</td><td>{{ pct(s.metrics_mean.true_resolution_rate.mean) }}</td>
<td>{{ fmt(s.metrics_mean.callback_count.mean, 1) }}</td><td>{{ fmt(s.metrics_mean.severe_loss_count.mean, 2) }}</td><td>{{ fmt(s.metrics_mean.sla_breach_count.mean, 1) }}</td><td>{{ fmt(s.metrics_mean.contracts_lost.mean, 2) }}</td></tr>{% endfor %}
</table></div>
{% if cross.get(world) %}<p class="meta">Exploratory change in ΔJ relative to the reference scenario, paired by replication:
{% for k, v in cross[world].items() %}{{ k }}: {{ fmt(v.mean, 0) }} [{{ fmt(v.ci_low, 0) }}, {{ fmt(v.ci_high, 0) }}]; {% endfor %}</p>{% endif %}
{% for c in charts_by_world.get(world, []) %}<figure><img alt="{{ c.alt }}" src="data:image/png;base64,{{ c.b64 }}"><figcaption>{{ c.alt }}</figcaption></figure>{% endfor %}
{% endfor %}
{% for c in extra_charts %}<figure><img alt="{{ c.alt }}" src="data:image/png;base64,{{ c.b64 }}"><figcaption>{{ c.alt }}</figcaption></figure>{% endfor %}
<h2>Claims</h2><div class="tw"><table><tr><th>claim</th><th>class</th><th>label</th><th>estimate</th><th>CI</th></tr>
{% for c in claims %}<tr><td style="white-space:normal">{{ c.claim }}</td><td>{{ c.classification }}</td><td>{{ c.label }}</td><td>{{ fmt(c.estimate, 0) }}</td><td>[{{ fmt(c.ci[0], 0) }}, {{ fmt(c.ci[1], 0) }}]</td></tr>{% endfor %}</table></div>
{% if xfails %}<h2>Frozen tests marked xfail</h2><pre>{{ xfails }}</pre>{% endif %}
<h2>Validation</h2><p class="meta">replications completed {{ v.replications_completed }}/{{ v.replications_planned }} · validation errors {{ v.errors|length }} · exclusions {{ v.exclusions|length }}</p>
</body></html>"""


def _b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode("ascii")


def fmt(x: Any, nd: int = 2) -> str:
    if x is None:
        return "null"
    try:
        return f"{float(x):,.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


def pct(x: Any) -> str:
    return "null" if x is None else f"{100 * float(x):.1f}%"


def build_report(out: Path) -> Path:
    out = Path(out)
    man = json.loads((out / "run_manifest.json").read_text())
    met = json.loads((out / "metrics.json").read_text())
    claims = json.loads((out / "claim_audit.json").read_text())["claims"]
    cfgs = json.loads((out / "config.json").read_text())
    series = json.loads((out / "series.json").read_text()) if (out / "series.json").exists() else {}
    val = json.loads((out / "validation.json").read_text())
    cdir = out / "charts"
    cap = lambda world: f"run {man['run_id']} · config {man['config_hashes'][world][:12]}"  # noqa: E731
    by_world: dict[str, list[dict[str, str]]] = {}
    for world, an in met["analyses"].items():
        lst = []
        p = cdir / f"{world}_proxy_vs_value.png"
        charts.proxy_vs_value(met["arm_summaries"][world], p, cap(world))
        lst.append({"alt": f"Proxy G and operator contribution J per policy, means with 95% CIs ({world})", "b64": _b64(p)})
        if an["contrasts"]:
            p = cdir / f"{world}_contrasts.png"
            charts.contrast_forest(an, met["materiality_dollars"], p, cap(world))
            lst.append({"alt": f"Paired ΔJ with CIs per contrast; shaded band is ±m ({world})", "b64": _b64(p)})
        p = cdir / f"{world}_resolution.png"
        charts.resolution_rates(met["arm_summaries"][world], p, cap(world))
        lst.append({"alt": f"Closure rate vs verified vs true resolution ({world})", "b64": _b64(p)})
        ws = {k: v for k, v in series.items() if k.split("|")[0] == world}
        if ws:
            p1, p2 = cdir / f"{world}_trajectories.png", cdir / f"{world}_cumulative.png"
            charts.trajectories(ws, cfgs[world], p1, p2, cap(world))
            if p1.exists():
                lst.append({"alt": f"Callback and backlog trajectories ({world})", "b64": _b64(p1)})
                lst.append({"alt": f"Cumulative discounted contribution ({world})", "b64": _b64(p2)})
        by_world[world] = lst
    extra = []
    audit_p = REPO_ROOT / "models" / "estimator_audit.json"
    if audit_p.exists():
        p = cdir / "estimator_calibration.png"
        charts.calibration_plots(json.loads(audit_p.read_text()), p, f"estimator {next(iter(man['estimator_hashes'].values()))[:12]} · calib partition")
        extra.append({"alt": "Estimator calibration on the calibration partition", "b64": _b64(p)})
    tdirs = sorted((out / "traces").glob("*/rep_0000/*")) if (out / "traces").exists() else []
    pick = next((d for d in tdirs if d.name == "P2"), tdirs[0] if tdirs else None)
    if pick is not None:
        p = cdir / "provenance_trace.png"
        rid = charts.provenance_trace(pick, p, f"run {man['run_id']} · {pick.parent.parent.name}/{pick.name}")
        if rid:
            extra.append({"alt": f"Decision-to-cash provenance trace for one request ({pick.name}, modeled dependency)", "b64": _b64(p)})
    sens_p = out / "sensitivity_panel.png"
    if not sens_p.exists() and man["experiment"] == "PRIMARY":
        sens_p = REPO_ROOT / "results" / "sensitivity" / "sensitivity_panel.png"
    if sens_p.exists():
        extra.append({"alt": "Sensitivity panels on the two dimensions most correlated with ΔJ(P2,P0)", "b64": _b64(sens_p)})
    xf = (REPO_ROOT / "tests" / "XFAIL_REASONS.txt")
    env = Environment(autoescape=True)
    env.globals.update(fmt=fmt, pct=pct)
    html = env.from_string(TEMPLATE).render(
        m=man, analyses=met["analyses"], summaries=met["arm_summaries"], cross=met.get("cross_world", {}),
        charts_by_world=by_world, extra_charts=extra, claims=claims, v=val,
        est_hash=next(iter(man["estimator_hashes"].values())), xfails=(xf.read_text().strip() if xf.exists() else ""))
    path = out / "report.html"
    path.write_text(html, encoding="utf-8")
    return path
