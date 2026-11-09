import ast
import hashlib
from pathlib import Path

import numpy as np

from marginbench.environment.randomness import POLICY_SALT, StreamFactory, key_to_seed, policy_mc_seed, run_nonce

SRC = Path(__file__).resolve().parents[2] / "src" / "marginbench"


def test_key_format_and_seed_derivation():
    sf = StreamFactory("sim-1.0", "dev", 11, 3)
    key = sf.key("repair", "R1", 2)
    assert key == "sim-1.0|dev|11|3|repair|R1|2"
    expected = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
    assert sf.seed("repair", "R1", 2) == expected == key_to_seed(key)


def test_same_key_same_draws_and_generator_type():
    sf = StreamFactory("sim-1.0", "dev", 11, 3)
    g = sf.gen("x", "e", 0)
    assert isinstance(g.bit_generator, np.random.PCG64DXSM)
    assert np.array_equal(sf.uniforms("x", "e", 0, 5), sf.uniforms("x", "e", 0, 5))
    assert not np.array_equal(sf.uniforms("x", "e", 0, 5), sf.uniforms("x", "e", 1, 5))


def test_policy_mc_seed_formula():
    nonce = run_nonce(5, "dev", 0)
    s = policy_mc_seed(nonce, "R1", 0)
    key = f"policy-mc|{POLICY_SALT}|{nonce}|R1|0"
    assert s == int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
    assert POLICY_SALT not in ("dev", "train", "calib", "eval", "stress", "sens", "pilot")


def test_no_global_rng_or_builtin_hash_in_src():
    banned_np = {"seed", "rand", "randn", "random", "randint", "choice", "normal", "uniform", "poisson",
                 "gamma", "beta", "lognormal", "shuffle", "permutation", "default_rng"}
    for py in SRC.rglob("*.py"):
        tree = ast.parse(py.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "hash":
                raise AssertionError(f"builtin hash() used in {py}")
            if isinstance(node, ast.Import):
                for n in node.names:
                    assert n.name != "random", f"stdlib random imported in {py}"
            if isinstance(node, ast.ImportFrom):
                assert node.module != "random", f"stdlib random imported in {py}"
            if isinstance(node, ast.Attribute) and node.attr in banned_np:
                v = node.value
                if isinstance(v, ast.Attribute) and v.attr == "random" and isinstance(v.value, ast.Name) and v.value.id in ("np", "numpy"):
                    raise AssertionError(f"global numpy RNG np.random.{node.attr} used in {py}")
