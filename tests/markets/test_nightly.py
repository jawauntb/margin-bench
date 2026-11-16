import datetime as dt
import pytest

from marginbench.markets import ledger, nightly, tape
from chart import chart, et, sessions, walk  # noqa: E402  (tests/markets on the path)

DAYS = sessions(dt.date(2023, 1, 2), 800)  # ends well before 2026
CFG = {
    "universe": ["AAA", "^VIX"],
    "data": {"history_range": "5y", "settle_buffer_min": 20},
    "tasks": {"ret1d": {"symbols": ["AAA"], "levels": [0.05, 0.5, 0.95]}},
    "forecasters": {"rw20": {"kind": "rw", "window": 20}, "vix": {"kind": "implied", "index": "^VIX", "symbols": ["AAA"]},
                    "off": None},
    "reference": "rw20",
    "score": {"min_n": 30, "ci": 0.9, "block": 5, "draws": 200},
}


def fetcher(n_days, fail=()):
    px, vx = walk(len(DAYS), seed=1), [15.0 + (i % 7) for i in range(len(DAYS))]

    def fetch(sym, _range):
        if sym in fail:
            raise TimeoutError("boom")
        d = DAYS[:n_days]
        return chart(d, (px if sym == "AAA" else vx)[:n_days], {DAYS[n_days - 1]: 0.25} if sym == "AAA" else None)

    return fetch


def _close_of(i):
    d = DAYS[i]
    return et(d.year, d.month, d.day, 17, 0)


def test_two_nights_issue_then_settle(tmp_path):
    r1 = nightly.run(CFG, tmp_path, _close_of(499), fetcher(500))
    assert r1["written"]["forecasts"] == 2 and r1["written"]["scores"] == 0
    assert not any("off" in n for n in r1["notes"])  # a null forecaster is off, not an error
    r2 = nightly.run(CFG, tmp_path, _close_of(500), fetcher(501))
    assert r2["written"] == {"outcomes": 1, "scores": 2, "forecasts": 2}
    scores = ledger.read(tmp_path, "scores")
    assert all(s["valid"] for s in scores)
    assert {s["target_session"] for s in scores} == {DAYS[500].isoformat()}
    assert (tmp_path / "LEADERBOARD.md").exists() and list((tmp_path / "receipts").glob("*.json"))


def test_rerun_is_idempotent(tmp_path):
    nightly.run(CFG, tmp_path, _close_of(499), fetcher(500))
    nightly.run(CFG, tmp_path, _close_of(500), fetcher(501))
    before = {n: (tmp_path / f"{n}.jsonl").read_text() for n in ("forecasts", "outcomes", "scores")}
    again = nightly.run(CFG, tmp_path, _close_of(500) + dt.timedelta(minutes=30), fetcher(501))
    assert again["written"] == {"outcomes": 0, "scores": 0, "forecasts": 0}
    assert before == {n: (tmp_path / f"{n}.jsonl").read_text() for n in before}


def test_forming_bar_is_never_stored_and_no_issue_in_session(tmp_path):
    d = DAYS[500]
    noon = et(d.year, d.month, d.day, 12, 0)
    r = nightly.run(CFG, tmp_path, noon, fetcher(501))
    assert r["written"]["forecasts"] == 0
    assert any("in session" in n for n in r["notes"])
    series, _, _ = nightly.observe(CFG, noon, fetcher(501))
    assert series["AAA"]["sessions"][-1] == DAYS[499].isoformat()


def test_failed_fetch_is_a_named_hold(tmp_path):
    r = nightly.run(CFG, tmp_path, _close_of(499), fetcher(500, fail=("^VIX",)))
    assert "^VIX" in r["holds"]
    assert r["written"]["forecasts"] == 1  # rw20 still speaks; vix has no input
    assert any("vix" in n for n in r["notes"])


def test_late_forecast_scored_invalid(tmp_path):
    nightly.run(CFG, tmp_path, _close_of(499), fetcher(500))
    rows = ledger.read(tmp_path, "forecasts")
    late = {k: v for k, v in rows[0].items() if k != "id"}
    late["issued_at"] = tape.utc_iso(_close_of(500))  # after the target opened
    late["forecaster"] = "late"
    late["id"] = tape.content_id(late)
    ledger.append(tmp_path, "forecasts", [late], key=lambda r: r["id"])
    nightly.run(CFG, tmp_path, _close_of(500), fetcher(501))
    s = [x for x in ledger.read(tmp_path, "scores") if x["forecaster"] == "late"][0]
    assert not s["valid"] and "after the target session opened" in s["reason"]


def test_private_forecast_scored_only_with_commitment(tmp_path):
    pub, priv = tmp_path / "pub", tmp_path / "priv"
    nightly.run(CFG, pub, _close_of(499), fetcher(500))
    base = ledger.read(pub, "forecasts")[0]
    mk = lambda name: tape.forecast(task="ret1d", forecaster=name, symbol="AAA", issued_at=base["issued_at"],  # noqa: E731
                                    base_session=base["base_session"], levels=base["levels"],
                                    quantiles=base["quantiles"], inputs_sha256="h", visibility="private")
    committed, uncommitted = mk("hvega"), mk("hvega-x")
    ledger.append(priv, "forecasts", [committed, uncommitted], key=lambda r: r["id"])
    ledger.append(pub, "commitments", [tape.commitment(committed, base["issued_at"])], key=lambda r: r["forecast_id"])
    nightly.run(CFG, pub, _close_of(500), fetcher(501), private=priv)
    s = {x["forecaster"]: x for x in ledger.read(pub, "scores")}
    assert s["hvega"]["valid"] and s["hvega"]["visibility"] == "private"
    assert not s["hvega-x"]["valid"]
    public_text = "".join(p.read_text() for p in pub.glob("*.jsonl"))
    assert "inputs_sha256\":\"h\"" not in public_text  # the private row itself never lands in public


def test_replay_null_is_off(tmp_path):
    with pytest.raises(ValueError, match="replay off"):
        nightly.replay({**CFG, "replay": None}, tmp_path, _close_of(499), fetcher(500))


def test_bars_are_one_day_candles_open_to_close_dividends_points():
    from marginbench.markets import yahoo

    obs = yahoo.observations("AAA", fetcher(500)("AAA", "5y"), _close_of(499), 20)
    b = [o for o in obs if o["kind"] == "bar.daily"][-1]
    assert b["window"]["type"] == "bar" and b["window"]["interval"] == "1d"
    assert b["window"]["start"] == b["payload"]["open_at"] and b["window"]["end"] == b["observed_at"]
    assert [o["window"] for o in obs if o["kind"] == "dividend"] == [{"type": "point"}]
