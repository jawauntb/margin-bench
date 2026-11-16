import json
from pathlib import Path

import pytest

from marginbench.markets import tape

FIX = Path(__file__).parent / "fixtures" / "envelope_v1.json"


def _obs(**kw):
    base = dict(kind="bar.daily", source="s", producer="p", symbol="SPY",
                observed_at="2026-11-13T21:00:00Z", payload={"close": 1.5})
    base.update(kw)
    return tape.observation(**base)


def test_same_fact_same_id_whenever_recorded():
    a = _obs(recorded_at="2026-11-13T22:00:00Z")
    b = _obs(recorded_at="2026-11-14T09:00:00Z")
    assert a["id"] == b["id"]
    assert _obs(payload={"close": 1.6})["id"] != a["id"]


def test_shared_fixture_pins_ids_across_repos():
    """hvega's stdlib writer (hvega.tape) must produce these exact ids; a copy of this fixture
    lives in hvega's tests. Change both or neither."""
    fx = json.loads(FIX.read_text())
    for row in fx["observations"]:
        assert tape.content_id(row) == row["id"]
        tape.validate_observation(row)


@pytest.mark.parametrize("bad", [
    {"extra": 1}, {"v": 2}, {"visibility": "secret"}, {"observed_at": "2026-11-13 21:00"},
])
def test_invalid_observation_is_an_error(bad):
    row = {k: v for k, v in _obs().items() if k != "id"}
    row.update(bad)
    with pytest.raises(tape.EnvelopeError):
        tape.validate_observation(row)


def test_tampered_id_rejected():
    row = _obs()
    row["payload"] = {"close": 9.9}
    with pytest.raises(tape.EnvelopeError):
        tape.validate_observation(row)


def test_forecast_rules():
    ok = dict(task="ret1d", forecaster="f", symbol="SPY", issued_at="2026-11-13T22:00:00Z",
              base_session="2026-11-13", levels=[0.1, 0.5, 0.9], quantiles=[-0.01, 0.0, 0.01],
              inputs_sha256="x")
    fc = tape.forecast(**ok)
    assert tape.validate_forecast(fc) is fc
    for bad in ({"quantiles": [0.01, 0.0, -0.01]}, {"levels": [0.5, 0.1, 0.9]}, {"levels": [0.0, 0.5, 0.9]},
                {"quantiles": [0.0, 0.0]}):
        with pytest.raises(tape.EnvelopeError):
            tape.forecast(**{**ok, **bad})


def test_commitment_reveals_only_the_hash():
    fc = tape.forecast(task="ret1d", forecaster="hvega", symbol="SPY", issued_at="2026-11-13T22:00:00Z",
                       base_session="2026-11-13", levels=[0.5], quantiles=[0.0], inputs_sha256="x",
                       visibility="private")
    c = tape.commitment(fc, "2026-11-13T22:01:00Z")
    assert c["forecast_id"] == fc["id"]
    assert "quantiles" not in c and "levels" not in c and "inputs_sha256" not in c


def test_window_optional_hashed_and_validated():
    plain = _obs()
    bar = _obs(window={"type": "bar", "interval": "1d", "start": "2026-11-13T14:30:00Z", "end": "2026-11-13T21:00:00Z"})
    assert "window" not in plain and bar["id"] != plain["id"]
    for bad in ({"type": "candle"}, {"type": "bar"}, {"type": "mixed", "by": {}}):
        with pytest.raises(tape.EnvelopeError):
            _obs(window=bad)
