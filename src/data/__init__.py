"""Data access layer initialization."""
from importlib import import_module

__all__ = ['GoogleSheetsClient', 'PerformanceDataClient', 'BatteryChronologyClient', 'VehicleIntelligenceClient']

_CLASS_TO_MODULE = {
    'GoogleSheetsClient': 'src.data.google_sheets',
    'PerformanceDataClient': 'src.data.performance_data',
    'BatteryChronologyClient': 'src.data.battery_chronology',
    'VehicleIntelligenceClient': 'src.data.vehicle_intelligence',
}


def __getattr__(name):
    """Lazily import data clients so one optional dependency cannot break every page."""
    if name not in _CLASS_TO_MODULE:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')

    module = import_module(_CLASS_TO_MODULE[name])
    return getattr(module, name)
