"""The nightly loop: observe, settle, score, issue, publish (docs/TRACK-M.md section 4).

Order matters. Settlement runs before issue, so a forecast is never scored on the run that wrote
it. Issue refuses to run during a regular session (09:30 to close + buffer ET on a weekday),
because a forecast for "the next session" issued after that session opened would be invalid.
Every run writes a receipt naming what it read, wrote and hashed. A symbol whose fetch fails is
a hold for that symbol and is named in the receipt; it is never treated as "no data".
"""

from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path
from typing import Any, Callable

import numpy as np

from marginbench.hashing import canonical_hash, file_sha256, write_json
from marginbench.markets import forecasters as F
from marginbench.markets import ledger, score, settle, tape, yahoo

Fetch = Callable[[str, str], dict[str, Any]]


def in_session(now: dt.datetime, buffer_min: int) -> bool:
    et = now.astimezone(yahoo.ET)
    if et.weekday() >= 5:
        return False
    t = et.hour * 60 + et.minute
    return 9 * 60 + 30 <= t < 16 * 60 + buffer_min


def observe(cfg: dict[str, Any], now: dt.datetime, fetch: Fetch) -> tuple[dict[str, dict[str, Any]], dict[str, str], list[dict[str, Any]]]:
    data = cfg.get("data") or {}
    series, holds, rows = {}, {}, []
    for sym in cfg.get("universe") or []:
        try:
            obs = yahoo.observations(sym, fetch(sym, data.get("history_range") or "5y"), now,
                                     int(data.get("settle_buffer_min") or 0))
        except Exception as e:  # noqa: BLE001  a failed fetch is a named hold for that symbol
            holds[sym] = f"{type(e).__name__}: {e}"
            continue
        rows += obs
        series[sym] = yahoo.series(obs, sym)
    return series, holds, rows


def sigma_for(name: str, p: dict[str, Any], sym: str, ser: dict[str, Any], series: dict[str, Any], upto: int) -> tuple[float | None, list[str]]:
    """sigma from data up to and including session index ``upto``, and the observation ids used."""
    r = F.total_log_returns(ser["close"][: upto + 1], ser["sessions"][: upto + 1], ser["div"])
    aux: dict[str, Any] = {}
    used = list(ser["ids"][: upto + 1])
    if p["kind"] == "implied":
        idx = series.get(p["index"])
        base = ser["sessions"][upto]
        if idx is not None and base in idx["sessions"]:
            j = idx["sessions"].index(base)
            aux["implied"] = idx["close"][j]
            used = [idx["ids"][j]]
    return F.KINDS[p["kind"]](r, p, aux), used


def _forecasters(cfg: dict[str, Any], task: str) -> list[tuple[str, dict[str, Any], list[str]]]:
    t = (cfg.get("tasks") or {}).get(task) or {}
    out = []
    for name, p in (cfg.get("forecasters") or {}).items():
        if p is None:
            continue
        out.append((name, p, list(p.get("symbols") or t.get("symbols") or [])))
    return out


def issue(cfg: dict[str, Any], series: dict[str, Any], now: dt.datetime, have: set[tuple]) -> tuple[list[dict[str, Any]], list[str]]:
    rows, notes = [], []
    for task, t in (cfg.get("tasks") or {}).items():
        if t is None:
            continue
        for name, p, syms in _forecasters(cfg, task):
            for sym in syms:
                ser = series.get(sym)
                if ser is None or not ser["sessions"]:
                    notes.append(f"{name} {sym}: no data (hold)")
                    continue
                base = ser["sessions"][-1]
                if (task, name, sym, base) in have:
                    continue
                sig, used = sigma_for(name, p, sym, ser, series, len(ser["sessions"]) - 1)
                if sig is None or not np.isfinite(sig) or sig <= 0:
                    notes.append(f"{name} {sym} {base}: no forecast (insufficient input)")
                    continue
                rows.append(tape.forecast(
                    task=task, forecaster=name, symbol=sym, issued_at=tape.utc_iso(now),
                    base_session=base, levels=list(t["levels"]),
                    quantiles=F.quantiles(sig, list(t["levels"])),
                    inputs_sha256=canonical_hash({"ids": used, "params": p}),
                ))
    return rows, notes


def settle_all(root: Path, series: dict[str, Any], private: Path | None) -> tuple[list[dict], list[dict]]:
    fcs = ledger.read(root, "forecasts") + (ledger.read(private, "forecasts") if private else [])
    commits = {c["forecast_id"]: c for c in ledger.read(root, "commitments")}
    scored = {s["forecast_id"] for s in ledger.read(root, "scores")}
    outs, scores = [], []
    for fc in fcs:
        tape.validate_forecast(fc)
        if fc["id"] in scored or fc["symbol"] not in series:
            continue
        out = settle.outcome(fc["task"], fc["symbol"], fc["base_session"], series[fc["symbol"]])
        if out is None:
            continue
        outs.append(out)
        scores.append(score.score_row(fc, out, settle.validity(fc, out, commits.get(fc["id"]))))
    return outs, scores


def _commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
                              cwd=Path(__file__).resolve().parent).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def run(cfg: dict[str, Any], root: str | Path, now: dt.datetime, fetch: Fetch = yahoo.fetch_raw,
        private: str | Path | None = None) -> dict[str, Any]:
    root = Path(root)
    priv = Path(private) if private else None
    series, holds, obs = observe(cfg, now, fetch)
    outs, scores = settle_all(root, series, priv)
    n_out = ledger.append(root, "outcomes", outs, key=lambda r: (r["task"], r["symbol"], r["base_session"]))
    n_sc = ledger.append(root, "scores", scores, key=lambda r: r["forecast_id"])
    buffer_min = int((cfg.get("data") or {}).get("settle_buffer_min") or 0)
    notes: list[str] = []
    n_fc = 0
    if in_session(now, buffer_min):
        notes.append("in session: no forecasts issued (a next-session forecast must precede the open)")
    else:
        have = {(f["task"], f["forecaster"], f["symbol"], f["base_session"]) for f in ledger.read(root, "forecasts")}
        fcs, notes = issue(cfg, series, now, have)
        n_fc = ledger.append(root, "forecasts", fcs, key=lambda r: r["id"])
    lb = score.leaderboard(ledger.read(root, "scores"), cfg)
    write_json(root / "leaderboard.json", lb)
    (root / "LEADERBOARD.md").write_text(
        score.markdown(lb, "Track M leaderboard (forward: every forecast committed before its outcome)"),
        encoding="utf-8",
    )
    receipt = {
        "v": tape.VERSION, "at": tape.utc_iso(now), "code_commit": _commit(),
        "config_sha256": canonical_hash(cfg), "observations": len(obs),
        "observations_sha256": canonical_hash(sorted(o["id"] for o in obs)),
        "holds": holds, "notes": notes,
        "written": {"outcomes": n_out, "scores": n_sc, "forecasts": n_fc},
        "files": {p.name: file_sha256(p) for p in sorted(root.glob("*.jsonl"))},
    }
    write_json(root / "receipts" / f"{now.astimezone(yahoo.ET):%Y-%m-%d-%H%M}.json", receipt)
    return receipt


def replay(cfg: dict[str, Any], out_dir: str | Path, now: dt.datetime, fetch: Fetch = yahoo.fetch_raw) -> dict[str, Any]:
    """Point-in-time backtest over the last N sessions. Labeled REPLAY: hindsight-free in its
    inputs, but nothing was committed in advance, so it is never forward evidence."""
    rcfg = cfg.get("replay")
    if rcfg is None or rcfg.get("sessions") is None:
        raise ValueError("replay off (replay: null)")
    n_back = int(rcfg["sessions"])
    series, holds, _ = observe(cfg, now, fetch)
    rows = []
    for task, t in (cfg.get("tasks") or {}).items():
        if t is None:
            continue
        for name, p, syms in _forecasters(cfg, task):
            for sym in syms:
                ser = series.get(sym)
                if ser is None:
                    continue
                last = len(ser["sessions"]) - 1
                for i in range(max(0, last - n_back), last):
                    sig, _ = sigma_for(name, p, sym, ser, series, i)
                    if sig is None or not np.isfinite(sig) or sig <= 0:
                        continue
                    base = ser["sessions"][i]
                    out = settle.outcome(task, sym, base, ser)
                    if out is None:
                        continue
                    fc = {"id": f"replay:{name}:{sym}:{base}", "forecaster": name, "task": task, "symbol": sym,
                          "base_session": base, "visibility": "public", "levels": list(t["levels"]),
                          "quantiles": F.quantiles(sig, list(t["levels"]))}
                    rows.append(score.score_row(fc, out, None))
    out_dir = Path(out_dir)
    lb = score.leaderboard(rows, cfg)
    write_json(out_dir / "replay.json", {"at": tape.utc_iso(now), "holds": holds, "leaderboard": lb})
    (out_dir / "REPLAY.md").write_text(
        score.markdown(lb, f"Track M REPLAY, last {n_back} sessions (point-in-time backtest, NOT forward evidence)"),
        encoding="utf-8",
    )
    return lb
