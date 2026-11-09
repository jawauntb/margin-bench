import math

import numpy as np
import pytest

from marginbench.hashing import StreamHasher, canonical_hash, canonical_json


def test_canonical_json_sorted_no_whitespace():
    assert canonical_json({"b": 1, "a": [1, 2]}) == '{"a":[1,2],"b":1}'


def test_float_repr_round_trip():
    x = 0.1 + 0.2
    s = canonical_json({"x": x})
    assert s == '{"x":' + repr(x) + "}"
    assert float(s[5:-1]) == x


def test_numpy_types_and_tuples():
    assert canonical_json({"a": np.int64(3), "b": np.float64(0.5), "c": (1, 2)}) == '{"a":3,"b":0.5,"c":[1,2]}'


def test_nan_rejected():
    with pytest.raises(ValueError):
        canonical_json({"x": math.nan})


def test_hash_deterministic():
    assert canonical_hash({"a": 1}) == canonical_hash({"a": 1})
    assert canonical_hash({"a": 1}) != canonical_hash({"a": 2})


def test_stream_hasher_order_sensitive():
    a, b = StreamHasher(), StreamHasher()
    a.add({"x": 1}); a.add({"x": 2})
    b.add({"x": 2}); b.add({"x": 1})
    assert a.hexdigest() != b.hexdigest()
