"""
VehicleIQ Database Module
Provides ORM models and database operations using SQLAlchemy for SQLite and PostgreSQL.
"""

from datetime import datetime
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Index
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

logger = logging.getLogger("VehicleIQ.Database")

Base = declarative_base()

class OBDTelemetry(Base):
    """SQLAlchemy model storing timestamped OBD-II telemetry records."""
    __tablename__ = "obd_telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    vehicle_id = Column(String(50), default="VEHICLE_001", nullable=False, index=True)
    
    # Core OBD-II PIDs
    rpm = Column(Float, nullable=True)                  # Engine RPM (0-8000)
    speed_kph = Column(Float, nullable=True)            # Vehicle Speed in km/h (0-250)
    coolant_temp_c = Column(Float, nullable=True)       # Engine Coolant Temp in °C (-40 to 150)
    throttle_pos_pct = Column(Float, nullable=True)     # Throttle Position % (0-100)
    short_fuel_trim_pct = Column(Float, nullable=True) # Short Term Fuel Trim % (-100 to +100)
    long_fuel_trim_pct = Column(Float, nullable=True)  # Long Term Fuel Trim % (-100 to +100)
    battery_voltage = Column(Float, nullable=True)      # Battery Control Module Voltage (8-16V)
    maf_g_s = Column(Float, nullable=True)              # Mass Air Flow in g/s (0-655 g/s)
    
    # Metadata scenario indicator
    scenario = Column(String(50), default="normal", nullable=True)

    __table_args__ = (
        Index("idx_vehicle_time", "vehicle_id", "timestamp"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "vehicle_id": self.vehicle_id,
            "rpm": self.rpm,
            "speed_kph": self.speed_kph,
            "coolant_temp_c": self.coolant_temp_c,
            "throttle_pos_pct": self.throttle_pos_pct,
            "short_fuel_trim_pct": self.short_fuel_trim_pct,
            "long_fuel_trim_pct": self.long_fuel_trim_pct,
            "battery_voltage": self.battery_voltage,
            "maf_g_s": self.maf_g_s,
            "scenario": self.scenario,
        }

# Global DB Engine & Session factory
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create database tables if they do not exist."""
    logger.info(f"Initializing database tables at: {settings.DATABASE_URL}")
    Base.metadata.create_all(bind=engine)

def save_telemetry_df(df: pd.DataFrame) -> int:
    """
    Saves a cleaned pandas DataFrame of telemetry into the database.
    Returns the number of inserted records.
    """
    if df.empty:
        return 0

    session = SessionLocal()
    try:
        records = []
        for _, row in df.iterrows():
            # Handle timestamp parsing
            ts = row.get("timestamp")
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            elif pd.isna(ts) or ts is None:
                ts = datetime.utcnow()

            record = OBDTelemetry(
                timestamp=ts,
                vehicle_id=str(row.get("vehicle_id", "VEHICLE_001")),
                rpm=float(row["rpm"]) if pd.notna(row.get("rpm")) else None,
                speed_kph=float(row["speed_kph"]) if pd.notna(row.get("speed_kph")) else None,
                coolant_temp_c=float(row["coolant_temp_c"]) if pd.notna(row.get("coolant_temp_c")) else None,
                throttle_pos_pct=float(row["throttle_pos_pct"]) if pd.notna(row.get("throttle_pos_pct")) else None,
                short_fuel_trim_pct=float(row["short_fuel_trim_pct"]) if pd.notna(row.get("short_fuel_trim_pct")) else None,
                long_fuel_trim_pct=float(row["long_fuel_trim_pct"]) if pd.notna(row.get("long_fuel_trim_pct")) else None,
                battery_voltage=float(row["battery_voltage"]) if pd.notna(row.get("battery_voltage")) else None,
                maf_g_s=float(row["maf_g_s"]) if pd.notna(row.get("maf_g_s")) else None,
                scenario=str(row.get("scenario", "normal")),
            )
            records.append(record)

        session.bulk_save_objects(records)
        session.commit()
        logger.info(f"Successfully saved {len(records)} telemetry records to DB.")
        return len(records)
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save telemetry records to DB: {e}")
        raise e
    finally:
        session.close()

def get_recent_telemetry(limit: int = 100, vehicle_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve recent records, optionally restricted to one vehicle."""
    session = SessionLocal()
    try:
        query = session.query(OBDTelemetry)
        if vehicle_id is not None:
            query = query.filter(OBDTelemetry.vehicle_id == vehicle_id)
        query = query.order_by(OBDTelemetry.timestamp.desc(), OBDTelemetry.id.desc()).limit(limit)
        return [record.to_dict() for record in query.all()]
    finally:
        session.close()

