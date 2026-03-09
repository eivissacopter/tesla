"""Battery chronology reference data and resolver logic."""
import re
from typing import Any, Optional

import pandas as pd
import streamlit as st


BATTERY_CODE_REFERENCE = [
    {
        'battery_code': 'D/E',
        'manufacturer': 'Panasonic',
        'cell_format': '18650',
        'chemistry': 'NCA',
        'cell_ah': None,
        'notes': 'Legacy Model S/X pack code from the provided Akkuchronik PDF.',
    },
    {
        'battery_code': 'b1',
        'manufacturer': 'Panasonic',
        'cell_format': '18650',
        'chemistry': 'NCA',
        'cell_ah': None,
        'notes': 'Legacy Model S/X battery code from the provided Akkuchronik PDF.',
    },
    {
        'battery_code': '1/1C/3/3C',
        'manufacturer': 'Panasonic',
        'cell_format': '2170C',
        'chemistry': 'NCA',
        'cell_ah': 4.8,
        'notes': 'Panasonic 2170C NCA family.',
    },
    {
        'battery_code': '1L/3L',
        'manufacturer': 'Panasonic',
        'cell_format': '2170L',
        'chemistry': 'NCA',
        'cell_ah': 5.0,
        'notes': 'Panasonic 2170L NCA family.',
    },
    {
        'battery_code': '5/5C',
        'manufacturer': 'LG Chem',
        'cell_format': '2170C',
        'chemistry': 'NMC',
        'cell_ah': 4.6,
        'notes': 'LG Chem 2170C NMC family.',
    },
    {
        'battery_code': '5L',
        'manufacturer': 'LG Chem',
        'cell_format': '2170L',
        'chemistry': 'NMC',
        'cell_ah': 5.0,
        'notes': 'LG Chem 2170L NMC family.',
    },
    {
        'battery_code': '5M',
        'manufacturer': 'LG Chem',
        'cell_format': '2170M',
        'chemistry': 'NMC',
        'cell_ah': 5.3,
        'notes': 'LG Chem 2170M NMC family.',
    },
    {
        'battery_code': '6/6C',
        'manufacturer': 'CATL',
        'cell_format': 'Prismatic',
        'chemistry': 'LFP',
        'cell_ah': 163.0,
        'notes': 'CATL prismatic LFP family used for early 62 kWh packs.',
    },
    {
        'battery_code': '6L',
        'manufacturer': 'CATL',
        'cell_format': 'Prismatic',
        'chemistry': 'LFP',
        'cell_ah': 173.0,
        'notes': 'CATL prismatic LFP family from the provided PDF.',
    },
    {
        'battery_code': '6M',
        'manufacturer': 'CATL',
        'cell_format': 'Prismatic',
        'chemistry': 'LFP',
        'cell_ah': 180.0,
        'notes': 'CATL prismatic LFP family used for 64.5 kWh era packs.',
    },
    {
        'battery_code': '7C',
        'manufacturer': 'BYD',
        'cell_format': 'Prismatic',
        'chemistry': 'LFP',
        'cell_ah': 177.6,
        'notes': 'BYD blade-family LFP pack code from the provided PDF.',
    },
    {
        'battery_code': '8L',
        'manufacturer': 'Unknown',
        'cell_format': 'Unknown',
        'chemistry': 'Unknown',
        'cell_ah': None,
        'notes': 'Placeholder entry present in the provided PDF.',
    },
    {
        'battery_code': '4680',
        'manufacturer': 'Tesla',
        'cell_format': '4680',
        'chemistry': 'NMC',
        'cell_ah': 23.35,
        'notes': 'Tesla 4680-based NMC pack family.',
    },
]


CHRONOLOGY_RECORDS = [
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Standard',
        'drivetrain': 'RWD',
        'battery_label': '52',
        'battery_code': None,
        'chemistry': 'Unknown',
        'plant': 'Fremont',
        'year_from': 2019,
        'quarter_from': 1,
        'year_to': 2020,
        'quarter_to': 2,
        'confidence': 'medium',
        'notes': 'Seeded from the provided Akkuchronik PDF. Early Europe Model 3 Standard RWD era.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Standard',
        'drivetrain': 'RWD',
        'battery_label': '55 MIC',
        'battery_code': None,
        'chemistry': 'Unknown',
        'plant': 'MIC',
        'year_from': 2020,
        'quarter_from': 3,
        'year_to': 2021,
        'quarter_to': 1,
        'confidence': 'medium',
        'notes': 'Transition period before the 62 MIC era, based on the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Standard',
        'drivetrain': 'RWD',
        'battery_label': '62 MIC',
        'battery_code': '6/6C',
        'chemistry': 'LFP',
        'plant': 'MIC',
        'year_from': 2021,
        'quarter_from': 2,
        'year_to': 2023,
        'quarter_to': 4,
        'confidence': 'high',
        'notes': 'Main 62 MIC phase shown in the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Standard',
        'drivetrain': 'RWD',
        'battery_label': '64.5 MIC',
        'battery_code': '6M',
        'chemistry': 'LFP',
        'plant': 'MIC',
        'year_from': 2024,
        'quarter_from': 1,
        'year_to': 2026,
        'quarter_to': 4,
        'confidence': 'high',
        'notes': 'Late MIC LFP era from the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Long Range',
        'drivetrain': 'AWD',
        'battery_label': '78',
        'battery_code': '1/1C/3/3C',
        'chemistry': 'NCA',
        'plant': 'Fremont',
        'year_from': 2019,
        'quarter_from': 1,
        'year_to': 2020,
        'quarter_to': 2,
        'confidence': 'medium',
        'notes': 'Early Europe Model 3 Long Range AWD era.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Long Range',
        'drivetrain': 'AWD',
        'battery_label': '82',
        'battery_code': '1L/3L',
        'chemistry': 'NCA',
        'plant': 'Fremont',
        'year_from': 2020,
        'quarter_from': 3,
        'year_to': 2021,
        'quarter_to': 4,
        'confidence': 'medium',
        'notes': 'Intermediate 82 kWh era from the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Long Range',
        'drivetrain': 'AWD',
        'battery_label': '79 MIC',
        'battery_code': '5L',
        'chemistry': 'NMC',
        'plant': 'MIC',
        'year_from': 2022,
        'quarter_from': 1,
        'year_to': 2024,
        'quarter_to': 4,
        'confidence': 'medium',
        'notes': 'MIC long-range era shown in the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Long Range',
        'drivetrain': 'AWD',
        'battery_label': '85 MIC',
        'battery_code': '5M',
        'chemistry': 'NMC',
        'plant': 'MIC',
        'year_from': 2025,
        'quarter_from': 1,
        'year_to': 2026,
        'quarter_to': 4,
        'confidence': 'medium',
        'notes': 'Late MIC long-range era shown in the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Performance',
        'drivetrain': 'AWD',
        'battery_label': '78',
        'battery_code': '1/1C/3/3C',
        'chemistry': 'NCA',
        'plant': 'Fremont',
        'year_from': 2019,
        'quarter_from': 1,
        'year_to': 2020,
        'quarter_to': 2,
        'confidence': 'medium',
        'notes': 'Early Europe Model 3 Performance era.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Performance',
        'drivetrain': 'AWD',
        'battery_label': '82',
        'battery_code': '1L/3L',
        'chemistry': 'NCA',
        'plant': 'Fremont',
        'year_from': 2020,
        'quarter_from': 3,
        'year_to': 2021,
        'quarter_to': 4,
        'confidence': 'medium',
        'notes': 'Intermediate Europe Model 3 Performance era.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Performance',
        'drivetrain': 'AWD',
        'battery_label': '79 MIC',
        'battery_code': '5L',
        'chemistry': 'NMC',
        'plant': 'MIC',
        'year_from': 2022,
        'quarter_from': 1,
        'year_to': 2024,
        'quarter_to': 4,
        'confidence': 'medium',
        'notes': 'MIC performance era from the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Performance',
        'drivetrain': 'AWD',
        'battery_label': '85 MIC',
        'battery_code': '5M',
        'chemistry': 'NMC',
        'plant': 'MIC',
        'year_from': 2025,
        'quarter_from': 1,
        'year_to': 2026,
        'quarter_to': 4,
        'confidence': 'medium',
        'notes': 'Late MIC performance era from the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Standard',
        'drivetrain': 'RWD',
        'battery_label': '62 MIC',
        'battery_code': '6/6C',
        'chemistry': 'LFP',
        'plant': 'MIC',
        'year_from': 2022,
        'quarter_from': 1,
        'year_to': 2022,
        'quarter_to': 2,
        'confidence': 'high',
        'notes': 'Initial Europe Model Y RWD phase from the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Standard',
        'drivetrain': 'RWD',
        'battery_label': '60 MIG',
        'battery_code': '7C',
        'chemistry': 'LFP',
        'plant': 'MIG',
        'year_from': 2022,
        'quarter_from': 3,
        'year_to': 2023,
        'quarter_to': 2,
        'confidence': 'medium',
        'notes': 'MIG transition phase from the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Standard',
        'drivetrain': 'RWD',
        'battery_label': '62 MIG',
        'battery_code': '6L',
        'chemistry': 'LFP',
        'plant': 'MIG',
        'year_from': 2023,
        'quarter_from': 3,
        'year_to': 2024,
        'quarter_to': 2,
        'confidence': 'medium',
        'notes': 'Main MIG LFP phase from the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Standard',
        'drivetrain': 'RWD',
        'battery_label': '64.5 MIG',
        'battery_code': '6M',
        'chemistry': 'LFP',
        'plant': 'MIG',
        'year_from': 2024,
        'quarter_from': 3,
        'year_to': 2026,
        'quarter_to': 4,
        'confidence': 'high',
        'notes': 'Late MIG LFP phase from the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Long Range',
        'drivetrain': 'RWD',
        'battery_label': '74 MIG',
        'battery_code': '5L',
        'chemistry': 'NMC',
        'plant': 'MIG',
        'year_from': 2025,
        'quarter_from': 1,
        'year_to': 2026,
        'quarter_to': 4,
        'confidence': 'medium',
        'notes': 'Standard LR RWD line in the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Long Range',
        'drivetrain': 'RWD',
        'battery_label': '79 MIG',
        'battery_code': '5L',
        'chemistry': 'NMC',
        'plant': 'MIG',
        'year_from': 2022,
        'quarter_from': 1,
        'year_to': 2024,
        'quarter_to': 4,
        'confidence': 'medium',
        'notes': 'Premium LR RWD line in the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Long Range',
        'drivetrain': 'RWD',
        'battery_label': '85 MIG',
        'battery_code': '5M',
        'chemistry': 'NMC',
        'plant': 'MIG',
        'year_from': 2025,
        'quarter_from': 1,
        'year_to': 2026,
        'quarter_to': 4,
        'confidence': 'medium',
        'notes': 'Late MIG long-range RWD era from the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Long Range',
        'drivetrain': 'AWD',
        'battery_label': '75 MIC',
        'battery_code': '1L/3L',
        'chemistry': 'NCA',
        'plant': 'MIC',
        'year_from': 2022,
        'quarter_from': 1,
        'year_to': 2022,
        'quarter_to': 2,
        'confidence': 'medium',
        'notes': 'Early Europe Model Y LR AWD phase from the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Long Range',
        'drivetrain': 'AWD',
        'battery_label': '79 MIC',
        'battery_code': '5L',
        'chemistry': 'NMC',
        'plant': 'MIC',
        'year_from': 2022,
        'quarter_from': 3,
        'year_to': 2023,
        'quarter_to': 4,
        'confidence': 'medium',
        'notes': 'MIC LR AWD phase from the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Long Range',
        'drivetrain': 'AWD',
        'battery_label': '79 MIG',
        'battery_code': '5L',
        'chemistry': 'NMC',
        'plant': 'MIG',
        'year_from': 2024,
        'quarter_from': 1,
        'year_to': 2024,
        'quarter_to': 4,
        'confidence': 'medium',
        'notes': 'MIG LR AWD phase from the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Long Range',
        'drivetrain': 'AWD',
        'battery_label': '85 MIG',
        'battery_code': '5M',
        'chemistry': 'NMC',
        'plant': 'MIG',
        'year_from': 2025,
        'quarter_from': 1,
        'year_to': 2026,
        'quarter_to': 4,
        'confidence': 'medium',
        'notes': 'Late MIG LR AWD phase from the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Performance',
        'drivetrain': 'AWD',
        'battery_label': '79 MIG',
        'battery_code': '5L',
        'chemistry': 'NMC',
        'plant': 'MIG',
        'year_from': 2022,
        'quarter_from': 1,
        'year_to': 2024,
        'quarter_to': 4,
        'confidence': 'medium',
        'notes': 'Main Model Y Performance era from the provided Akkuchronik PDF.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Performance',
        'drivetrain': 'AWD',
        'battery_label': '85 MIG',
        'battery_code': '5M',
        'chemistry': 'NMC',
        'plant': 'MIG',
        'year_from': 2025,
        'quarter_from': 1,
        'year_to': 2026,
        'quarter_to': 4,
        'confidence': 'medium',
        'notes': 'Late Model Y Performance era from the provided Akkuchronik PDF.',
    },
]


class BatteryChronologyClient:
    """Access and resolve Akkuchronik reference data."""

    @staticmethod
    @st.cache_data
    def get_chronology_df() -> pd.DataFrame:
        """Return the curated chronology dataset as a DataFrame."""
        df = pd.DataFrame(CHRONOLOGY_RECORDS)
        if not df.empty:
            df['start_index'] = df.apply(
                lambda row: BatteryChronologyClient._quarter_index(int(row['year_from']), int(row['quarter_from'])),
                axis=1,
            )
            df['end_index'] = df.apply(
                lambda row: BatteryChronologyClient._quarter_index(int(row['year_to']), int(row['quarter_to'])),
                axis=1,
            )
        return df

    @staticmethod
    @st.cache_data
    def get_battery_code_df() -> pd.DataFrame:
        """Return the curated battery code taxonomy as a DataFrame."""
        return pd.DataFrame(BATTERY_CODE_REFERENCE)

    @staticmethod
    def resolve_candidates(
        market: str,
        model: str,
        trim: Optional[str] = None,
        drivetrain: Optional[str] = None,
        year: Optional[int] = None,
        quarter: Optional[int] = None,
    ) -> pd.DataFrame:
        """Resolve likely battery candidates for a model + quarter selection."""
        chronology_df = BatteryChronologyClient.get_chronology_df()
        if chronology_df.empty:
            return chronology_df

        candidates = chronology_df[
            (chronology_df['market'] == market)
            & (chronology_df['model'] == model)
        ].copy()

        if trim:
            candidates = candidates[candidates['trim'] == trim]
        if drivetrain:
            candidates = candidates[candidates['drivetrain'] == drivetrain]

        if year is not None and quarter is not None:
            requested_index = BatteryChronologyClient._quarter_index(year, quarter)
            candidates = candidates[
                (candidates['start_index'] <= requested_index)
                & (candidates['end_index'] >= requested_index)
            ].copy()
            if not candidates.empty:
                candidates['match_type'] = 'Quarter match'
        else:
            candidates['match_type'] = 'Model/trim match'

        if candidates.empty:
            return candidates

        candidates['sort_key'] = candidates['confidence'].map({'high': 0, 'medium': 1, 'low': 2}).fillna(9)
        return candidates.sort_values(['sort_key', 'year_from', 'quarter_from', 'battery_label']).drop(columns=['sort_key'])

    @staticmethod
    def list_models(market: str) -> list[str]:
        """List known models for a market."""
        chronology_df = BatteryChronologyClient.get_chronology_df()
        models = chronology_df.loc[chronology_df['market'] == market, 'model'].dropna().unique().tolist()
        return sorted(models)

    @staticmethod
    def list_trims(market: str, model: str) -> list[str]:
        """List known trims for a market/model combination."""
        chronology_df = BatteryChronologyClient.get_chronology_df()
        trims = chronology_df[
            (chronology_df['market'] == market) & (chronology_df['model'] == model)
        ]['trim'].dropna().unique().tolist()
        return sorted(trims)

    @staticmethod
    def list_drivetrains(market: str, model: str, trim: Optional[str] = None) -> list[str]:
        """List known drivetrains for a market/model/trim combination."""
        chronology_df = BatteryChronologyClient.get_chronology_df()
        candidates = chronology_df[
            (chronology_df['market'] == market) & (chronology_df['model'] == model)
        ]
        if trim:
            candidates = candidates[candidates['trim'] == trim]
        drivetrains = candidates['drivetrain'].dropna().unique().tolist()
        return sorted(drivetrains)

    @staticmethod
    def available_years(market: str, model: str) -> list[int]:
        """List all years covered by the chronology for the selected market/model."""
        chronology_df = BatteryChronologyClient.get_chronology_df()
        candidates = chronology_df[
            (chronology_df['market'] == market) & (chronology_df['model'] == model)
        ]
        years = set()
        for _, row in candidates.iterrows():
            years.update(range(int(row['year_from']), int(row['year_to']) + 1))
        return sorted(years)

    @staticmethod
    def annotate_dataframe(df: pd.DataFrame, market: str = 'Europe') -> pd.DataFrame:
        """Annotate a battery dataset with chronology-derived fields."""
        if df.empty:
            return df.copy()

        annotations = df.apply(
            lambda row: BatteryChronologyClient.resolve_row(row, market=market),
            axis=1,
            result_type='expand',
        )
        return pd.concat([df.copy(), annotations], axis=1)

    @staticmethod
    def resolve_row(row: pd.Series, market: str = 'Europe') -> dict[str, Any]:
        """Resolve the best chronology candidate for a single row."""
        model = BatteryChronologyClient.normalize_model(row.get('Tesla'))
        version_text = BatteryChronologyClient._normalize_text(row.get('Version'))
        battery_text = BatteryChronologyClient._normalize_text(row.get('Battery'))
        trim = BatteryChronologyClient.infer_trim(version_text)
        drivetrain = BatteryChronologyClient.infer_drivetrain(version_text, trim)
        year, quarter, source = BatteryChronologyClient.infer_year_quarter(row)

        base_result = {
            'Chronology Model': model,
            'Chronology Trim': trim,
            'Chronology Drive': drivetrain,
            'Chronology Pack': None,
            'Chronology Code': None,
            'Chronology Chemistry': None,
            'Chronology Plant': None,
            'Chronology Confidence': None,
            'Chronology Match': 'No match',
            'Chronology Source': source,
            'Chronology Candidate Count': 0,
        }

        if not model:
            return base_result

        candidates = BatteryChronologyClient.resolve_candidates(
            market=market,
            model=model,
            trim=trim,
            drivetrain=drivetrain,
            year=year,
            quarter=quarter,
        )
        if candidates.empty and year is not None:
            candidates = BatteryChronologyClient.get_chronology_df()
            candidates = candidates[
                (candidates['market'] == market)
                & (candidates['model'] == model)
                & (candidates['year_from'] <= year)
                & (candidates['year_to'] >= year)
            ].copy()
            if trim:
                candidates = candidates[candidates['trim'] == trim]
            if drivetrain:
                candidates = candidates[candidates['drivetrain'] == drivetrain]
            if not candidates.empty:
                candidates['match_type'] = 'Year match'

        if candidates.empty:
            return base_result

        ranked = candidates.copy()
        ranked['battery_hint_score'] = ranked.apply(
            lambda candidate: BatteryChronologyClient._score_candidate(candidate, battery_text),
            axis=1,
        )
        ranked['confidence_rank'] = ranked['confidence'].map({'high': 0, 'medium': 1, 'low': 2}).fillna(9)
        ranked['resolution_score'] = (
            ranked['battery_hint_score'] * 10
            + ranked['confidence_rank'].map({0: 25, 1: 15, 2: 5}).fillna(0)
            + ranked['match_type'].map({
                'Quarter match': 40,
                'Year match': 30,
                'Model/trim match': 16,
                'Model match': 10,
            }).fillna(0)
        )
        ranked = ranked.sort_values(
            ['resolution_score', 'confidence_rank', 'year_from', 'quarter_from', 'battery_label'],
            ascending=[False, True, False, False, True],
        )

        top_candidate = ranked.iloc[0]
        ambiguous = len(ranked) > 1 and ranked.iloc[0]['resolution_score'] == ranked.iloc[1]['resolution_score']
        match_text = top_candidate['match_type']
        if top_candidate['battery_hint_score'] > 0:
            match_text += ' + battery hint'
        if ambiguous:
            match_text += ' (ambiguous)'

        confidence = top_candidate['confidence']
        if ambiguous and confidence == 'high':
            confidence = 'medium'
        elif ambiguous and confidence == 'medium':
            confidence = 'low'

        return {
            'Chronology Model': model,
            'Chronology Trim': trim,
            'Chronology Drive': drivetrain,
            'Chronology Pack': top_candidate['battery_label'],
            'Chronology Code': top_candidate['battery_code'],
            'Chronology Chemistry': top_candidate['chemistry'],
            'Chronology Plant': top_candidate['plant'],
            'Chronology Confidence': confidence,
            'Chronology Match': match_text,
            'Chronology Source': source,
            'Chronology Candidate Count': int(len(ranked)),
        }

    @staticmethod
    def chemistry_guidance(chemistry: Optional[str]) -> Optional[str]:
        """Return a short usage hint based on the identified chemistry."""
        if chemistry == 'LFP':
            return 'LFP packs can usually be charged to 100% without the same everyday stress concerns as nickel-based packs, and full charges often help the BMS calibrate.'
        if chemistry in {'NCA', 'NMC'}:
            return 'NCA/NMC packs usually benefit from a more conservative daily charge window like 80-20 or 90-10 when full range is not needed.'
        return None

    @staticmethod
    def normalize_model(value: Any) -> Optional[str]:
        """Normalize free-form Tesla model labels to chronology models."""
        text = BatteryChronologyClient._normalize_text(value)
        if not text:
            return None
        if any(hint in text for hint in ['model 3', 'model3', 'm3', 'highland']):
            return 'Model 3'
        if any(hint in text for hint in ['model y', 'modely', 'my', 'juniper']):
            return 'Model Y'
        return None

    @staticmethod
    def infer_trim(value: Any) -> Optional[str]:
        """Infer trim from a version string."""
        text = BatteryChronologyClient._normalize_text(value)
        if not text:
            return None
        if 'plaid' in text:
            return 'Plaid'
        if 'performance' in text:
            return 'Performance'
        if 'long range' in text or re.search(r'\blr\b', text):
            return 'Long Range'
        if 'standard range' in text or 'standard' in text or re.search(r'\bsr\b', text) or re.search(r'\brwd\b', text):
            return 'Standard'
        return None

    @staticmethod
    def infer_drivetrain(value: Any, trim: Optional[str] = None) -> Optional[str]:
        """Infer drivetrain from a version string."""
        text = BatteryChronologyClient._normalize_text(value)
        if text and ('rwd' in text or 'rear wheel drive' in text):
            return 'RWD'
        if text and ('awd' in text or 'all wheel drive' in text or 'dual motor' in text or 'dual-motor' in text):
            return 'AWD'
        if trim in {'Performance', 'Plaid'}:
            return 'AWD'
        if trim == 'Standard':
            return 'RWD'
        return None

    @staticmethod
    def infer_year_quarter(row: pd.Series) -> tuple[Optional[int], Optional[int], Optional[str]]:
        """Try to infer year and quarter from common timeline columns."""
        year_columns = [
            'Year', 'Model Year', 'Build Year', 'Production Year', 'Registration Year', 'Delivery Year'
        ]
        quarter_columns = [
            'Quarter', 'Build Quarter', 'Production Quarter', 'Registration Quarter', 'Delivery Quarter'
        ]
        date_columns = [
            'Date', 'Build Date', 'Production Date', 'Registration Date', 'First Registration', 'Delivery Date'
        ]

        for year_column in year_columns:
            year = BatteryChronologyClient._parse_year_value(row.get(year_column))
            if year is None:
                continue
            for quarter_column in quarter_columns:
                quarter = BatteryChronologyClient._parse_quarter_value(row.get(quarter_column))
                if quarter is not None:
                    return year, quarter, f'{year_column}/{quarter_column}'
            return year, None, year_column

        for date_column in date_columns:
            year, quarter = BatteryChronologyClient._parse_date_like_value(row.get(date_column))
            if year is not None:
                return year, quarter, date_column

        for column_name in row.index:
            normalized_column = str(column_name).lower()
            if not any(token in normalized_column for token in ['quarter', 'year', 'date', 'delivery', 'registration', 'build', 'production']):
                continue
            year, quarter = BatteryChronologyClient._parse_year_quarter_value(row.get(column_name))
            if year is not None:
                return year, quarter, str(column_name)

        return None, None, None

    @staticmethod
    def _score_candidate(candidate: pd.Series, battery_text: str) -> int:
        """Score how well a chronology candidate matches a raw battery label."""
        if not battery_text:
            return 0

        score = 0
        battery_label = BatteryChronologyClient._normalize_text(candidate.get('battery_label'))
        battery_code = BatteryChronologyClient._normalize_text(candidate.get('battery_code'))
        chemistry = BatteryChronologyClient._normalize_text(candidate.get('chemistry'))
        plant = BatteryChronologyClient._normalize_text(candidate.get('plant'))

        if battery_label and battery_label in battery_text:
            score += 8

        label_number = BatteryChronologyClient._extract_capacity_number(candidate.get('battery_label'))
        if label_number and label_number in battery_text:
            score += 6
        if battery_code and battery_code in battery_text:
            score += 4
        if chemistry and chemistry in battery_text:
            score += 2
        if plant and plant in battery_text:
            score += 2

        return score

    @staticmethod
    def _extract_capacity_number(value: Any) -> Optional[str]:
        """Extract the pack capacity number from a battery label."""
        match = re.search(r'\d+(?:\.\d+)?', str(value or ''))
        return match.group(0) if match else None

    @staticmethod
    def _parse_year_value(value: Any) -> Optional[int]:
        """Parse a four-digit year from free-form text."""
        if value is None:
            return None
        if isinstance(value, int) and 2010 <= value <= 2100:
            return value

        text = str(value).strip()
        if not text:
            return None
        if text.isdigit() and len(text) == 4:
            year = int(text)
            return year if 2010 <= year <= 2100 else None

        match = re.search(r'(20\d{2})', text)
        return int(match.group(1)) if match else None

    @staticmethod
    def _parse_quarter_value(value: Any) -> Optional[int]:
        """Parse a quarter number from free-form text."""
        if value is None:
            return None
        if isinstance(value, int) and 1 <= value <= 4:
            return value

        text = str(value).strip().upper()
        if text in {'1', '2', '3', '4'}:
            return int(text)
        match = re.search(r'Q([1-4])', text)
        return int(match.group(1)) if match else None

    @staticmethod
    def _parse_date_like_value(value: Any) -> tuple[Optional[int], Optional[int]]:
        """Parse a date-like value into year and quarter."""
        if value is None:
            return None, None

        parsed = pd.to_datetime(value, errors='coerce', dayfirst=True)
        if pd.isna(parsed):
            return None, None
        return int(parsed.year), int(((parsed.month - 1) // 3) + 1)

    @staticmethod
    def _parse_year_quarter_value(value: Any) -> tuple[Optional[int], Optional[int]]:
        """Parse combined year-quarter text like Q2 2024."""
        year, quarter = BatteryChronologyClient._parse_date_like_value(value)
        if year is not None:
            return year, quarter

        text = str(value or '').strip().upper()
        if not text:
            return None, None
        return BatteryChronologyClient._parse_year_value(text), BatteryChronologyClient._parse_quarter_value(text)

    @staticmethod
    def _normalize_text(value: Any) -> str:
        """Normalize free-form text for matching."""
        if value is None:
            return ''
        return ' '.join(str(value).strip().lower().split())

    @staticmethod
    def _quarter_index(year: int, quarter: int) -> int:
        """Convert a year and quarter into a sortable integer."""
        return year * 4 + quarter - 1
