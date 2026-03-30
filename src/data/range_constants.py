"""Sidebar-friendly accessors for verified rated-range constants."""
from __future__ import annotations

from typing import Any, Dict, List

from .consumption_constants import FACTORY_CONSTANTS


CUSTOM_REFERENCE: Dict[str, Any] = {
    "label": "Custom / Manual",
    "model_family": "Any Tesla",
    "constant_wh_km": 140.0,
    "market": "Europe",
    "notes": "Use this when your exact pack or wheel setup is not listed yet.",
}


def _build_reference(record) -> Dict[str, Any]:
    details = [record.pack_code, record.battery, record.years]
    if record.wheels:
        details.append(record.wheels)
    if record.release:
        details.append(record.release)

    return {
        "label": record.preset_label(),
        "model_family": f"{record.model} {record.variant}",
        "constant_wh_km": record.constant_wh_km,
        "market": "Europe",
        "notes": " | ".join(part for part in details if part),
    }


class RangeConstantClient:
    """Helper accessors for rated-range constants."""

    @staticmethod
    def list_labels() -> List[str]:
        """Return all selectable range-constant presets."""
        return [CUSTOM_REFERENCE["label"]] + [
            _build_reference(record)["label"] for record in FACTORY_CONSTANTS
        ]

    @staticmethod
    def get_reference(label: str) -> Dict[str, Any]:
        """Return a preset record by label."""
        if label == CUSTOM_REFERENCE["label"]:
            return CUSTOM_REFERENCE.copy()

        for record in FACTORY_CONSTANTS:
            reference = _build_reference(record)
            if reference["label"] == label:
                return reference

        return CUSTOM_REFERENCE.copy()
