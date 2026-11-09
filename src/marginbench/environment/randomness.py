"""Keyed randomness (SPEC 11).

Stream key = SHA-256(f"{sim_version}|{partition}|{master_seed}|{replication}|{mechanism}|{entity_id}|{index}").
The first 8 bytes, as an unsigned big-endian integer, seed np.random.Generator(PCG64DXSM(seed)).
No global RNG and no Python ``hash()`` anywhere.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

POLICY_SALT = "MB-POLICY-MC-SALT-7f3a9c"  # distinct from every environment key component


def key_to_seed(key: str) -> int:
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "big", signed=False)


def generator_from_seed(seed: int) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64DXSM(seed))


@dataclass(frozen=True)
class StreamFactory:
    """Builds keyed generators for one (sim_version, partition, master_seed, replication)."""

    sim_version: str
    partition: str
    master_seed: int
    replication: int

    def key(self, mechanism: str, entity_id: str, index: int | str = 0) -> str:
        return (
            f"{self.sim_version}|{self.partition}|{self.master_seed}|{self.replication}|"
            f"{mechanism}|{entity_id}|{index}"
        )

    def seed(self, mechanism: str, entity_id: str, index: int | str = 0) -> int:
        return key_to_seed(self.key(mechanism, entity_id, index))

    def gen(self, mechanism: str, entity_id: str, index: int | str = 0) -> np.random.Generator:
        return generator_from_seed(self.seed(mechanism, entity_id, index))

    def uniforms(self, mechanism: str, entity_id: str, index: int | str, n: int) -> np.ndarray:
        return self.gen(mechanism, entity_id, index).random(n)


def run_nonce(nonce_key: int, partition: str, replication: int) -> int:
    """Per-replication nonce for policy Monte Carlo, unrelated to master_seed (SPEC 11)."""
    return key_to_seed(f"run-nonce|{nonce_key}|{partition}|{replication}")


def policy_mc_seed(run_nonce_value: int, request_id: str, decision_index: int) -> int:
    """SHA-256(f"policy-mc|{POLICY_SALT}|{run_nonce}|{request_id}|{decision_index}")."""
    return key_to_seed(f"policy-mc|{POLICY_SALT}|{run_nonce_value}|{request_id}|{decision_index}")
