"""
VehicleIQ Data Pipeline Module
Parses, cleans, validates, and structures raw OBD-II sensor streams into production DataFrames.
"""

import logging
from typing import List, Dict, Any, Union
import pandas as pd
import numpy as np

logger = logging.getLogger("VehicleIQ.DataPipeline")

# Physical boundary constraints for OBD-II parameters
VALIDATION_RANGES = {
    "rpm": (0.0, 9000.0),
    "speed_kph": (0.0, 300.0),
    "coolant_temp_c": (-40.0, 150.0),
    "throttle_pos_pct": (0.0, 100.0),
    "short_fuel_trim_pct": (-100.0, 100.0),
    "long_fuel_trim_pct": (-100.0, 100.0),
    "battery_voltage": (5.0, 20.0),
    "maf_g_s": (0.0, 650.0),
}

DEFAULT_IMPUTE_VALUES = {
    "rpm": 750.0,
    "speed_kph": 0.0,
    "coolant_temp_c": 90.0,
    "throttle_pos_pct": 0.0,
    "short_fuel_trim_pct": 0.0,
    "long_fuel_trim_pct": 0.0,
    "battery_voltage": 13.8,
    "maf_g_s": 3.5,
}

class OBDDataPipeline:
    """Processes raw OBD-II sensor dictionaries into clean, structured DataFrames."""

    def __init__(self):
        pass

    def clean_batch(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Converts a list of raw sensor dicts into a validated and cleaned DataFrame.
        """
        if not raw_data:
            return pd.DataFrame()

        df = pd.DataFrame(raw_data)

        # 1. Standardize timestamp column
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        else:
            df["timestamp"] = pd.Timestamp.utcnow()

        # 2. Impute missing timestamps with current UTC
        df["timestamp"] = df["timestamp"].fillna(pd.Timestamp.utcnow())

        # Resolve the vehicle before imputing any sensor reading.
        if "vehicle_id" not in df.columns:
            df["vehicle_id"] = "VEHICLE_001"
        else:
            df["vehicle_id"] = df["vehicle_id"].fillna("VEHICLE_001")

        # Previous readings must be previous in time, not in input order.
        df = df.sort_values(by="timestamp", kind="mergesort").reset_index(drop=True)

        # 3. Numeric conversion and outlier clipping according to physical ranges
        for col, (min_val, max_val) in VALIDATION_RANGES.items():
            if col in df.columns:
                # Force numeric type
                df[col] = pd.to_numeric(df[col], errors="coerce")
                
                # Reuse only earlier readings from this vehicle within this batch.
                df[col] = (
                    df.groupby("vehicle_id", sort=False)[col]
                    .ffill()
                    .fillna(DEFAULT_IMPUTE_VALUES[col])
                )

                # Clip sensor readings within physically plausible bounds
                df[col] = df[col].clip(lower=min_val, upper=max_val)
            else:
                # Add missing column with default value
                df[col] = DEFAULT_IMPUTE_VALUES[col]

        # 4. Fill missing string metadata
        if "scenario" not in df.columns:
            df["scenario"] = "normal"
        else:
            df["scenario"] = df["scenario"].fillna("normal")

        logger.debug(f"Cleaned batch of {len(df)} OBD records.")
        return df

    def compute_summary_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates summary statistics across sensor readings in a window."""
        if df.empty:
            return {}

        return {
            "record_count": len(df),
            "start_time": df["timestamp"].min().isoformat(),
            "end_time": df["timestamp"].max().isoformat(),
            "avg_rpm": float(df["rpm"].mean()),
            "max_rpm": float(df["rpm"].max()),
            "avg_speed": float(df["speed_kph"].mean()),
            "max_speed": float(df["speed_kph"].max()),
            "avg_coolant_temp": float(df["coolant_temp_c"].mean()),
            "max_coolant_temp": float(df["coolant_temp_c"].max()),
            "min_battery_voltage": float(df["battery_voltage"].min()),
            "avg_battery_voltage": float(df["battery_voltage"].mean()),
        }
