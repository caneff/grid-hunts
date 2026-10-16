"""`renbanana_verify.covering` picks few grids that between them hold every key
the pool holds; both known-grid tests lean on it (#556).

    uv run finders/renbanana/tools/test_covering_grids.py

Run it from the repo root.
"""

import sys

sys.path.insert(0, "finders")
import renbanana_verify as rv


def test_picks_greedily_and_covers_every_key():
    keys = {"a": {1, 2, 3}, "b": {3, 4}, "c": {4}, "d": {5}}
    picked = rv.covering(keys.keys(), keys.get)
    assert picked == ["a", "b", "d"], picked


def test_the_largest_remaining_set_beats_the_first_useful_one():
    keys = {"small": {1}, "big": {1, 2, 3}, "tail": {3, 4}}
    assert rv.covering(keys.keys(), keys.get) == ["big", "tail"]


def test_first_best_wins_a_tie():
    keys = {"x": {1}, "y": {1}}
    assert rv.covering(["x", "y"], keys.get) == ["x"]


def test_group_key_tells_chocolate_shape_from_banana_size():
    assert rv.group_key([(0, 0), (0, 1), (0, 2)], True) == ("chocolate", 1, 3)
    assert rv.group_key([(0, 0), (1, 0), (1, 1)], False) == ("banana", 3)


if __name__ == "__main__":
    test_picks_greedily_and_covers_every_key()
    test_the_largest_remaining_set_beats_the_first_useful_one()
    test_first_best_wins_a_tie()
    test_group_key_tells_chocolate_shape_from_banana_size()
    print("PASS")
