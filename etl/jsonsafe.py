"""Make payloads strict-JSON safe.

Python's json writes NaN/Infinity as bare ``NaN``/``Infinity`` tokens, which are
invalid JSON — browsers (JSON.parse), PostgREST and many parsers reject them.
``clean`` recursively replaces non-finite floats with None so artifacts are
valid JSON everywhere.
"""

from __future__ import annotations

import math


def clean(obj):
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    return obj
