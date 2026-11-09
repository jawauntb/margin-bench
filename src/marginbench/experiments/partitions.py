"""Partitions and seed manifests (SPEC 11, 12)."""

from __future__ import annotations

from typing import Any

from marginbench.config import PARTITIONS, Config
from marginbench.environment.randomness import run_nonce


def seed_manifest(cfg: Config, partition: str, replications: list[int]) -> dict[str, Any]:
    if partition not in PARTITIONS:
        raise ValueError(f"unknown partition {partition}")
    return {
        "partition": partition,
        "master_seed": cfg.seeds.master(partition),
        "sim_version": cfg.versions.sim_version,
        "stream_schema": cfg.versions.stream_schema,
        "nonce_key": cfg.seeds.nonce_key,
        "replications": [{"replication": r, "run_nonce": run_nonce(cfg.seeds.nonce_key, partition, r)} for r in replications],
    }
