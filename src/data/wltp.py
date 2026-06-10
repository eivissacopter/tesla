"""WLTP range & efficiency reference, transcribed from the maintained Akkuwiki.

Each record is one homologated WLTP figure for a (model, trim, drive, year,
variant, wheel) combination: range in km and consumption in Wh/km. WLTP
consumption is distinct from Tesla's EPA-based rated "constant" and is kept
separate on purpose. `wheel` is the rim diameter in inches, or None when the
wiki did not break the figure down by wheel size. `wh_km` is None where the
source left it open.
"""
from typing import List, Optional

import pandas as pd
import streamlit as st

# Cell supplier (first token of the pack label) -> chemistry family.
_SUPPLIER_CHEMISTRY = {
    'Panasonic': 'NCA',
    'LG': 'NMC',
    'CATL': 'LFP',
    'BYD': 'LFP',
    'Tesla': 'NMC',
}

# fmt: off
WLTP_RECORDS = [
    # model, trim, drive, year, variant, battery, wheel, range_km, wh_km
    ('Model 3', 'Standard Range', 'RWD', '2019-2020', 'E1R',  'Panasonic 1',  None, 409, 149),
    ('Model 3', 'Standard Range', 'RWD', '2021',      'E1LR', 'Panasonic 1L', None, 448, 140),
    ('Model 3', 'Long Range',     'RWD', '2019',      'E3R',  'Panasonic 3',  None, 600, 147),
    ('Model 3', 'Long Range',     'AWD', '2019-2020', 'E3D',  'Panasonic 3',  None, 560, 160),
    ('Model 3', 'Performance',    'AWD', '2019-2020', 'E3D',  'Panasonic 3',  None, 530, 166),
    ('Model 3', 'Long Range',     'AWD', '2021',      'E3CD', 'Panasonic 3C', None, 580, 148),
    ('Model 3', 'Long Range',     'AWD', '2021',      'E3LD', 'Panasonic 3L', None, 614, 147),
    ('Model 3', 'Performance',    'AWD', '2021',      'E3LD', 'Panasonic 3L', None, 567, 165),
    ('Model 3', 'Performance',    'AWD', '2022',      'E3LD', 'Panasonic 3L', None, 559, 165),

    ('Model 3', 'Long Range',     'AWD', '2021',      'E5CD', 'LG 5C', None, 580, 148),
    ('Model Y', 'Long Range',     'AWD', '2021',      'Y5CD', 'LG 5C', None, 507, 169),

    ('Model 3', 'Long Range',     'AWD', '2021',      'E5LD', 'LG 5L', None, 614, 147),
    ('Model 3', 'Long Range',     'AWD', '2022',      'E5LD', 'LG 5L', None, 604, 147),
    ('Model 3', 'Long Range',     'AWD', '2023',      'E5LD', 'LG 5L', None, 604, 147),
    ('Model 3', 'Long Range',     'RWD', '2023',      'E5LR', 'LG 5L', 19, 620, 144),
    ('Model 3', 'Long Range',     'RWD', '2023',      'E5LR', 'LG 5L', 18, 678, 130),
    ('Model 3', 'Long Range',     'AWD', '2024-2025', 'H5LD', 'LG 5L', None, 629, 147),
    ('Model 3', 'Performance',    'AWD', '2022-2023', 'E5LD', 'LG 5L', None, 547, 165),
    ('Model 3', 'Performance',    'AWD', '2024-2025', 'H5LD', 'LG 5L', None, 528, 167),
    ('Model Y', 'Long Range',     'AWD', '2022-2025', 'Y5LD', 'LG 5L', None, 533, 169),
    ('Model Y', 'Long Range',     'RWD', '2024-2025', 'Y5LR', 'LG 5L', 20, 565, 155),
    ('Model Y', 'Long Range',     'RWD', '2024-2025', 'Y5LR', 'LG 5L', 19, 600, 149),
    ('Model Y', 'Long Range',     'AWD', '2025',      'YS5LD', 'LG 5L', 20, 568, 153),
    ('Model Y', 'Long Range',     'AWD', '2025',      'YS5LD', 'LG 5L', 19, 586, 148),
    ('Model Y', 'Long Range',     'RWD', '2025',      'YS5LR', 'LG 5L', 20, 622, 142),
    ('Model Y', 'Performance',    'AWD', '2022-2025', 'Y5LD', 'LG 5L', None, 514, 171),

    ('Model 3', 'Long Range',     'RWD', '2025',      'H5MR',  'LG 5M', 19, 691, 136),
    ('Model 3', 'Long Range',     'RWD', '2025',      'H5MR',  'LG 5M', 18, 750, 126),
    ('Model 3', 'Long Range',     'AWD', '2025',      'H5MD',  'LG 5M', 19, 660, 143),
    ('Model 3', 'Performance',    'AWD', '2025',      'H5MD',  'LG 5M', 20, 571, 165),
    ('Model Y', 'Long Range',     'RWD', '2026',      'YS5MR', 'LG 5M', 20, 661, 142),
    ('Model Y', 'Long Range',     'AWD', '2025',      'YS5MD', 'LG 5M', 20, 600, 159),
    ('Model Y', 'Long Range',     'AWD', '2025',      'YS5MD', 'LG 5M', 19, 629, 149),
    ('Model Y', 'Performance',    'AWD', '2025',      'YS5MD', 'LG 5M', 21, 580, 162),

    ('Model Y L', 'Long Range',   'AWD', '2026',      'YL5ND', 'LG 5N', 19, 681, 146),

    ('Model 3', 'Standard Range', 'RWD', '2020',      'E6R',  'CATL 6C', None, 440, 142),
    ('Model 3', 'Standard Range', 'RWD', '2021',      'E6CR', 'CATL 6C', None, 448, 142),
    ('Model 3', 'Standard Range', 'RWD', '2021',      'E6LR', 'CATL 6L', None, 491, 144),
    ('Model 3', 'Standard Range', 'RWD', '2022',      'E6LR', 'CATL 6L', None, 491, 144),
    ('Model 3', 'Standard Range', 'RWD', '2023',      'E6LR', 'CATL 6L', None, 491, 144),
    ('Model 3', 'Standard Range', 'RWD', '2024',      'H6LR', 'CATL 6L', None, 513, 132),
    ('Model Y', 'Standard Range', 'RWD', '2022-2024', 'Y6LR', 'CATL 6L', 19, 455, 157),
    ('Model Y', 'Standard Range', 'RWD', '2022-2024', 'Y6LR', 'CATL 6L', 20, 430, None),

    ('Model 3', 'Standard Range', 'RWD', '2025',      'H6MR',  'CATL 6M', 19, 520, 138),
    ('Model 3', 'Standard',       'RWD', '2026',      'HB6MR', 'CATL 6M', 18, 534, 130),
    ('Model Y', 'Standard Range', 'RWD', '2025',      'YS6MR', 'CATL 6M', 19, 500, 139),
    ('Model Y', 'Standard Range', 'RWD', '2025',      'YS6MR', 'CATL 6M', 20, 466, 153),
    ('Model Y', 'Standard',       'RWD', '2026',      'YB6MR', 'CATL 6M', 18, 534, 131),
    ('Model Y', 'Standard',       'RWD', '2026',      'YB6MR', 'CATL 6M', 19, 505, 138),

    ('Model Y', 'Standard Range', 'RWD', '2023',      'Y7CR', 'BYD 7C', 19, 455, 157),
    ('Model Y', 'Standard Range', 'RWD', '2023',      'Y7CR', 'BYD 7C', 20, 430, 157),
    ('Model Y', 'Standard Range', 'RWD', '2024',      'Y7CR', 'BYD 7C', 19, 455, 157),
    ('Model Y', 'Standard Range', 'RWD', '2024',      'Y7CR', 'BYD 7C', 20, 430, 157),

    ('Model Y', 'Long Range',     'RWD', '2026',      'YB8LR', 'Tesla 8L', 19, 657, 127),
    ('Model Y', 'Long Range',     'RWD', '2026',      'YB8LR', 'Tesla 8L', 20, 617, 136),
    ('Model Y', 'Long Range',     'RWD', '2026',      'YS8LR', 'Tesla 8L', 20, 603, 140),
]
# fmt: on

_COLUMNS = ['Model', 'Trim', 'Drive', 'Year', 'Variant', 'Battery', 'Wheel', 'Range_km', 'Wh_km']


class WltpReference:
    """Access to the WLTP range/consumption reference dataset."""

    @staticmethod
    @st.cache_data(show_spinner=False)
    def get_df() -> pd.DataFrame:
        """Return the WLTP records as a tidy, annotated DataFrame."""
        df = pd.DataFrame(WLTP_RECORDS, columns=_COLUMNS)
        df['Chemistry'] = df['Battery'].map(
            lambda label: _SUPPLIER_CHEMISTRY.get(str(label).split(' ')[0], 'Other')
        )
        df['Wheel'] = df['Wheel'].astype('Int64')
        df['Wheel Label'] = df['Wheel'].map(lambda w: f'{int(w)}"' if pd.notna(w) else 'std')
        trim_short = {
            'Long Range': 'LR', 'Performance': 'Perf', 'Standard Range': 'SR',
            'Standard': 'Std', 'Plaid': 'Plaid',
        }
        df['Trim Short'] = df['Trim'].map(lambda t: trim_short.get(t, t))
        df['Config'] = df['Model'] + ' ' + df['Trim'] + ' ' + df['Drive'] + ' ' + df['Year']
        # Spec uniquely identifies a configuration (variant + trim + drive + year) so
        # chart categories never collide and get silently summed by Plotly.
        df['Spec'] = df['Variant'] + ' · ' + df['Trim Short'] + ' ' + df['Drive'] + ' · ' + df['Year']
        df['Label'] = df['Spec'] + ' (' + df['Wheel Label'] + ')'
        df['Year Start'] = df['Year'].str.extract(r'(\d{4})').astype(int)
        return df
