"""Greedy clue minimizer (#483/#486): drop items from a dict while a caller
predicate stays true, batching removals so most drops cost no proof. `test`
is any predicate over a dict.
"""


def strip(items, keep, test):
    """Drop half the remaining items at once, halve the batch on failure, and
    pin an item only when it fails alone. Items in `keep` are never dropped."""
    items = dict(items)
    order = [q for q in items if q not in keep]
    i, k = 0, max(1, len(order) // 2)
    while i < len(order):
        chunk = order[i : i + k]
        trial = {q: v for q, v in items.items() if q not in chunk}
        if test(trial):
            items, i = trial, i + k
        elif k > 1:
            k //= 2
        else:
            i += 1
    return items
