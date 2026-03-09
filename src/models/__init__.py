"""Data models for Tesla Battery Analysis."""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

import pandas as pd


@dataclass
class BatteryData:
    """Model for battery analysis data."""

    dataframe: pd.DataFrame
    battery_pack_column: Optional[str] = None

    def filter_by_username(self, username: str) -> 'BatteryData':
        """Filter data by username.

        Args:
            username: Username to filter by.

        Returns:
            New BatteryData instance with filtered data.
        """
        if not username:
            return self

        filtered_df = self.dataframe[
            self.dataframe["Username"].str.contains(username, case=False, na=False)
        ]
        return BatteryData(filtered_df, self.battery_pack_column)

    def get_latest_entries(self, n: int = 3) -> pd.DataFrame:
        """Get the latest n entries from the data.

        Args:
            n: Number of latest entries to retrieve.

        Returns:
            DataFrame with latest entries in reverse order.
        """
        return self.dataframe.iloc[-n:][::-1]


@dataclass
class FilterCriteria:
    """Model for data filtering criteria."""

    tesla_models: List[str]
    versions: List[str]
    batteries: List[str]
    min_age: int
    max_age: int
    min_odo: int
    max_odo: int
    chronology_chemistries: List[str]
    chronology_plants: List[str]
    chronology_codes: List[str]
    hide_replaced_packs: bool = True
    daily_soc_min: Optional[float] = None
    daily_soc_max: Optional[float] = None
    dc_ratio_min: Optional[float] = None
    dc_ratio_max: Optional[float] = None


@dataclass
class PerformanceFolder:
    """Model for performance test folder metadata."""

    manufacturer: str
    model: str
    variant: str
    model_year: str
    battery: str
    front_motor: str
    rear_motor: str
    tuning: str
    acceleration_mode: str
    path: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation of the folder.
        """
        return {
            'manufacturer': self.manufacturer,
            'model': self.model,
            'variant': self.variant,
            'model_year': self.model_year,
            'battery': self.battery,
            'front_motor': self.front_motor,
            'rear_motor': self.rear_motor,
            'tuning': self.tuning,
            'acceleration_mode': self.acceleration_mode,
            'path': self.path
        }

    def get_legend_label(self) -> str:
        """Generate legend label for plotting.

        Returns:
            Formatted legend label string.
        """
        return (
            f"{self.model} {self.variant} {self.model_year} "
            f"{self.battery} {self.rear_motor} {self.acceleration_mode}"
        )


@dataclass
class PerformanceFileInfo:
    """Model for performance test file information."""

    path: str
    soc: int
    cell_temp_mid: int
    name: str
    folder: PerformanceFolder

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation of the file info.
        """
        return {
            'path': self.path,
            'SOC': self.soc,
            'Cell temp mid': self.cell_temp_mid,
            'name': self.name,
            'folder': self.folder.to_dict()
        }


@dataclass
class SOHProjection:
    """Model for State of Health (SOH) projection results."""

    battery_type: str
    years: Optional[str] = None
    kilometers: Optional[str] = None
    cycles: Optional[str] = None

    def get_display_text(self) -> str:
        """Generate display text for the projection.

        Returns:
            HTML formatted display text.
        """
        text = (
            f"<span style='color:orange; font-weight:bold;'>{self.battery_type}</span> "
            f"is expected to reach <span style='color:orange; font-weight:bold;'>70% SOH</span> after "
        )

        projections = [value for value in [self.years, self.kilometers, self.cycles] if value and value != 'unknown']
        if not projections:
            return (
                f"There is insufficient data to project the 70% SOH for the "
                f"<span style='color:orange; font-weight:bold;'>{self.battery_type}</span>."
            )

        highlighted = [f"<span style='color:orange; font-weight:bold;'>{value}</span>" for value in projections]
        return text + " or ".join(highlighted) + "."
