"""Human-readable, anonymous car labels.

Turns the opaque HMAC car id into something a person can read in a legend or
dropdown -- e.g. "Model Y Long Range AWD 2024 MIG" -- while staying fully
anonymous (still just model/trim/drivetrain/year/plant, no identity). Cars that
share the exact same spec get a stable "#n" suffix so they remain distinct.
"""

from __future__ import annotations

from collections import defaultdict


def build_label(rec: dict) -> str:
    """Build a readable label from a record's public identity fields."""
    parts = []
    for key, cast in (("model", str), ("trim", str), ("drivetrain", str),
                      ("model_year", lambda v: str(int(float(v)))), ("factory", str)):
        val = rec.get(key)
        if val is None or (isinstance(val, float) and val != val):  # None / NaN
            continue
        s = cast(val).strip()
        if s and s.lower() != "nan":
            parts.append(s)
    return " ".join(parts) if parts else "Unknown Tesla"


def build_car_labels(records: list[dict]) -> dict[str, str]:
    """Map each car id -> a readable, de-duplicated label.

    ``records`` are dicts carrying at least 'car' plus identity fields. Cars with
    an identical spec get a deterministic '#n' suffix (ordered by car id).
    """
    base = {r["car"]: build_label(r) for r in records if r.get("car")}
    groups: dict[str, list[str]] = defaultdict(list)
    for car, lbl in base.items():
        groups[lbl].append(car)
    out: dict[str, str] = {}
    for lbl, cars in groups.items():
        if len(cars) == 1:
            out[cars[0]] = lbl
        else:
            for i, car in enumerate(sorted(cars), 1):
                out[car] = f"{lbl} #{i}"
    return out
