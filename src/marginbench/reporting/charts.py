"""Charts (SPEC 19.1). Matplotlib Agg PNGs. Dollars and percentages never share an axis.
Every caption carries its run_id and config hash. Policy colors follow the entity (fixed
categorical order), never rank."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
POLICY_COLOR = {"P0": SERIES[0], "P1": SERIES[1], "P2": SERIES[2], "P3": SERIES[3], "P4": SERIES[4], "P5": SERIES[5],
                "P6": SERIES[6]}
NEUTRAL = "#8a8985"


def _style(ax: Any) -> None:
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.yaxis.label.set_color(INK2)
    ax.xaxis.label.set_color(INK2)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def _fig(w: float = 7.0, h: float = 3.6, ncols: int = 1) -> tuple[Any, Any]:
    fig, axes = plt.subplots(1, ncols, figsize=(w, h), facecolor=SURFACE)
    axs = np.atleast_1d(axes)
    for ax in axs:
        _style(ax)
    return fig, axes


def _save(fig: Any, path: Path, caption: str) -> None:
    fig.text(0.01, 0.005, caption, fontsize=6.5, color=INK2, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140, facecolor=SURFACE)
    plt.close(fig)


def proxy_vs_value(summaries: dict[str, Any], path: Path, caption: str, title_suffix: str = "") -> None:
    pols = list(summaries)
    fig, (a1, a2) = _fig(7.6, 3.4, 2)
    for i, p in enumerate(pols):
        s = summaries[p]
        g = s.get("G") or {}
        j = s["J"]
        c = POLICY_COLOR.get(p, NEUTRAL)
        if g.get("mean") is not None:
            lo, hi = g.get("ci_low"), g.get("ci_high")
            a1.plot(i, g["mean"], "o", color=c, markersize=8, markeredgecolor=SURFACE, markeredgewidth=1.5)
            if lo is not None:
                a1.errorbar(i, g["mean"], yerr=[[g["mean"] - lo], [hi - g["mean"]]], color=INK, capsize=3, lw=1)
        lo, hi = j.get("ci_low"), j.get("ci_high")
        a2.plot(i, j["mean"] / 1000.0, "o", color=c, markersize=8, markeredgecolor=SURFACE, markeredgewidth=1.5)
        if lo is not None:
            a2.errorbar(i, j["mean"] / 1000.0, yerr=[[(j["mean"] - lo) / 1000], [(hi - j["mean"]) / 1000]], color=INK,
                        capsize=3, lw=1)
    for a in (a1, a2):
        a.set_xticks(range(len(pols)))
        a.set_xticklabels(pols)
    a2.set_xlim(-0.6, len(pols) - 0.4)
    a1.set_xlim(-0.6, len(pols) - 0.4)
    a1.set_title("Proxy G (proxy_v1, dimensionless)" + title_suffix, fontsize=9, color=INK)
    a2.set_title("Operator contribution J (thousand USD)" + title_suffix, fontsize=9, color=INK)
    js = [summaries[p]["J"]["mean"] / 1000 for p in pols]
    if js:
        lo, hi = min(js), max(js)
        pad = max((hi - lo) * 0.6, 1.0)
        a2.set_ylim(lo - pad, hi + pad)
    _save(fig, path, caption)


def contrast_forest(analysis: dict[str, Any], m: float, path: Path, caption: str) -> None:
    items = list(analysis["contrasts"].items())
    if not items:
        return
    fig, ax = _fig(7.0, 0.5 + 0.42 * len(items))
    ax.axvspan(-m / 1000, m / 1000, color="#ecebe7", zorder=0)
    ax.set_title(f"Shaded: materiality band ±m (m = ${m:,.0f})", fontsize=8, color=INK2, loc="left")
    ax.axvline(0, color=NEUTRAL, lw=0.8)
    for i, (k, c) in enumerate(items):
        dj = c["dJ"]
        if dj.get("ci_low") is None:
            continue
        y = len(items) - 1 - i
        col = POLICY_COLOR.get(c["a"], NEUTRAL)
        ax.plot([dj["ci_low"] / 1000, dj["ci_high"] / 1000], [y, y], color=col, lw=2)
        ax.plot(dj["mean"] / 1000, y, "o", color=col, markersize=6, markeredgecolor=SURFACE, markeredgewidth=1.5)
        ax.text(1.01, y, f"{c['classification']}{' (STRONG)' if c.get('strong') else ''}", transform=ax.get_yaxis_transform(),
                fontsize=7, color=INK2, va="center")
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([f"{c['a']} − {c['b']} [{c['label'][:4]}, {int(round(c['level']*1000))/10}% CI]"
                        for _, c in reversed(items)], fontsize=7.5)
    ax.set_xlabel("Paired ΔJ (thousand USD)")
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    _save(fig, path, caption)


def resolution_rates(summaries: dict[str, Any], path: Path, caption: str) -> None:
    pols = list(summaries)
    keys = [("closure_rate", "closure within target (proxy)"), ("verified_resolution_rate", "verified resolution"),
            ("true_resolution_rate", "true resolution (latent)")]
    fig, ax = _fig(7.0, 3.4)
    w = 0.26
    tones = [SERIES[0], SERIES[6], NEUTRAL]
    for kidx, (k, lab) in enumerate(keys):
        vals = [summaries[p]["metrics_mean"][k]["mean"] or 0.0 for p in pols]
        ax.bar(np.arange(len(pols)) + (kidx - 1) * w, [v * 100 for v in vals], width=w - 0.02, color=tones[kidx], label=lab)
    ax.set_xticks(range(len(pols)))
    ax.set_xticklabels(pols)
    ax.set_ylabel("Share of decision cohort (%)")
    ax.set_ylim(0, 105)
    ax.legend(fontsize=7, frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    _save(fig, path, caption)


def trajectories(series: dict[str, Any], cfg: dict[str, Any], path_cb: Path, path_cum: Path, caption: str) -> None:
    if not series:
        return
    by_pol: dict[str, list[dict[str, Any]]] = {}
    for _, per in series.items():
        for p, s in per.items():
            by_pol.setdefault(p, []).append(s)
    W = cfg["time"]["warmup_days"]
    D = cfg["time"]["decision_days"]
    fig, (a1, a2) = _fig(7.6, 3.4, 2)
    for p, lst in by_pol.items():
        n = min(len(s["callbacks"]) for s in lst)
        cb = np.mean([s["callbacks"][:n] for s in lst], axis=0)
        k = 7
        cbs = np.convolve(cb, np.ones(k) / k, mode="same")
        bl = np.mean([s["backlog"][:n] for s in lst], axis=0)
        c = POLICY_COLOR.get(p, NEUTRAL)
        a1.plot(np.arange(n), cbs, color=c, lw=1.6, label=p)
        a2.plot(np.arange(n), bl, color=c, lw=1.6, label=p)
    for a in (a1, a2):
        a.axvline(W, color=NEUTRAL, lw=0.8, ls="--")
        a.axvline(W + D, color=NEUTRAL, lw=0.8, ls="--")
        a.set_xlabel("Day")
    a1.set_title("Callbacks per day (7-day mean)", fontsize=9, color=INK)
    a2.set_title("Open-request backlog at day end", fontsize=9, color=INK)
    a2.legend(fontsize=7, frameon=False)
    _save(fig, path_cb, caption + " · dashed lines: decision window start/end · mean of first replications")
    fig, ax = _fig(7.0, 3.4)
    for p, lst in by_pol.items():
        n = min(len(s["cum_discounted_dollars"]) for s in lst)
        cum = np.mean([s["cum_discounted_dollars"][:n] for s in lst], axis=0)
        ax.plot(np.arange(W, W + n), cum / 1000.0, color=POLICY_COLOR.get(p, NEUTRAL), lw=1.6, label=p)
    ax.axvline(W + D, color=NEUTRAL, lw=0.8, ls="--")
    ax.text(W + D + 2, ax.get_ylim()[0], "maturation →", fontsize=7, color=INK2, va="bottom")
    ax.set_xlabel("Day")
    ax.set_ylabel("Cumulative discounted contribution (thousand USD)")
    ax.legend(fontsize=7, frameon=False)
    _save(fig, path_cum, caption + " · dashed line: decision/maturation boundary")


def calibration_plots(audit: dict[str, Any], path: Path, caption: str) -> None:
    fig, axes = _fig(7.6, 3.4, 2)
    for ax, key, title in ((axes[0], "success_model", "Success model (selection labels)"),
                           (axes[1], "callback_model", "Callback after closure")):
        cur = audit.get(key, {}).get("calibration_curve") or []
        ax.plot([0, 1], [0, 1], color=NEUTRAL, lw=0.8, ls="--")
        if cur:
            xs = [c["mean_pred"] for c in cur]
            ys = [c["mean_obs"] for c in cur]
            ax.plot(xs, ys, "o-", color=SERIES[0], lw=1.6, markersize=5, markeredgecolor=SURFACE)
        ax.set_xlabel("Predicted probability")
        ax.set_ylabel("Observed frequency")
        ax.set_title(f"{title} · Brier {audit.get(key, {}).get('brier_calib', float('nan')):.3f}", fontsize=9, color=INK)
    _save(fig, path, caption)


def provenance_trace(trace_dir: Path, path: Path, caption: str) -> Optional[str]:
    """Decision-to-cash trace for one request: actions, events and ledger entries."""
    ev_p, led_p = trace_dir / "events.jsonl", trace_dir / "ledger.jsonl"
    if not ev_p.exists():
        return None
    events = [json.loads(x) for x in ev_p.read_text().splitlines()]
    ledger = [json.loads(x) for x in led_p.read_text().splitlines()]
    counts: dict[str, int] = {}
    cohort = {e["request_id"] for e in events if e["type"] == "ARRIVAL" and e["data"].get("cohort")}
    for e in events:
        if e["request_id"] in cohort and e["type"] in ("CALLBACK", "VERIFY_RESULT", "SLA_BREACH", "SEVERE_LOSS"):
            counts[e["request_id"]] = counts.get(e["request_id"], 0) + 1
    if not counts:
        rid = next((e["request_id"] for e in events if e["type"] == "ARRIVAL" and e["data"].get("cohort")), None)
    else:
        rid = max(sorted(counts), key=lambda r: counts[r])
    if rid is None:
        return None
    evs = [e for e in events if e["request_id"] == rid]
    led = [l for l in ledger if l["request_id"] == rid]
    fig, ax = _fig(7.6, 0.6 + 0.24 * (len(evs) + len(led)))
    ax.grid(False)
    rows = []
    for e in evs:
        lab = e["type"]
        d = e["data"]
        if e["type"] == "ACTION":
            lab = f"action: {d['action_type']}{'(' + d['contractor'] + ')' if d.get('contractor') else ''} by {d['policy']}"
        elif e["type"] == "WORK_COMPLETE":
            lab = f"work complete: report={d['report']}"
        elif e["type"] == "VERIFY_RESULT":
            lab = f"verification: {d['result']}"
        rows.append((e["tick"] / 1440.0, lab, "event", e["event_id"]))
        for l in led:
            if l["event_id"] == e["event_id"]:
                rows.append((l["tick"] / 1440.0, f"  ledger {l['principal']} {l['category']} {l['amount_cents']/100:+.2f} USD",
                             "ledger", e["event_id"]))
    for i, (t, lab, kind, _) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.plot(t, y, "o" if kind == "event" else "s", color=SERIES[0] if kind == "event" else SERIES[1], markersize=4)
        ax.text(t, y, "  " + lab, fontsize=6.5, color=INK, va="center")
    ax.set_yticks([])
    ax.set_xlabel("Day")
    ax.set_title(f"Decision-to-cash provenance for request {rid} (modeled dependency)", fontsize=9, color=INK)
    if rows:
        ts = [r[0] for r in rows]
        ax.set_xlim(min(ts) - 0.5, max(ts) + (max(ts) - min(ts)) * 0.6 + 2)
    _save(fig, path, caption + " · modeled dependency, not a causal claim about the real world")
    return rid


def sensitivity_panels(rows: list[dict[str, Any]], dims: list[str], path: Path, caption: str) -> None:
    if len(dims) < 2 or not rows:
        return
    from matplotlib.colors import TwoSlopeNorm

    x = np.array([r[dims[0]] for r in rows])
    y = np.array([r[dims[1]] for r in rows])
    z = np.array([r["dJ_P2_P0"] for r in rows]) / 1000.0
    fig, ax = _fig(6.2, 4.2)
    lim = max(abs(z).max(), 1e-6)
    sc = ax.scatter(x, y, c=z, cmap="RdBu", norm=TwoSlopeNorm(0, -lim, lim), s=60, edgecolors=SURFACE, linewidths=1.5)
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("ΔJ(P2, P0), thousand USD", color=INK2, fontsize=8)
    for r, xi, yi in zip(rows, x, y):
        ax.text(xi, yi, " " + r["class_P2_P0"][:3], fontsize=5.5, color=INK2, va="center")
    ax.set_xlabel(dims[0])
    ax.set_ylabel(dims[1])
    ax.set_title("Sensitivity: tested design points (not real-world probabilities)", fontsize=9, color=INK)
    _save(fig, path, caption)
