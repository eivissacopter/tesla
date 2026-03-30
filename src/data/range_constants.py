"""Rated-range consumption constants curated from the Akkuwiki."""
from __future__ import annotations

from typing import Any, Dict, List


RANGE_CONSTANT_REFERENCES: List[Dict[str, Any]] = [
    {
        'label': 'Custom / Manual',
        'model_family': 'Any Tesla',
        'constant_wh_km': 140.0,
        'market': 'Global',
        'notes': 'Use this when your exact trim or wheel setup is not listed yet.',
    },
    {
        'label': 'Model 3 RWD 2020 (E6R)',
        'model_family': 'Model 3 RWD',
        'constant_wh_km': 133.0,
        'market': 'Europe',
        'notes': 'CATL 6C reference from the Akkuwiki.',
    },
    {
        'label': 'Model 3 RWD 2021 (E6CR)',
        'model_family': 'Model 3 RWD',
        'constant_wh_km': 128.0,
        'market': 'Europe',
        'notes': 'CATL 6C reference from the Akkuwiki.',
    },
    {
        'label': 'Model 3 RWD 2021-2024 (E6LR / H6LR)',
        'model_family': 'Model 3 RWD',
        'constant_wh_km': 139.0,
        'market': 'Europe',
        'notes': 'CATL 6L reference used for the main Model 3 RWD era.',
    },
    {
        'label': 'Model 3 LR RWD 2019 (E3R)',
        'model_family': 'Model 3 Long Range',
        'constant_wh_km': 145.5,
        'market': 'Europe',
        'notes': 'Panasonic long-range RWD reference.',
    },
    {
        'label': 'Model 3 LR AWD 2019-2020 (E3D)',
        'model_family': 'Model 3 Long Range',
        'constant_wh_km': 152.5,
        'market': 'Europe',
        'notes': 'Early pre-refresh dual-motor constant.',
    },
    {
        'label': 'Model 3 LR AWD 2021-2023 (E3CD / E3LD / E5LD)',
        'model_family': 'Model 3 Long Range',
        'constant_wh_km': 136.7,
        'market': 'Europe',
        'notes': 'Refresh-era long-range AWD constant.',
    },
    {
        'label': 'Model 3 LR RWD 2023 (E5LR)',
        'model_family': 'Model 3 Long Range',
        'constant_wh_km': 143.0,
        'market': 'Europe',
        'notes': 'LG 5L long-range RWD reference.',
    },
    {
        'label': 'Model 3 LR AWD 2024-2025 (H5LD)',
        'model_family': 'Model 3 Long Range',
        'constant_wh_km': 143.5,
        'market': 'Europe',
        'notes': 'Highland long-range AWD reference.',
    },
    {
        'label': 'Model 3 Performance 2019-2020 (E3D)',
        'model_family': 'Model 3 Performance',
        'constant_wh_km': 152.5,
        'market': 'Europe',
        'notes': 'Early performance constant from the Akkuwiki.',
    },
    {
        'label': 'Model 3 Performance 2021-2023 (E3LD / E5LD)',
        'model_family': 'Model 3 Performance',
        'constant_wh_km': 159.0,
        'market': 'Europe',
        'notes': 'Refresh-era performance constant.',
    },
    {
        'label': 'Model Y RWD 2022-2024 19in (Y6LR / Y7CR)',
        'model_family': 'Model Y RWD',
        'constant_wh_km': 142.5,
        'market': 'Europe',
        'notes': 'CATL/BYD RWD reference on 19-inch wheels.',
    },
    {
        'label': 'Model Y RWD 2022-2024 20in (Y6LR / Y7CR)',
        'model_family': 'Model Y RWD',
        'constant_wh_km': 153.0,
        'market': 'Europe',
        'notes': 'CATL/BYD RWD reference on 20-inch wheels.',
    },
    {
        'label': 'Model Y RWD 2025 19in (YS6MR)',
        'model_family': 'Model Y RWD',
        'constant_wh_km': 147.6,
        'market': 'Europe',
        'notes': 'CATL 6M reference on 19-inch wheels.',
    },
    {
        'label': 'Model Y RWD 2025 20in (YS6MR)',
        'model_family': 'Model Y RWD',
        'constant_wh_km': 152.6,
        'market': 'Europe',
        'notes': 'CATL 6M reference on 20-inch wheels.',
    },
    {
        'label': 'Model Y LR AWD 2021-2025 (Y5CD / Y5LD)',
        'model_family': 'Model Y Long Range',
        'constant_wh_km': 148.5,
        'market': 'Europe',
        'notes': 'Main long-range AWD reference.',
    },
    {
        'label': 'Model Y LR AWD 2025 19in (YS5LD)',
        'model_family': 'Model Y Long Range',
        'constant_wh_km': 147.1,
        'market': 'Europe',
        'notes': 'Opal long-range AWD reference on 19-inch wheels.',
    },
    {
        'label': 'Model Y LR AWD 2025 20in (YS5LD)',
        'model_family': 'Model Y Long Range',
        'constant_wh_km': 158.7,
        'market': 'Europe',
        'notes': 'Opal long-range AWD reference on 20-inch wheels.',
    },
    {
        'label': 'Model Y Performance 2022-2025 (Y5LD)',
        'model_family': 'Model Y Performance',
        'constant_wh_km': 165.0,
        'market': 'Europe',
        'notes': 'Model Y Performance AWD reference.',
    },
    {
        'label': 'Model Y Performance 2025+ (YS5MD)',
        'model_family': 'Model Y Performance',
        'constant_wh_km': 169.2,
        'market': 'Europe',
        'notes': 'Opal performance reference.',
    },
]


class RangeConstantClient:
    """Helper accessors for rated-range constants."""

    @staticmethod
    def list_labels() -> List[str]:
        """Return all selectable range-constant presets."""
        return [record['label'] for record in RANGE_CONSTANT_REFERENCES]

    @staticmethod
    def get_reference(label: str) -> Dict[str, Any]:
        """Return a preset record by label."""
        for record in RANGE_CONSTANT_REFERENCES:
            if record['label'] == label:
                return record
        return RANGE_CONSTANT_REFERENCES[0].copy()
