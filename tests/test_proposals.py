import math

import pytest

from app.policy.proposals import action_hash, canonical_json


def test_hash_is_stable_across_key_order():
    assert action_hash({"target": "USER", "body": {"b": 2, "a": 1}}) == action_hash({"body": {"a": 1, "b": 2}, "target": "USER"})


def test_nonfinite_numbers_are_rejected():
    with pytest.raises(ValueError):
        canonical_json({"value": math.nan})
