"""Track M: MarginBench on real markets (docs/TRACK-M.md).

The synthetic benchmark asks whether beating a proxy raises long-horizon value in a declared world.
Track M asks the same question of real forecasters on real market outcomes: every forecast is
committed before its outcome exists, settled from public data, and scored with proper scores.

Modules: ``tape`` (the Observation and Forecast envelopes, shared with hvega), ``yahoo`` (public
daily bars, the only I/O), ``forecasters`` (pure baselines), ``ledger`` (append-only files),
``settle``, ``score`` (proper scores and the paired evidence gate) and ``nightly`` (the loop).
"""
