"""Public daily bars from Yahoo's chart endpoint: the one I/O module of Track M.

Each final session becomes a ``bar.daily`` Observation and each dividend a ``dividend``
Observation (``tape``). A session is final only once ``settle_buffer_min`` minutes have passed
after its regular close (09:30 ET open + 390 minutes); a bar still forming is dropped, never
stored. Raw bars are a cache (DECISIONS D-49): only derived outcomes enter the public ledger.
"""

from __future__ import annotations

import datetime as dt
import json
import urllib.parse
import urllib.request
from typing import Any
from zoneinfo import ZoneInfo

from marginbench.markets import tape

ET = ZoneInfo("America/New_York")
SOURCE = "yahoo.chart.v8"
PRODUCER = "marginbench.markets.yahoo@1"
SESSION_MIN = 390
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?{q}"


def fetch_raw(symbol: str, range_: str, timeout: float = 20.0) -> dict[str, Any]:
    q = urllib.parse.urlencode({"range": range_, "interval": "1d", "events": "div"})
    req = urllib.request.Request(
        URL.format(sym=urllib.parse.quote(symbol), q=q), headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (fixed https host)
        return json.loads(resp.read().decode("utf-8"))


def observations(
    symbol: str, raw: dict[str, Any], now: dt.datetime, settle_buffer_min: int
) -> list[dict[str, Any]]:
    """Final bars and dividends from one chart response, as Observations, oldest first."""
    res = (raw.get("chart") or {}).get("result") or []
    if not res:
        raise tape.EnvelopeError(f"{symbol}: empty chart response")
    r = res[0]
    ts = r.get("timestamp") or []
    quote = (r.get("indicators") or {}).get("quote") or [{}]
    q = quote[0]
    rows: list[dict[str, Any]] = []
    for i, t in enumerate(ts):
        o, h, lo, c, v = (q.get(k, [None] * len(ts))[i] for k in ("open", "high", "low", "close", "volume"))
        if c is None:
            continue
        opened = dt.datetime.fromtimestamp(t, tz=dt.timezone.utc)
        closed = opened + dt.timedelta(minutes=SESSION_MIN)
        if now < closed + dt.timedelta(minutes=settle_buffer_min):
            continue  # still forming: never stored
        rows.append(
            tape.observation(
                kind="bar.daily", source=SOURCE, producer=PRODUCER, symbol=symbol,
                observed_at=tape.utc_iso(closed),
                window={"type": "bar", "interval": "1d", "start": tape.utc_iso(opened), "end": tape.utc_iso(closed)},
                payload={
                    "session": opened.astimezone(ET).date().isoformat(),
                    "open_at": tape.utc_iso(opened),
                    "open": o, "high": h, "low": lo, "close": c, "volume": v,
                },
            )
        )
    for d in sorted(((r.get("events") or {}).get("dividends") or {}).values(), key=lambda d: d["date"]):
        at = dt.datetime.fromtimestamp(d["date"], tz=dt.timezone.utc)
        rows.append(
            tape.observation(
                kind="dividend", source=SOURCE, producer=PRODUCER, symbol=symbol,
                observed_at=tape.utc_iso(at), window={"type": "point"},
                payload={"ex_session": at.astimezone(ET).date().isoformat(), "amount": d["amount"]},
            )
        )
    return rows


def series(obs: list[dict[str, Any]], symbol: str) -> dict[str, Any]:
    """Sessions, closes and dividends by ex-session for one symbol, oldest first, deduplicated."""
    bars: dict[str, dict[str, Any]] = {}
    divs: dict[str, float] = {}
    unique = {o["id"]: o for o in obs}  # the same fact fetched twice counts once
    for o in unique.values():
        if o["symbol"] != symbol:
            continue
        p = o["payload"]
        if o["kind"] == "bar.daily":
            bars[p["session"]] = {"close": float(p["close"]), "open_at": p["open_at"], "id": o["id"]}
        elif o["kind"] == "dividend":
            divs[p["ex_session"]] = divs.get(p["ex_session"], 0.0) + float(p["amount"])
    sessions = sorted(bars)
    return {
        "sessions": sessions,
        "close": [bars[s]["close"] for s in sessions],
        "open_at": [bars[s]["open_at"] for s in sessions],
        "ids": [bars[s]["id"] for s in sessions],
        "div": divs,
    }
